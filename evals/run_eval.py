"""
evals/run_eval.py
-----------------
Eval runner: loads a claim dataset, runs each claim through the DocuCheck
heuristic (or LLM) verification path, computes metrics, and writes outputs.

Usage:
    python -m evals.run_eval --dataset evals/data/smoke.jsonl
    python -m evals.run_eval --dataset evals/data/smoke.jsonl --provider gemini
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals.schema import EvalClaim, EvalConfig, EvalRunSummary, Prediction, load_eval_claims
from evals.metrics import compute_metrics
from src.literature.fetcher import Paper
from src.tree.state import Claim, ResearchState
from src.tree.nodes import fact_checker_node

logger = logging.getLogger(__name__)


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL, text=True, timeout=5,
        ).strip()
    except Exception:
        return "unknown"


def _git_branch() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL, text=True, timeout=5,
        ).strip()
    except Exception:
        return "unknown"


def _build_mock_papers(claim: EvalClaim) -> list[Paper]:
    """Build Paper objects from the claim's gold evidence for retrieval context."""
    papers = []
    for ev in claim.gold_evidence:
        papers.append(Paper(
            paper_id=ev.source_id,
            title=ev.source_title,
            abstract=ev.quote or "",
            authors=[],
            year=0,
            citation_count=0,
            source="eval_gold",
            url=ev.url,
        ))
    return papers


def _run_single_claim(eval_claim: EvalClaim, provider: str) -> Prediction:
    """Run the DocuCheck verifier on a single eval claim and return a Prediction."""
    papers = _build_mock_papers(eval_claim)
    tree_claim = Claim(
        claim_id=eval_claim.id,
        angle_id="eval",
        text=eval_claim.claim,
        source_titles=[p.title for p in papers],
    )

    state = ResearchState(
        topic=eval_claim.domain,
        papers=papers,
        claims=[tree_claim],
    )

    # Force heuristic path if provider is not gemini
    had_key = "GEMINI_API_KEY" in os.environ
    original_key = os.environ.get("GEMINI_API_KEY")
    if provider != "gemini":
        os.environ["GEMINI_API_KEY"] = "your_dummy"

    try:
        state = fact_checker_node(state)
    finally:
        if provider != "gemini":
            if had_key and original_key is not None:
                os.environ["GEMINI_API_KEY"] = original_key
            else:
                os.environ.pop("GEMINI_API_KEY", None)

    if state.verifications:
        v = state.verifications[0]
        return Prediction(
            claim_id=eval_claim.id,
            predicted_label=v.verdict,
            confidence=v.confidence,
            evidence_ids=[],
            fallback_used=(provider != "gemini"),
        )

    return Prediction(
        claim_id=eval_claim.id,
        predicted_label="UNVERIFIABLE",
        confidence=0.0,
        fallback_used=True,
        error="No verification produced",
    )


def run_eval(dataset_path: str, provider: str = "heuristic", notes: str = "") -> Path:
    """Run the full eval: load claims, predict, compute metrics, write outputs."""
    claims = load_eval_claims(dataset_path)
    logger.info("Loaded %d eval claims from %s", len(claims), dataset_path)

    # Run predictions
    predictions: list[Prediction] = []
    for claim in claims:
        t0 = time.monotonic()
        pred = _run_single_claim(claim, provider)
        elapsed = round((time.monotonic() - t0) * 1000)
        predictions.append(pred)
        logger.info(
            "  %s: gold=%s pred=%s conf=%.2f (%dms)",
            claim.id, claim.gold_label, pred.predicted_label, pred.confidence, elapsed,
        )

    # Compute metrics
    metrics = compute_metrics(claims, predictions)
    logger.info(
        "Metrics: accuracy=%.2f%% f1_macro=%.4f conf_wrong=%.2f%% abstention=%.2f%%",
        metrics.accuracy * 100, metrics.f1_macro,
        metrics.confidently_wrong_rate * 100, metrics.abstention_rate * 100,
    )

    # Write outputs
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path("outputs/evals") / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    git_sha = _git_sha()
    config = EvalConfig(
        git_sha=git_sha,
        branch=_git_branch(),
        dataset=Path(dataset_path).name,
        provider=provider,
        model="gemini-1.5-flash" if provider == "gemini" else "none",
        notes=notes,
    )

    (out_dir / "config.json").write_text(config.to_json(), encoding="utf-8")
    (out_dir / "metrics.json").write_text(
        json.dumps(metrics.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    with (out_dir / "predictions.jsonl").open("w", encoding="utf-8") as f:
        for p in predictions:
            f.write(p.to_json() + "\n")

    # Append to index
    index_path = Path("outputs/evals/index.jsonl")
    index_path.parent.mkdir(parents=True, exist_ok=True)
    summary = EvalRunSummary(
        timestamp=timestamp,
        git_sha=git_sha,
        dataset=Path(dataset_path).name,
        provider=provider,
        accuracy=metrics.accuracy,
        f1_macro=metrics.f1_macro,
        confidently_wrong_rate=metrics.confidently_wrong_rate,
        abstention_rate=metrics.abstention_rate,
        num_claims=metrics.num_claims,
        notes=notes,
    )
    with index_path.open("a", encoding="utf-8") as f:
        f.write(summary.to_json() + "\n")

    logger.info("Results written to %s", out_dir)
    return out_dir


def main():
    parser = argparse.ArgumentParser(description="DocuCheck eval runner")
    parser.add_argument("--dataset", required=True, help="Path to eval JSONL file")
    parser.add_argument("--provider", default="heuristic", choices=["heuristic", "gemini"],
                        help="Verification provider (default: heuristic)")
    parser.add_argument("--notes", default="", help="Free-text notes for this run")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
    out_dir = run_eval(args.dataset, args.provider, args.notes)
    print(f"\n[OK] Eval complete. Results: {out_dir}")


if __name__ == "__main__":
    main()
