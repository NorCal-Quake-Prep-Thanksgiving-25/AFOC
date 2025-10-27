"""CSV ingestion utilities for usage data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Mapping, Sequence, cast

import polars as pl
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..db.models import Base, UsageEvent


@dataclass
class _SessionHandle:
    """Container describing a managed SQLAlchemy session."""

    session: Session
    created: bool


def _ensure_session(session: Session | None = None) -> _SessionHandle:
    """Return a usable session, creating one from configuration if needed."""

    if session is not None:
        return _SessionHandle(session=session, created=False)
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    return _SessionHandle(session=factory(), created=True)


def _finalise_session(handle: _SessionHandle, exc: Exception | None) -> None:
    """Commit/rollback and close sessions created on demand."""

    session = handle.session
    if handle.created:
        try:
            if exc is None:
                session.commit()
            else:
                session.rollback()
        finally:
            session.close()


def _persist_usage_events(
    records: pl.DataFrame, session: Session | None = None
) -> pl.DataFrame:
    """Insert the provided usage events into the database."""

    handle = _ensure_session(session)
    exc: Exception | None = None
    try:
        for payload in records.to_dicts():
            occurred_at = payload.get("occurred_at")
            if isinstance(occurred_at, str):
                occurred_at = datetime.fromisoformat(occurred_at)
            metadata = payload.get("metadata") or {}
            if payload.get("account"):
                metadata = {**metadata, "account": payload["account"]}
            event = UsageEvent(
                occurred_at=occurred_at,
                source=payload.get("provider", "unknown"),
                service=payload["service"],
                cost=Decimal(str(payload.get("cost_usd", 0.0))),
                metadata=metadata or None,
            )
            handle.session.add(event)
        handle.session.flush()
    except Exception as err:  # pragma: no cover - defensive rollback
        exc = err
        raise
    finally:
        _finalise_session(handle, exc)
    return records


def _read_csv(path: str | Path) -> pl.DataFrame:
    """Load a CSV file with sensible defaults for timestamps."""

    return pl.read_csv(path, try_parse_dates=True)


def _validate_usage_records(frame: pl.DataFrame) -> pl.DataFrame:
    """Validate canonical usage records before persistence."""

    required_columns = {"occurred_at", "service", "cost_usd"}
    missing = required_columns.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    if frame.filter(pl.col("occurred_at").is_null()).height:
        raise ValueError("Usage events require an occurred_at timestamp")
    if frame.filter(
        pl.col("service").is_null()
        | (pl.col("service").cast(pl.Utf8).str.strip_chars().eq(""))
    ).height:
        raise ValueError("Usage events require a service identifier")
    if frame.filter(pl.col("cost_usd").is_null() | (pl.col("cost_usd") < 0)).height:
        raise ValueError("Usage cost values must be non-negative")
    return frame


def load_openai_usage_csv(
    path: str | Path, session: Session | None = None
) -> pl.DataFrame:
    """Ingest an OpenAI usage export into canonical usage events."""

    raw = _read_csv(path)
    metadata_cols = [
        column
        for column in raw.columns
        if column not in {"timestamp", "project_id", "model", "cost_usd"}
    ]
    structured = (
        raw.with_columns(
            pl.col("timestamp")
            .str.strptime(pl.Datetime, strict=False)
            .alias("occurred_at"),
            pl.lit("openai").alias("provider"),
            pl.col("project_id").fill_null("default").alias("account"),
            pl.col("model").alias("service"),
            pl.col("cost_usd").cast(pl.Float64).alias("cost_usd"),
            (pl.struct(metadata_cols) if metadata_cols else pl.lit({})).alias(
                "metadata"
            ),
        )
        .select(
            ["occurred_at", "provider", "account", "service", "cost_usd", "metadata"]
        )
        .sort("occurred_at")
    )
    return _persist_usage_events(_validate_usage_records(structured), session=session)


def load_aws_cur_csv(path: str | Path, session: Session | None = None) -> pl.DataFrame:
    """Ingest an AWS Cost and Usage Report export."""

    raw = _read_csv(path)
    metadata_cols = [
        column
        for column in raw.columns
        if column
        not in {
            "line_item_usage_start_date",
            "product_product_name",
            "line_item_unblended_cost",
            "line_item_usage_account_id",
        }
    ]
    structured = (
        raw.with_columns(
            pl.col("line_item_usage_start_date")
            .str.strptime(pl.Datetime, strict=False)
            .alias("occurred_at"),
            pl.lit("aws").alias("provider"),
            pl.col("line_item_usage_account_id").fill_null("unknown").alias("account"),
            pl.col("product_product_name").alias("service"),
            pl.col("line_item_unblended_cost").cast(pl.Float64).alias("cost_usd"),
            (pl.struct(metadata_cols) if metadata_cols else pl.lit({})).alias(
                "metadata"
            ),
        )
        .select(
            ["occurred_at", "provider", "account", "service", "cost_usd", "metadata"]
        )
        .sort("occurred_at")
    )
    return _persist_usage_events(_validate_usage_records(structured), session=session)


def load_generic_usage_csv(
    path: str | Path,
    mapping: Mapping[str, str | Sequence[str] | None],
    session: Session | None = None,
) -> pl.DataFrame:
    """Ingest a custom CSV using an explicit column mapping."""

    raw = _read_csv(path)
    timestamp_key = cast(str, mapping["timestamp"])  # type: ignore[index]
    service_key = cast(str, mapping["service"])  # type: ignore[index]
    cost_key = cast(str, mapping["cost"])  # type: ignore[index]

    def _resolve(
        value: str | Sequence[str] | None, default: str | None = None
    ) -> pl.Expr:
        if value is None:
            return pl.lit(default or "")
        if isinstance(value, str):
            column_name: str = cast(str, value)
            if column_name in raw.columns:
                return pl.col(column_name)  # type: ignore[arg-type]
            return pl.lit(column_name)
        # Sequence of strings representing a struct payload
        sequence_value: Sequence[str] = cast(Sequence[str], value)
        existing = [col for col in sequence_value if col in raw.columns]
        return pl.struct(existing)  # type: ignore[arg-type]

    provider_value: str | Sequence[str] | None = mapping.get("provider")
    account_value: str | Sequence[str] | None = mapping.get("account")
    metadata_value: str | Sequence[str] | None = mapping.get("metadata")
    provider_expr = _resolve(provider_value, default="custom")
    account_expr = _resolve(account_value)
    if metadata_value is None:
        metadata_cols = [
            column
            for column in raw.columns
            if column not in {timestamp_key, service_key, cost_key}
            and column != mapping.get("provider")
            and column != mapping.get("account")
        ]
        metadata_expr = pl.struct(metadata_cols) if metadata_cols else pl.lit({})
    elif isinstance(metadata_value, (list, tuple)):
        metadata_expr = pl.struct([col for col in metadata_value if col in raw.columns])
    else:
        metadata_expr = _resolve(metadata_value)

    structured = (
        raw.with_columns(
            pl.col(timestamp_key)
            .str.strptime(pl.Datetime, strict=False)
            .alias("occurred_at"),
            provider_expr.alias("provider"),
            account_expr.alias("account"),
            pl.col(service_key).alias("service"),
            pl.col(cost_key).cast(pl.Float64).alias("cost_usd"),
            metadata_expr.alias("metadata"),
        )
        .select(
            ["occurred_at", "provider", "account", "service", "cost_usd", "metadata"]
        )
        .sort("occurred_at")
    )
    return _persist_usage_events(_validate_usage_records(structured), session=session)
