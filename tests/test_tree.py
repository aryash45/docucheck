"""
tests/test_tree.py
------------------
Stage 3 integration test: run the full plan-execute-verify graph
with a real topic and verify structural correctness of the output.

Designed to run entirely offline (no API keys required).
All nodes have heuristic fallbacks, so the test always passes.
"""

import sys
import logging
import shutil

sys.path.insert(0, ".")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")

from src.literature.fetcher import Paper
from src.tree.graph import ResearchGraph
from src.tree.state import ResearchState
from src.sandbox.executor import SandboxExecutor, SandboxResult

# ---------------------------------------------------------------------------
# Realistic mock paper corpus (same style as test_literature.py)
# ---------------------------------------------------------------------------
MOCK_PAPERS = [
    Paper(
        paper_id="mock_1",
        title="Attention Is All You Need",
        abstract=(
            "The dominant sequence transduction models are based on complex recurrent "
            "or convolutional neural networks. We propose the Transformer, a model "
            "architecture based entirely on attention mechanisms."
        ),
        authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
        year=2017,
        citation_count=100_000,
        source="semantic_scholar",
        url="https://www.semanticscholar.org/paper/mock_1",
    ),
    Paper(
        paper_id="mock_2",
        title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        abstract=(
            "We introduce BERT, a language representation model designed to pre-train "
            "deep bidirectional representations by jointly conditioning on both left "
            "and right context in all layers."
        ),
        authors=["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee"],
        year=2018,
        citation_count=80_000,
        source="semantic_scholar",
        url="https://www.semanticscholar.org/paper/mock_2",
    ),
    Paper(
        paper_id="mock_3",
        title="Sparsity in Deep Learning: Pruning and Growth for Efficient Inference",
        abstract=(
            "Sparsity in neural networks reduces computational complexity. We survey "
            "pruning and growth strategies that achieve high compression ratios with "
            "minimal accuracy loss."
        ),
        authors=["Torsten Hoefler", "Dan Alistarh"],
        year=2021,
        citation_count=2_000,
        source="openAlex",
        url="https://api.openalex.org/works/mock_3",
    ),
    Paper(
        paper_id="mock_4",
        title="Deep Double Descent: Where Bigger Models and More Data Hurt",
        abstract=(
            "We show that the double descent phenomenon occurs in modern deep learning. "
            "Model performance first improves, then degrades, then improves again as "
            "model size or training data grows beyond the interpolation threshold."
        ),
        authors=["Preetum Nakkiran", "Gal Kaplun"],
        year=2019,
        citation_count=1_500,
        source="openAlex",
        url="https://api.openalex.org/works/mock_4",
    ),
    Paper(
        paper_id="mock_5",
        title="Scaling Laws for Neural Language Models",
        abstract=(
            "We study empirical scaling laws for language model performance on the "
            "cross-entropy loss. Performance scales as a power-law with model size, "
            "dataset size, and compute."
        ),
        authors=["Jared Kaplan", "Sam McCandlish"],
        year=2020,
        citation_count=5_000,
        source="semantic_scholar",
        url="https://www.semanticscholar.org/paper/mock_5",
    ),
]

TOPIC = "efficiency of transformer attention mechanisms"


# ---------------------------------------------------------------------------
# Stage 2: SandboxExecutor tests
# ---------------------------------------------------------------------------

def test_sandbox_local_mode():
    """SandboxExecutor falls back to local mode when no E2B key is set."""
    print("\n--- TEST S2-1: SandboxExecutor local mode ---")
    executor = SandboxExecutor(timeout_seconds=10, budget_usd=1.0)
    assert executor.mode in ("e2b", "local"), "Unexpected executor mode"
    print(f"[OK] Executor mode: {executor.mode}")


def test_sandbox_run_simple():
    """Local executor correctly runs simple Python and captures stdout."""
    print("\n--- TEST S2-2: SandboxExecutor run simple code ---")
    executor = SandboxExecutor(timeout_seconds=10, budget_usd=1.0)
    result = executor.run("print('hello sandbox')")

    assert isinstance(result, SandboxResult), "run() must return SandboxResult"
    assert result.success, f"Execution failed: {result.error}"
    assert "hello sandbox" in result.stdout, "stdout missing expected text"
    assert result.execution_time_ms >= 0
    print(f"[OK] stdout: {result.stdout.strip()!r}")
    print(f"[OK] time: {result.execution_time_ms}ms")


