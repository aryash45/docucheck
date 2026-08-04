"""
src/tree/nodes.py
-----------------
Individual pipeline nodes for the plan-execute-verify loop.

Each node:
  • Accepts a ResearchState
  • Does exactly one job
  • Returns the mutated ResearchState
  • Never raises — errors are appended to state.errors

LLM calls use the Gemini REST API when GEMINI_API_KEY is set.
When no key is present every node uses a deterministic heuristic fallback
so the pipeline and tests always run offline.
"""

from __future__ import annotations

import json
import logging
import os
import re
import textwrap
import time
from typing import Optional

import requests

from .state import (
    Claim,
    ClaimVerification,
    Evidence,
    ResearchAngle,
    ResearchState,
    VerificationScore,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini REST helper
# ---------------------------------------------------------------------------

_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent"
)


def _call_gemini(prompt: str, max_tokens: int = 1024) -> Optional[str]:
    """
    Call Gemini 1.5 Flash via REST. Returns text or None on failure.
    Does NOT raise — callers fall back to heuristics on None.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key.startswith("your_"):
        return None

    try:
        resp = requests.post(
            f"{_GEMINI_URL}?key={api_key}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3},
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as exc:
        logger.warning("Gemini call failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Heuristic helpers (offline fallbacks)
# ---------------------------------------------------------------------------

def _heuristic_angles(topic: str, papers: list, max_angles: int) -> list[ResearchAngle]:
    """
    Generate research angles from paper titles without an LLM.
    Groups papers by decade and picks top cited as angle seeds.
    """
    if not papers:
        # Generic angles from topic words
        words = topic.split()[:4]
        angles = []
        for i, w in enumerate(words[:max_angles]):
            angles.append(ResearchAngle(
                angle_id=f"angle_{i}",
                title=f"{w.capitalize()} perspective",
                description=f"Examining {topic} through the lens of {w}.",
                query=f"{topic} {w}",
            ))
        return angles

    # Use top-cited papers as angle seeds
    sorted_papers = sorted(papers, key=lambda p: getattr(p, "citation_count", 0), reverse=True)
    angles = []
    for i, paper in enumerate(sorted_papers[:max_angles]):
        title = getattr(paper, "title", f"Paper {i}")
        short = title[:60] + ("…" if len(title) > 60 else "")
        angles.append(ResearchAngle(
            angle_id=f"angle_{i}",
            title=short,
            description=(
                f"Analyse {topic} in the context of: {title}. "
                f"({getattr(paper, 'year', '?')}, "
                f"cited {getattr(paper, 'citation_count', 0)} times)"
            ),
            query=f"{topic} {title[:40]}",
        ))
    return angles


def _parse_json_block(text: str) -> Optional[dict | list]:
    """Extract first JSON object/array from an LLM response."""
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        text = match.group(1)
    try:
        return json.loads(text.strip())
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Node 1 — Planner
# ---------------------------------------------------------------------------

def planner_node(state: ResearchState) -> ResearchState:
    """
    Generate research angles for the given topic and paper corpus.

    Output: state.angles  (list[ResearchAngle])
    """
    state.current_node = "planner"
    logger.info("Planner: generating angles for '%s' (%d papers)", state.topic, len(state.papers))

    max_angles = state.max_angles
    topic = state.topic
    paper_titles = [getattr(p, "title", "") for p in state.papers[:10]]

    # --- Try Gemini ---
    prompt = textwrap.dedent(f"""\
        You are a research planner.  Given the topic and a list of paper titles,
        generate {max_angles} distinct research angles worth investigating.

        Topic: {topic}

        Top papers (by citation count):
        {json.dumps(paper_titles, indent=2)}

        Return ONLY valid JSON — a list of objects with keys:
          angle_id  (string: "angle_0", "angle_1", ...)
          title     (string: short label, ≤ 10 words)
          description (string: 1–2 sentences)
          query     (string: search / analysis query for this angle)

        Example:
        ```json
        [
          {{
            "angle_id": "angle_0",
            "title": "Efficiency of attention mechanisms",
            "description": "Examine computational trade-offs in self-attention.",
            "query": "attention mechanism efficiency transformers"
          }}
        ]
        ```
    """)

    llm_text = _call_gemini(prompt, max_tokens=512)
    angles: list[ResearchAngle] = []

    if llm_text:
        parsed = _parse_json_block(llm_text)
        if isinstance(parsed, list):
            for item in parsed[:max_angles]:
                try:
                    angles.append(ResearchAngle(**{k: item[k] for k in ResearchAngle.__dataclass_fields__}))
                except Exception as exc:
                    state.errors.append(f"Planner: bad angle item — {exc}")

    if not angles:
        logger.info("Planner: LLM unavailable/parse failed, using heuristic angles")
        angles = _heuristic_angles(topic, state.papers, max_angles)

    state.angles = angles
    logger.info("Planner: produced %d angles", len(angles))
    return state


# ---------------------------------------------------------------------------
# Node 2 — Executor
# ---------------------------------------------------------------------------

def executor_node(state: ResearchState) -> ResearchState:
    """
    For each angle, gather evidence from the paper corpus.
    Optionally runs a sandbox snippet for quantitative support.

    Output: state.evidence  (list[Evidence])
    """
    state.current_node = "executor"
    evidence_list: list[Evidence] = []

    # Lazy-import SandboxExecutor (Stage 2); graceful if unavailable
    sandbox = None
    try:
        from src.sandbox.executor import SandboxExecutor
        sandbox = SandboxExecutor(timeout_seconds=30, budget_usd=state.budget_usd)
    except Exception as exc:
        state.errors.append(f"Executor: sandbox unavailable — {exc}")
        logger.warning("Executor: sandbox disabled (%s)", exc)

    for angle in state.angles:
        logger.info("Executor: gathering evidence for '%s'", angle.title)

        # Find relevant papers by keyword overlap
        relevant = _find_relevant_papers(angle.query, state.papers, top_k=5)
        source_titles = [getattr(p, "title", "") for p in relevant]

        # Build summary from abstracts
        summary = _summarise_evidence(angle, relevant, state.topic)

        # Optional: run sandbox for quantitative check
        sandbox_stdout = ""
        sandbox_used = False

        if sandbox and state.spent_usd < state.budget_usd and relevant:
            code = _build_analysis_code(angle, relevant)
            try:
                result = sandbox.run_analysis(f"angle: {angle.title}", code)
                state.spent_usd += result.cost_estimate_usd
                if result.success and result.stdout:
                    sandbox_stdout = result.stdout[:500]
                    sandbox_used = True
            except Exception as exc:
                state.errors.append(f"Executor sandbox run failed: {exc}")

        evidence_list.append(Evidence(
            angle_id=angle.angle_id,
            source_titles=source_titles,
            summary=summary,
            sandbox_stdout=sandbox_stdout,
            sandbox_used=sandbox_used,
        ))

    state.evidence = evidence_list
    logger.info("Executor: produced evidence for %d angles", len(evidence_list))
    return state


def _find_relevant_papers(query: str, papers: list, top_k: int = 5) -> list:
    """Keyword-overlap ranking — no embeddings needed here."""
    query_words = set(query.lower().split())
    scored = []
    for paper in papers:
        text = (
            getattr(paper, "title", "") + " " + getattr(paper, "abstract", "")
        ).lower()
        overlap = sum(1 for w in query_words if w in text)
        scored.append((overlap, paper))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:top_k] if _ > 0] or papers[:top_k]


def _summarise_evidence(angle: ResearchAngle, papers: list, topic: str) -> str:
    """
    Try Gemini summary; fall back to concatenated abstracts.
    """
    if not papers:
        return f"No relevant papers found for angle: {angle.title}"

    snippets = []
    for p in papers[:3]:
        abstract = getattr(p, "abstract", "")
        snippets.append(f"- {getattr(p, 'title', '?')} ({getattr(p, 'year', '?')}): {abstract[:200]}")

    prompt = textwrap.dedent(f"""\
        Summarise the evidence from these papers for the research angle below.
        Be concise (3–5 sentences). Focus on what the papers say about the angle.

        Topic: {topic}
        Angle: {angle.title} — {angle.description}

        Papers:
        {chr(10).join(snippets)}

        Return plain text — no markdown, no JSON.
    """)

    llm_text = _call_gemini(prompt, max_tokens=256)
    if llm_text and len(llm_text.strip()) > 20:
        return llm_text.strip()

    # Heuristic fallback
    return (
        f"Evidence for '{angle.title}': "
        + " | ".join(
            f"{getattr(p, 'title', '?')[:50]} ({getattr(p, 'year', '?')})"
            for p in papers[:3]
        )
    )


def _build_analysis_code(angle: ResearchAngle, papers: list) -> str:
    """
    Build a simple Python snippet that quantifies evidence strength
    using citation counts — safe to run in local or E2B sandbox.
    """
    citations = [getattr(p, "citation_count", 0) for p in papers]
    titles = [getattr(p, "title", "")[:40] for p in papers]

    return textwrap.dedent(f"""\
        citations = {citations}
        titles = {json.dumps(titles)}
        total = sum(citations)
        avg = total / len(citations) if citations else 0
        top = max(citations) if citations else 0
        print(f"angle: {angle.angle_id}")
        print(f"papers analysed: {{len(citations)}}")
        print(f"total citations: {{total}}")
        print(f"avg citations: {{avg:.1f}}")
        print(f"top paper citations: {{top}}")
        print(f"top paper: {{titles[citations.index(top)] if citations else 'n/a'}}")
    """)


# ---------------------------------------------------------------------------
# Node 3 — Verifier
# ---------------------------------------------------------------------------

def verifier_node(state: ResearchState) -> ResearchState:
    """
    Score each angle's evidence for strength.

    Output: state.scores  (list[VerificationScore])
    """
    state.current_node = "verifier"
    threshold = state.evidence_score_threshold
    scores: list[VerificationScore] = []

    for ev in state.evidence:
        angle = next((a for a in state.angles if a.angle_id == ev.angle_id), None)
        score, rationale = _score_evidence(ev, angle, state.papers)
        passed = score >= threshold
        scores.append(VerificationScore(
            angle_id=ev.angle_id,
            score=score,
            rationale=rationale,
            passed=passed,
        ))
        logger.info(
            "Verifier: angle=%s score=%.2f passed=%s", ev.angle_id, score, passed
        )

    state.scores = scores
    return state


def _score_evidence(ev: Evidence, angle: Optional[ResearchAngle], papers: list) -> tuple[float, str]:
    """
    Heuristic scoring (0–1):
      • 0.4 points for having ≥ 2 source papers
      • 0.3 points for sandbox confirmation
      • 0.3 points for high citation weight
    """
    score = 0.0
    reasons = []

    n_sources = len(ev.source_titles)
    if n_sources >= 3:
        score += 0.4
        reasons.append(f"{n_sources} supporting papers")
    elif n_sources >= 1:
        score += 0.2
        reasons.append(f"{n_sources} supporting paper(s)")

    if ev.sandbox_used and ev.sandbox_stdout:
        score += 0.3
        reasons.append("quantitative sandbox confirmation")

    # Citation weight: look up papers by title
    title_set = set(ev.source_titles)
    relevant = [p for p in papers if getattr(p, "title", "") in title_set]
    total_cites = sum(getattr(p, "citation_count", 0) for p in relevant)
    if total_cites > 10_000:
        score += 0.3
        reasons.append(f"high citation weight ({total_cites:,})")
    elif total_cites > 1_000:
        score += 0.15
        reasons.append(f"moderate citation weight ({total_cites:,})")
    elif total_cites > 0:
        score += 0.05
        reasons.append(f"low citation weight ({total_cites:,})")

    score = min(1.0, score)
    rationale = "; ".join(reasons) if reasons else "insufficient evidence"
    return round(score, 3), rationale


# ---------------------------------------------------------------------------
# Node 4 — Claim Extractor
# ---------------------------------------------------------------------------

def claim_extractor_node(state: ResearchState) -> ResearchState:
    """
    Pull verifiable claims from evidence of each passing angle.

    Output: state.claims  (list[Claim])
    """
    state.current_node = "claim_extractor"
    claims: list[Claim] = []
    claim_counter = 0

    # Only extract from angles that passed the evidence threshold
    passing_ids = {s.angle_id for s in state.scores if s.passed}
    target_evidence = [ev for ev in state.evidence if ev.angle_id in passing_ids]

    if not target_evidence:
        # Fall back to all evidence if nothing passed
        target_evidence = state.evidence
        logger.info("ClaimExtractor: no angles passed threshold — extracting from all evidence")

    for ev in target_evidence:
        extracted = _extract_claims(ev, state.topic, claim_counter)
        claims.extend(extracted)
        claim_counter += len(extracted)

    state.claims = claims
    logger.info("ClaimExtractor: extracted %d claims", len(claims))
    return state


def _extract_claims(ev: Evidence, topic: str, counter_start: int) -> list[Claim]:
    """
    Extract 1–3 claims from an Evidence block.
    Tries Gemini; falls back to sentence-splitting the summary.
    """
    prompt = textwrap.dedent(f"""\
        Extract 1–3 short, verifiable factual claims from the evidence summary below.
        Each claim must be a single declarative sentence that can be checked against sources.

        Topic: {topic}
        Evidence summary: {ev.summary}
        Sources: {', '.join(ev.source_titles[:3])}

        Return ONLY valid JSON — a list of claim strings.
        Example: ["Transformers outperform RNNs on sequence tasks.", "Attention is O(n²) in sequence length."]
    """)

    llm_text = _call_gemini(prompt, max_tokens=256)
    raw_claims: list[str] = []

    if llm_text:
        parsed = _parse_json_block(llm_text)
        if isinstance(parsed, list):
            raw_claims = [str(c) for c in parsed[:3]]

    if not raw_claims:
        # Fallback: split summary into sentences, take first 2
        sentences = [s.strip() for s in ev.summary.split(".") if len(s.strip()) > 20]
        raw_claims = sentences[:2]

    if not raw_claims:
        raw_claims = [f"{topic} is studied via {ev.angle_id}."]

    claims = []
    for i, text in enumerate(raw_claims):
        claims.append(Claim(
            claim_id=f"claim_{counter_start + i}",
            angle_id=ev.angle_id,
            text=text.strip(),
            source_titles=ev.source_titles[:3],
        ))
    return claims


# ---------------------------------------------------------------------------
# Node 5 — Fact Checker
# ---------------------------------------------------------------------------

def fact_checker_node(state: ResearchState) -> ResearchState:
    """
    Cross-reference each claim against the paper corpus.

    Output: state.verifications  (list[ClaimVerification])
    """
    state.current_node = "fact_checker"
    verifications: list[ClaimVerification] = []

    for claim in state.claims:
        v = _verify_claim(claim, state.papers, state.topic)
        verifications.append(v)
        logger.info(
            "FactChecker: claim=%s verdict=%s confidence=%.2f",
            claim.claim_id, v.verdict, v.confidence,
        )

    state.verifications = verifications
    return state


def _verify_claim(claim: Claim, papers: list, topic: str) -> ClaimVerification:
    """
    Attempt LLM cross-reference; fall back to keyword-overlap heuristic.
    """
    # Build a small context from papers whose titles are in the claim sources
    title_set = set(claim.source_titles)
    relevant = [p for p in papers if getattr(p, "title", "") in title_set]
    if not relevant:
        relevant = _find_relevant_papers(claim.text, papers, top_k=3)

    context_lines = []
    for p in relevant[:3]:
        abstract = getattr(p, "abstract", "")[:200]
        context_lines.append(f"- {getattr(p, 'title', '?')}: {abstract}")

    prompt = textwrap.dedent(f"""\
        You are a fact-checker.  Given the claim and supporting literature context,
        decide whether the claim is SUPPORTED, REFUTED, or UNVERIFIABLE.

        Claim: {claim.text}

        Literature context:
        {chr(10).join(context_lines)}

        Return ONLY valid JSON with keys:
          verdict       ("SUPPORTED" | "REFUTED" | "UNVERIFIABLE")
          confidence    (float 0.0–1.0)
          rationale     (one sentence)

        Example: {{"verdict": "SUPPORTED", "confidence": 0.85, "rationale": "Multiple papers confirm this."}}
    """)

    llm_text = _call_gemini(prompt, max_tokens=128)
    if llm_text:
        parsed = _parse_json_block(llm_text)
        if isinstance(parsed, dict) and "verdict" in parsed:
            verdict = str(parsed.get("verdict", "UNVERIFIABLE")).upper()
            if verdict not in ("SUPPORTED", "REFUTED", "UNVERIFIABLE"):
                verdict = "UNVERIFIABLE"
            confidence = float(parsed.get("confidence", 0.5))
            return ClaimVerification(
                claim_id=claim.claim_id,
                supported=verdict == "SUPPORTED",
                confidence=confidence,
                supporting_sources=[t for t in claim.source_titles if verdict == "SUPPORTED"],
                contradicting_sources=[t for t in claim.source_titles if verdict == "REFUTED"],
                verdict=verdict,
            )

    # Heuristic fallback: keyword overlap with abstracts
    claim_words = set(claim.text.lower().split())
    supporting = []
    contradicting = []
    for p in relevant:
        abstract_words = set(getattr(p, "abstract", "").lower().split())
        overlap = len(claim_words & abstract_words)
        if overlap >= 3:
            supporting.append(getattr(p, "title", ""))
        # Simple negation heuristic
        if any(neg in getattr(p, "abstract", "").lower() for neg in ["however", "contrary", "disagree", "refute"]):
            contradicting.append(getattr(p, "title", ""))

    if supporting:
        verdict = "SUPPORTED"
        confidence = min(0.5 + 0.1 * len(supporting), 0.85)
    elif not relevant:
        verdict = "UNVERIFIABLE"
        confidence = 0.2
    else:
        verdict = "UNVERIFIABLE"
        confidence = 0.35

    return ClaimVerification(
        claim_id=claim.claim_id,
        supported=verdict == "SUPPORTED",
        confidence=round(confidence, 3),
        supporting_sources=supporting[:3],
        contradicting_sources=contradicting[:2],
        verdict=verdict,
    )
