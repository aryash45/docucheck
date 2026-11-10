"""Evidence construction and direction classification for claim verification."""

from __future__ import annotations

import re

from src.retrieval.evidence import RetrievedPassage
from .state import PassageEvidence

_NEGATION = re.compile(
    r"\b(?:not|no|never|without|fails? to|unable to|contrary|however|refute|disagree)\b",
    re.IGNORECASE,
)


def classify_direction(claim: str, quote: str) -> str:
    """Classify a passage conservatively using lexical evidence only."""
    claim_terms = set(re.findall(r"[a-z0-9]{3,}", claim.lower()))
    quote_terms = set(re.findall(r"[a-z0-9]{3,}", quote.lower()))
    overlap = len(claim_terms & quote_terms)
    if overlap < 2:
        return "neutral"
    if _NEGATION.search(quote) and not _NEGATION.search(claim):
        return "contradicting"
    return "supporting"


def to_passage_evidence(
    claim: str,
    retrieved: list[RetrievedPassage],
) -> list[PassageEvidence]:
    """Convert retrieval results into stable, serializable evidence records."""
    evidence: list[PassageEvidence] = []
    for item in retrieved:
        chunk = item.chunk
        direction = classify_direction(claim, chunk.text)
        evidence.append(PassageEvidence(
            evidence_id=f"{chunk.chunk_id}:evidence",
            source_id=chunk.document_id or "document",
            source_title=chunk.document_id or "document",
            quote=chunk.text,
            direction=direction,
            score=item.score,
            chunk_id=chunk.chunk_id,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            char_start=chunk.char_start,
            char_end=chunk.char_end,
        ))
    return evidence
