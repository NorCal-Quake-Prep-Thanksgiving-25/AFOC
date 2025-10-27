"""Tests for CSV ingestion utilities."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

try:  # pragma: no cover - optional dependency guard
    import polars as pl
    from afoc.db.models import UsageEvent
    from afoc.ingest import (
        load_aws_cur_csv,
        load_generic_usage_csv,
        load_openai_usage_csv,
    )
except ImportError:  # pragma: no cover - skip when ingestion deps missing
    pl = None  # type: ignore
    UsageEvent = None  # type: ignore
    load_aws_cur_csv = None  # type: ignore
    load_generic_usage_csv = None  # type: ignore
    load_openai_usage_csv = None  # type: ignore

pytestmark = pytest.mark.skipif(
    pl is None or UsageEvent is None,
    reason="polars/sqlalchemy dependencies not available",
)


def _write_csv(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    content = ",".join(headers) + "\n"
    for row in rows:
        values = [str(value) for value in row]
        content += ",".join(values) + "\n"
    path.write_text(content, encoding="utf-8")


@pytest.fixture()
def base_timestamp() -> datetime:
    return datetime(2024, 1, 1, 12, 0, 0)


def test_load_openai_usage_csv_inserts_usage_events(session, tmp_path: Path, base_timestamp: datetime) -> None:
    """The OpenAI loader should normalise data and insert usage events."""

    csv_path = tmp_path / "openai_usage.csv"
    headers = [
        "timestamp",
        "project_id",
        "model",
        "cost_usd",
        "prompt_tokens",
        "completion_tokens",
    ]
    rows = [
        [base_timestamp.isoformat(), "proj-a", "gpt-4", 2.5, 1000, 500],
        [(base_timestamp + timedelta(days=1)).isoformat(), "proj-a", "gpt-4", 3.0, 1200, 600],
    ]
    _write_csv(csv_path, headers, rows)

    df = load_openai_usage_csv(csv_path, session=session)

    assert isinstance(df, pl.DataFrame)
    assert df.shape[0] == 2
    assert df.columns == ["occurred_at", "provider", "account", "service", "cost_usd", "metadata"]

    events = session.query(UsageEvent).order_by(UsageEvent.id).all()
    assert len(events) == 2
    assert events[0].source == "openai"
    assert events[0].service == "gpt-4"
    assert events[0].metadata["prompt_tokens"] == 1000


def test_load_aws_cur_csv_inserts_usage_events(session, tmp_path: Path, base_timestamp: datetime) -> None:
    """AWS CUR loader should standardise AWS exports."""

    csv_path = tmp_path / "aws_cur.csv"
    headers = [
        "line_item_usage_start_date",
        "product_product_name",
        "line_item_unblended_cost",
        "line_item_usage_account_id",
        "line_item_usage_type",
    ]
    rows = [
        [base_timestamp.isoformat(), "AmazonEC2", 10.25, "123456789012", "BoxUsage:t3.micro"],
        [
            (base_timestamp + timedelta(days=1)).isoformat(),
            "AmazonEC2",
            11.75,
            "123456789012",
            "BoxUsage:t3.micro",
        ],
    ]
    _write_csv(csv_path, headers, rows)

    df = load_aws_cur_csv(csv_path, session=session)

    assert isinstance(df, pl.DataFrame)
    assert df.shape[0] == 2
    assert df.select("provider").item() == "aws"

    events = session.query(UsageEvent).order_by(UsageEvent.id).all()
    assert len(events) == 4  # includes previous test inserts
    assert events[-1].metadata["line_item_usage_type"] == "BoxUsage:t3.micro"


def test_load_generic_usage_csv_allows_custom_mapping(session, tmp_path: Path, base_timestamp: datetime) -> None:
    """Generic loader should honour explicit column mappings."""

    csv_path = tmp_path / "custom.csv"
    headers = ["ts", "svc", "amount", "tenant", "notes"]
    rows = [
        [base_timestamp.isoformat(), "storage", 5.5, "tenant-a", "coldline"],
        [(base_timestamp + timedelta(days=1)).isoformat(), "storage", 6.0, "tenant-b", "standard"],
    ]
    _write_csv(csv_path, headers, rows)

    df = load_generic_usage_csv(
        csv_path,
        mapping={
            "timestamp": "ts",
            "service": "svc",
            "cost": "amount",
            "provider": "custom-provider",
            "account": "tenant",
            "metadata": ["notes"],
        },
        session=session,
    )

    assert isinstance(df, pl.DataFrame)
    assert df.shape[0] == 2
    assert df.select("provider").to_series().to_list() == ["custom-provider", "custom-provider"]

    events = session.query(UsageEvent).order_by(UsageEvent.id).all()
    assert len(events) == 6
    assert events[-1].source == "custom-provider"
    assert events[-1].metadata["notes"] == "standard"
