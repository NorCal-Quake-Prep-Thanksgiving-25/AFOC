"""Data fabric orchestrating relational, cache, and ingestion services."""

from __future__ import annotations

import time
import json
from hashlib import sha256
from contextlib import contextmanager
from base64 import urlsafe_b64encode
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hmac
from typing import Any, Dict, Generator, Iterable, List, Optional

try:  # pragma: no cover - optional dependency
    from cryptography.fernet import Fernet
except Exception:  # pragma: no cover - fallback when cryptography is unavailable
    Fernet = None  # type: ignore

try:  # pragma: no cover - optional dependency
    from sqlalchemy import (
        Column,
        Float,
        Integer,
        MetaData,
        String,
        Table,
        Text,
        create_engine,
        delete,
        select,
        update,
    )
    from sqlalchemy.engine import Engine
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.orm import Session, sessionmaker
except Exception:  # pragma: no cover - fallback
    Column = Float = String = Table = MetaData = Integer = Text = None  # type: ignore
    create_engine = None
    delete = None
    select = None
    update = None
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
from ..reliability import JobRecord


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
        self._job_table: Any | None = None
        self._audit_table: Any | None = None
        self._cache: Dict[str, Any] = {}
        self._redis: Any | None = None
        encryption_key = self.credential_provider.get_secret("encryption_key")
        self._fernet_master_key: bytes | None = (
            encryption_key.encode("utf-8") if encryption_key else None
        )
        self._fernet = self._initialise_fernet(self._fernet_master_key)
        self._tenant_fernets: Dict[str, Any] = {}
        self._tenant_namespaces: Dict[str, str] = {}
        self._job_memory: Dict[str, Dict[str, JobRecord]] = {}
        self._audit_memory: List[Dict[str, Any]] = []
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
                Column("tenant_id", String, index=True),
                Column("namespace", String, index=True),
                Column("workload", String, index=True),
                Column("amount", Float),
                Column("source", String, default="manual"),
                Column("payload", String),
            )
            self._job_table = Table(
                "job_queue",
                self._metadata,
                Column("id", String, primary_key=True),
                Column("tenant_id", String, index=True),
                Column("namespace", String, index=True),
                Column("status", String, index=True),
                Column("payload", Text),
                Column("attempts", Integer, default=0),
                Column("last_error", Text),
                Column("scheduled_at", Float),
                Column("available_at", Float),
                Column("worker_id", String),
            )
            self._audit_table = Table(
                "audit_events",
                self._metadata,
                Column("id", String, primary_key=True),
                Column("tenant_id", String, index=True),
                Column("namespace", String, index=True),
                Column("action", String),
                Column("payload", Text),
                Column("created_at", Float),
            )
            self._metadata.create_all(self._engine)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error("Failed to initialise relational store", error=str(exc))
            self._engine = None
            self._Session = None
            self._metadata = None
            self._spend_table = None
            self._job_table = None
            self._audit_table = None

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
        self,
        record_id: str,
        workload: str,
        amount: float,
        *,
        tenant_id: str = "default",
        source: str = "manual",
    ) -> None:
        payload = {
            "id": record_id,
            "tenant_id": tenant_id,
            "namespace": self._tenant_namespace(tenant_id),
            "workload": workload,
            "amount": amount,
            "source": source,
        }
        encrypted = self._encrypt_payload(payload, tenant_id)
        cache_key = self._cache_key(tenant_id, workload)
        if self._engine is None or self._Session is None or self._spend_table is None:
            self.cache_set(cache_key, payload)
            self.append_audit(tenant_id, "spend.store", payload)
            return
        with self.session() as session:
            if session is None or self._spend_table is None:
                return
            session.execute(
                delete(self._spend_table).where(
                    (self._spend_table.c.id == record_id)
                    & (self._spend_table.c.tenant_id == tenant_id)
                )
            )
            session.execute(
                self._spend_table.insert().values(
                    {
                        "id": record_id,
                        "tenant_id": tenant_id,
                        "namespace": payload["namespace"],
                        "workload": workload,
                        "amount": amount,
                        "source": source,
                        "payload": encrypted,
                    }
                )
            )
        self.cache_set(cache_key, payload)
        self.append_audit(tenant_id, "spend.store", payload)

    def fetch_spend(self, workload: str, *, tenant_id: str = "default") -> float:
        cache_key = self._cache_key(tenant_id, workload)
        cached = self.cache_get(cache_key)
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
                select(self._spend_table.c.amount, self._spend_table.c.payload)
                .where(
                    (self._spend_table.c.workload == workload)
                    & (self._spend_table.c.tenant_id == tenant_id)
                )
                .limit(1)
            ).fetchone()
            if result:
                amount = float(result[0])
                payload = self._decrypt_payload(result[1], tenant_id)
                if isinstance(payload, dict):
                    amount = float(payload.get("amount", amount))
                self.cache_set(cache_key, {"workload": workload, "amount": amount})
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
            tenant_id = str(item.get("tenant_id", "default"))
            attempts = 0
            stored = False
            while attempts < max_attempts and not stored:
                attempts += 1
                try:
                    self.store_spend(
                        record_id,
                        workload,
                        amount,
                        tenant_id=tenant_id,
                        source=source,
                    )
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
                self.cache_set(
                    self._cache_key(tenant_id, record_id),
                    {"workload": workload, "amount": amount},
                )
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
            "encryption": bool(self._fernet),
            "tenants_tracked": len(self._tenant_namespaces),
            "job_backend": "relational" if self._job_table is not None else "memory",
        }

    def close(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
        if self._redis is not None:
            try:
                self._redis.close()
            except Exception as exc:  # pragma: no cover - redis close optional
                logger.debug("Failed to close redis connection", error=str(exc))

    # ------------------------------------------------------------------
    # Job queue & audit helpers
    # ------------------------------------------------------------------
    def persist_job(self, job: JobRecord) -> None:
        namespace = self._tenant_namespace(job.tenant_id)
        if self._engine is None or self._Session is None or self._job_table is None:
            tenant_jobs = self._job_memory.setdefault(job.tenant_id, {})
            tenant_jobs[job.job_id] = self._job_copy(job)
            return
        with self.session() as session:
            if session is None:
                tenant_jobs = self._job_memory.setdefault(job.tenant_id, {})
                tenant_jobs[job.job_id] = self._job_copy(job)
                return
            session.execute(
                delete(self._job_table).where(
                    (self._job_table.c.id == job.job_id)
                    & (self._job_table.c.tenant_id == job.tenant_id)
                )
            )
            session.execute(
                self._job_table.insert().values(
                    {
                        "id": job.job_id,
                        "tenant_id": job.tenant_id,
                        "namespace": namespace,
                        "status": job.status,
                        "payload": self._encrypt_payload(job.payload, job.tenant_id),
                        "attempts": job.attempts,
                        "last_error": job.last_error,
                        "scheduled_at": job.scheduled_at.timestamp(),
                        "available_at": job.available_at.timestamp(),
                        "worker_id": job.worker_id,
                    }
                )
            )

    def fetch_job(self, *, tenant_id: str, job_id: str) -> JobRecord | None:
        if (
            self._engine is None
            or self._Session is None
            or self._job_table is None
            or select is None
        ):
            tenant_jobs = self._job_memory.get(tenant_id, {})
            job = tenant_jobs.get(job_id)
            return self._job_copy(job) if job else None
        with self.session() as session:
            if session is None:
                tenant_jobs = self._job_memory.get(tenant_id, {})
                job = tenant_jobs.get(job_id)
                return self._job_copy(job) if job else None
            row = session.execute(
                select(self._job_table).where(
                    (self._job_table.c.id == job_id) & (self._job_table.c.tenant_id == tenant_id)
                )
            ).fetchone()
            if row is None:
                return None
            return self._job_from_mapping(row._mapping)

    def lease_next_job(
        self,
        *,
        tenant_id: str,
        now: datetime,
        worker_id: str,
        visibility_timeout: int,
    ) -> JobRecord | None:
        if (
            self._engine is None
            or self._Session is None
            or self._job_table is None
            or select is None
            or update is None
        ):
            return self._lease_job_memory(
                tenant_id=tenant_id,
                now=now,
                worker_id=worker_id,
                visibility_timeout=visibility_timeout,
            )
        with self.session() as session:
            if session is None:
                return self._lease_job_memory(
                    tenant_id=tenant_id,
                    now=now,
                    worker_id=worker_id,
                    visibility_timeout=visibility_timeout,
                )
            now_ts = now.timestamp()
            row = session.execute(
                select(self._job_table)
                .where(
                    (self._job_table.c.tenant_id == tenant_id)
                    & (self._job_table.c.status == "pending")
                    & (self._job_table.c.available_at <= now_ts)
                )
                .order_by(self._job_table.c.available_at.asc())
                .limit(1)
            ).fetchone()
            if row is None:
                return None
            job = self._job_from_mapping(row._mapping)
            job.status = "processing"
            job.worker_id = worker_id
            job.attempts += 1
            job.available_at = now + timedelta(seconds=visibility_timeout)
            session.execute(
                update(self._job_table)
                .where(
                    (self._job_table.c.id == job.job_id)
                    & (self._job_table.c.tenant_id == tenant_id)
                )
                .values(
                    status="processing",
                    attempts=job.attempts,
                    worker_id=worker_id,
                    available_at=job.available_at.timestamp(),
                )
            )
            return job

    def update_job(self, job: JobRecord) -> None:
        if (
            self._engine is None
            or self._Session is None
            or self._job_table is None
            or update is None
        ):
            tenant_jobs = self._job_memory.setdefault(job.tenant_id, {})
            tenant_jobs[job.job_id] = self._job_copy(job)
            return
        with self.session() as session:
            if session is None:
                tenant_jobs = self._job_memory.setdefault(job.tenant_id, {})
                tenant_jobs[job.job_id] = self._job_copy(job)
                return
            session.execute(
                update(self._job_table)
                .where(
                    (self._job_table.c.id == job.job_id)
                    & (self._job_table.c.tenant_id == job.tenant_id)
                )
                .values(
                    status=job.status,
                    attempts=job.attempts,
                    last_error=job.last_error,
                    available_at=job.available_at.timestamp(),
                    worker_id=job.worker_id,
                )
            )

    def append_audit(self, tenant_id: str, action: str, payload: Dict[str, Any]) -> None:
        timestamp = datetime.now(timezone.utc)
        namespace = self._tenant_namespace(tenant_id)
        record = {
            "id": sha256(
                f"{tenant_id}:{action}:{timestamp.timestamp()}".encode("utf-8")
            ).hexdigest(),
            "tenant_id": tenant_id,
            "namespace": namespace,
            "action": action,
            "payload": json.dumps(payload),
            "created_at": timestamp.timestamp(),
        }
        if self._engine is None or self._Session is None or self._audit_table is None:
            self._audit_memory.append(record)
            return
        with self.session() as session:
            if session is None:
                self._audit_memory.append(record)
                return
            session.execute(self._audit_table.insert().values(record))

    def record_audit_event(self, tenant_id: str, action: str, payload: Dict[str, Any]) -> None:
        self.append_audit(tenant_id, action, payload)

    # ------------------------------------------------------------------
    # Internal helpers for job queue
    # ------------------------------------------------------------------
    def _job_copy(self, job: JobRecord) -> JobRecord:
        try:
            payload = json.loads(json.dumps(job.payload))
        except TypeError:
            payload = dict(job.payload)
        return JobRecord(
            job_id=job.job_id,
            tenant_id=job.tenant_id,
            payload=payload,
            status=job.status,
            attempts=job.attempts,
            last_error=job.last_error,
            scheduled_at=job.scheduled_at,
            available_at=job.available_at,
            worker_id=job.worker_id,
        )

    def _lease_job_memory(
        self,
        *,
        tenant_id: str,
        now: datetime,
        worker_id: str,
        visibility_timeout: int,
    ) -> JobRecord | None:
        tenant_jobs = self._job_memory.get(tenant_id, {})
        pending_jobs = [
            job
            for job in tenant_jobs.values()
            if job.status == "pending" and job.available_at <= now
        ]
        if not pending_jobs:
            return None
        job = sorted(pending_jobs, key=lambda item: item.available_at)[0]
        leased = self._job_copy(job)
        leased.status = "processing"
        leased.worker_id = worker_id
        leased.attempts += 1
        leased.available_at = now + timedelta(seconds=visibility_timeout)
        tenant_jobs[job.job_id] = leased
        return self._job_copy(leased)

    def _job_from_mapping(self, mapping: Any) -> JobRecord:
        tenant_id = mapping["tenant_id"]
        payload_raw = mapping.get("payload")
        payload = self._decrypt_payload(payload_raw, tenant_id) if payload_raw is not None else {}
        scheduled_at = datetime.fromtimestamp(mapping.get("scheduled_at") or 0, tz=timezone.utc)
        available_at = datetime.fromtimestamp(mapping.get("available_at") or 0, tz=timezone.utc)
        return JobRecord(
            job_id=mapping["id"],
            tenant_id=tenant_id,
            payload=payload or {},
            status=mapping.get("status", "pending"),
            attempts=int(mapping.get("attempts", 0) or 0),
            last_error=mapping.get("last_error"),
            scheduled_at=scheduled_at,
            available_at=available_at,
            worker_id=mapping.get("worker_id"),
        )

    # ------------------------------------------------------------------
    # Encryption helpers
    # ------------------------------------------------------------------
    def _initialise_fernet(self, key: bytes | None) -> Any:
        if not key:
            return None
        if Fernet is None:
            logger.warning("Encryption key provided but cryptography is unavailable")
            return None
        try:
            return Fernet(key)
        except Exception as exc:  # pragma: no cover - invalid key
            logger.error("Invalid encryption key supplied", error=str(exc))
            return None

    def _encrypt_payload(self, payload: Dict[str, Any], tenant_id: str) -> str:
        serialised = json.dumps(payload)
        fernet = self._derive_fernet(tenant_id)
        if fernet is None:
            return serialised
        token = fernet.encrypt(serialised.encode("utf-8"))
        return token.decode("utf-8")

    def _decrypt_payload(self, token: Any, tenant_id: str) -> Dict[str, Any] | None:
        if token is None:
            return None
        raw = str(token)
        fernet = self._derive_fernet(tenant_id)
        if fernet is None:
            try:
                return json.loads(raw)
            except Exception:
                return None
        try:
            decrypted = fernet.decrypt(raw.encode("utf-8"))
            return json.loads(decrypted)
        except Exception:  # pragma: no cover - invalid token
            return None

    def _tenant_namespace(self, tenant_id: str) -> str:
        namespace = self._tenant_namespaces.get(tenant_id)
        if namespace:
            return namespace
        digest = sha256(tenant_id.encode("utf-8")).hexdigest()
        namespace = digest[:16]
        self._tenant_namespaces[tenant_id] = namespace
        return namespace

    def _derive_fernet(self, tenant_id: str) -> Any:
        if Fernet is None or self._fernet is None:
            return None
        if not tenant_id:
            return self._fernet
        if tenant_id in self._tenant_fernets:
            return self._tenant_fernets[tenant_id]
        if self._fernet_master_key is None:
            self._tenant_fernets[tenant_id] = self._fernet
            return self._fernet
        try:
            digest = hmac.new(
                self._fernet_master_key,
                tenant_id.encode("utf-8"),
                sha256,
            ).digest()
            derived = urlsafe_b64encode(digest)
            self._tenant_fernets[tenant_id] = Fernet(derived)
        except Exception:
            self._tenant_fernets[tenant_id] = self._fernet
        return self._tenant_fernets[tenant_id]

    def _cache_key(self, tenant_id: str, key: str) -> str:
        namespace = self._tenant_namespace(tenant_id)
        digest = sha256(f"{namespace}:{key}".encode("utf-8")).hexdigest()
        return f"tenant:{namespace}:key:{digest}"
