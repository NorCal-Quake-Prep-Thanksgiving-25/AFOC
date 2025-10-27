"""Test configuration for pytest."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

try:  # pragma: no cover - optional dependency guard
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.pool import StaticPool
    from afoc.db.models import Base

    SQLALCHEMY_AVAILABLE = True
except ImportError:  # pragma: no cover - used to skip tests when unavailable
    SQLALCHEMY_AVAILABLE = False
    Session = object  # type: ignore

# Ensure the repository root is on the Python path for package imports.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def session() -> Session:
    """Provide an in-memory SQLite session for tests."""

    if not SQLALCHEMY_AVAILABLE:  # pragma: no cover - skip when dependency missing
        pytest.skip("sqlalchemy is required for ingestion tests")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    db_session = factory()
    try:
        yield db_session
        db_session.commit()
    finally:
        db_session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _isolate_database(tmp_path: Path) -> None:
    """Point database configuration at an isolated SQLite database."""

    db_path = tmp_path / "afoc.sqlite"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["AFOC_TELEMETRY_URL"] = f"sqlite:///{db_path}"
    os.environ["API_TOKENS"] = "test-token"
    from afoc.config import get_settings

    try:
        from afoc.db import get_engine, get_session_factory
        from afoc.db.models import Base
    except ModuleNotFoundError:  # pragma: no cover - dependency optional
        pytest.skip("sqlalchemy is required for database-backed tests")

    get_settings.cache_clear()  # type: ignore[attr-defined]
    get_engine.cache_clear()  # type: ignore[attr-defined]
    get_session_factory.cache_clear()  # type: ignore[attr-defined]
    engine = get_engine()
    Base.metadata.create_all(engine)
