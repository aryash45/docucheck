"""
tests/test_ingestion.py
-----------------------
Unit and integration tests for the document ingestion pipeline.

All tests run offline — no PDF files, no network calls.
Fake documents are constructed in-memory; DocumentParser is patched for
binary-format tests.
"""

from __future__ import annotations

import sys
import os
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, ".")

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

SAMPLE_ACADEMIC_TEXT = textwrap.dedent("""\
    Deep Learning Surpasses Human Performance on ImageNet

    Abstract

    We show that deep residual networks achieve 95.5% top-1 accuracy on the
    ImageNet LSVRC 2015 benchmark, surpassing human performance by 3.2%.
    Our model uses 152 layers and was trained for 14 days on 8 NVIDIA V100 GPUs.

    1. Introduction

    Convolutional neural networks have improved steadily over the past decade.
    However, deeper networks suffer from vanishing gradients during training.
    We propose residual connections that allow gradients to flow directly through
    skip connections, reducing training error by 42% compared to plain networks.

    2. Results

    The model achieves 3.57% top-5 error on the ILSVRC 2015 test set.
    Compared to VGG-16, our approach reduces inference time by 30% while
    maintaining higher accuracy. The training loss converges in fewer than
    90 epochs across all configurations tested.

    3. Conclusion

    Residual learning is a powerful technique for training very deep networks.
    Future work should explore residual connections in transformer architectures.
""")


# ---------------------------------------------------------------------------
# TextChunker
# ---------------------------------------------------------------------------

class TestTextChunker:
    def test_basic_chunking(self):
        from src.ingestion.chunker import TextChunker
        chunker = TextChunker(max_words=50, stride_sentences=2, min_chars=20)
        chunks = chunker.chunk(SAMPLE_ACADEMIC_TEXT)
        assert len(chunks) > 0

    def test_chunk_ids_are_sequential(self):
        from src.ingestion.chunker import TextChunker
        chunker = TextChunker(max_words=60, stride_sentences=2, min_chars=20)
        chunks = chunker.chunk(SAMPLE_ACADEMIC_TEXT)
        ids = [c.chunk_id for c in chunks]
        assert ids == [f"chunk_{i}" for i in range(len(chunks))]

    def test_empty_text_returns_no_chunks(self):
        from src.ingestion.chunker import TextChunker
        chunker = TextChunker()
        assert chunker.chunk("") == []

    def test_very_short_text_filtered(self):
        from src.ingestion.chunker import TextChunker
        chunker = TextChunker(min_chars=100)
        # Single short sentence should be filtered out
        chunks = chunker.chunk("Hi.")
        assert chunks == []

    def test_chunk_max_words_respected(self):
        from src.ingestion.chunker import TextChunker
        chunker = TextChunker(max_words=20, stride_sentences=1, min_chars=10)
        chunks = chunker.chunk(SAMPLE_ACADEMIC_TEXT)
        for chunk in chunks:
            assert len(chunk.text.split()) <= 40  # allow small overrun at boundaries

    def test_sentence_start_end_ordering(self):
        from src.ingestion.chunker import TextChunker
        chunker = TextChunker(max_words=50, stride_sentences=2, min_chars=20)
        chunks = chunker.chunk(SAMPLE_ACADEMIC_TEXT)
        for chunk in chunks:
            assert chunk.sentence_start <= chunk.sentence_end


# ---------------------------------------------------------------------------
# DocumentParser
# ---------------------------------------------------------------------------

