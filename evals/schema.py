"""
evals/schema.py
---------------
Data models for the evaluation harness.

Defines the JSONL schema for eval claims, predictions, metrics, and run configs.
All models use dataclasses for zero-dependency serialization.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Literal

Label = Literal["supported", "refuted", "unverifiable"]
Direction = Literal["supporting", "contradicting", "neutral"]


@dataclass
class GoldEvidence:
    """One piece of gold-standard evidence for an eval claim."""
    source_id: str
    source_title: str
    url: str = ""
    quote: str = ""
    location: dict = field(default_factory=dict)  # {page, char_start, char_end}
    direction: Direction = "supporting"


@dataclass
class EvalClaim:
    """One labeled claim in the eval dataset (one JSONL line)."""
    id: str
    domain: str
    document_id: str
    claim: str
    gold_label: Label
    gold_evidence: list[GoldEvidence] = field(default_factory=list)
    allowed_sources: list[str] = field(default_factory=list)
    notes: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict) -> EvalClaim:
        data = dict(d)
        evidence = [GoldEvidence(**e) for e in data.pop("gold_evidence", [])]
        return cls(**data, gold_evidence=evidence)


@dataclass
class Prediction:
    """Model prediction for one eval claim."""
    claim_id: str
    predicted_label: str  # SUPPORTED / REFUTED / UNVERIFIABLE
    confidence: float
    evidence_ids: list[str] = field(default_factory=list)
    evidence_directions: dict[str, str] = field(default_factory=dict)
    citation_statuses: dict[str, str] = field(default_factory=dict)
    fallback_used: bool = False
    error: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass
class EvalConfig:
    """Snapshot of the eval run configuration."""
    git_sha: str = ""
    branch: str = ""
    dataset: str = ""
    provider: str = "heuristic"
    model: str = "none"
    prompt_version: str = ""
    thresholds: dict = field(default_factory=dict)
    environment: dict = field(default_factory=dict)
    notes: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


@dataclass
class EvalRunSummary:
    """One-line summary appended to the eval index."""
    timestamp: str
    git_sha: str
    dataset: str
    provider: str
    accuracy: float
    f1_macro: float
    confidently_wrong_rate: float
    abstention_rate: float
    num_claims: int
    retrieval_recall_at_k: float | None = None
    evidence_direction_accuracy: float | None = None
    citation_link_resolution_rate: float | None = None
    notes: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


def load_eval_claims(path: str | Path) -> list[EvalClaim]:
    """Load eval claims from a JSONL file."""
    claims = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                claims.append(EvalClaim.from_dict(json.loads(line_str)))
    return claims
