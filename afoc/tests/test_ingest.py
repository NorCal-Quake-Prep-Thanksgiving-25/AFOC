"""Tests for ingestion utilities."""

from afoc.ingest import load_placeholder_dataset


def test_load_placeholder_dataset_returns_default() -> None:
    """The loader should provide a non-empty placeholder dataset."""

    data = load_placeholder_dataset()
    assert isinstance(data, list)
    assert data[0]["id"] == 1
