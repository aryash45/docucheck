import pytest

from src.writer.scaffold_writer import ScaffoldWriter

pytestmark = pytest.mark.local


def test_fact_check_markdown_includes_passage_and_citation_status(tmp_path):
    writer = ScaffoldWriter(tmp_path)
    result = writer.write(
        {
            "topic": "test",
            "claims": [{"id": "c1", "text": "A claim", "angle_id": "doc"}],
            "verifications": [{
                "claim_id": "c1",
                "verdict": "SUPPORTED",
                "confidence": 0.8,
                "supported_by": ["paper"],
                "direction_counts": {"supporting": 1, "contradicting": 0, "neutral": 0},
                "evidence": [{
                    "source_title": "paper",
                    "source_id": "p1",
                    "quote": "Exact passage",
                    "direction": "supporting",
                    "score": 0.9,
                    "page_start": 3,
                    "char_start": 20,
                    "char_end": 34,
                }],
            }],
            "citations": [{"source_id": "p1", "status": "resolved"}],
        },
        [],
    )

    markdown = (tmp_path / "fact_check_card.md").read_text(encoding="utf-8")
    assert "Passage evidence" in markdown
    assert "Exact passage" in markdown
    assert "supporting=1" in markdown
    assert "Citation checks" in markdown