def test_sandbox_handles_error():
    """Executor returns success=False and captures error on bad code."""
    print("\n--- TEST S2-3: SandboxExecutor error handling ---")
    executor = SandboxExecutor(timeout_seconds=10, budget_usd=1.0)
    result = executor.run("raise ValueError('intentional test error')")

    assert isinstance(result, SandboxResult)
    assert not result.success, "Expected failure for code that raises"
    assert result.error is not None
    print(f"[OK] error captured: {result.error[:60]!r}")


def test_sandbox_budget_tracking():
    """Spent USD accumulates across runs (even if it's 0 in local mode)."""
    print("\n--- TEST S2-4: SandboxExecutor budget tracking ---")
    executor = SandboxExecutor(timeout_seconds=10, budget_usd=1.0)
    executor.run("x = 1 + 1")
    executor.run("x = 2 + 2")
    assert executor.spent_usd >= 0.0
    assert executor.budget_remaining_usd() <= executor.budget_usd
    print(f"[OK] spent=${executor.spent_usd:.6f} remaining=${executor.budget_remaining_usd():.6f}")


def test_sandbox_run_analysis():
    """run_analysis() convenience wrapper works."""
    print("\n--- TEST S2-5: SandboxExecutor.run_analysis ---")
    executor = SandboxExecutor(timeout_seconds=10, budget_usd=1.0)
    result = executor.run_analysis(
        "citation count summary",
        "citations=[100,200,300]\nprint(f'total={sum(citations)}')",
    )
    assert result.success
    assert "total=600" in result.stdout
    print(f"[OK] output: {result.stdout.strip()!r}")


# ---------------------------------------------------------------------------
# Stage 3: full graph tests
# ---------------------------------------------------------------------------

def test_graph_produces_angles():
    """Planner always generates at least one angle."""
    print("\n--- TEST S3-1: Planner generates angles ---")
    graph = ResearchGraph(budget_usd=0.10, max_angles=3)
    output = graph.run(topic=TOPIC, papers=MOCK_PAPERS)

    assert "angles" in output, "Output missing 'angles'"
    assert len(output["angles"]) >= 1, "Planner returned no angles"
    for angle in output["angles"]:
        assert "id" in angle
        assert "title" in angle
        assert len(angle["title"]) > 0
    print(f"[OK] {len(output['angles'])} angles generated")
    for a in output["angles"]:
        print(f"  • {a['id']}: {a['title']}")


def test_graph_produces_evidence():
    """Executor populates evidence for every angle."""
    print("\n--- TEST S3-2: Executor gathers evidence ---")
    graph = ResearchGraph(budget_usd=0.10, max_angles=2)
    output = graph.run(topic=TOPIC, papers=MOCK_PAPERS)

    assert "evidence" in output, "Output missing 'evidence'"
    assert len(output["evidence"]) >= 1, "No evidence produced"
    for ev in output["evidence"]:
        assert "angle_id" in ev
        assert "summary" in ev
        assert len(ev["summary"]) > 0, "Evidence summary is empty"
    print(f"[OK] {len(output['evidence'])} evidence blocks")
    for ev in output["evidence"]:
        print(f"  • {ev['angle_id']}: {ev['summary'][:80]}…")


def test_graph_produces_scores():
    """Verifier assigns a score to each evidence block."""
    print("\n--- TEST S3-3: Verifier scores evidence ---")
    graph = ResearchGraph(budget_usd=0.10, max_angles=2)
    output = graph.run(topic=TOPIC, papers=MOCK_PAPERS)

    assert "scores" in output, "Output missing 'scores'"
    assert len(output["scores"]) >= 1
    for s in output["scores"]:
        assert "angle_id" in s
        assert "score" in s
        assert 0.0 <= s["score"] <= 1.0, f"Score out of range: {s['score']}"
        assert "passed" in s
    print(f"[OK] {len(output['scores'])} scores")
    for s in output["scores"]:
        print(f"  • {s['angle_id']}: score={s['score']:.2f} passed={s['passed']}")


def test_graph_produces_claims():
    """Claim extractor pulls at least one claim."""
    print("\n--- TEST S3-4: Claim extractor produces claims ---")
    graph = ResearchGraph(budget_usd=0.10, max_angles=2, evidence_score_threshold=0.0)
    output = graph.run(topic=TOPIC, papers=MOCK_PAPERS)

    assert "claims" in output, "Output missing 'claims'"
    assert len(output["claims"]) >= 1, "No claims extracted"
    for c in output["claims"]:
        assert "id" in c
        assert "text" in c
        assert len(c["text"]) > 0
    print(f"[OK] {len(output['claims'])} claims extracted")
    for c in output["claims"][:3]:
        print(f"  • {c['id']}: {c['text'][:80]}")