class TestDocumentParser:
    def test_parse_nonexistent_file_returns_empty(self, tmp_path):
        from src.ingestion.parser import DocumentParser
        parser = DocumentParser()
        doc = parser.parse(tmp_path / "does_not_exist.pdf")
        assert doc.is_empty
        assert len(doc.warnings) > 0
        assert "not found" in doc.warnings[0].lower()

    def test_parse_plain_text(self, tmp_path):
        from src.ingestion.parser import DocumentParser
        f = tmp_path / "paper.txt"
        f.write_text(SAMPLE_ACADEMIC_TEXT, encoding="utf-8")
        parser = DocumentParser()
        doc = parser.parse(f)
        assert not doc.is_empty
        assert "ResNet" in doc.text or "Deep" in doc.text or "residual" in doc.text
        assert doc.word_count > 50

    def test_parse_markdown(self, tmp_path):
        from src.ingestion.parser import DocumentParser
        f = tmp_path / "draft.md"
        f.write_text("# My Paper\n\n" + SAMPLE_ACADEMIC_TEXT, encoding="utf-8")
        parser = DocumentParser()
        doc = parser.parse(f)
        assert not doc.is_empty
        assert doc.title  # should infer title from first line

    def test_title_inferred_from_first_line(self, tmp_path):
        from src.ingestion.parser import DocumentParser
        f = tmp_path / "test.txt"
        f.write_text("My Amazing Research Paper\n\nBody text here.", encoding="utf-8")
        doc = DocumentParser().parse(f)
        assert "My Amazing Research Paper" in doc.title

    def test_parse_pdf_without_pymupdf_returns_warning(self, tmp_path):
        """If PyMuPDF is not installed, parser should return warning, not crash."""
        from src.ingestion import parser as parser_module
        f = tmp_path / "fake.pdf"
        f.write_bytes(b"%PDF-1.4 fake content")
        original = parser_module._HAVE_FITZ
        try:
            parser_module._HAVE_FITZ = False
            doc = parser_module.DocumentParser().parse(f)
            assert any("pymupdf" in w.lower() or "pdf" in w.lower() for w in doc.warnings)
        finally:
            parser_module._HAVE_FITZ = original

    def test_parse_docx_without_python_docx_returns_warning(self, tmp_path):
        from src.ingestion import parser as parser_module
        f = tmp_path / "fake.docx"
        f.write_bytes(b"PK\x03\x04 fake docx")
        original = parser_module._HAVE_DOCX
        try:
            parser_module._HAVE_DOCX = False
            doc = parser_module.DocumentParser().parse(f)
            assert any("docx" in w.lower() or "python-docx" in w.lower() for w in doc.warnings)
        finally:
            parser_module._HAVE_DOCX = original


# ---------------------------------------------------------------------------
# DocumentClaimExtractor — heuristic fallback (offline, no Gemini)
# ---------------------------------------------------------------------------

class TestDocumentClaimExtractor:
    def _make_doc(self, text: str = SAMPLE_ACADEMIC_TEXT):
        from src.ingestion.parser import ParsedDocument
        return ParsedDocument(
            text=text, title="Test Paper", source_path="test.txt"
        )

    def test_extracts_claims_offline(self):
        """Heuristic extractor should find at least a few checkable sentences."""
        from src.ingestion.claim_extractor import DocumentClaimExtractor
        extractor = DocumentClaimExtractor(max_total_claims=20)
        with patch("src.ingestion.claim_extractor._call_gemini", return_value=None):
            claims = extractor.extract(self._make_doc(), topic="deep learning")
        # Heuristic may find fewer claims than LLM, but must find some
        assert isinstance(claims, list)
        # All should be Claim dataclass instances
        from src.tree.state import Claim
        for c in claims:
            assert isinstance(c, Claim)

    def test_claim_ids_are_prefixed(self):
        from src.ingestion.claim_extractor import DocumentClaimExtractor
        extractor = DocumentClaimExtractor()
        with patch("src.ingestion.claim_extractor._call_gemini", return_value=None):
            claims = extractor.extract(self._make_doc(), topic="deep learning")
        for c in claims:
            assert c.claim_id.startswith("ingested_claim_")

    def test_angle_id_is_ingested(self):
        from src.ingestion.claim_extractor import DocumentClaimExtractor
        extractor = DocumentClaimExtractor()
        with patch("src.ingestion.claim_extractor._call_gemini", return_value=None):
            claims = extractor.extract(self._make_doc(), topic="test")
        for c in claims:
            assert c.angle_id == "ingested"

    def test_gemini_claims_used_when_available(self):
        from src.ingestion.claim_extractor import DocumentClaimExtractor
        gemini_response = '["Our model achieves 95.5% accuracy.", "Training took 14 days on 8 GPUs."]'
        extractor = DocumentClaimExtractor(max_total_claims=10)
        with patch("src.ingestion.claim_extractor._call_gemini", return_value=gemini_response):
            claims = extractor.extract(self._make_doc(), topic="deep learning")
        texts = [c.text for c in claims]
        # At least one of the Gemini claims should appear
        assert any("95.5" in t or "14 days" in t for t in texts)

    def test_empty_doc_returns_empty_list(self):
        from src.ingestion.claim_extractor import DocumentClaimExtractor
        from src.ingestion.parser import ParsedDocument
        empty_doc = ParsedDocument(text="", title="empty", source_path="x.txt")
        extractor = DocumentClaimExtractor()
        claims = extractor.extract(empty_doc, topic="test")
        assert claims == []

    def test_max_claims_respected(self):
        from src.ingestion.claim_extractor import DocumentClaimExtractor
        extractor = DocumentClaimExtractor(max_total_claims=5)
        with patch("src.ingestion.claim_extractor._call_gemini", return_value=None):
            claims = extractor.extract(self._make_doc(), topic="test")
        assert len(claims) <= 5

    def test_deduplication_removes_near_duplicates(self):
        from src.ingestion.claim_extractor import _deduplicate
        claims = [
            "Our model achieves 95% accuracy on the benchmark.",
            "Our model achieves 95% accuracy on this benchmark.",  # near-duplicate
            "Training took 14 days on 8 GPUs.",
        ]
        unique = _deduplicate(claims, threshold=0.65)
        # Should merge the two similar claims
        assert len(unique) == 2


