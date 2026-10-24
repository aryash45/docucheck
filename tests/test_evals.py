"""
tests/test_evals.py
-------------------
Unit tests for the evaluation harness:
- Schema serialization and immutability of inputs
- Streaming loader
- Metrics computation (including unknown/malformed labels and edge cases)
- Subprocess timeouts and environment variable safety
"""

import os
import pytest
from pathlib import Path

from evals.schema import EvalClaim, GoldEvidence, Prediction, load_eval_claims
from evals.metrics import compute_metrics, LABELS
from evals.run_eval import _run_single_claim


def test_eval_claim_from_dict_does_not_mutate_input():
    raw_dict = {
        "id": "claim_test_1",
        "domain": "ml",
        "document_id": "doc_1",
        "claim": "Test claim statement",
        "gold_label": "supported",
        "gold_evidence": [
            {
                "source_id": "src_1",
                "source_title": "Paper 1",
                "quote": "Quote text",
            }
        ],
    }
    # Pass raw_dict and ensure original dictionary is untouched
    claim = EvalClaim.from_dict(raw_dict)
    assert "gold_evidence" in raw_dict
    assert len(raw_dict["gold_evidence"]) == 1
    assert claim.id == "claim_test_1"
    assert len(claim.gold_evidence) == 1
    assert claim.gold_evidence[0].source_id == "src_1"


def test_load_eval_claims_streaming(tmp_path):
    test_jsonl = tmp_path / "test_claims.jsonl"
    lines = [
        '{"id": "c1", "domain": "cs", "document_id": "d1", "claim": "Statement 1", "gold_label": "supported"}',
        '{"id": "c2", "domain": "bio", "document_id": "d2", "claim": "Statement 2", "gold_label": "refuted"}',
        '',  # empty line should be ignored
    ]
    test_jsonl.write_text("\n".join(lines), encoding="utf-8")

    loaded = load_eval_claims(test_jsonl)
    assert len(loaded) == 2
    assert loaded[0].id == "c1"
    assert loaded[1].id == "c2"


def test_compute_metrics_unknown_and_malformed_labels():
    claims = [
        EvalClaim(id="c1", domain="x", document_id="d1", claim="c1", gold_label="supported"),
        EvalClaim(id="c2", domain="x", document_id="d1", claim="c2", gold_label="REFUTED "),
        EvalClaim(id="c3", domain="x", document_id="d1", claim="c3", gold_label="custom_unknown_label"),
    ]
    predictions = [
        Prediction(claim_id="c1", predicted_label="SUPPORTED", confidence=0.8),
        Prediction(claim_id="c2", predicted_label="unverifiable", confidence=0.3),
        Prediction(claim_id="c3", predicted_label="UNEXPECTED_LABEL", confidence=0.5),
    ]

    # Must compute cleanly without KeyError
    metrics = compute_metrics(claims, predictions)
    assert metrics.num_claims == 3
    assert metrics.num_correct == 1
    assert metrics.accuracy == round(1 / 3, 4)


def test_run_eval_env_var_safety():
    # If GEMINI_API_KEY was not in os.environ, running a heuristic prediction
    # should NOT leave an empty string in os.environ
    os.environ.pop("GEMINI_API_KEY", None)
    claim = EvalClaim(id="c1", domain="x", document_id="d1", claim="test", gold_label="supported")
    pred = _run_single_claim(claim, provider="heuristic")

    assert "GEMINI_API_KEY" not in os.environ
    assert pred.claim_id == "c1"

    # If GEMINI_API_KEY was originally present, it should be restored
    os.environ["GEMINI_API_KEY"] = "original_secret_key"
    try:
        pred = _run_single_claim(claim, provider="heuristic")
        assert os.environ.get("GEMINI_API_KEY") == "original_secret_key"
    finally:
        os.environ.pop("GEMINI_API_KEY", None)
