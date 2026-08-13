

from __future__ import annotations

import json
import logging
import os
import re
import textwrap
from typing import Optional

import requests

from .parser import ParsedDocument
from .chunker import TextChunker, TextChunk
from src.tree.state import Claim

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini REST (identical helper to nodes.py — kept local to avoid coupling)
# ---------------------------------------------------------------------------

_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent"
)


def _call_gemini(prompt: str, max_tokens: int = 512) -> Optional[str]:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key.startswith("your_"):
        return None
    try:
        resp = requests.post(
            f"{_GEMINI_URL}?key={api_key}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.2},
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as exc:
        logger.warning("Gemini call failed: %s", exc)
        return None


def _parse_json_list(text: str) -> list[str]:
    """Extract first JSON array of strings from LLM response."""
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        text = match.group(1)
    try:
        result = json.loads(text.strip())
        if isinstance(result, list):
            return [str(x) for x in result if isinstance(x, str) and len(x) > 10]
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# Heuristic claim detector
# ---------------------------------------------------------------------------

# Signals that a sentence is declarative and checkable
_QUANTITATIVE = re.compile(
    r"\b(\d+\.?\d*\s*%|\d+\s*(times|x|fold)|p\s*[<>=]\s*[\d.]+|"
    r"r\s*=\s*[\d.]+|accuracy|precision|recall|F1|BLEU|ROUGE|"
    r"outperform|surpass|exceed|improve|reduc|increas|decreas)\b",
    re.IGNORECASE,
)
_COMPARATIVE = re.compile(
    r"\b(more|less|better|worse|higher|lower|faster|slower|larger|smaller"
    r"|greater|fewer|compared|versus|vs\.?|than|while|whereas)\b",
    re.IGNORECASE,
)
_METHODOLOGY = re.compile(
    r"\b(we (show|demonstrate|find|observe|propose|introduce|present|report)|"
    r"our (model|method|approach|system|results?)|"
    r"this (paper|study|work|approach)|results? show|experiments? (show|demonstrate))\b",
    re.IGNORECASE,
)


def _is_checkable(sentence: str) -> bool:
    """Return True if the sentence looks like a verifiable factual claim."""
    if len(sentence) < 25:
        return False
    score = 0
    if _QUANTITATIVE.search(sentence):
        score += 2
    if _COMPARATIVE.search(sentence):
        score += 1
    if _METHODOLOGY.search(sentence):
        score += 1
    return score >= 2


def _heuristic_extract(chunk_text: str) -> list[str]:
    """Rule-based extraction: pick sentences that score as checkable."""
    # Simple sentence split on period + space + capital
    raw_sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", chunk_text)
    return [s.strip() for s in raw_sentences if _is_checkable(s)]


# ---------------------------------------------------------------------------
# Jaccard deduplication
# ---------------------------------------------------------------------------

def _jaccard(a: str, b: str) -> float:
    wa = set(a.lower().split())
    wb = set(b.lower().split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _deduplicate(claims: list[str], threshold: float = 0.65) -> list[str]:
    """Remove near-duplicate claims using Jaccard similarity."""
    unique: list[str] = []
    for candidate in claims:
        if all(_jaccard(candidate, kept) < threshold for kept in unique):
            unique.append(candidate)
    return unique


# ---------------------------------------------------------------------------
# DocumentClaimExtractor
# ---------------------------------------------------------------------------

class DocumentClaimExtractor:
    """
    Extract verifiable claims from a ParsedDocument.

    Parameters
    ----------
    max_claims_per_chunk : int
        Maximum LLM-extracted claims per text chunk (default 3).
    max_total_claims : int
        Hard cap on total claims returned (default 30).
    chunker : TextChunker | None
        Override default chunker for testing.
    """

    def __init__(
        self,
        max_claims_per_chunk: int = 3,
        max_total_claims: int = 30,
        chunker: Optional[TextChunker] = None,
    ):
        self.max_claims_per_chunk = max_claims_per_chunk
        self.max_total_claims = max_total_claims
        self.chunker = chunker or TextChunker()

    def extract(self, doc: ParsedDocument, topic: str = "") -> list[Claim]:
        """
        Parse the document into chunks, extract claims per chunk, deduplicate,
        and return list[Claim] ready for ResearchState.claims.

        Parameters
        ----------
        doc : ParsedDocument
            Output of DocumentParser.parse().
        topic : str
            Research topic — used as context in LLM prompts.
            Falls back to doc.title if empty.
        """
        if doc.is_empty:
            logger.warning("DocumentClaimExtractor: document is empty — no claims extracted")
            return []

        effective_topic = topic or doc.title or "the document"
        chunks = self.chunker.chunk(doc.text)
        logger.info(
            "DocumentClaimExtractor: '%s' → %d chunks",
            doc.title or doc.source_path,
            len(chunks),
        )

        raw_claims: list[str] = []
        for chunk in chunks:
            extracted = self._extract_from_chunk(chunk, effective_topic)
            raw_claims.extend(extracted)
            if len(raw_claims) >= self.max_total_claims * 2:
                break  # gather enough before dedup

        # Deduplicate then cap
        unique = _deduplicate(raw_claims)
        capped = unique[: self.max_total_claims]

        logger.info(
            "DocumentClaimExtractor: %d raw → %d unique → %d capped claims",
            len(raw_claims), len(unique), len(capped),
        )

        # Wrap in Claim dataclass (angle_id = "ingested" to distinguish from
        # graph-generated claims in Mode 1)
        return [
            Claim(
                claim_id=f"ingested_claim_{i}",
                angle_id="ingested",
                text=text.strip(),
                source_titles=[doc.title or doc.source_path],
            )
            for i, text in enumerate(capped)
        ]

    # ------------------------------------------------------------------
    # Internal — per-chunk extraction
    # ------------------------------------------------------------------

    def _extract_from_chunk(self, chunk: TextChunk, topic: str) -> list[str]:
        """Try Gemini then fall back to heuristic."""
        llm_result = self._llm_extract(chunk.text, topic)
        if llm_result:
            return llm_result

        return _heuristic_extract(chunk.text)

    def _llm_extract(self, chunk_text: str, topic: str) -> list[str]:
        prompt = textwrap.dedent(f"""\
            You are a research fact-checker. Extract {self.max_claims_per_chunk} short,
            verifiable factual claims from the passage below.

            Rules:
            - Each claim must be a single declarative sentence.
            - Include only specific, checkable statements (numbers, comparisons,
              method names, findings — not vague generalisations).
            - Do NOT paraphrase beyond what the text states.

            Topic context: {topic}

            Passage:
            {chunk_text[:1500]}

            Return ONLY valid JSON — a list of claim strings.
            Example: ["Model X achieves 94.2% accuracy on benchmark Y.",
                      "Training took 3 days on 8 A100 GPUs."]
        """)

        llm_text = _call_gemini(prompt, max_tokens=256)
        if not llm_text:
            return []
        return _parse_json_list(llm_text)[: self.max_claims_per_chunk]
