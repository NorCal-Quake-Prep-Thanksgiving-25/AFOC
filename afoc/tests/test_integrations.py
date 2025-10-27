"""Integration tests for AWS helpers using stubbed clients."""

from __future__ import annotations

import pytest

try:  # pragma: no cover - skip tests when pandas missing
    import pandas as pd
except ImportError:  # pragma: no cover - handled via pytest marker
    pd = None  # type: ignore[assignment]

from afoc.integrations.aws import CostAnomalyDetector, EC2RightSizer


pytestmark = pytest.mark.skipif(pd is None, reason="pandas not available")


class _FakeCostExplorer:
    def __init__(self) -> None:
        self.calls = 0

    def get_cost_and_usage(self, **_kwargs):
        self.calls += 1
        if self.calls > 1:
            return {"ResultsByTime": [], "NextPageToken": None}
        return {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-01-02"},
                    "Groups": [
                        {
                            "Keys": ["AmazonEC2"],
                            "Metrics": {"UnblendedCost": {"Amount": "10.0"}},
                        }
                    ],
                },
                {
                    "TimePeriod": {"Start": "2024-01-02", "End": "2024-01-03"},
                    "Groups": [
                        {
                            "Keys": ["AmazonEC2"],
                            "Metrics": {"UnblendedCost": {"Amount": "40.0"}},
                        }
                    ],
                },
            ],
            "NextPageToken": None,
        }


class _FakeCloudWatch:
    def get_metric_statistics(self, **_kwargs):
        return {
            "Datapoints": [
                {"Average": 10.0},
                {"Average": 20.0},
            ]
        }


class _FakeEC2:
    def describe_instances(self, **_kwargs):
        return {
            "Reservations": [
                {
                    "Instances": [
                        {"InstanceId": "i-1", "InstanceType": "m5.large"},
                    ]
                }
            ]
        }


def test_cost_anomaly_detector_returns_z_score():
    detector = CostAnomalyDetector(ce_client=_FakeCostExplorer())
    data = detector.get_cost_data(days=5)
    assert isinstance(data, pd.DataFrame)
    anomalies = detector.detect_anomalies(data, threshold=0.5)
    assert not anomalies.empty
    assert (anomalies["service"] == "AmazonEC2").all()


def test_ec2_rightsizer_downsizes_instances():
    rightsizer = EC2RightSizer(
        ec2_client=_FakeEC2(), cloudwatch_client=_FakeCloudWatch()
    )
    recommendations = rightsizer.analyze_instances()
    assert not recommendations.empty
    assert set(recommendations.columns) >= {
        "instance_id",
        "current_type",
        "recommendation",
        "estimated_savings",
    }
    assert "Downsize" in set(recommendations["recommendation"])
