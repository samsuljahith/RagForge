"""
Migration engine: re-embed, validate, and swap embedding models.

Uses a shadow-index approach: build the new index alongside the old one,
gate the cutover with real retrieval metrics (recall@k, MRR, hit_rate)
against a golden dataset, and only swap if the new model actually beats
the old one on YOUR data — or `force=True` to override.

Hot-set-first: when a golden dataset is given, the chunks it references
(`relevant_chunk_ids` — the chunks real queries actually hit) are re-embedded
and gated FIRST, before paying to re-embed the rest of the corpus. If the
gate rejects the new model, the long tail of rarely-queried chunks never
gets re-embedded at all — that's the "cheap cutover."
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from ragforge.core.models import Chunk
from ragforge.core.registry import get
from ragforge.evaluation.evaluator import Evaluator
from ragforge.evaluation.golden import GoldenDataset
from ragforge.pipeline.bm25 import BM25Index
from ragforge.pipeline.embeddings import Embedder, DefaultEmbedder
from ragforge.pipeline.knowledge import KnowledgeBase
from ragforge.pipeline.store import InMemoryStore


_KB_DIR = Path.home() / ".ragforge" / "knowledge_bases"

# Pure retrieval metrics only — no LLM-judge metrics, so the gate never
# needs an LLM configured and stays fast/deterministic.
GATE_METRICS = ["recall_at_k", "mrr", "hit_rate"]


def _get_embedder(model_name: str) -> Embedder:
    """
    Get an embedding model by name.

    First tries `model_name` as a registered backend name (e.g. "default",
    "openai"). If that's not found, treats it as a sentence-transformers
    model id (e.g. "BAAI/bge-small-en-v1.5") so migrating between two
    specific HF models doesn't require pre-registering each one. Falls
    back to DefaultEmbedder if sentence-transformers isn't installed.
    """
    try:
        cls = get("embedder", model_name)
        return cls()
    except KeyError:
        try:
            from ragforge.pipeline.embeddings import SentenceTransformerEmbedder

            return SentenceTransformerEmbedder(model_name=model_name)
        except ImportError:
            return DefaultEmbedder()


def _encode_with_cache(
    embedder: Embedder,
    chunks: list[Chunk],
    cached_vectors: dict[str, list[float]] | None,
) -> list[list[float]]:
    """
    Encode `chunks` with `embedder`, reusing any vector already present in
    `cached_vectors` (keyed by chunk id) instead of recomputing it.

    Used to avoid re-embedding hot-set chunks that the decision gate already
    embedded with the same new model.
    """
    cached_vectors = cached_vectors or {}
    to_encode = [c for c in chunks if c.id not in cached_vectors]
    fresh = dict(zip(
        (c.id for c in to_encode),
        embedder.encode([c.text for c in to_encode]) if to_encode else [],
    ))
    return [cached_vectors[c.id] if c.id in cached_vectors else fresh[c.id] for c in chunks]


def _shadow_kb(name: str, chunks: list[Chunk], vectors: list[list[float]], embedder: Embedder) -> KnowledgeBase:
    """Build an in-memory, unpersisted KnowledgeBase over a chunk subset for evaluation."""
    store = InMemoryStore()
    if chunks:
        store.add(chunks, vectors)
    return KnowledgeBase(name=name, embedder=embedder, store=store, bm25=BM25Index())


def _run_gate(
    old_chunks: list[Chunk],
    old_vectors: list[list[float]],
    new_chunks: list[Chunk],
    new_vectors: list[list[float]],
    old_embedder: Embedder,
    new_embedder: Embedder,
    golden: GoldenDataset,
    top_k: int,
) -> dict[str, Any]:
    """
    Real A/B comparison (old model vs new model) on a golden set, using
    recall@k / MRR / hit_rate — dense-only, so the embedding model is what's
    actually being measured (BM25 is identical on both sides and would mask
    the difference).
    """
    old_kb = _shadow_kb("old_model", old_chunks, old_vectors, old_embedder)
    new_kb = _shadow_kb("new_model", new_chunks, new_vectors, new_embedder)

    comparison = Evaluator.compare(
        old_kb,
        new_kb,
        golden,
        metrics=GATE_METRICS,
        top_k=top_k,
        mode="dense",
        label_a="old_model",
        label_b="new_model",
    )

    return {
        "passed": comparison["winner"] != "old_model",
        "winner": comparison["winner"],
        "delta": comparison["delta"],
        "old_model_summary": comparison["report_a"]["summary"],
        "new_model_summary": comparison["report_b"]["summary"],
    }


def migrate_knowledge_base(
    knowledge: str,
    from_model: str,
    to_model: str,
    validate: bool = True,
    golden_path: str | Path | None = None,
    hot_set_first: bool = True,
    force: bool = False,
    top_k: int = 5,
    options: dict[str, Any] | None = None,
    cached_vectors: dict[str, list[float]] | None = None,
) -> dict[str, Any]:
    """
    Migrate a knowledge base from one embedding model to another.

    Strategy:
      1. Load the existing knowledge base and its chunks.
      2. If a golden dataset is given: re-embed the hot set (chunks the
         golden questions actually reference) first, and gate on real
         recall@k / MRR / hit_rate — old model vs new model.
      3. If the gate fails and `force` isn't set, stop here. Nothing is
         re-embedded beyond the hot set, and nothing is swapped.
      4. Otherwise, re-embed whatever's left (the cold chunks), swap the
         index (old becomes a backup), and report the gate results.

    Args:
        knowledge: Name of the knowledge base to migrate.
        from_model: Current embedding model name.
        to_model: Target embedding model name.
        validate: Whether to run the quality gate at all.
        golden_path: Path to a GoldenDataset (JSON/CSV). Required for a real
                     gate — without it, `validate` has nothing to check
                     against and the migration proceeds unguarded.
        hot_set_first: Re-embed+gate only the golden set's referenced chunks
                       before touching the rest of the corpus.
        force: Swap even if the gate rejects the new model.
        top_k: top_k used for gate retrieval metrics.
        options: Additional migration options (currently unused; reserved
                 for future backends).
        cached_vectors: Already-computed `to_model` embeddings, keyed by
                         chunk id (e.g. from a prior `run_decision_gate()`
                         call). Chunks present here are never re-encoded.
                         Caller is responsible for ensuring these vectors
                         were actually produced by `to_model`.

    Returns:
        dict with migration status, gate results (if run), and counts.
    """
    options = options or {}
    kb_path = _KB_DIR / knowledge

    if not kb_path.exists():
        raise FileNotFoundError(f"Knowledge base '{knowledge}' not found")

    store_path = kb_path / "vectors.json"
    if not store_path.exists():
        raise FileNotFoundError(f"Vector store not found for '{knowledge}'")

    old_store = InMemoryStore.load(store_path)
    chunks = old_store.chunks

    if not chunks:
        return {
            "knowledge": knowledge,
            "from_model": from_model,
            "to_model": to_model,
            "status": "nothing_to_migrate",
            "num_chunks_migrated": 0,
        }

    old_embedder = _get_embedder(from_model)
    new_embedder = _get_embedder(to_model)

    golden = GoldenDataset.load(golden_path) if golden_path else None

    gate: dict[str, Any] | None = None
    hot_chunks, cold_chunks = chunks, []

    if validate and golden and len(golden) > 0:
        chunk_ids = {c.id for c in chunks}
        hot_ids = {cid for item in golden for cid in item.relevant_chunk_ids} & chunk_ids

        if hot_set_first and hot_ids:
            hot_chunks = [c for c in chunks if c.id in hot_ids]
            cold_chunks = [c for c in chunks if c.id not in hot_ids]

        # Pay for re-embedding the hot set ONLY, then gate before going further.
        hot_new_vectors = _encode_with_cache(new_embedder, hot_chunks, cached_vectors)
        old_hot_chunks, old_hot_vectors = old_store.get_vectors({c.id for c in hot_chunks})

        gate = _run_gate(
            old_hot_chunks, old_hot_vectors,
            hot_chunks, hot_new_vectors,
            old_embedder, new_embedder,
            golden, top_k,
        )
        gate["hot_set_size"] = len(hot_chunks)
        gate["total_chunks"] = len(chunks)

        if not gate["passed"] and not force:
            return {
                "knowledge": knowledge,
                "from_model": from_model,
                "to_model": to_model,
                "status": "rejected_quality_gate",
                "gate": gate,
                "num_chunks_migrated": 0,
            }

        new_vectors_by_chunk = hot_new_vectors
    else:
        new_vectors_by_chunk = _encode_with_cache(new_embedder, hot_chunks, cached_vectors)

    # Gate passed (or forced, or no golden set at all) — re-embed whatever's left.
    cold_new_vectors = _encode_with_cache(new_embedder, cold_chunks, cached_vectors) if cold_chunks else []

    all_chunks = hot_chunks + cold_chunks
    all_new_vectors = new_vectors_by_chunk + cold_new_vectors

    new_store = InMemoryStore()
    new_store.add(all_chunks, all_new_vectors)

    # Backup old store, then swap.
    backup_path = kb_path / "vectors_backup.json"
    shutil.copy2(store_path, backup_path)
    new_store.save(store_path)

    meta_path = kb_path / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta["embedder_name"] = to_model
    meta["migrated_from"] = from_model
    meta["embedder_dim"] = new_embedder.dimension
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    return {
        "knowledge": knowledge,
        "from_model": from_model,
        "to_model": to_model,
        "status": "migrated",
        "gate": gate,
        "num_chunks_migrated": len(all_chunks),
    }


def migrate_with_gate(
    knowledge: str,
    from_model: str,
    to_model: str,
    golden_path: str | Path,
    primary_metric: str = "recall_at_k",
    threshold_margin: float = 0.0,
    top_k: int = 5,
    hot_set_first: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    """
    Run the decision gate FIRST, then migrate only if GO.

    This is the recommended entrypoint for safe migrations. It:
      1. Loads the KB and golden dataset
      2. Runs the decision gate (old vs new model on your queries)
      3. If NO_GO and force=False → aborts, returns the gate decision
      4. If GO (or force=True) → proceeds with full migration

    The gate uses the new public gate.py API (run_decision_gate) which
    provides a structured GateDecision with print_table() for clear output.

    Args:
        knowledge: Name of the knowledge base to migrate.
        from_model: Current embedding model name.
        to_model: Target embedding model name.
        golden_path: Path to golden dataset (JSON). Required for the gate.
        primary_metric: Metric that decides GO/NO_GO (default: recall_at_k).
        threshold_margin: Allowed regression on primary metric (0.0 = must not regress).
        top_k: top_k for gate retrieval evaluation.
        hot_set_first: Only embed/evaluate the hot set before deciding (cheaper).
        force: Proceed even if the gate says NO_GO.

    Returns:
        dict with: gate_decision (GateDecision.to_dict()), migration_status, counts.
    """
    from ragforge.migration.gate import run_decision_gate, GateDecision

    kb_path = _KB_DIR / knowledge
    if not kb_path.exists():
        raise FileNotFoundError(f"Knowledge base '{knowledge}' not found")

    store_path = kb_path / "vectors.json"
    if not store_path.exists():
        raise FileNotFoundError(f"Vector store not found for '{knowledge}'")

    old_store = InMemoryStore.load(store_path)
    chunks = old_store.chunks

    if not chunks:
        return {
            "status": "nothing_to_migrate",
            "gate_decision": None,
            "num_chunks_migrated": 0,
        }

    golden = GoldenDataset.load(golden_path)
    old_embedder = _get_embedder(from_model)
    new_embedder = _get_embedder(to_model)

    # Run the decision gate
    decision = run_decision_gate(
        chunks=chunks,
        old_embedder=old_embedder,
        new_embedder=new_embedder,
        golden=golden,
        primary_metric=primary_metric,
        threshold_margin=threshold_margin,
        top_k=top_k,
        hot_set_only=hot_set_first,
    )

    # Print the comparison table
    decision.print_table()

    # If NO_GO and not forced, abort
    if decision.recommendation == "NO_GO" and not force:
        return {
            "status": "rejected_by_gate",
            "gate_decision": decision.to_dict(),
            "num_chunks_migrated": 0,
            "knowledge": knowledge,
            "from_model": from_model,
            "to_model": to_model,
        }

    # Gate passed (or forced) — proceed with full migration, reusing whatever
    # new-model embeddings the gate already computed (the hot set, normally)
    # instead of paying to re-embed those same chunks a second time. Only
    # reuse the cache if it was actually produced by the model we're
    # migrating to.
    cached_vectors = (
        decision.new_model_vectors if decision.new_model_name == new_embedder.name else None
    )
    result = migrate_knowledge_base(
        knowledge=knowledge,
        from_model=from_model,
        to_model=to_model,
        validate=False,  # gate already validated
        golden_path=None,
        force=True,
        cached_vectors=cached_vectors,
    )
    result["gate_decision"] = decision.to_dict()
    return result
