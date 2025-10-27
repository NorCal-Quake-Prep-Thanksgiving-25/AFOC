"""Tests for right-sizing services."""

from afoc.services import rightsizing


def test_generate_recommendations_returns_list() -> None:
    """Ensure the right-sizing service returns a list."""

    result = rightsizing.generate_recommendations([{"resource": "test"}])
    assert isinstance(result, list)
