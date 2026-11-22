from src.tree.evidence import classify_direction, review_evidence
from src.tree.state import PassageEvidence
from src.ingestion.chunker import TextChunk
from src.literature.fetcher import Paper
from src.tree.nodes import fact_checker_node
from src.tree.state import Claim, ResearchState


def _evidence(direction: str, score: float = 0.8, quote: str = "Exact passage") -> PassageEvidence:
    return PassageEvidence(
        evidence_id=f"ev_{direction}", source_id="paper", source_title="Paper",
        quote=quote, direction=direction, score=score,
    )


def test_review_flags_conflict_and_missing_evidence():
    assert "missing_evidence" in review_evidence([])
    flags = review_evidence([_evidence("supporting"), _evidence("contradicting")])
    assert "conflicting_evidence" in flags


def test_review_flags_weak_and_invalid_citations():
    item = _evidence("supporting", score=0.1)
    item.source_id = ""
    item.quote = ""
    item.char_start, item.char_end = 10, 2
    flags = review_evidence([item])
    assert {"weak_evidence", "citation_integrity", "invalid_location"}.issubset(flags)


def test_review_flags_numeric_condition_mismatch():
    flags = review_evidence([_evidence("supporting", quote="Capacity was 180 mAh/g at 0.5C.")], claim="capacity reaches 210 mAh/g at 1C")
    assert "condition_mismatch" in flags


def test_absence_language_is_not_mistaken_for_refutation():
    assert classify_direction(
        "The treatment reduces mortality",
        "The paper reports no comparable evidence for whether the treatment reduces mortality.",
    ) == "neutral"


def test_neutral_passage_forces_abstention(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    paper = Paper("paper", "Paper", "No comparable evidence is reported.", [], 2026, 0, "test", "")
    state = ResearchState(
        papers=[paper],
        claims=[Claim("claim", "eval", "The treatment reduces mortality", ["Paper"])],
        passages=[TextChunk("paper:chunk_0", "No comparable evidence is reported for whether the treatment reduces mortality.", 0, 1, document_id="paper")],
    )
    fact_checker_node(state)
    assert state.verifications[0].verdict == "UNVERIFIABLE"
