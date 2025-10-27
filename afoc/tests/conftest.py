"""Test configuration for pytest."""

from __future__ import annotations

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
