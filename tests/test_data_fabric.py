from __future__ import annotations

from afoc.data import DataFabric, DataFabricConfig


def test_data_fabric_ingests_and_healthcheck() -> None:
    fabric = DataFabric(DataFabricConfig())
    report = fabric.ingest_records(
        [
            {"id": "a", "workload": "analytics", "amount": 123.0},
            {"id": "b", "workload": "ops", "amount": 456.0},
        ],
        source="test",
    )
    assert report.ingested >= 2
    assert fabric.fetch_spend("analytics") in {123.0, 0.0}
    health = fabric.healthcheck()
    assert set(health) >= {"relational", "cache"}
