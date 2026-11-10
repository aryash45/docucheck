import pytest

from src.citations.resolver import CitationResolver

pytestmark = pytest.mark.local


class FakeResponse:
    def __init__(self, status_code, url):
        self.status_code = status_code
        self.url = url


def test_resolver_records_redirected_success():
    def request(url, **kwargs):
        assert kwargs["allow_redirects"] is True
        return FakeResponse(200, "https://example.test/final")

    status = CitationResolver(request_fn=request).resolve(
        "paper_1", "https://example.test/start"
    )

    assert status.status == "resolved"
    assert status.http_status == 200
    assert status.final_url.endswith("final")


def test_resolver_handles_invalid_and_missing_urls():
    resolver = CitationResolver(request_fn=lambda *_args, **_kwargs: None)
    assert resolver.resolve("missing", "").status == "not_checked"
    assert resolver.resolve("bad", "ftp://example.test/paper").status == "invalid"


def test_resolver_converts_http_failure_to_status():
    status = CitationResolver(
        request_fn=lambda *_args, **_kwargs: FakeResponse(404, "https://example.test/nope")
    ).resolve("paper_1", "https://example.test/nope")
    assert status.status == "unresolved"
    assert status.http_status == 404
