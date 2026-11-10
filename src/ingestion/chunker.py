"""
src/ingestion/chunker.py
------------------------
TextChunker — splits a document's raw text into overlapping sentence-boundary
windows ready for claim extraction.

Strategy (matches Elicit / Consensus pipeline design)
------------------------------------------------------
  1. Sentence-split on `.`, `?`, `!` followed by whitespace or end-of-string.
  2. Accumulate sentences into windows of ≤ `max_tokens` words.
  3. Slide forward by `stride` sentences (overlap = window - stride sentences).
  4. Filter chunks shorter than `min_chars`.

This is intentionally simple and dependency-free — no spaCy required.
The sentence splitter handles the 95% case for academic prose.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .parser import ParsedDocument

logger = logging.getLogger(__name__)

# Sentence boundary: period/question/exclamation followed by space or end,
# but not inside abbreviations like "Fig." "et al." "e.g." "i.e."
_ABBREV = re.compile(
    r"(?<!\bFig)(?<!\bet al)(?<!\be\.g)(?<!\bi\.e)(?<!\bDr)(?<!\bMr)(?<!\bMs)"
    r"(?<!\bProf)(?<!\bvs)(?<!\bapprox)(?<!\bref)"
    r"[.?!](?=\s+[A-Z]|\s*$)"
)


@dataclass
class TextChunk:
    """A window of text from the source document."""
    chunk_id: str
    text: str
    sentence_start: int   # index of first sentence in this chunk
    sentence_end: int     # index of last sentence (exclusive)
    document_id: str = ""
    char_start: int = 0
    char_end: int = 0
    page_start: int | None = None
    page_end: int | None = None


class TextChunker:
    """
    Sliding-window chunker with sentence-boundary awareness.

    Parameters
    ----------
    max_words : int
        Approximate maximum words per chunk (default 200 ≈ 512 tokens).
    stride_sentences : int
        Number of sentences to advance between consecutive windows.
        Overlap = (window_sentences - stride_sentences) sentences.
    min_chars : int
        Chunks shorter than this are discarded.
    """

    def __init__(
        self,
        max_words: int = 200,
        stride_sentences: int = 3,
        min_chars: int = 60,
    ):
        self.max_words = max_words
        self.stride_sentences = stride_sentences
        self.min_chars = min_chars

    def chunk(
        self,
        text: str,
        document_id: str = "",
        page_ranges: list[tuple[int, int, int]] | None = None,
    ) -> list[TextChunk]:
        """Split text into chunks and attach stable location metadata.

        ``page_ranges`` contains ``(char_start, char_end, page_number)`` tuples.
        Page numbers are optional because plain text and DOCX inputs do not
        reliably expose pagination.
        """
        sentences = self._split_sentences(text)
        if not sentences:
            return []

        sentence_spans = self._locate_sentences(text, sentences)

        chunks: list[TextChunk] = []
        chunk_idx = 0
        i = 0

        while i < len(sentences):
            window: list[str] = []
            word_count = 0
            j = i

            while j < len(sentences):
                sent = sentences[j]
                sent_words = len(sent.split())
                if window and (word_count + sent_words) > self.max_words:
                    break
                window.append(sent)
                word_count += sent_words
                j += 1

            chunk_text = " ".join(window).strip()
            if len(chunk_text) >= self.min_chars:
                char_start = sentence_spans[i][0]
                char_end = sentence_spans[j - 1][1]
                page_start, page_end = self._pages_for_span(
                    char_start, char_end, page_ranges
                )
                prefix = f"{document_id}:" if document_id else ""
                chunks.append(TextChunk(
                    chunk_id=f"{prefix}chunk_{chunk_idx}",
                    text=chunk_text,
                    sentence_start=i,
                    sentence_end=j,
                    document_id=document_id,
                    char_start=char_start,
                    char_end=char_end,
                    page_start=page_start,
                    page_end=page_end,
                ))
                chunk_idx += 1

            # Slide forward; if stride would exceed window size, just move by 1
            advance = min(self.stride_sentences, max(1, j - i))
            i += advance

        logger.debug("TextChunker: %d sentences → %d chunks", len(sentences), len(chunks))
        return chunks

    def chunk_document(self, document: "ParsedDocument") -> list[TextChunk]:
        """Chunk a ParsedDocument and carry through its document/page metadata."""
        page_ranges = None
        if document.pages:
            page_ranges = []
            cursor = 0
            for page_number, page_text in enumerate(document.pages, start=1):
                start = document.text.find(page_text, cursor) if page_text else cursor
                if start < 0:
                    start = cursor
                end = start + len(page_text)
                page_ranges.append((start, end, page_number))
                cursor = end + 2  # ParsedDocument joins pages with two newlines.
        return self.chunk(
            document.text,
            document_id=document.document_id,
            page_ranges=page_ranges,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _split_sentences(self, text: str) -> list[str]:
        """
        Split text into sentences using a regex that respects common
        academic abbreviations.
        """
        # Replace sentence boundaries with a separator
        separated = _ABBREV.sub(lambda m: m.group(0) + "\x00", text)
        raw = [s.strip() for s in separated.split("\x00")]
        # Secondary split on newlines that act as paragraph boundaries
        sentences: list[str] = []
        for part in raw:
            # Split on double-newlines as natural sentence boundaries
            sub_parts = re.split(r"\n{2,}", part)
            for sp in sub_parts:
                cleaned = sp.replace("\n", " ").strip()
                if len(cleaned) >= 15:
                    sentences.append(cleaned)
        return sentences

    @staticmethod
    def _locate_sentences(text: str, sentences: list[str]) -> list[tuple[int, int]]:
        """Locate normalized sentence text in the original input in order."""
        spans: list[tuple[int, int]] = []
        cursor = 0
        for sentence in sentences:
            compact = " ".join(sentence.split())
            normalized_tail = " ".join(text[cursor:].split())
            relative = normalized_tail.find(compact)
            if relative >= 0:
                # Convert the normalized search back to a conservative source
                # span. The end is exact for normal prose and still monotonic
                # when line breaks were normalized.
                start = cursor + relative
                end = min(len(text), start + len(sentence))
            else:
                start = cursor
                end = min(len(text), start + len(sentence))
            spans.append((start, end))
            cursor = max(end, cursor + 1)
        return spans

    @staticmethod
    def _pages_for_span(
        char_start: int,
        char_end: int,
        page_ranges: list[tuple[int, int, int]] | None,
    ) -> tuple[int | None, int | None]:
        if not page_ranges:
            return None, None
        pages = [
            page for start, end, page in page_ranges
            if char_end > start and char_start < end
        ]
        return (min(pages), max(pages)) if pages else (None, None)
