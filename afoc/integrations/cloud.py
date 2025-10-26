"""Cloud cost integrations backed by real provider SDKs with graceful fallbacks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import os
import random
import time
from typing import Any, Callable, Dict, Iterable, List, TypeVar

import logging

from ..pydantic_compat import BaseModel, Field
from ..reliability import CircuitBreaker, CircuitBreakerOpen

LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


class IntegrationError(RuntimeError):
    """Raised when a provider integration fails."""


class MissingDependencyError(IntegrationError):
    """Raised when a provider dependency is not installed."""


@dataclass(frozen=True)
class CloudSpendWindow:
    """Defines the time window used for cost collection."""

    start: date
    end: date
    granularity: str = "DAILY"

    @classmethod
    def trailing_days(cls, days: int = 30, granularity: str = "DAILY") -> "CloudSpendWindow":
        today = date.today()
        return cls(start=today - timedelta(days=days), end=today, granularity=granularity)


class CloudSpendSample(BaseModel):
    provider: str
    service: str
    amount: float
    currency: str = Field(default="USD")
    start: date | None = None
    end: date | None = None


class CostCollector(BaseModel):
    provider: str
    credentials_ref: str | None = None
    max_attempts: int = Field(default=4, ge=1)
    initial_backoff: float = Field(default=0.5, ge=0.0)
    breaker_failure_threshold: int = Field(default=5, ge=1)
    breaker_reset_timeout: float = Field(default=60.0, ge=1.0)

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data: Any) -> None:  # type: ignore[override]
        super().__init__(**data)
        self._breaker = CircuitBreaker(
            failure_threshold=self.breaker_failure_threshold,
            recovery_timeout=self.breaker_reset_timeout,
            on_state_change=self._log_breaker_state,
        )

    def collect(self, window: CloudSpendWindow | None = None) -> List[CloudSpendSample]:
        window = window or CloudSpendWindow.trailing_days()
        try:
            samples = self._breaker.call(lambda: self._collect_with_guard(window))
            return list(samples)
        except CircuitBreakerOpen:
            LOGGER.warning("Circuit breaker open for provider %s", self.provider)
            return self._simulate(window)
        except MissingDependencyError:
            LOGGER.warning(
                "Provider dependencies missing for %s; using synthetic data", self.provider
            )
            return self._simulate(window)
        except Exception as exc:  # pragma: no cover - defensive path
            LOGGER.error("Failed to collect spend from %s: %s", self.provider, exc)
            return self._simulate(window)

    async def collect_async(self, window: CloudSpendWindow | None = None) -> List[CloudSpendSample]:
        # Lazy import to avoid asyncio dependency at import time.
        import asyncio

        return await asyncio.to_thread(self.collect, window)

    # ------------------------------------------------------------------
    # Provider implementations should override the methods below.
    # ------------------------------------------------------------------
    def _collect(
        self, window: CloudSpendWindow
    ) -> Iterable[CloudSpendSample]:  # pragma: no cover - interface
        yield from ()

    def _simulate(self, window: CloudSpendWindow) -> List[CloudSpendSample]:
        random.seed(f"{self.provider}:{window.start}:{window.end}")
        services = ["compute", "storage", "networking", "database"]
        span = (window.end - window.start).days or 1
        base = 500.0
        return [
            CloudSpendSample(
                provider=self.provider,
                service=service,
                amount=base
                + random.random() * 100.0 * span,  # nosec B311 - deterministic seed above
                start=window.start,
                end=window.end,
            )
            for service in services
        ]

    # ------------------------------------------------------------------
    # Resilience helpers
    # ------------------------------------------------------------------
    def _call_with_backoff(self, func: Callable[[], T], *, label: str) -> T:
        attempts = 0
        delay = self.initial_backoff or 0.0
        while True:
            try:
                return func()
            except Exception as exc:
                attempts += 1
                if attempts >= self.max_attempts or not self._is_retryable(exc):
                    raise
                sleep_for = delay or 0.0
                if sleep_for:
                    jitter = random.uniform(0, sleep_for / 2)
                    time.sleep(sleep_for + jitter)
                    delay *= 2 or 1
                LOGGER.info("Retrying %s after transient failure", label, exc_info=exc)

    def _is_retryable(self, exc: Exception) -> bool:
        message = str(exc).lower()
        retry_markers = (
            "throttl",
            "rate",
            "429",
            "timeout",
            "temporarily unavailable",
        )
        if any(marker in message for marker in retry_markers):
            return True
        try:  # pragma: no cover - optional dependency
            from botocore.exceptions import ClientError  # type: ignore

            if isinstance(exc, ClientError):
                code = exc.response.get("Error", {}).get("Code", "").upper()
                return code in {
                    "THROTTLINGEXCEPTION",
                    "TOOMANYREQUESTSEXCEPTION",
                    "REQUESTLIMITEXCEEDED",
                }
        except Exception:
            pass
        if hasattr(exc, "status_code") and getattr(exc, "status_code") in {429, 500, 502, 503, 504}:
            return True
        if hasattr(exc, "response") and isinstance(getattr(exc, "response"), dict):
            code = exc.response.get("Error", {}).get("Code", "").lower()
            return any(marker in code for marker in retry_markers)
        try:  # pragma: no cover - optional dependency
            from google.api_core import exceptions as google_exceptions  # type: ignore

            if isinstance(exc, google_exceptions.GoogleAPICallError):
                if getattr(exc, "code", None) in {429, 500, 503}:  # type: ignore[attr-defined]
                    return True
        except Exception:
            pass
        return False

    def _collect_with_guard(self, window: CloudSpendWindow) -> Iterable[CloudSpendSample]:
        samples = list(self._collect(window))
        if not samples:
            raise IntegrationError("Provider returned no spend data")
        return samples

    def _log_breaker_state(self, state: str) -> None:
        LOGGER.debug("collector circuit state", extra={"provider": self.provider, "state": state})


class AWSCostCollector(CostCollector):
    provider: str = "aws"
    region: str = Field(default="us-east-1")

    def _collect(
        self, window: CloudSpendWindow
    ) -> Iterable[CloudSpendSample]:  # pragma: no cover - optional
        try:
            import boto3  # type: ignore
        except Exception as exc:  # pragma: no cover - dependency missing
            raise MissingDependencyError("boto3 is required for AWS cost collection") from exc

        client = boto3.client("ce", region_name=self.region)
        token: str | None = None
        while True:

            def _call() -> Dict[str, Any]:
                params = {
                    "TimePeriod": {
                        "Start": window.start.isoformat(),
                        "End": window.end.isoformat(),
                    },
                    "Granularity": window.granularity.upper(),
                    "Metrics": ["UnblendedCost"],
                    "GroupBy": [{"Type": "DIMENSION", "Key": "SERVICE"}],
                }
                if token:
                    params["NextPageToken"] = token
                return client.get_cost_and_usage(**params)

            response = self._call_with_backoff(_call, label="aws_cost_usage")
            for result in response.get("ResultsByTime", []):
                start = date.fromisoformat(result["TimePeriod"]["Start"])
                end = date.fromisoformat(result["TimePeriod"]["End"])
                for group in result.get("Groups", []):
                    amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                    yield CloudSpendSample(
                        provider=self.provider,
                        service=group["Keys"][0],
                        amount=amount,
                        currency=group["Metrics"]["UnblendedCost"].get("Unit", "USD"),
                        start=start,
                        end=end,
                    )
            token = response.get("NextPageToken")
            if not token:
                break


class AzureCostCollector(CostCollector):
    provider: str = "azure"
    scope: str = Field(
        default_factory=lambda: os.getenv(
            "AZURE_COST_SCOPE", "00000000-0000-0000-0000-000000000000"
        )
    )

    def _collect(
        self, window: CloudSpendWindow
    ) -> Iterable[CloudSpendSample]:  # pragma: no cover - optional
        try:
            from azure.identity import DefaultAzureCredential  # type: ignore
            from azure.mgmt.costmanagement import CostManagementClient  # type: ignore
            from azure.core.exceptions import HttpResponseError  # type: ignore
        except Exception as exc:  # pragma: no cover - dependency missing
            raise MissingDependencyError(
                "azure-identity and azure-mgmt-costmanagement are required for Azure cost collection"
            ) from exc

        credential = DefaultAzureCredential()
        client = CostManagementClient(credential)
        body = {
            "type": "Usage",
            "timeframe": "Custom",
            "timePeriod": {"from": window.start.isoformat(), "to": window.end.isoformat()},
            "dataset": {
                "granularity": window.granularity.capitalize(),
                "aggregation": {"totalCost": {"name": "PreTaxCost", "function": "Sum"}},
                "grouping": [{"type": "Dimension", "name": "ServiceName"}],
            },
        }
        scope = self.scope
        if not scope.startswith("/"):
            scope = f"/subscriptions/{scope}"

        def _call() -> Any:
            return client.query.usage(scope=scope, parameters=body)

        try:
            query = self._call_with_backoff(_call, label="azure_cost_usage")
        except HttpResponseError as exc:  # pragma: no cover - optional dependency
            if exc.status_code == 404:
                raise IntegrationError("Azure scope not found for cost query") from exc
            raise
        for row in query.rows or []:
            service, amount = row[0], float(row[1])
            yield CloudSpendSample(
                provider=self.provider,
                service=str(service),
                amount=amount,
                currency=query.columns[1].name if query.columns else "USD",
                start=window.start,
                end=window.end,
            )


class GCPCostCollector(CostCollector):
    provider: str = "gcp"
    billing_account: str = Field(
        default_factory=lambda: os.getenv("GCP_BILLING_ACCOUNT", "000000-000000-000000")
    )
    billing_table: str | None = Field(default_factory=lambda: os.getenv("GCP_BILLING_TABLE"))

    def _collect(
        self, window: CloudSpendWindow
    ) -> Iterable[CloudSpendSample]:  # pragma: no cover - optional
        try:
            from google.cloud import bigquery  # type: ignore
            from google.api_core import exceptions as google_exceptions  # type: ignore
        except Exception as exc:  # pragma: no cover - dependency missing
            raise MissingDependencyError(
                "google-cloud-bigquery is required for GCP cost collection"
            ) from exc
        if not self.billing_table:
            raise IntegrationError("GCP_BILLING_TABLE must be configured for billing export")

        client = bigquery.Client()
        table = self.billing_table
        window_hash = abs(
            hash((table, window.start.isoformat(), window.end.isoformat(), self.billing_account))
        )
        job_id = f"afoc_cost_{window_hash}"
        query = f"""
            SELECT
              service.description AS service_name,
              SUM(cost) AS total_cost
            FROM `{table}`
            WHERE usage_start_time >= @start AND usage_end_time <= @end
            GROUP BY service_name
        """
        job_config = bigquery.QueryJobConfig(
            use_legacy_sql=False,
            query_parameters=[
                bigquery.ScalarQueryParameter("start", "TIMESTAMP", window.start.isoformat()),
                bigquery.ScalarQueryParameter("end", "TIMESTAMP", window.end.isoformat()),
            ],
        )

        def _submit() -> Any:
            return client.query(query, job_config=job_config, job_id=job_id)

        job = self._call_with_backoff(_submit, label="gcp_cost_query")

        def _await() -> Any:
            return job.result(timeout=60)

        try:
            rows = self._call_with_backoff(_await, label="gcp_cost_results")
        except google_exceptions.GoogleAPICallError as exc:  # pragma: no cover - optional
            raise IntegrationError("Failed to retrieve GCP billing export") from exc

        for row in rows:
            service = _extract_value(row, "service_name", index=0)
            amount = float(_extract_value(row, "total_cost", index=1) or 0.0)
            yield CloudSpendSample(
                provider=self.provider,
                service=str(service or "unknown"),
                amount=amount,
                currency="USD",
                start=window.start,
                end=window.end,
            )


def _extract_value(row: Any, key: str, index: int) -> Any:
    if hasattr(row, "get"):
        try:
            value = row.get(key)
            if value is not None:
                return value
        except Exception:  # pragma: no cover - defensive
            pass
    if hasattr(row, key):
        return getattr(row, key)
    if isinstance(row, (list, tuple)) and len(row) > index:
        return row[index]
    return None


AVAILABLE_COLLECTORS: Dict[str, type[CostCollector]] = {
    "aws_cur": AWSCostCollector,
    "azure_cost": AzureCostCollector,
    "gcp_billing": GCPCostCollector,
}
