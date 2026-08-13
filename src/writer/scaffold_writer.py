

from __future__ import annotations

import logging
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VERDICT_EMOJI = {
    "SUPPORTED":    "✅",
    "REFUTED":      "❌",
    "UNVERIFIABLE": "⚠️",
}

_SCORE_BAR_WIDTH = 20  # characters for the ASCII progress bar


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

@dataclass
class WriterResult:
    """Paths of every file the writer produced."""
    scaffold_path: str
    fact_check_path: str
    sources_path: str

    def summary(self) -> str:
        return (
            f"  📄 {self.scaffold_path}\n"
            f"  🔍 {self.fact_check_path}\n"
            f"  📚 {self.sources_path}"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score_bar(score: float, width: int = _SCORE_BAR_WIDTH) -> str:
    """Render a compact ASCII progress bar, e.g. ████████░░░░ 0.65."""
    filled = round(score * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"`{bar}` {score:.2f}"


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.80:
        return "High"
    if confidence >= 0.50:
        return "Medium"
    return "Low"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _wrap(text: str, width: int = 88) -> str:
    """Soft-wrap long prose for readable Markdown."""
    return "\n".join(
        textwrap.fill(line, width) if len(line) > width else line
        for line in text.splitlines()
    )


def _paper_lookup(papers: list) -> dict[str, Any]:
    """Title -> Paper object map for quick lookups."""
    return {getattr(p, "title", ""): p for p in papers}


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------

class ScaffoldWriter:
    """
    Renders three Markdown output files from the ResearchGraph evidence map.

    Parameters
    ----------
    output_dir : str | Path
        Directory where the three files will be written.  Created if absent.
    """

    def __init__(self, output_dir: str | Path = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write(self, evidence_map: dict, papers: list) -> WriterResult:
        """
        Write all three output files from the evidence map dict.

        Parameters
        ----------
        evidence_map : dict
            The dict returned by ``ResearchGraph.run()``.
        papers : list[Paper]
            The original paper corpus (``LiteraturePipeline.fetch()`` output).
            Used to enrich the bibliography with full metadata.

        Returns
        -------
        WriterResult
            Dataclass holding the path of each file written.
        """
        paper_map = _paper_lookup(papers)

        scaffold_path = self._write_scaffold(evidence_map, paper_map)
        fact_check_path = self._write_fact_check_card(evidence_map)
        sources_path = self._write_sources(evidence_map, paper_map)

        result = WriterResult(
            scaffold_path=str(scaffold_path),
            fact_check_path=str(fact_check_path),
            sources_path=str(sources_path),
        )
        logger.info("ScaffoldWriter: wrote 3 files\n%s", result.summary())
        return result

    def write_from_state(self, state) -> WriterResult:
        """
        Convenience entry point that accepts a ``ResearchState`` object directly.

        Parameters
        ----------
        state : ResearchState
            Must have ``state.output`` populated (i.e., the graph has finished).

        Returns
        -------
        WriterResult
        """
        if state.output is None:
            raise ValueError(
                "ResearchState.output is None — run the graph first "
                "(graph.run_from_state(state) sets state.output)."
            )
        return self.write(state.output, state.papers)

    # ------------------------------------------------------------------
    # File 1 — research_scaffold.md
    # ------------------------------------------------------------------

    def _write_scaffold(self, em: dict, paper_map: dict) -> Path:
        """Build and write research_scaffold.md."""
        lines: list[str] = []

        topic = em.get("topic", "Unknown topic")
        budget = em.get("budget", {})
        errors = em.get("errors", [])

        # ---- Header ----
        lines += [
            "# Research Scaffold",
            "",
            f"> **Topic:** {topic}  ",
            f"> **Generated:** {_ts()}  ",
            f"> **Budget used:** ${budget.get('spent_usd', 0):.4f} / "
            f"${budget.get('allocated_usd', 0):.4f}",
            "",
            "---",
            "",
        ]

        # ---- Topic Overview ----
        lines += [
            "## Topic Overview",
            "",
            _wrap(
                f"This scaffold summarises the automated research conducted on "
                f"**{topic}**. The pipeline retrieved academic papers, generated "
                f"research angles, gathered evidence for each angle, scored the "
                f"strength of that evidence, extracted verifiable claims, and "
                f"fact-checked each claim against the source literature."
            ),
            "",
        ]

        angles_data   = em.get("angles", [])
        evidence_data = em.get("evidence", [])
        scores_data   = em.get("scores", [])
        claims_data   = em.get("claims", [])
        verif_data    = em.get("verifications", [])

        passed_count    = sum(1 for s in scores_data if s.get("passed", False))
        supported_count = sum(1 for v in verif_data if v.get("verdict") == "SUPPORTED")

        lines += [
            "| Metric | Value |",
            "| --- | --- |",
            f"| Research angles generated | {len(angles_data)} |",
            f"| Angles with passing evidence | {passed_count} |",
            f"| Claims extracted | {len(claims_data)} |",
            f"| Claims verified as SUPPORTED | {supported_count} |",
            "",
            "---",
            "",
        ]

        # ---- Per-angle sections ----
        lines += ["## Research Angles", ""]

        evidence_by_angle: dict[str, dict] = {
            ev["angle_id"]: ev for ev in evidence_data
        }
        score_by_angle: dict[str, dict] = {
            s["angle_id"]: s for s in scores_data
        }

        for angle in angles_data:
            angle_id     = angle.get("id", "?")
            title        = angle.get("title", "Untitled")
            description  = angle.get("description", "")
            ev           = evidence_by_angle.get(angle_id, {})
            sc           = score_by_angle.get(angle_id, {})

            score        = sc.get("score", 0.0)
            passed       = sc.get("passed", False)
            rationale    = sc.get("rationale", "")
            summary      = ev.get("summary", "_No evidence summary available._")
            sources      = ev.get("sources", [])
            sandbox_used = ev.get("sandbox_used", False)

            status_badge = "✅ PASSED" if passed else "⚠️ BELOW THRESHOLD"

            lines += [
                f"### {angle_id.upper()} — {title}",
                "",
                f"> {description}",
                "",
                f"**Evidence Strength:** {_score_bar(score)}  ",
                f"**Status:** {status_badge}  ",
                f"**Rationale:** {rationale or 'n/a'}  ",
                f"**Quantitative sandbox:** {'used' if sandbox_used else 'not used'}",
                "",
                "#### Evidence Summary",
                "",
                _wrap(summary),
                "",
            ]

            if sources:
                lines += ["#### Key Papers", ""]
                for src_title in sources[:5]:
                    paper = paper_map.get(src_title)
                    if paper:
                        authors_list = getattr(paper, "authors", [])
                        authors_str  = ", ".join(authors_list[:3])
                        if len(authors_list) > 3:
                            authors_str += " et al."
                        url  = getattr(paper, "url", "")
                        year = getattr(paper, "year", "?")
                        cites = getattr(paper, "citation_count", 0)
                        lines.append(
                            f"- **{src_title}** ({year})  \n"
                            f"  _{authors_str}_  \n"
                            f"  Citations: {cites:,}  \n"
                            f"  {url}"
                        )
                    else:
                        lines.append(f"- {src_title}")
                lines.append("")

            lines += ["---", ""]

        # ---- Pipeline warnings ----
        if errors:
            lines += [
                "## Pipeline Warnings",
                "",
                "> The following non-fatal issues were recorded during the run:",
                "",
            ]
            for err in errors:
                lines.append(f"- {err}")
            lines.append("")

        return self._save(lines, "research_scaffold.md")

    # ------------------------------------------------------------------
    # File 2 — fact_check_card.md
    # ------------------------------------------------------------------

    def _write_fact_check_card(self, em: dict) -> Path:
        """Build and write fact_check_card.md."""
        lines: list[str] = []

        topic       = em.get("topic", "Unknown topic")
        claims_data = em.get("claims", [])
        verif_data  = em.get("verifications", [])

        lines += [
            "# Fact-Check Card",
            "",
            f"> **Topic:** {topic}  ",
            f"> **Generated:** {_ts()}  ",
            f"> **Claims checked:** {len(verif_data)}",
            "",
            "---",
            "",
        ]

        # Summary table
        verdict_counts: dict[str, int] = {
            "SUPPORTED": 0, "REFUTED": 0, "UNVERIFIABLE": 0
        }
        for v in verif_data:
            verdict_counts[v.get("verdict", "UNVERIFIABLE")] += 1

        lines += [
            "## Summary",
            "",
            "| Verdict | Count |",
            "| --- | --- |",
            f"| ✅ SUPPORTED | {verdict_counts['SUPPORTED']} |",
            f"| ❌ REFUTED | {verdict_counts['REFUTED']} |",
            f"| ⚠️ UNVERIFIABLE | {verdict_counts['UNVERIFIABLE']} |",
            "",
            "---",
            "",
            "## Claims",
            "",
        ]

        # Build claim-text lookup (handle both "id" and "claim_id" key variants)
        claim_by_id: dict[str, dict] = {}
        for c in claims_data:
            key = c.get("id") or c.get("claim_id", "?")
            claim_by_id[key] = c

        if not verif_data:
            lines += ["_No claims were verified in this run._", ""]
        else:
            for v in verif_data:
                claim_id   = v.get("claim_id", "?")
                verdict    = v.get("verdict", "UNVERIFIABLE")
                confidence = float(v.get("confidence", 0.0))
                supported  = v.get("supported_by", [])
                emoji      = _VERDICT_EMOJI.get(verdict, "⚠️")
                conf_label = _confidence_label(confidence)

                claim_obj  = claim_by_id.get(claim_id, {})
                claim_text = claim_obj.get("text", "_Claim text unavailable._")
                angle_id   = claim_obj.get("angle_id", "")

                lines += [
                    f"### {claim_id}",
                    "",
                    f"> {claim_text}",
                    "",
                    "| Field | Value |",
                    "| --- | --- |",
                    f"| Verdict | {emoji} **{verdict}** |",
                    f"| Confidence | {confidence:.2f} ({conf_label}) |",
                    f"| Research angle | {angle_id or 'n/a'} |",
                ]

                if supported:
                    src_str = "; ".join(f"*{s}*" for s in supported)
                    lines.append(f"| Supporting sources | {src_str} |")

                contradicting = v.get("contradicting_sources", [])
                if contradicting:
                    con_str = "; ".join(f"*{s}*" for s in contradicting)
                    lines.append(f"| Contradicting sources | {con_str} |")

                lines += ["", "---", ""]

        return self._save(lines, "fact_check_card.md")

    # ------------------------------------------------------------------
    # File 3 — sources.md
    # ------------------------------------------------------------------

    def _write_sources(self, em: dict, paper_map: dict) -> Path:
        """Build and write sources.md."""
        lines: list[str] = []

        topic = em.get("topic", "Unknown topic")

        lines += [
            "# Sources",
            "",
            f"> **Topic:** {topic}  ",
            f"> **Generated:** {_ts()}",
            "",
            "---",
            "",
            "## Bibliography",
            "",
        ]

        # Collect titles cited in evidence/verifications
        referenced_titles: set[str] = set()
        for ev in em.get("evidence", []):
            referenced_titles.update(ev.get("sources", []))
        for v in em.get("verifications", []):
            referenced_titles.update(v.get("supported_by", []))

        # Include full corpus too — entries marked with a star if cited
        all_titles = referenced_titles | set(paper_map.keys())

        papers_to_list = sorted(
            (p for t, p in paper_map.items() if t in all_titles),
            key=lambda p: getattr(p, "citation_count", 0),
            reverse=True,
        )

        if not papers_to_list:
            lines += ["_No papers were used in this run._", ""]
        else:
            lines += [
                f"Total papers in corpus: **{len(paper_map)}**  ",
                f"Papers cited in evidence: **{len(referenced_titles)}**",
                "",
            ]
            for i, paper in enumerate(papers_to_list, 1):
                title   = getattr(paper, "title", "Unknown")
                authors = getattr(paper, "authors", [])
                year    = getattr(paper, "year", "?")
                cites   = getattr(paper, "citation_count", 0)
                url     = getattr(paper, "url", "")
                source  = getattr(paper, "source", "")

                author_str = "; ".join(authors[:5])
                if len(authors) > 5:
                    author_str += f" + {len(authors) - 5} more"

                cited_badge = "⭐ " if title in referenced_titles else ""

                lines += [
                    f"### [{i}] {cited_badge}{title}",
                    "",
                    "| Field | Value |",
                    "| --- | --- |",
                    f"| Authors | {author_str or 'Unknown'} |",
                    f"| Year | {year} |",
                    f"| Citation count | {cites:,} |",
                    f"| Source | {source} |",
                ]
                if url:
                    lines.append(f"| URL | [{url}]({url}) |")
                lines += ["", "---", ""]

        return self._save(lines, "sources.md")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _save(self, lines: list[str], filename: str) -> Path:
        path = self.output_dir / filename
        content = "\n".join(lines)
        path.write_text(content, encoding="utf-8")
        logger.info("ScaffoldWriter: wrote %s (%d bytes)", path, len(content))
        return path
