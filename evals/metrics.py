"""
evals/metrics.py
----------------
Compute verification quality metrics from predictions against gold labels.

Reports: accuracy, per-class P/R/F1, confidently-wrong rate, abstention rate,
and retrieval recall when evidence labels exist.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, asdict
from typing import Sequence

from .schema import EvalClaim, Prediction

LABELS = ("supported", "refuted", "unverifiable")
_CONFIDENCE_THRESHOLD = 0.6


@dataclass
class ClassMetrics:
    label: str
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    support: int = 0


@dataclass
class EvalMetrics:
    accuracy: float = 0.0
    per_class: list[ClassMetrics] = field(default_factory=list)
    f1_macro: float = 0.0
    confidently_wrong_rate: float = 0.0
    abstention_rate: float = 0.0
    retrieval_recall_at_k: float | None = None
    retrieval_claims: int = 0
    num_claims: int = 0
    num_correct: int = 0
    num_confidently_wrong: int = 0
    num_abstained: int = 0
    label_distribution: dict[str, int] = field(default_factory=dict)
    predicted_distribution: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["per_class"] = [asdict(c) for c in self.per_class]
        return d


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def _class_prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = _safe_div(tp, tp + fp)
    r = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * p * r, p + r)
    return round(p, 4), round(r, 4), round(f1, 4)


def compute_metrics(
    claims: Sequence[EvalClaim],
    predictions: Sequence[Prediction],
    confidence_threshold: float = _CONFIDENCE_THRESHOLD,
) -> EvalMetrics:
    """Compute all eval metrics from gold claims and model predictions."""
    pred_map = {p.claim_id: p for p in predictions}
    n = len(claims)
    if n == 0:
        return EvalMetrics()

    correct = 0
    confidently_wrong = 0
    abstained = 0
    gold_counts: Counter[str] = Counter()
    pred_counts: Counter[str] = Counter()
    tp: dict[str, int] = {l: 0 for l in LABELS}
    fp: dict[str, int] = {l: 0 for l in LABELS}
    fn: dict[str, int] = {l: 0 for l in LABELS}

    for claim in claims:
        pred = pred_map.get(claim.id)
        gold = claim.gold_label.strip().lower()
        gold_counts[gold] += 1

        if pred is None:
            if gold in fn:
                fn[gold] += 1
            continue

        predicted = pred.predicted_label.strip().lower()
        pred_counts[predicted] += 1

        if predicted == "unverifiable":
            abstained += 1

        if predicted == gold:
            correct += 1
            if gold in tp:
                tp[gold] += 1
        else:
            if predicted in fp:
                fp[predicted] += 1
            if gold in fn:
                fn[gold] += 1
            if pred.confidence >= confidence_threshold:
                confidently_wrong += 1

    # Per-class metrics
    per_class = []
    f1_sum = 0.0
    for label in LABELS:
        p, r, f1 = _class_prf(tp[label], fp[label], fn[label])
        per_class.append(ClassMetrics(label=label, precision=p, recall=r, f1=f1, support=gold_counts[label]))
        f1_sum += f1

    # Retrieval recall (if any gold evidence exists). This is intentionally
    # computed from IDs supplied by the runner rather than from verdict text.
    # A future retriever can populate Prediction.evidence_ids without changing
    # the metric implementation.
    retrieval_recalls: list[float] = []
    for claim in claims:
        gold_ids = {e.source_id for e in claim.gold_evidence if e.source_id}
        if not gold_ids:
            continue
        pred = pred_map.get(claim.id)
        predicted_ids = set(pred.evidence_ids) if pred else set()
        retrieval_recalls.append(len(gold_ids & predicted_ids) / len(gold_ids))
    retrieval_recall = (
        round(sum(retrieval_recalls) / len(retrieval_recalls), 4)
        if retrieval_recalls else None
    )

    return EvalMetrics(
        accuracy=round(_safe_div(correct, n), 4),
        per_class=per_class,
        f1_macro=round(_safe_div(f1_sum, len(LABELS)), 4),
        confidently_wrong_rate=round(_safe_div(confidently_wrong, n), 4),
        abstention_rate=round(_safe_div(abstained, n), 4),
        retrieval_recall_at_k=retrieval_recall,
        retrieval_claims=len(retrieval_recalls),
        num_claims=n,
        num_correct=correct,
        num_confidently_wrong=confidently_wrong,
        num_abstained=abstained,
        label_distribution=dict(gold_counts),
        predicted_distribution=dict(pred_counts),
    )
