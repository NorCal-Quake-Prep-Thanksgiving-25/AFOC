"""Tests for the FastAPI layer."""

import pytest

try:
    from fastapi.testclient import TestClient
    from afoc.api.app import create_app
except ImportError:  # pragma: no cover - dependency may be missing in CI
    TestClient = None  # type: ignore
    create_app = None  # type: ignore


@pytest.mark.skipif(TestClient is None or create_app is None, reason="FastAPI not available")
def test_ingest_sample_endpoint() -> None:
    """The ingest sample endpoint should return placeholder data."""

    client = TestClient(create_app())  # type: ignore[operator]
    response = client.get("/ingest/sample")
    assert response.status_code == 200
    assert response.json()[0]["id"] == 1
