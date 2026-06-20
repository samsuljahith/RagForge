"""
KnowledgeBase — the main object most users will touch.

Ties together the full pipeline end-to-end:
    sources → parse → chunk → embed → store + BM25 index → retrieve

Keep its API small and obvious: build() to index, query() to retrieve.
Everything is persisted to disk so a KnowledgeBase survives restarts.

Usage:
    from ragforge.pipeline import KnowledgeBase

    kb = KnowledgeBase.build(
        name="my-kb",
        sources=["docs/", "faq.md"],
        embedder="default",
        chunk_strategy="structure",
    )

    results = kb.query("How do refunds work?", top_k=5, mode="hybrid")
    for chunk, score in results:
        print(f"  [{score:.4f}] {chunk.text[:80]}...")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ragforge.core.models import Chunk
from ragforge.core.registry import get
from ragforge.parsing import parse_file
from ragforge.chunking import chunk_document
from ragforge.pipeline.embeddings import Embedder, DefaultEmbedder
from ragforge.pipeline.store import InMemoryStore, VectorStore
from ragforge.pipeline.bm25 import BM25Index
from ragforge.pipeline.retriever import Retriever, RetrievalMode

# Default persistence directory
_KB_DIR = Path.home() / ".ragforge" / "knowledge_bases"


def _resolve_embedder(name_or_instance: str | Embedder) -> Embedder:
    """Resolve an embedder by registry name or pass through an instance."""
    if isinstance(name_or_instance, Embedder):
        return name_or_instance
    try:
        cls = get("embedder", name_or_instance)
        return cls()
    except KeyError:
        return DefaultEmbedder()


class KnowledgeBase:
    """
    End-to-end RAG knowledge base: build from sources, query with hybrid search.

    This is the orchestrator that most users interact with. It manages:
      - Parsing source files into Documents
      - Chunking Documents into Chunks
      - Embedding and storing Chunks in a vector store
      - Building a BM25 keyword index for hybrid search
      - Persisting everything to disk
      - Querying with the Retriever (dense / bm25 / hybrid + reranking)
    """

    def __init__(
        self,
        name: str,
        embedder: Embedder,
        store: VectorStore,
        bm25: BM25Index,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.embedder = embedder
        self.store = store
        self.bm25 = bm25
        self.metadata = metadata or {}
        self._retriever = Retriever(embedder=embedder, store=store, bm25=bm25)

    # ------------------------------------------------------------------
    # Build (class method — the primary constructor)
    # ------------------------------------------------------------------

    @classmethod
    def build(
        cls,
        name: str,
        sources: list[str],
        embedder: str | Embedder = "default",
        chunk_strategy: str = "structure",
        chunk_options: dict[str, Any] | None = None,
        store: VectorStore | None = None,
        persist: bool = True,
    ) -> "KnowledgeBase":
        """
        Build a knowledge base from source files or directories.

        Parses → chunks → embeds → stores. Persists to disk by default.

        Args:
            name: Unique name for this knowledge base (used for persistence).
            sources: File paths or directories to index. Directories are walked
                     recursively; unsupported files are skipped silently.
            embedder: Embedder instance or registry name (e.g. "default",
                      "sentence-transformers", "openai").
            chunk_strategy: Chunking strategy name ("structure" or "fixed").
            chunk_options: Options passed to the chunker (e.g. {"max_tokens": 384}).
            store: A VectorStore instance. Defaults to InMemoryStore.
            persist: Whether to save the built KB to disk (default True).

        Returns:
            A ready-to-query KnowledgeBase instance.
        """
        chunk_options = chunk_options or {}
        emb = _resolve_embedder(embedder)
        vs = store or InMemoryStore()
        bm25 = BM25Index()

        all_chunks: list[Chunk] = []
        num_documents = 0

        for source in sources:
            p = Path(source)
            if p.is_dir():
                files = sorted(
                    f for f in p.rglob("*") if f.is_file() and not f.name.startswith(".")
                )
            else:
                files = [p]

            for file_path in files:
                try:
                    doc = parse_file(str(file_path))
                    chunks = chunk_document(doc, strategy=chunk_strategy, **chunk_options)
                    all_chunks.extend(chunks)
                    num_documents += 1
                except (ValueError, ImportError, OSError):
                    # Skip files we can't parse
                    continue

        # Embed and store
        if all_chunks:
            texts = [c.text for c in all_chunks]
            vectors = emb.encode(texts)
            vs.add(all_chunks, vectors)
            bm25.add(all_chunks)

        metadata = {
            "name": name,
            "embedder_name": emb.name,
            "embedder_dim": emb.dimension,
            "chunk_strategy": chunk_strategy,
            "chunk_options": chunk_options,
            "num_documents": num_documents,
            "num_chunks": len(all_chunks),
        }

        kb = cls(name=name, embedder=emb, store=vs, bm25=bm25, metadata=metadata)

        if persist:
            kb.save()

        return kb

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(
        self,
        question: str,
        top_k: int = 5,
        mode: RetrievalMode = "hybrid",
        rerank: bool = False,
    ) -> list[tuple[Chunk, float]]:
        """
        Query the knowledge base and retrieve relevant chunks.

        Args:
            question: The question or search query.
            top_k: Number of results to return.
            mode: Search mode — "dense", "bm25", or "hybrid" (default).
            rerank: Whether to apply cross-encoder reranking (requires
                    sentence-transformers; degrades gracefully if missing).

        Returns:
            List of (chunk, score) pairs, sorted by descending relevance.
        """
        return self._retriever.search(
            query=question,
            top_k=top_k,
            mode=mode,
            rerank=rerank,
        )

    def query_traced(
        self,
        question: str,
        top_k: int = 5,
        mode: RetrievalMode = "hybrid",
        rerank: bool = False,
    ) -> tuple[list[tuple[Chunk, float]], str]:
        """
        Query with tracing — same as query() but records a structured trace.

        Returns:
            Tuple of (results, run_id) where run_id links to the stored trace.
        """
        from ragforge.tracing import Tracer

        tracer = Tracer()
        with tracer.trace(query=question, knowledge=self.name, mode=mode, top_k=top_k) as t:
            t.step("retrieval", mode=mode, top_k=top_k, rerank=rerank)
            results = self._retriever.search(
                query=question, top_k=top_k, mode=mode, rerank=rerank,
            )
            chunks_data = [
                {"id": c.id, "text": c.text[:200], "score": round(s, 4), "section": c.metadata.get("section", "")}
                for c, s in results
            ]
            t.step("retrieval_done", num_chunks=len(results), chunks=chunks_data)

        return results, t.run_id

    # ------------------------------------------------------------------
    # Answer (retrieve + generate grounded answer)
    # ------------------------------------------------------------------

    def answer(
        self,
        question: str,
        top_k: int = 5,
        mode: RetrievalMode = "hybrid",
        rerank: bool = False,
        llm: str = "ollama",
        llm_opts: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve relevant chunks AND generate a grounded answer with sources.

        This is the full RAG loop: question → retrieve → generate → answer + sources.
        The LLM is instructed to answer ONLY from retrieved context and to refuse
        if the context doesn't contain the answer.

        Args:
            question: The question to answer.
            top_k: Number of chunks to retrieve for context.
            mode: Retrieval mode — "dense", "bm25", or "hybrid".
            rerank: Whether to apply cross-encoder reranking.
            llm: LLM provider name — "openai", "anthropic", or "ollama".
            llm_opts: Options passed to the LLM provider constructor (e.g. model="gpt-4o").

        Returns:
            dict with:
                answer: The generated answer text.
                sources: List of chunks used as context (with scores and metadata).
                question: The original question.
                mode: Retrieval mode used.
                llm_name: Name/model of the LLM that generated the answer.
        """
        from ragforge.pipeline.generation import get_llm, build_grounded_prompt

        llm_opts = llm_opts or {}

        # Step 1: Retrieve relevant chunks
        results = self.query(question=question, top_k=top_k, mode=mode, rerank=rerank)

        # Step 2: Format chunks for the prompt
        sources = [
            {
                "id": chunk.id,
                "text": chunk.text,
                "doc_id": chunk.doc_id,
                "index": chunk.index,
                "metadata": chunk.metadata,
                "score": round(score, 4),
            }
            for chunk, score in results
        ]

        # Step 3: Build grounded prompt
        prompt = build_grounded_prompt(question, sources)

        # Step 4: Generate answer
        provider = get_llm(llm, **llm_opts)
        answer_text = provider.generate(prompt)

        return {
            "answer": answer_text,
            "sources": sources,
            "question": question,
            "mode": mode,
            "llm_name": provider.name,
        }

    def answer_traced(
        self,
        question: str,
        top_k: int = 5,
        mode: RetrievalMode = "hybrid",
        rerank: bool = False,
        llm: str = "ollama",
        llm_opts: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        answer() with full tracing — records retrieval, prompt, and response steps.

        Returns the same dict as answer() but with an added 'run_id' field
        linking to the stored trace for observability.
        """
        from ragforge.pipeline.generation import get_llm, build_grounded_prompt
        from ragforge.tracing import Tracer

        llm_opts = llm_opts or {}
        tracer = Tracer()

        with tracer.trace(query=question, knowledge=self.name, mode=mode, top_k=top_k, llm=llm) as t:
            # Step 1: Retrieval
            t.step("retrieval", mode=mode, top_k=top_k, rerank=rerank)
            results = self.query(question=question, top_k=top_k, mode=mode, rerank=rerank)

            sources = [
                {
                    "id": chunk.id,
                    "text": chunk.text,
                    "doc_id": chunk.doc_id,
                    "index": chunk.index,
                    "metadata": chunk.metadata,
                    "score": round(score, 4),
                }
                for chunk, score in results
            ]
            t.step("retrieval_done", num_chunks=len(results),
                   chunks=[{"id": s["id"], "text": s["text"][:200], "score": s["score"]} for s in sources])

            # Step 2: Build prompt
            prompt = build_grounded_prompt(question, sources)
            t.step("prompt_built", char_count=len(prompt), prompt_preview=prompt[:500])

            # Step 3: LLM generation
            t.step("generation", llm=llm, model=llm_opts.get("model", "default"))
            provider = get_llm(llm, **llm_opts)
            answer_text = provider.generate(prompt)
            t.step("generation_done", char_count=len(answer_text), answer_preview=answer_text[:500])

        return {
            "answer": answer_text,
            "sources": sources,
            "question": question,
            "mode": mode,
            "llm_name": provider.name,
            "run_id": t.run_id,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, base_dir: str | Path | None = None) -> Path:
        """
        Persist the knowledge base to disk.

        Saves the vector store, BM25 index, and metadata as separate files
        inside a directory named after the KB.

        Args:
            base_dir: Parent directory. Defaults to ~/.ragforge/knowledge_bases/

        Returns:
            Path to the KB directory.
        """
        base = Path(base_dir) if base_dir else _KB_DIR
        kb_path = base / self.name
        kb_path.mkdir(parents=True, exist_ok=True)

        self.store.save(kb_path / "vectors.json")
        self.bm25.save(kb_path / "bm25.json")
        (kb_path / "meta.json").write_text(json.dumps(self.metadata), encoding="utf-8")

        return kb_path

    @classmethod
    def load(cls, name: str, base_dir: str | Path | None = None) -> "KnowledgeBase":
        """
        Load a persisted knowledge base from disk.

        Args:
            name: Name of the knowledge base (directory name).
            base_dir: Parent directory. Defaults to ~/.ragforge/knowledge_bases/

        Returns:
            A ready-to-query KnowledgeBase instance.

        Raises:
            FileNotFoundError: If the KB directory or required files don't exist.
        """
        base = Path(base_dir) if base_dir else _KB_DIR
        kb_path = base / name

        if not kb_path.exists():
            raise FileNotFoundError(f"Knowledge base '{name}' not found at {kb_path}")

        # Load metadata
        meta_path = kb_path / "meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"Metadata not found for knowledge base '{name}'")
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))

        # Load vector store
        store = InMemoryStore.load(kb_path / "vectors.json")

        # Load BM25 index
        bm25_path = kb_path / "bm25.json"
        if bm25_path.exists():
            bm25 = BM25Index.load(bm25_path)
        else:
            # Rebuild BM25 from stored chunks (backward compat with old KBs)
            bm25 = BM25Index()
            bm25.add(store.chunks)

        # Resolve embedder
        embedder_name = metadata.get("embedder_name", "default")
        # For loading, we only need the embedder for query-time encoding
        # Use the same embedder that was used to build
        emb = _resolve_embedder(embedder_name)

        return cls(name=name, embedder=emb, store=store, bm25=bm25, metadata=metadata)

    @classmethod
    def exists(cls, name: str, base_dir: str | Path | None = None) -> bool:
        """Check if a knowledge base exists on disk."""
        base = Path(base_dir) if base_dir else _KB_DIR
        return (base / name / "meta.json").exists()

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def num_chunks(self) -> int:
        """Number of chunks in the knowledge base."""
        return self.store.count()

    @property
    def num_documents(self) -> int:
        """Number of source documents indexed (from metadata)."""
        return self.metadata.get("num_documents", 0)

    def __repr__(self) -> str:
        return (
            f"KnowledgeBase(name={self.name!r}, "
            f"chunks={self.num_chunks}, "
            f"embedder={self.embedder.name!r})"
        )


# ---------------------------------------------------------------------------
# Module-level convenience functions (for backward compatibility with the API/CLI)
# ---------------------------------------------------------------------------


def build_knowledge_base(
    name: str,
    sources: list[str],
    embedding_model: str = "default",
    chunk_strategy: str = "structure",
    chunk_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a knowledge base (functional interface for API/CLI).

    This wraps KnowledgeBase.build() and returns a plain dict suitable for
    JSON serialization in API responses.
    """
    kb = KnowledgeBase.build(
        name=name,
        sources=sources,
        embedder=embedding_model,
        chunk_strategy=chunk_strategy,
        chunk_options=chunk_options,
    )
    return {
        "name": kb.name,
        "status": "built",
        "num_documents": kb.num_documents,
        "num_chunks": kb.num_chunks,
        "embedding_model": kb.embedder.name,
    }


def query_knowledge_base(
    knowledge: str,
    question: str,
    top_k: int = 5,
    mode: RetrievalMode = "hybrid",
    rerank: bool = False,
    generate: bool = False,
    llm: str | None = None,
    llm_opts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Query a knowledge base (functional interface for API/CLI).

    Loads the KB from disk and runs a query. If generate=True and an LLM
    is configured, also generates a grounded answer with sources.
    Returns a plain dict suitable for JSON serialization in API responses.
    """
    kb = KnowledgeBase.load(knowledge)

    # If generation requested, use the full answer() path
    if generate and llm:
        result = kb.answer(
            question=question,
            top_k=top_k,
            mode=mode,
            rerank=rerank,
            llm=llm,
            llm_opts=llm_opts or {},
        )
        return {
            "question": question,
            "knowledge": knowledge,
            "chunks": result["sources"],
            "answer": result["answer"],
            "llm": result["llm_name"],
        }

    # Otherwise, retrieval-only (existing behavior)
    results = kb.query(question=question, top_k=top_k, mode=mode, rerank=rerank)

    chunks_out = [
        {
            "id": chunk.id,
            "text": chunk.text,
            "doc_id": chunk.doc_id,
            "index": chunk.index,
            "metadata": chunk.metadata,
            "score": round(score, 4),
        }
        for chunk, score in results
    ]

    return {
        "question": question,
        "knowledge": knowledge,
        "chunks": chunks_out,
        "answer": None,
    }