def test_graph_produces_verifications():
    """Fact checker verifies every claim."""
    print("\n--- TEST S3-5: Fact checker verifies claims ---")
    graph = ResearchGraph(budget_usd=0.10, max_angles=2, evidence_score_threshold=0.0)
    output = graph.run(topic=TOPIC, papers=MOCK_PAPERS)

    assert "verifications" in output, "Output missing 'verifications'"
    assert len(output["verifications"]) >= 1, "No verifications produced"
    verdicts = {"SUPPORTED", "REFUTED", "UNVERIFIABLE"}
    for v in output["verifications"]:
        assert "claim_id" in v
        assert "verdict" in v
        assert v["verdict"] in verdicts, f"Unknown verdict: {v['verdict']}"
        assert 0.0 <= v["confidence"] <= 1.0
    print(f"[OK] {len(output['verifications'])} verifications")
    for v in output["verifications"][:3]:
        print(f"  • {v['claim_id']}: {v['verdict']} (confidence={v['confidence']:.2f})")


def test_graph_full_run_structure():
    """Full end-to-end: output has all required top-level keys."""
    print("\n--- TEST S3-6: Full graph output structure ---")
    graph = ResearchGraph(budget_usd=0.10, max_angles=3, evidence_score_threshold=0.0)
    output = graph.run(topic=TOPIC, papers=MOCK_PAPERS)

    required_keys = {"topic", "angles", "evidence", "scores", "claims", "verifications", "budget"}
    missing = required_keys - output.keys()
    assert not missing, f"Output missing keys: {missing}"

    assert output["topic"] == TOPIC
    assert isinstance(output["angles"], list)
    assert isinstance(output["evidence"], list)
    assert isinstance(output["scores"], list)
    assert isinstance(output["claims"], list)
    assert isinstance(output["verifications"], list)
    assert "allocated_usd" in output["budget"]
    assert "spent_usd" in output["budget"]

    print("[OK] All required keys present")
    print(f"     topic={output['topic']!r}")
    print(f"     angles={len(output['angles'])}, evidence={len(output['evidence'])}")
    print(f"     claims={len(output['claims'])}, verifications={len(output['verifications'])}")
    print(f"     budget: allocated=${output['budget']['allocated_usd']} "
          f"spent=${output['budget']['spent_usd']}")


def test_graph_no_papers():
    """Graph handles empty paper list gracefully — no crash."""
    print("\n--- TEST S3-7: Graph with no papers (graceful degradation) ---")
    graph = ResearchGraph(budget_usd=0.10, max_angles=2, evidence_score_threshold=0.0)
    output = graph.run(topic="quantum computing error correction", papers=[])
    assert "angles" in output
    assert "errors" in output
    print(f"[OK] Ran with 0 papers — angles={len(output['angles'])} errors={len(output['errors'])}")


def test_run_from_state():
    """run_from_state() returns a ResearchState with output populated."""
    print("\n--- TEST S3-8: run_from_state() returns ResearchState ---")
    from src.tree.state import ResearchState as RS
    graph = ResearchGraph(budget_usd=0.10, max_angles=2, evidence_score_threshold=0.0)
    state = RS(topic=TOPIC, papers=MOCK_PAPERS, max_angles=2)
    final_state = graph.run_from_state(state)

    assert isinstance(final_state, RS)
    assert final_state.output is not None
    assert len(final_state.angles) >= 1
    assert len(final_state.claims) >= 1
    print(f"[OK] state.angles={len(final_state.angles)} claims={len(final_state.claims)}")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("STAGE 2 + 3 Tests: Sandbox Executor + Research Graph")
    print("=" * 60)

    # Stage 2 tests
    s2_tests = [
        test_sandbox_local_mode,
        test_sandbox_run_simple,
        test_sandbox_handles_error,
        test_sandbox_budget_tracking,
        test_sandbox_run_analysis,
    ]

    # Stage 3 tests
    s3_tests = [
        test_graph_produces_angles,
        test_graph_produces_evidence,
        test_graph_produces_scores,
        test_graph_produces_claims,
        test_graph_produces_verifications,
        test_graph_full_run_structure,
        test_graph_no_papers,
        test_run_from_state,
    ]

    all_tests = s2_tests + s3_tests
    failed = 0

    for test_fn in all_tests:
        try:
            test_fn()
        except AssertionError as e:
            print(f"\n[FAIL] {test_fn.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"\n[ERROR] {test_fn.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    if failed == 0:
        print(f"[OK] ALL {len(all_tests)} TESTS PASSED — Ready for Stage 4")
    else:
        print(f"[FAIL] {failed}/{len(all_tests)} tests failed")
        sys.exit(1)
    print("=" * 60)
