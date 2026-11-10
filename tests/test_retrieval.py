import pytest

from src.ingestion.chunker import TextChunk
from src.retrieval.evidence import PassageRetriever

pytestmark = pytest.mark.local


def test_retriever_returns_ranked_matching_passages():
    passages = [
        TextChunk(
            chunk_id="doc:chunk_0",
            text="Attention mechanisms connect every token and have quadratic complexity.",
            sentence_start=0,
            sentence_end=1,
            document_id="doc",
            char_start=0,
            char_end=75,
        ),
        TextChunk(
            chunk_id="doc:chunk_1",
            text="This passage discusses unrelated optimization details.",
            sentence_start=1,
            sentence_end=2,
            document_id="doc",
            char_start=76,
            char_end=130,
        ),
    ]

    results = PassageRetriever().retrieve(
        "Attention mechanisms have quadratic complexity", passages, top_k=1
    )

    assert len(results) == 1
    assert results[0].chunk.chunk_id == "doc:chunk_0"
    assert "attention" in results[0].matched_terms
    assert results[0].score > 0


def test_retriever_is_empty_for_no_overlap():
    passage = TextChunk("doc:chunk_0", "Cats and dogs.", 0, 1)
    assert PassageRetriever().retrieve("quantum entanglement", [passage]) == []
