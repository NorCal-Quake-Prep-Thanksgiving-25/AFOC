"""DevOps integrations pulling live metrics when credentials are provided."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Dict, Mapping

import logging

try:  # pragma: no cover - optional dependency
    import httpx
except Exception:  # pragma: no cover - fallback when httpx is unavailable
    httpx = None  # type: ignore

LOGGER = logging.getLogger(__name__)


class DevOpsIntegrationError(RuntimeError):
    """Raised when DevOps metrics cannot be fetched."""


@dataclass
class DevOpsMetric:
    source: str
    metric: str
    value: float
    collected_at: datetime


class DevOpsCollector:
    source: str

    def pull_metrics(self) -> Dict[str, DevOpsMetric]:
        raise NotImplementedError


class GitHubCollector(DevOpsCollector):
    source = "github"

    def __init__(self, repository: str | None = None, token: str | None = None) -> None:
        self.repository = repository or os.getenv("GITHUB_REPOSITORY", "openai/example")
        self.token = token or os.getenv("GITHUB_TOKEN")

    def pull_metrics(self) -> Dict[str, DevOpsMetric]:  # pragma: no cover - network interaction
        collected_at = datetime.now(UTC)
        if httpx is None or not self.token:
            return self._synthetic(collected_at)
        url = f"https://api.github.com/repos/{self.repository}/pulls"
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json"}
        params = {"state": "open", "per_page": 100}
        with httpx.Client(timeout=10) as client:
            response = client.get(url, headers=headers, params=params)
            response.raise_for_status()
            pulls = response.json()
        open_prs = len(pulls)
        deployment_url = f"https://api.github.com/repos/{self.repository}/deployments"
        with httpx.Client(timeout=10) as client:
            deployments = client.get(deployment_url, headers=headers, params={"per_page": 100})
            deployments.raise_for_status()
            deployments_payload = deployments.json()
        deploy_frequency = self._deploy_frequency(deployments_payload)
        return {
            "open_prs": DevOpsMetric(self.source, "open_prs", float(open_prs), collected_at),
            "deploy_frequency": DevOpsMetric(
                self.source, "deploy_frequency", deploy_frequency, collected_at
            ),
        }

    def _deploy_frequency(self, payload: Mapping[str, object]) -> float:
        if not isinstance(payload, list) or not payload:
            return 0.0
        deployments = [
            datetime.fromisoformat(
                item.get("created_at", "1970-01-01T00:00:00+00:00").replace("Z", "+00:00")
            )
            for item in payload
            if isinstance(item, Mapping)
        ]
        if len(deployments) < 2:
            return 0.0
        deployments.sort(reverse=True)
        delta = deployments[0] - deployments[-1]
        days = max(delta.days, 1)
        return len(deployments) / float(days)

    def _synthetic(self, collected_at: datetime) -> Dict[str, DevOpsMetric]:
        return {
            "open_prs": DevOpsMetric(self.source, "open_prs", 4.0, collected_at),
            "deploy_frequency": DevOpsMetric(self.source, "deploy_frequency", 6.0, collected_at),
        }


class DatadogCollector(DevOpsCollector):
    source = "datadog"

    def __init__(
        self,
        api_key: str | None = None,
        app_key: str | None = None,
        query: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("DATADOG_API_KEY")
        self.app_key = app_key or os.getenv("DATADOG_APP_KEY")
        self.query = query or os.getenv("DATADOG_METRIC_QUERY", "avg:system.cpu.user{*}")

    def pull_metrics(self) -> Dict[str, DevOpsMetric]:  # pragma: no cover - network interaction
        collected_at = datetime.now(UTC)
        if httpx is None or not (self.api_key and self.app_key):
            return self._synthetic(collected_at)
        url = "https://api.datadoghq.com/api/v2/query_timeseries"
        end = int(datetime.now(UTC).timestamp())
        start = end - 3600
        params = {"query": self.query, "from": start, "to": end}
        headers = {"DD-API-KEY": self.api_key, "DD-APPLICATION-KEY": self.app_key}
        with httpx.Client(timeout=10) as client:
            response = client.get(url, headers=headers, params=params)
            response.raise_for_status()
            payload = response.json()
        series = payload.get("data", [])
        if not series:
            raise DevOpsIntegrationError("Datadog query returned no data")
        points = series[0].get("attributes", {}).get("values", [])
        latest_value = float(points[-1][1]) if points else 0.0
        return {"metric": DevOpsMetric(self.source, "metric", latest_value, collected_at)}

    def _synthetic(self, collected_at: datetime) -> Dict[str, DevOpsMetric]:
        return {
            "metric": DevOpsMetric(self.source, "metric", 0.85, collected_at),
        }


class GrafanaCollector(DevOpsCollector):
    source = "grafana"

    def __init__(
        self, base_url: str | None = None, token: str | None = None, query: str | None = None
    ) -> None:
        self.base_url = base_url or os.getenv("GRAFANA_BASE_URL", "https://grafana.example.com")
        self.token = token or os.getenv("GRAFANA_TOKEN")
        self.query = query or os.getenv("GRAFANA_QUERY", "sum(node_cpu_seconds_total)")

    def pull_metrics(self) -> Dict[str, DevOpsMetric]:  # pragma: no cover - network interaction
        collected_at = datetime.now(UTC)
        if httpx is None or not self.token:
            return self._synthetic(collected_at)
        url = f"{self.base_url}/api/ds/query"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "queries": [
                {
                    "datasource": {"type": "prometheus", "uid": "prometheus"},
                    "expr": self.query,
                    "intervalMs": 60000,
                    "maxDataPoints": 1440,
                }
            ]
        }
        with httpx.Client(timeout=10) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
        results = result.get("results", {})
        if not results:
            raise DevOpsIntegrationError("Grafana query returned no data")
        metrics = {}
        for key, value in results.items():
            frames = value.get("frames", [])
            if not frames:
                continue
            data = frames[0].get("data", {})
            values = data.get("values", [])
            metric_value = float(values[-1][-1]) if values and values[-1] else 0.0
            metrics[key] = DevOpsMetric(self.source, key, metric_value, collected_at)
        return metrics or self._synthetic(collected_at)

    def _synthetic(self, collected_at: datetime) -> Dict[str, DevOpsMetric]:
        return {
            "cpu_usage": DevOpsMetric(self.source, "cpu_usage", 62.0, collected_at),
            "memory_usage": DevOpsMetric(self.source, "memory_usage", 70.0, collected_at),
        }


AVAILABLE_DEVOPS_COLLECTORS = {
    "github": GitHubCollector,
    "datadog": DatadogCollector,
    "grafana": GrafanaCollector,
}
