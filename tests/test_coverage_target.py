from afoc.coverage_target import CoverageMetric, summarise_metrics


def test_metric_status_and_summary_pass() -> None:
    metrics = [
        CoverageMetric(name="bandit", value=1.0, threshold=0.9),
        CoverageMetric(name="pytest", value=0.95, threshold=0.9),
    ]
    summary = summarise_metrics(metrics)
    assert summary["average"] >= 0.95
    assert summary["passes"] == ["bandit", "pytest"]
    assert summary["failures"] == []
    assert all(metric.status() == "pass" for metric in metrics)


def test_metric_summary_failure() -> None:
    metrics = [
        CoverageMetric(name="coverage", value=0.9, threshold=0.95),
    ]
    summary = summarise_metrics(metrics)
    assert summary["passes"] == []
    assert summary["failures"] == ["coverage"]
    assert metrics[0].status() == "fail"


def test_summarise_metrics_requires_values() -> None:
    try:
        summarise_metrics([])
    except ValueError as exc:
        assert "must not be empty" in str(exc)
    else:  # pragma: no cover - defensive guard
        raise AssertionError("expected failure for empty metrics")
