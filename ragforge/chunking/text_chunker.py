"""
Concrete chunkers.

- FixedChunker:      classic sliding window of ~N tokens with overlap. Simple, fast,
                     but can cut sentences/tables in half. The baseline everyone starts
                     with (and then complains about on Reddit).

- StructureChunker:  respects document structure. It splits on markdown headers and
                     paragraph boundaries, keeps code blocks and tables intact, and
                     records the section each chunk came from. This is the "fixed most
                     of it" approach practitioners recommend.

Both estimate size in tokens using the core's ~4-chars-per-token rule, so no tokenizer
dependency is required for the first version.
"""

from __future__ import annotations

import re

from ragforge.core.models import Chunk, Document, estimate_tokens
from ragforge.core.registry import register
from ragforge.chunking.base import Chunker


@register("chunker", "fixed")
class FixedChunker(Chunker):
    """
    Sliding-window chunker.

    chunk_tokens: target size of each chunk (in estimated tokens)
    overlap_tokens: how many tokens of the previous chunk to repeat at the start of the
                    next one (overlap helps an answer that straddles a boundary survive)
    """

    def __init__(self, chunk_tokens: int = 256, overlap_tokens: int = 32) -> None:
        if overlap_tokens >= chunk_tokens:
            raise ValueError("overlap_tokens must be smaller than chunk_tokens")
        self.chunk_tokens = chunk_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, document: Document) -> list[Chunk]:
        # work in words; convert token targets to word counts (~0.75 words per token)
        words = document.text.split()
        if not words:
            return []
        size = max(1, int(self.chunk_tokens * 0.75))
        step = max(1, size - int(self.overlap_tokens * 0.75))

        chunks: list[Chunk] = []
        for i in range(0, len(words), step):
            window = words[i : i + size]
            if not window:
                continue
            text = " ".join(window)
            chunks.append(self._make_chunk(text, document, len(chunks)))
            if i + size >= len(words):
                break
        return chunks


# Matches a markdown header line like "## Section title"
_HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)$")
# A fenced code block ```...```
_CODE_FENCE = "```"


@register("chunker", "structure")
class StructureChunker(Chunker):
    """
    Structure-aware chunker.

    Strategy:
      1. Walk the document line by line, tracking the current section (from markdown
         headers) so each chunk remembers where it came from.
      2. Never split inside a fenced code block or a markdown table — keep them whole.
      3. Group paragraphs under a section until adding the next paragraph would exceed
         max_tokens; then start a new chunk (still tagged with the same section).
      4. If a single block is larger than max_tokens on its own (e.g. a huge table),
         keep it as one oversized chunk rather than corrupting it by cutting.

    This directly targets the "broke my tables and code" and "embedding dilution"
    complaints: answers stay with their context and structured content stays intact.
    """

    def __init__(self, max_tokens: int = 384, min_tokens: int = 64) -> None:
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens

    def _split_blocks(self, text: str) -> list[tuple[str, str]]:
        """
        Break text into (section, block) pairs.
        A 'block' is a paragraph, a code fence, or a table — an atomic unit we won't cut.
        """
        lines = text.splitlines()
        blocks: list[tuple[str, str]] = []
        section = "(top)"
        buf: list[str] = []
        in_code = False

        def flush() -> None:
            nonlocal buf
            if buf and "".join(buf).strip():
                blocks.append((section, "\n".join(buf).strip()))
            buf = []

        for line in lines:
            stripped = line.strip()

            # toggle code-fence mode; never split inside a fence
            if stripped.startswith(_CODE_FENCE):
                buf.append(line)
                if in_code:
                    in_code = False
                    flush()
                else:
                    flush()  # close off prose before the code block
                    in_code = True
                continue
            if in_code:
                buf.append(line)
                continue

            # header => new section boundary
            m = _HEADER_RE.match(stripped)
            if m:
                flush()
                section = m.group(2).strip() or section
                continue

            # blank line => paragraph boundary
            if not stripped:
                flush()
                continue

            buf.append(line)

        flush()
        return blocks

    def chunk(self, document: Document) -> list[Chunk]:
        blocks = self._split_blocks(document.text)
        if not blocks:
            return []

        chunks: list[Chunk] = []
        cur_section = blocks[0][0]
        cur_text: list[str] = []
        cur_tokens = 0

        def emit() -> None:
            nonlocal cur_text, cur_tokens
            if cur_text:
                joined = "\n\n".join(cur_text)
                chunks.append(
                    self._make_chunk(joined, document, len(chunks), section=cur_section)
                )
            cur_text = []
            cur_tokens = 0

        for section, block in blocks:
            block_tokens = estimate_tokens(block)

            # section changed -> close current chunk so chunks don't mix sections
            if section != cur_section and cur_text:
                emit()
            cur_section = section

            # a single oversized block (e.g. big table/code): keep it whole, alone
            if block_tokens >= self.max_tokens:
                emit()
                chunks.append(
                    self._make_chunk(block, document, len(chunks),
                                     section=section, oversized=True)
                )
                continue

            # would overflow -> start a new chunk first
            if cur_tokens + block_tokens > self.max_tokens and cur_text:
                emit()

            cur_text.append(block)
            cur_tokens += block_tokens

        emit()
        return chunks


# --- convenience -----------------------------------------------------------------

def chunk_document(document: Document, strategy: str = "structure", **kwargs) -> list[Chunk]:
    """Chunk a Document with the named strategy ('fixed' or 'structure')."""
    from ragforge.core.registry import get

    chunker_cls = get("chunker", strategy)
    return chunker_cls(**kwargs).chunk(document)
