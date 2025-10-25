"""Data fabric orchestrating relational and cache storage."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Generator, Optional

try:  # pragma: no cover - optional dependency
    from sqlalchemy import Column, Float, MetaData, String, Table, create_engine
    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import sessionmaker
except Exception:  # pragma: no cover - fallback
    Column = Float = String = Table = MetaData = None  # type: ignore
    create_engine = None
    Engine = None
    sessionmaker = None


@dataclass
class DataFabricConfig:
    database_url: str = "sqlite:///:memory:"
    echo: bool = False


class DataFabric:
    """Abstraction over relational store with Redis-style cache hook."""

    def __init__(self, config: DataFabricConfig | None = None) -> None:
        self.config = config or DataFabricConfig()
        self._engine: Engine | None = None
        self._Session = None
        self._cache: Dict[str, Any] = {}
        if create_engine is not None:
            self._engine = create_engine(self.config.database_url, echo=self.config.echo)
            self._Session = sessionmaker(bind=self._engine)
            self._metadata = MetaData()
            self._ensure_tables()
        else:
            self._metadata = None

    def _ensure_tables(self) -> None:
        if self._engine is None or Table is None:
            return
        Table(
            "spend_records",
            self._metadata,
            Column("id", String, primary_key=True),
            Column("workload", String),
            Column("amount", Float),
        )
        self._metadata.create_all(self._engine)

    @contextmanager
    def session(self) -> Generator[Any, None, None]:
        if self._Session is None:
            yield None
            return
        session = self._Session()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    def cache_set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self._cache[key] = value

    def cache_get(self, key: str) -> Any | None:
        return self._cache.get(key)

    def store_spend(self, record_id: str, workload: str, amount: float) -> None:
        if self._engine is None or self._Session is None:
            self.cache_set(f"spend:{record_id}", {"workload": workload, "amount": amount})
            return
        with self.session() as session:
            if session is None:
                return
            session.execute(
                "INSERT OR REPLACE INTO spend_records(id, workload, amount) VALUES (?, ?, ?)",
                (record_id, workload, amount),
            )

    def fetch_spend(self, workload: str) -> float:
        cached = self.cache_get(f"spend:{workload}")
        if cached:
            return float(cached["amount"])
        if self._engine is None or self._Session is None:
            return 0.0
        with self.session() as session:
            if session is None:
                return 0.0
            result = session.execute(
                "SELECT amount FROM spend_records WHERE workload=?", (workload,)
            ).fetchone()
            if result:
                return float(result[0])
        return 0.0
