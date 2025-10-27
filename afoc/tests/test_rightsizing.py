"""Tests for right-sizing services."""

from __future__ import annotations

import math

from afoc.services import rightsizing


INVENTORY = [
    {
        "resource_id": "i-001",
        "instance_type": "m5.large",
        "price": 0.12,
        "cpu_capacity": 2.0,
        "memory_capacity": 8.0,
        "metadata": {
            "options": [
                {
                    "instance_type": "t3.large",
                    "price": 0.1,
                    "cpu_capacity": 2.0,
                    "memory_capacity": 8.0,
                },
                {
                    "instance_type": "t3.medium",
                    "price": 0.067,
                    "cpu_capacity": 2.0,
                    "memory_capacity": 4.0,
                },
            ]
        },
    },
    {
        "resource_id": "i-002",
        "instance_type": "c5.2xlarge",
        "price": 0.34,
        "cpu_capacity": 8.0,
        "memory_capacity": 16.0,
        "metadata": {
            "options": [
                {
                    "instance_type": "c5.2xlarge",
                    "price": 0.34,
                    "cpu_capacity": 8.0,
                    "memory_capacity": 16.0,
                },
                {
                    "instance_type": "c5.xlarge",
                    "price": 0.17,
                    "cpu_capacity": 4.0,
                    "memory_capacity": 8.0,
                },
            ]
        },
    },
]

UTILIZATION = [
    {"resource_id": "i-001", "p95_cpu": 35.0, "p95_mem": 38.0},
    {"resource_id": "i-002", "p95_cpu": 78.0, "p95_mem": 55.0},
]


def test_generate_recommendations_downsizes_when_possible() -> None:
    """The service should recommend lower-cost shapes when headroom allows."""

    results = rightsizing.generate_recommendations(
        INVENTORY, UTILIZATION, headroom=0.15
    )
    rec_map = {item["resource_id"]: item for item in results}

    assert rec_map["i-001"]["recommended_type"] == "t3.medium"
    assert math.isclose(
        float(rec_map["i-001"]["estimated_savings"]), 0.053, rel_tol=1e-3
    )
    assert rec_map["i-001"]["method"] in {"greedy", "cp_sat"}


def test_generate_recommendations_respects_policy_cp_sat() -> None:
    """The CP-SAT policy should produce feasible assignments when available."""

    results = rightsizing.generate_recommendations(
        INVENTORY, UTILIZATION, policy="cp_sat"
    )
    rec_map = {item["resource_id"]: item for item in results}

    assert rec_map["i-002"]["recommended_type"] == "c5.2xlarge"
    assert float(rec_map["i-002"]["estimated_savings"]) == 0.0
    assert float(rec_map["i-002"]["demand_cpu"]) > 0
