"""AWS-native integrations for anomaly detection and right-sizing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional

import pandas as pd

from typing import TYPE_CHECKING

try:  # pragma: no cover - optional dependency for production deployments
    import boto3  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - keep tests functional without boto3
    boto3 = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover - for static type checking only
    from botocore.exceptions import BotoCoreError as _BotoCoreError  # type: ignore
    from botocore.exceptions import ClientError as _ClientError  # type: ignore
else:  # pragma: no cover - executed at runtime
    try:
        from botocore.exceptions import BotoCoreError as _BotoCoreError  # type: ignore
        from botocore.exceptions import ClientError as _ClientError  # type: ignore
    except ImportError:  # pragma: no cover - dependency missing

        class _BotoCoreError(Exception):
            """Fallback base exception when botocore is not available."""

        class _ClientError(Exception):
            """Fallback client error when botocore is not available."""


BotoCoreError = _BotoCoreError
ClientError = _ClientError


def _require_client(factory, name: str):
    """Ensure boto3 is available before attempting to construct a client."""

    if factory is not None:
        return factory
    if boto3 is None:  # pragma: no cover - explicit failure for missing optional dep
        raise RuntimeError(f"boto3 is required for {name} integrations")
    return boto3.client(name)


def _paginate_cost_and_usage(client, **kwargs) -> Iterable[Dict]:
    """Yield paginated Cost Explorer results with retry-safe token handling."""

    token: Optional[str] = None
    while True:
        request = dict(kwargs)
        if token:
            request["NextPageToken"] = token
        response = client.get_cost_and_usage(**request)
        yield response
        token = response.get("NextPageToken")
        if not token:
            break


class CostAnomalyDetector:
    """Fetch daily AWS costs and flag anomalies."""

    def __init__(self, ce_client=None):
        self._client = ce_client

    def _client_or_default(self):
        return _require_client(self._client, "ce")

    def get_cost_data(self, days: int = 30) -> pd.DataFrame:
        """Fetch daily costs grouped by service for anomaly detection."""

        end = datetime.utcnow()
        start = end - timedelta(days=days)
        client = self._client_or_default()
        results: List[Dict[str, object]] = []

        try:
            for response in _paginate_cost_and_usage(
                client,
                TimePeriod={
                    "Start": start.strftime("%Y-%m-%d"),
                    "End": end.strftime("%Y-%m-%d"),
                },
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            ):
                for day in response.get("ResultsByTime", []):
                    for group in day.get("Groups", []):
                        results.append(
                            {
                                "date": day["TimePeriod"]["Start"],
                                "service": group["Keys"][0],
                                "cost": float(
                                    group["Metrics"]["UnblendedCost"]["Amount"]
                                ),
                            }
                        )
        except (
            BotoCoreError,
            ClientError,
        ) as exc:  # pragma: no cover - network failure
            raise RuntimeError("Failed to retrieve AWS cost data") from exc

        return pd.DataFrame(results)

    def detect_anomalies(
        self, df: pd.DataFrame, threshold: float = 2.0
    ) -> pd.DataFrame:
        """Flag cost spikes using a Z-score heuristic."""

        if df.empty:
            return pd.DataFrame(
                columns=["date", "service", "cost", "z_score", "expected_range"]
            )

        anomalies: List[Dict[str, object]] = []
        grouped = df.groupby("service")
        for service, frame in grouped:
            mean = frame["cost"].mean()
            std = frame["cost"].std(ddof=0)
            for _, row in frame.iterrows():
                if std == 0:
                    z_score = 0.0
                else:
                    z_score = (row["cost"] - mean) / std
                if abs(z_score) > threshold:
                    anomalies.append(
                        {
                            "date": row["date"],
                            "service": service,
                            "cost": row["cost"],
                            "z_score": z_score,
                            "expected_range": (
                                f"{(mean - threshold * std):.2f} - {(mean + threshold * std):.2f}"
                                if std > 0
                                else "stable"
                            ),
                            "is_anomaly": True,
                        }
                    )

        return pd.DataFrame(anomalies)

    def analyze(self, days: int = 30, threshold: float = 2.0) -> pd.DataFrame:
        """Fetch costs and return detected anomalies in a single call."""

        data = self.get_cost_data(days=days)
        return self.detect_anomalies(data, threshold=threshold)


@dataclass
class InstanceMetrics:
    """Container for summarised instance utilisation."""

    instance_id: str
    avg_cpu_percent: float
    max_cpu_percent: float


class EC2RightSizer:
    """Produce right-sizing suggestions using CloudWatch metrics."""

    def __init__(self, ec2_client=None, cloudwatch_client=None):
        self._ec2 = ec2_client
        self._cloudwatch = cloudwatch_client

    def _ec2_or_default(self):
        return _require_client(self._ec2, "ec2")

    def _cloudwatch_or_default(self):
        return _require_client(self._cloudwatch, "cloudwatch")

    def get_instance_metrics(self, instance_id: str, days: int = 14) -> InstanceMetrics:
        """Aggregate CPU utilisation for the given instance."""

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        response = self._cloudwatch_or_default().get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName="CPUUtilization",
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,
            Statistics=["Average"],
        )
        datapoints = response.get("Datapoints", [])
        cpu_values = [point.get("Average", 0.0) for point in datapoints]
        avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0.0
        max_cpu = max(cpu_values) if cpu_values else 0.0
        return InstanceMetrics(
            instance_id=instance_id,
            avg_cpu_percent=avg_cpu,
            max_cpu_percent=max_cpu,
        )

    def analyze_instances(self) -> pd.DataFrame:
        """Inspect running instances and recommend right-sizing actions."""

        response = self._ec2_or_default().describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )
        recommendations: List[Dict[str, object]] = []

        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instance_id = instance["InstanceId"]
                instance_type = instance["InstanceType"]
                metrics = self.get_instance_metrics(instance_id)
                avg_cpu = metrics.avg_cpu_percent
                if avg_cpu < 20:
                    recommendation = "Downsize"
                elif avg_cpu > 80:
                    recommendation = "Upsize"
                else:
                    recommendation = "Right-sized"
                recommendations.append(
                    {
                        "instance_id": instance_id,
                        "current_type": instance_type,
                        "avg_cpu_percent": avg_cpu,
                        "max_cpu_percent": metrics.max_cpu_percent,
                        "recommendation": recommendation,
                        "estimated_savings": self.estimate_savings(
                            instance_type, recommendation
                        ),
                    }
                )

        return pd.DataFrame(recommendations)

    @staticmethod
    def estimate_savings(instance_type: str, recommendation: str) -> float:
        """Rudimentary savings estimator used for quick what-if analyses."""

        savings_map = {"Downsize": 0.35, "Upsize": -0.20, "Right-sized": 0.0}
        base = savings_map.get(recommendation, 0.0)
        return base


__all__ = ["CostAnomalyDetector", "EC2RightSizer", "InstanceMetrics"]
