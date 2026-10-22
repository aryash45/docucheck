"""Shared pytest controls for deterministic local tests."""

import pytest


@pytest.fixture(autouse=True)
def disable_external_services_for_local_tests(monkeypatch, request):
    """Prevent local tests from using configured Gemini or E2B credentials."""
    if "integration" not in request.node.keywords:
        monkeypatch.setenv("GEMINI_API_KEY", "your_dummy")
        monkeypatch.setenv("E2B_API_KEY", "your_dummy")
