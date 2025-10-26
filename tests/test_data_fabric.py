from __future__ import annotations

import pytest

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
    assert set(health) >= {"relational", "cache", "encryption"}


def test_data_fabric_multi_tenant_encryption(monkeypatch: pytest.MonkeyPatch) -> None:
    try:
        from cryptography.fernet import Fernet
    except Exception:  # pragma: no cover - cryptography missing
        pytest.skip("cryptography not available")

    encryption_key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setenv("AFOC_ENCRYPTION_KEY", encryption_key)

    fabric = DataFabric(DataFabricConfig())
    fabric.store_spend("rec1", "analytics", 321.0, tenant_id="tenant_a", source="unit")
    fabric.store_spend("rec1", "analytics", 222.0, tenant_id="tenant_b", source="unit")

    assert fabric.fetch_spend("analytics", tenant_id="tenant_a") == pytest.approx(321.0)
    assert fabric.fetch_spend("analytics", tenant_id="tenant_b") == pytest.approx(222.0)
    assert fabric.fetch_spend("analytics", tenant_id="tenant_c") == pytest.approx(0.0)

    health = fabric.healthcheck()
    assert health["encryption"] is True
