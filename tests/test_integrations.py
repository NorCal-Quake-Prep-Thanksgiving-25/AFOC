from __future__ import annotations

from datetime import date

from afoc.integrations import (
    AVAILABLE_COLLECTORS,
    AVAILABLE_DEVOPS_COLLECTORS,
    AVAILABLE_USAGE_COLLECTORS,
    CloudSpendWindow,
)


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
