"""Data fabric orchestrating relational, cache, and ingestion services."""

from __future__ import annotations

import time
import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Generator, Iterable, List, Optional

try:  # pragma: no cover - optional dependency
    from sqlalchemy import Column, Float, MetaData, String, Table, create_engine, delete, select
    from sqlalchemy.engine import Engine
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.orm import Session, sessionmaker
except Exception:  # pragma: no cover - fallback
    Column = Float = String = Table = MetaData = None  # type: ignore
    create_engine = None
    delete = None
    select = None
    Engine = None
    Session = None
    SQLAlchemyError = Exception  # type: ignore
    sessionmaker = None

try:  # pragma: no cover - optional dependency
    import redis
except Exception:  # pragma: no cover - fallback
    redis = None  # type: ignore

from ..credentials import CredentialProvider, default_credential_provider
from ..logging import get_logger


logger = get_logger(__name__)


@dataclass
class DataFabricConfig:
    """Configuration for the shared data fabric."""

    database_url: str | None = None
    cache_url: str | None = None
    echo: bool = False
    pool_size: int = 5
    connect_args: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestionReport:
    """Outcome of a data ingestion run."""

    ingested: int
    cached: int
    failed: List[str]
    started_at: datetime
    completed_at: datetime


class DataFabric:
    """Abstraction over relational store with cache and ingestion utilities."""

    def __init__(
        self,
        config: DataFabricConfig | None = None,
        credential_provider: CredentialProvider | None = None,
    ) -> None:
        self.credential_provider = credential_provider or default_credential_provider
        self.config = self._resolve_config(config or DataFabricConfig())
        self._engine: Engine | None = None
        self._Session: Any | None = None
        self._metadata: Any | None = None
        self._spend_table: Any | None = None
        self._cache: Dict[str, Any] = {}
        self._redis: Any | None = None
        self._initialise_relational()
        self._initialise_cache()

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    def _resolve_config(self, config: DataFabricConfig) -> DataFabricConfig:
        resolved = DataFabricConfig(
            database_url=config.database_url
            or self.credential_provider.get_secret("database_url")
            or "sqlite:///:memory:",
            cache_url=config.cache_url or self.credential_provider.get_secret("cache_url"),
            echo=config.echo,
            pool_size=config.pool_size,
            connect_args=dict(config.connect_args),
        )
        return resolved

    # ------------------------------------------------------------------
    # Relational storage
    # ------------------------------------------------------------------
    def _initialise_relational(self) -> None:
        if create_engine is None:
            logger.warning("SQLAlchemy not available; DataFabric operating in cache-only mode")
            return
        try:
            self._engine = create_engine(
                self.config.database_url,
                echo=self.config.echo,
                pool_size=self.config.pool_size,
                connect_args=self.config.connect_args,
            )
            self._Session = sessionmaker(bind=self._engine)
            self._metadata = MetaData()
            self._spend_table = Table(
                "spend_records",
                self._metadata,
                Column("id", String, primary_key=True),
                Column("workload", String, index=True),
                Column("amount", Float),
                Column("source", String, default="manual"),
            )
            self._metadata.create_all(self._engine)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error("Failed to initialise relational store", error=str(exc))
            self._engine = None
            self._Session = None
            self._metadata = None
            self._spend_table = None

    def _initialise_cache(self) -> None:
        cache_url = self.config.cache_url
        if redis is None or not cache_url:
            return
        try:
            self._redis = redis.Redis.from_url(cache_url)
            self._redis.ping()
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("Redis unavailable; falling back to in-memory cache", error=str(exc))
            self._redis = None

    @contextmanager
    def session(self) -> Generator[Session | None, None, None]:
        if self._Session is None:
            yield None
            return
        session = self._Session()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as exc:  # pragma: no cover - optional dependency
            session.rollback()
            logger.error("DataFabric session error", error=str(exc))
            raise
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------
    def cache_set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if self._redis is not None:
            try:
                serialised = json.dumps(value)
            except TypeError:
                serialised = json.dumps({"value": value})
            if ttl:
                self._redis.setex(key, ttl, serialised)
            else:
                self._redis.set(key, serialised)
            return
        self._cache[key] = value

    def cache_get(self, key: str) -> Any | None:
        if self._redis is not None:
            payload = self._redis.get(key)
            if payload is None:
                return None
            try:
                return json.loads(payload)
            except Exception:  # pragma: no cover - defensive
                return None
        return self._cache.get(key)

    def cache_delete(self, key: str) -> None:
        if self._redis is not None:
            self._redis.delete(key)
        else:
            self._cache.pop(key, None)

    # ------------------------------------------------------------------
    # CRUD utilities
    # ------------------------------------------------------------------
    def store_spend(
        self, record_id: str, workload: str, amount: float, source: str = "manual"
    ) -> None:
        payload = {"id": record_id, "workload": workload, "amount": amount, "source": source}
        if self._engine is None or self._Session is None or self._spend_table is None:
            self.cache_set(f"spend:{record_id}", payload)
            return
        with self.session() as session:
            if session is None or self._spend_table is None:
                return
            session.execute(delete(self._spend_table).where(self._spend_table.c.id == record_id))
            session.execute(self._spend_table.insert().values(payload))

    def fetch_spend(self, workload: str) -> float:
        cached = self.cache_get(f"spend:{workload}")
        if cached:
            return float(cached.get("amount", 0.0))
        if (
            self._engine is None
            or self._Session is None
            or self._spend_table is None
            or select is None
        ):
            return 0.0
        with self.session() as session:
            if session is None:
                return 0.0
            result = session.execute(
                select(self._spend_table.c.amount).where(self._spend_table.c.workload == workload)
            ).fetchone()
            if result:
                amount = float(result[0])
                self.cache_set(f"spend:{workload}", {"workload": workload, "amount": amount})
                return amount
        return 0.0

    # ------------------------------------------------------------------
    # Ingestion orchestration
    # ------------------------------------------------------------------
    def ingest_records(
        self,
        records: Iterable[Dict[str, Any]],
        *,
        source: str = "ingestion",
        max_attempts: int = 3,
        backoff_seconds: float = 0.5,
    ) -> IngestionReport:
        started = datetime.now(timezone.utc)
        ingested = 0
        cached = 0
        failed: List[str] = []
        for item in records:
            record_id = str(item.get("id") or item.get("workload") or f"anon-{ingested}")
            workload = str(item.get("workload", record_id))
            amount = float(item.get("amount", 0.0))
            attempts = 0
            stored = False
            while attempts < max_attempts and not stored:
                attempts += 1
                try:
                    self.store_spend(record_id, workload, amount, source=source)
                    ingested += 1
                    stored = True
                except Exception as exc:  # pragma: no cover - defensive guard
                    if attempts >= max_attempts:
                        logger.error(
                            "Failed to ingest record",
                            record_id=record_id,
                            workload=workload,
                            error=str(exc),
                        )
                        failed.append(record_id)
                    else:
                        time.sleep(backoff_seconds * attempts)
            if not stored:
                self.cache_set(f"spend:{record_id}", {"workload": workload, "amount": amount})
                cached += 1
        completed = datetime.now(timezone.utc)
        return IngestionReport(
            ingested=ingested,
            cached=cached,
            failed=failed,
            started_at=started,
            completed_at=completed,
        )

    # ------------------------------------------------------------------
    # Health reporting
    # ------------------------------------------------------------------
    def healthcheck(self) -> Dict[str, Any]:
        relational = self._engine is not None
        cache_ready = self._redis is not None
        return {
            "relational": relational,
            "cache": cache_ready,
            "database_url": self.config.database_url,
            "cache_url": self.config.cache_url,
        }

    def close(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
        if self._redis is not None:
            try:
                self._redis.close()
            except Exception as exc:  # pragma: no cover - redis close optional
                logger.debug("Failed to close redis connection", error=str(exc))
