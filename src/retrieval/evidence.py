"""Small, dependency-free passage retriever used by Mode 3.

This is deliberately lexical for Phase 2: it is deterministic, inspectable, and
gives the eval harness a retrieval baseline before embeddings are introduced.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.ingestion.chunker import TextChunk

_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,}")
_STOPWORDS = {
    "about", "after", "again", "also", "been", "being", "between", "from",
    "have", "into", "more", "only", "over", "that", "their", "there",
    "these", "they", "this", "those", "through", "using", "with", "would",
}


def _terms(text: str) -> set[str]:
    return {
        token.lower()
        for token in _TOKEN.findall(text)
        if token.lower() not in _STOPWORDS
    }


@dataclass(frozen=True)
class RetrievedPassage:
    chunk: TextChunk
    score: float
    matched_terms: tuple[str, ...]


class PassageRetriever:
    """Rank chunks by normalized lexical overlap with a claim."""

    def retrieve(
        self,
        claim: str,
        passages: list[TextChunk],
        top_k: int = 5,
    ) -> list[RetrievedPassage]:
        if top_k <= 0 or not passages:
            return []
        query_terms = _terms(claim)
        if not query_terms:
            return []

        scored: list[RetrievedPassage] = []
        for chunk in passages:
            passage_terms = _terms(chunk.text)
            matched = query_terms & passage_terms
            if not matched:
                continue
            overlap = len(matched) / len(query_terms)
            density = len(matched) / max(1, len(passage_terms))
            phrase_bonus = 0.15 if claim.lower().strip(" .?!") in chunk.text.lower() else 0.0
            score = min(1.0, (0.75 * overlap) + (0.25 * density) + phrase_bonus)
            scored.append(RetrievedPassage(
                chunk=chunk,
                score=round(score, 4),
                matched_terms=tuple(sorted(matched)),
            ))

        scored.sort(key=lambda item: (-item.score, item.chunk.chunk_id))
        return scored[:top_k]
