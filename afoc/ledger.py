"""Distributed fiscal ledger implementation."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping, Sequence

from .datatypes import (
    LedgerBalance,
    LedgerEntry,
    LedgerException,
    LedgerExceptionReport,
    LedgerHealth,
    LedgerReconciliation,
    LedgerSnapshot,
    LedgerSyncReport,
    LedgerSyncStatus,
    SpendingAlert,
    SpendingAlertFeed,
)


@dataclass
class DistributedLedger:
    """Simplified distributed ledger to track fiscal entries."""

    name: str
    entries: list[LedgerEntry]

    def append(self, entry: LedgerEntry) -> None:
        self.entries.append(entry)

    def totals_by_phase(self) -> Mapping[str, float]:
        totals = defaultdict(float)
        for entry in self.entries:
            totals[entry.phase] += entry.amount
        return dict(totals)

    def burn_rate(self) -> Mapping[str, float]:
        totals = self.totals_by_phase()
        return {phase: amount / len(self.entries) if self.entries else 0.0 for phase, amount in totals.items()}


class DistributedFiscalLedger:
    """Coordinates multiple ledgers and performs reconciliations."""

    def __init__(self) -> None:
        self._ledgers: dict[str, DistributedLedger] = {}

    def register_ledger(self, name: str) -> None:
        self._ledgers.setdefault(name, DistributedLedger(name, []))

    def record_entry(self, ledger_name: str, entry: LedgerEntry) -> None:
        ledger = self._ledgers.setdefault(ledger_name, DistributedLedger(ledger_name, []))
        ledger.append(entry)

    def snapshot(self, ledger_name: str) -> LedgerSnapshot:
        ledger = self._ledgers.get(ledger_name, DistributedLedger(ledger_name, []))
        return LedgerSnapshot(
            entries=list(ledger.entries),
            totals=ledger.totals_by_phase(),
            burn_rate=ledger.burn_rate(),
        )

    def health(self) -> LedgerHealth:
        balances = []
        for ledger in self._ledgers.values():
            totals = ledger.totals_by_phase()
            for phase, amount in totals.items():
                balances.append(
                    LedgerBalance(
                        phase=f"{ledger.name}:{phase}",
                        committed=amount,
                        spent=amount * 0.8,
                        remaining=amount * 0.2,
                    )
                )
        return LedgerHealth(balances=balances)

    def reconcile(self) -> LedgerReconciliation:
        snapshots = [self.snapshot(name) for name in self._ledgers]
        discrepancies = []
        for snapshot in snapshots:
            for phase, burn in snapshot.burn_rate.items():
                if burn > 1.5:
                    discrepancies.append(f"High burn rate detected in {phase}")
        return LedgerReconciliation(snapshots=snapshots, discrepancies=discrepancies)

    def sync_status(self) -> LedgerSyncReport:
        statuses = []
        now = datetime.utcnow()
        for ledger in self._ledgers.values():
            statuses.append(
                LedgerSyncStatus(
                    ledger_name=ledger.name,
                    synced=True,
                    entries_processed=len(ledger.entries),
                    last_sync=now,
                )
            )
        return LedgerSyncReport(statuses=statuses)

    def detect_anomalies(self) -> LedgerExceptionReport:
        exceptions = []
        for ledger in self._ledgers.values():
            for entry in ledger.entries:
                if entry.amount < 0:
                    exceptions.append(LedgerException(entry=entry, reason="Negative entry detected"))
        return LedgerExceptionReport(exceptions=exceptions)

    def build_spending_alerts(self, threshold: float) -> SpendingAlertFeed:
        alerts = []
        for ledger in self._ledgers.values():
            totals = ledger.totals_by_phase()
            for phase, amount in totals.items():
                if amount > threshold:
                    alerts.append(
                        SpendingAlert(
                            phase=phase,
                            message=f"Spending exceeded threshold in {phase}",
                            severity="high",
                        )
                    )
        return SpendingAlertFeed(alerts=alerts)

