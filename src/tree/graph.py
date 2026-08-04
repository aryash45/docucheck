"""
src/tree/graph.py
-----------------
Wires the five nodes into a plan-execute-verify pipeline.

Design
------
This is a pure-Python state machine with the same semantics as LangGraph
but zero extra dependencies.  Each step calls one node function, passes the
mutated ResearchState to the next, and the final state is serialised into a
structured evidence map.

Flow
----
    topic + papers (Stage 1)
          ↓
    [planner_node]        → generates research angles
          ↓
    [executor_node]       → gathers evidence per angle (calls Stage 2 sandbox)
          ↓
    [verifier_node]       → scores each angle's evidence strength
          ↓
    [claim_extractor_node]→ pulls verifiable claims from passing angles
          ↓
    [fact_checker_node]   → cross-references each claim against papers
          ↓
    structured evidence map  (consumed by Stage 5 writer)

Usage
-----
    from src.tree.graph import ResearchGraph
    from src.literature.fetcher import LiteraturePipeline

    pipeline = LiteraturePipeline()
    papers = pipeline.fetch("attention mechanism transformers")

    graph = ResearchGraph()
    output = graph.run(topic="attention mechanism transformers", papers=papers)
    # output is a dict with keys: angles, evidence, scores, claims, verifications
"""

from __future__ import annotations

import logging
import time
from typing import Any

from .state import ResearchState
from .nodes import (
    planner_node,
    executor_node,
    verifier_node,
    claim_extractor_node,
    fact_checker_node,
)

logger = logging.getLogger(__name__)

# Ordered sequence of (name, callable) pairs — the pipeline edges
_PIPELINE: list[tuple[str, Any]] = [
    ("planner",         planner_node),
    ("executor",        executor_node),
    ("verifier",        verifier_node),
    ("claim_extractor", claim_extractor_node),
    ("fact_checker",    fact_checker_node),
]


class ResearchGraph:
    """
    The plan-execute-verify graph.

    Parameters
    ----------
    budget_usd : float
        Total E2B sandbox budget for one run.  Defaults to $0.50.
    max_angles : int
        How many research angles the planner generates.  Defaults to 3.
    evidence_score_threshold : float
        Minimum verifier score (0–1) for an angle to be considered strong.
    """

    def __init__(
        self,
        budget_usd: float = 0.50,
        max_angles: int = 3,
        evidence_score_threshold: float = 0.3,
    ):
        self.budget_usd = budget_usd
        self.max_angles = max_angles
        self.evidence_score_threshold = evidence_score_threshold

    def run(self, topic: str, papers: list) -> dict:
        """
        Execute the full pipeline and return the structured evidence map.

        Parameters
        ----------
        topic : str
            Research topic / question.
        papers : list[Paper]
            Papers returned by LiteraturePipeline.fetch() (Stage 1).

        Returns
        -------
        dict
            Structured evidence map.  Keys: topic, angles, evidence,
            scores, claims, verifications, budget, errors.
        """
        state = ResearchState(
            topic=topic,
            papers=papers,
            budget_usd=self.budget_usd,
            max_angles=self.max_angles,
            evidence_score_threshold=self.evidence_score_threshold,
        )

        logger.info(
            "ResearchGraph: starting run | topic='%s' papers=%d budget=$%.2f",
            topic, len(papers), self.budget_usd,
        )
        t0 = time.monotonic()

        for step_name, node_fn in _PIPELINE:
            logger.info("ResearchGraph: → %s", step_name)
            step_start = time.monotonic()
            try:
                state = node_fn(state)
            except Exception as exc:
                # Non-fatal: log and continue so downstream nodes still run
                msg = f"Node '{step_name}' raised: {exc}"
                state.errors.append(msg)
                logger.error("ResearchGraph: %s", msg, exc_info=True)
            logger.info(
                "ResearchGraph: ← %s (%.2fs)", step_name, time.monotonic() - step_start
            )

        output = state.to_output_dict()
        elapsed = time.monotonic() - t0
        logger.info(
            "ResearchGraph: done in %.2fs | angles=%d claims=%d verified=%d errors=%d",
            elapsed,
            len(state.angles),
            len(state.claims),
            len(state.verifications),
            len(state.errors),
        )

        state.output = output
        return output

    def run_from_state(self, state: ResearchState) -> ResearchState:
        """
        Lower-level entry point: accepts a pre-built ResearchState,
        runs the pipeline, and returns the mutated state (not the dict).
        Useful for testing individual nodes or resuming partial runs.
        """
        for step_name, node_fn in _PIPELINE:
            try:
                state = node_fn(state)
            except Exception as exc:
                state.errors.append(f"Node '{step_name}' raised: {exc}")
                logger.error("ResearchGraph: %s raised: %s", step_name, exc, exc_info=True)
        state.output = state.to_output_dict()
        return state
