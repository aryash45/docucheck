import pytest

from src.ingestion.chunker import TextChunk
from src.retrieval.evidence import PassageRetriever
from src.tree.evidence import classify_direction, to_passage_evidence

pytestmark = pytest.mark.local


def test_direction_classifier_distinguishes_support_and_contradiction():
    assert classify_direction(
        "The treatment reduces mortality", "The treatment reduces mortality by 20 percent."
    ) == "supporting"
    assert classify_direction(
        "The treatment reduces mortality", "However, the treatment does not reduce mortality."
    ) == "contradicting"


def test_to_passage_evidence_preserves_location_and_score():
    chunk = TextChunk(
        "doc:chunk_0", "The treatment reduces mortality.", 0, 1,
        document_id="doc", char_start=10, char_end=44, page_start=2, page_end=2,
    )
    retrieved = PassageRetriever().retrieve("treatment reduces mortality", [chunk], top_k=1)
    evidence = to_passage_evidence("treatment reduces mortality", retrieved)

    assert evidence[0].source_id == "doc"
    assert evidence[0].page_start == 2
    assert evidence[0].char_start == 10
    assert evidence[0].direction == "supporting"
    assert evidence[0].score > 0
