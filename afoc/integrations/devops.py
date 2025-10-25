"""DevOps telemetry integrations for GitHub, Datadog, and Grafana."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class DevOpsMetric:
    source: str
    metric: str
    value: float


class DevOpsCollector:
    source: str

    def pull_metrics(self) -> Dict[str, DevOpsMetric]:
        raise NotImplementedError


class GitHubCollector(DevOpsCollector):
    source = "github"

    def pull_metrics(self) -> Dict[str, DevOpsMetric]:
        return {
            "open_prs": DevOpsMetric(source=self.source, metric="open_prs", value=4),
            "deploy_frequency": DevOpsMetric(source=self.source, metric="deploy_frequency", value=7),
        }


class DatadogCollector(DevOpsCollector):
    source = "datadog"

    def pull_metrics(self) -> Dict[str, DevOpsMetric]:
        return {
            "error_rate": DevOpsMetric(source=self.source, metric="error_rate", value=0.01),
            "latency_p95": DevOpsMetric(source=self.source, metric="latency_p95", value=120),
        }


class GrafanaCollector(DevOpsCollector):
    source = "grafana"

    def pull_metrics(self) -> Dict[str, DevOpsMetric]:
        return {
            "cpu_usage": DevOpsMetric(source=self.source, metric="cpu_usage", value=65.0),
            "memory_usage": DevOpsMetric(source=self.source, metric="memory_usage", value=72.0),
        }


AVAILABLE_DEVOPS_COLLECTORS = {
    "github": GitHubCollector,
    "datadog": DatadogCollector,
    "grafana": GrafanaCollector,
}