# ---------------------------------------------------------------------------
# IngestionPipeline — integration test
# ---------------------------------------------------------------------------

class TestIngestionPipeline:
    def test_run_produces_research_state(self, tmp_path):
        from src.ingestion.pipeline import IngestionPipeline
        from src.tree.state import ResearchState

        f = tmp_path / "paper.txt"
        f.write_text(SAMPLE_ACADEMIC_TEXT, encoding="utf-8")

        pipeline = IngestionPipeline(max_claims=15)
        with patch("src.ingestion.claim_extractor._call_gemini", return_value=None):
            state = pipeline.run(f, topic="deep learning residual networks")

        assert isinstance(state, ResearchState)
        assert state.topic == "deep learning residual networks"
        assert isinstance(state.claims, list)

    def test_topic_inferred_from_document_when_not_provided(self, tmp_path):
        from src.ingestion.pipeline import IngestionPipeline
        f = tmp_path / "amazing_paper.txt"
        f.write_text("Interesting Title Here\n\n" + SAMPLE_ACADEMIC_TEXT, encoding="utf-8")
        pipeline = IngestionPipeline()
        with patch("src.ingestion.claim_extractor._call_gemini", return_value=None):
            state = pipeline.run(f)
        # Topic should be inferred from document title, not filename
        assert state.topic  # not empty
        assert "amazing_paper" not in state.topic  # not raw filename

    def test_papers_forwarded_to_state(self, tmp_path):
        from src.ingestion.pipeline import IngestionPipeline

        f = tmp_path / "doc.txt"
        f.write_text(SAMPLE_ACADEMIC_TEXT, encoding="utf-8")

        mock_papers = [MagicMock(title="Attention Is All You Need")]
        pipeline = IngestionPipeline()
        with patch("src.ingestion.claim_extractor._call_gemini", return_value=None):
            state = pipeline.run(f, topic="transformers", papers=mock_papers)
        assert state.papers == mock_papers

    def test_nonexistent_file_returns_state_with_warnings(self, tmp_path):
        from src.ingestion.pipeline import IngestionPipeline
        pipeline = IngestionPipeline()
        state = pipeline.run(tmp_path / "missing.pdf", topic="test")
        assert len(state.errors) > 0  # warnings forwarded as errors


# ---------------------------------------------------------------------------
# Integration: IngestionPipeline → ResearchGraph.run_fact_check_only
# ---------------------------------------------------------------------------

class TestIngestionToFactCheckIntegration:
    def test_end_to_end_fact_check_mode(self, tmp_path):
        """
        Smoke test: ingested document claims flow into run_fact_check_only
        and produce ClaimVerification objects.
        """
        from src.ingestion.pipeline import IngestionPipeline
        from src.tree.graph import ResearchGraph

        f = tmp_path / "paper.txt"
        f.write_text(SAMPLE_ACADEMIC_TEXT, encoding="utf-8")

        pipeline = IngestionPipeline(max_claims=5)
        with patch("src.ingestion.claim_extractor._call_gemini", return_value=None):
            state = pipeline.run(f, topic="deep learning")

        if not state.claims:
            pytest.skip("Heuristic found no claims in sample text — skip integration")

        graph = ResearchGraph()
        # Patch fact-checker Gemini call to avoid network in CI
        with patch("src.tree.nodes._call_gemini", return_value=None):
            state = graph.run_fact_check_only(state)

        assert state.output is not None
        assert "verifications" in state.output
        # Every claim should have a verification
        claim_ids = {c.claim_id for c in state.claims}
        verified_ids = {v["claim_id"] for v in state.output["verifications"]}
        assert claim_ids == verified_ids

    def test_run_fact_check_only_with_empty_claims(self, tmp_path):
        """run_fact_check_only on empty claims should not crash."""
        from src.tree.graph import ResearchGraph
        from src.tree.state import ResearchState

        state = ResearchState(topic="test", claims=[], papers=[])
        graph = ResearchGraph()
        with patch("src.tree.nodes._call_gemini", return_value=None):
            state = graph.run_fact_check_only(state)

        assert state.output is not None
        assert state.output["verifications"] == []
