"""Bounded citation URL resolution with explicit status reporting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlparse

import requests


@dataclass
class CitationStatus:
    source_id: str
    url: str
    status: str  # resolved | unresolved | invalid | not_checked
    http_status: int | None = None
    final_url: str = ""
    reason: str = ""
    checked_at: str = ""


class CitationResolver:
    """Resolve source URLs without failing the fact-check run."""

    def __init__(
        self,
        timeout_seconds: float = 8.0,
        request_fn: Callable[..., Any] | None = None,
    ):
        self.timeout_seconds = timeout_seconds
        self.request_fn = request_fn or requests.head

    def resolve(self, source_id: str, url: str) -> CitationStatus:
        checked_at = datetime.now(timezone.utc).isoformat()
        if not url:
            return CitationStatus(source_id, url, "not_checked", reason="URL missing")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return CitationStatus(source_id, url, "invalid", reason="Unsupported URL")
        try:
            response = self.request_fn(
                url,
                allow_redirects=True,
                timeout=self.timeout_seconds,
                headers={"User-Agent": "DocuCheck/phase2"},
            )
            status = "resolved" if 200 <= response.status_code < 400 else "unresolved"
            return CitationStatus(
                source_id=source_id,
                url=url,
                status=status,
                http_status=response.status_code,
                final_url=getattr(response, "url", "") or url,
                reason="" if status == "resolved" else f"HTTP {response.status_code}",
                checked_at=checked_at,
            )
        except Exception as exc:
            return CitationStatus(
                source_id=source_id,
                url=url,
                status="unresolved",
                reason=str(exc)[:200],
                checked_at=checked_at,
            )

    def resolve_papers(self, papers: list) -> list[CitationStatus]:
        statuses = []
        for paper in papers:
            statuses.append(self.resolve(
                str(getattr(paper, "paper_id", "")),
                str(getattr(paper, "url", "") or ""),
            ))
        return statuses
