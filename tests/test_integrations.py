from __future__ import annotations

from datetime import date
import sys
import types

import pytest

httpx = pytest.importorskip("httpx")

from afoc.integrations import (
    AVAILABLE_COLLECTORS,
    AVAILABLE_DEVOPS_COLLECTORS,
    AVAILABLE_USAGE_COLLECTORS,
    AWSCostCollector,
    CloudSpendWindow,
    GCPCostCollector,
    OpenAIUsageCollector,
)
from afoc.integrations.cloud import CloudSpendSample, CostCollector


def test_cloud_collectors_fallback_to_synthetic() -> None:
    window = CloudSpendWindow(start=date(2024, 1, 1), end=date(2024, 1, 31))
    for name, collector_cls in AVAILABLE_COLLECTORS.items():
        collector = collector_cls()
        samples = collector.collect(window)
        assert samples, f"collector {name} returned no samples"
        assert all(sample.provider for sample in samples)


def test_devops_collectors_return_metrics() -> None:
    for name, collector_cls in AVAILABLE_DEVOPS_COLLECTORS.items():
        collector = collector_cls()
        metrics = collector.pull_metrics()
        assert metrics, f"collector {name} returned no metrics"


def test_llm_collectors_return_usage() -> None:
    for name, collector_cls in AVAILABLE_USAGE_COLLECTORS.items():
        collector = collector_cls()
        usage = collector.fetch_usage()
        assert usage.provider == name
        assert usage.tokens > 0


def test_aws_collector_retries_on_throttle(monkeypatch: pytest.MonkeyPatch) -> None:
    window = CloudSpendWindow(start=date(2024, 1, 1), end=date(2024, 1, 2))

    class ThrottleError(Exception):
        def __init__(self) -> None:
            self.response = {"Error": {"Code": "ThrottlingException"}}

    class DummyClient:
        def __init__(self) -> None:
            self.calls = 0

        def get_cost_and_usage(self, **_: object) -> dict:
            self.calls += 1
            if self.calls == 1:
                raise ThrottleError()
            return {
                "ResultsByTime": [
                    {
                        "TimePeriod": {
                            "Start": window.start.isoformat(),
                            "End": window.end.isoformat(),
                        },
                        "Groups": [
                            {
                                "Keys": ["AmazonEC2"],
                                "Metrics": {"UnblendedCost": {"Amount": "10.0", "Unit": "USD"}},
                            }
                        ],
                    }
                ]
            }

    dummy_client = DummyClient()
    boto3_module = types.SimpleNamespace(client=lambda *_, **__: dummy_client)
    monkeypatch.setitem(sys.modules, "boto3", boto3_module)

    collector = AWSCostCollector(max_attempts=3, initial_backoff=0.0)
    samples = collector.collect(window)
    assert dummy_client.calls == 2
    assert samples and samples[0].service == "AmazonEC2"


def test_gcp_collector_builds_idempotent_job(monkeypatch: pytest.MonkeyPatch) -> None:
    window = CloudSpendWindow(start=date(2024, 2, 1), end=date(2024, 2, 2))
    monkeypatch.setenv("GCP_BILLING_TABLE", "project.dataset.table")

    submitted_job_ids: list[str] = []

    class DummyJob:
        def __init__(self, job_id: str) -> None:
            self.job_id = job_id
            self.result_calls = 0

        def result(self, timeout: int | None = None) -> list[dict[str, object]]:
            self.result_calls += 1
            return [{"service_name": "Compute Engine", "total_cost": 42.0}]

    class DummyClient:
        def query(self, query: str, job_config: object, job_id: str) -> DummyJob:
            submitted_job_ids.append(job_id)
            return DummyJob(job_id)

    bigquery_module = types.ModuleType("google.cloud.bigquery")
    bigquery_module.Client = lambda: DummyClient()
    bigquery_module.QueryJobConfig = lambda **kwargs: types.SimpleNamespace(**kwargs)
    bigquery_module.ScalarQueryParameter = lambda name, typ, value: types.SimpleNamespace(
        name=name, typ=typ, value=value
    )

    google_cloud_module = types.ModuleType("google.cloud")
    google_cloud_module.bigquery = bigquery_module
    google_module = types.ModuleType("google")
    google_module.cloud = google_cloud_module

    exceptions_module = types.ModuleType("google.api_core.exceptions")

    class DummyAPICallError(Exception):
        def __init__(self, code: int | None = None) -> None:
            self.code = code

    exceptions_module.GoogleAPICallError = DummyAPICallError
    google_api_core_module = types.ModuleType("google.api_core")
    google_api_core_module.exceptions = exceptions_module

    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.cloud", google_cloud_module)
    monkeypatch.setitem(sys.modules, "google.cloud.bigquery", bigquery_module)
    monkeypatch.setitem(sys.modules, "google.api_core", google_api_core_module)
    monkeypatch.setitem(sys.modules, "google.api_core.exceptions", exceptions_module)

    collector = GCPCostCollector(max_attempts=2, initial_backoff=0.0)
    samples = collector.collect(window)
    assert samples and samples[0].service == "Compute Engine"
    assert submitted_job_ids
    assert all(job_id == submitted_job_ids[0] for job_id in submitted_job_ids)
    assert submitted_job_ids[0].startswith("afoc_cost_")


def test_openai_usage_collector_retries_rate_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyClient:
        def __init__(self) -> None:
            self.calls = 0

        def __enter__(self) -> "DummyClient":
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def get(self, url: str, headers: dict[str, str], params: dict[str, str]) -> httpx.Response:
            self.calls += 1
            request = httpx.Request("GET", url, headers=headers, params=params)
            if self.calls == 1:
                response = httpx.Response(429, request=request)
                raise httpx.HTTPStatusError("Too Many Requests", request=request, response=response)
            return httpx.Response(
                200,
                request=request,
                json={"total_usage": {"total_tokens": 1000, "total_cost": 10.5}},
            )

    dummy_client = DummyClient()

    class DummyClientFactory:
        def __call__(self, *_, **__):
            return dummy_client

    monkeypatch.setattr("afoc.integrations.llm.httpx.Client", DummyClientFactory())

    collector = OpenAIUsageCollector(api_key="test", max_attempts=3, initial_backoff=0.0)
    usage = collector.fetch_usage()
    assert usage.tokens == 1000
    assert usage.cost_usd == 10.5
    assert dummy_client.calls == 2


def test_cost_collector_circuit_breaker_falls_back() -> None:
    window = CloudSpendWindow(start=date(2024, 3, 1), end=date(2024, 3, 2))

    class ExplodingCollector(CostCollector):
        provider = "exploding"

        def _collect(self, window: CloudSpendWindow):  # type: ignore[override]
            raise RuntimeError("boom")

    collector = ExplodingCollector(
        max_attempts=1,
        initial_backoff=0.0,
        breaker_failure_threshold=1,
        breaker_reset_timeout=1.0,
    )
    samples = collector.collect(window)
    assert samples and all(isinstance(sample, CloudSpendSample) for sample in samples)
