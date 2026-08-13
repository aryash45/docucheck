"""
src/ingestion/pipeline.py
--------------------------
IngestionPipeline — the single public entry point for document ingestion.

Converts an uploaded file into a ResearchState with pre-populated claims,
ready to be fed into ResearchGraph.run_fact_check_only().

Mode 3 — Fact Check flow
------------------------
    state = IngestionPipeline().run("paper.pdf", topic="LLM alignment")
    state = graph.run_fact_check_only(state)
    result = writer.write_from_state(state)

Mode 2 — Improve flow (future)
-------------------------------
    state = IngestionPipeline().run("draft.pdf", topic="...", papers=papers)
    # gap_analysis_node will compare state.claims against literature
"""

from __future__ import annotations

import logging
from pathlib import Path

from .parser import DocumentParser
from .claim_extractor import DocumentClaimExtractor
from src.tree.state import ResearchState

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    Parse a user document and populate a ResearchState ready for fact-checking.

    Parameters
    ----------
    output_dir : str
        Directory for writer output artifacts (passed through to ResearchState).
    max_claims : int
        Maximum number of claims to extract from the document.
    budget_usd : float
        Sandbox budget forwarded to ResearchState (used if sandbox runs).
    """

    def __init__(
        self,
        max_claims: int = 30,
        budget_usd: float = 0.50,
    ):
        self.max_claims = max_claims
        self.budget_usd = budget_usd
        self._parser = DocumentParser()
        self._extractor = DocumentClaimExtractor(max_total_claims=max_claims)

    def run(
        self,
        file_path: str | Path,
        topic: str = "",
        papers: list = [],
    ) -> ResearchState:
        """
        Parse the file, extract claims, and return a ready ResearchState.

        Parameters
        ----------
        file_path : str | Path
            Path to PDF, .docx, .txt, or .md file.
        topic : str
            Research topic for context in claim extraction prompts.
            If empty, the document's inferred title is used.
        papers : list[Paper]
            Optional: pre-fetched literature corpus for fact-checking context.
            If empty, the fact-checker will run with no supporting literature
            (verdicts will mostly be UNVERIFIABLE — fetch papers first for best results).

        Returns
        -------
        ResearchState
            - state.claims   → populated from the ingested document
            - state.papers   → forwarded from `papers` argument
            - state.topic    → `topic` or inferred from document title
            - state.output   → None (set after graph run)
        """
        path = Path(file_path)
        logger.info("IngestionPipeline: ingesting '%s'", path.name)

        # Step 1: Parse the document
        doc = self._parser.parse(path)

        if doc.warnings:
            for w in doc.warnings:
                logger.warning("IngestionPipeline: %s", w)

        if doc.is_empty:
            logger.error(
                "IngestionPipeline: document is empty or could not be parsed — "
                "returning empty state"
            )

        # Step 2: Resolve topic
        effective_topic = topic or doc.title or path.stem
        logger.info(
            "IngestionPipeline: topic='%s' | words=%d | pages=%d",
            effective_topic, doc.word_count, doc.page_count,
        )

        # Step 3: Extract claims
        claims = self._extractor.extract(doc, effective_topic)
        logger.info("IngestionPipeline: extracted %d claims", len(claims))

        # Step 4: Build ResearchState
        state = ResearchState(
            topic=effective_topic,
            papers=list(papers),
            claims=claims,
            budget_usd=self.budget_usd,
        )

        # Tag any parser warnings as pipeline errors (non-fatal)
        state.errors.extend(doc.warnings)

        return state
