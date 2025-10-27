"""Cost anomaly detection services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List

import numpy as np
import pandas as pd

try:  # pragma: no cover - optional dependency guard
    from sklearn.ensemble import IsolationForest
except ImportError:  # pragma: no cover - fallback path tested separately
    IsolationForest = None  # type: ignore


@dataclass
class Anomaly:
    """Represents a detected anomaly."""

    ts: datetime
    scope: tuple[str, str | None, str]
    observed: float
    expected: float
    score: float
    method: str


def _prepare_frame(records: Iterable[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(list(records))
    if frame.empty:
        return frame
    frame = frame.copy()
    frame["ts"] = pd.to_datetime(frame["ts"], utc=False)
    frame.sort_values("ts", inplace=True)
    frame["provider"].fillna("unknown", inplace=True)
    frame["account"].fillna("", inplace=True)
    return frame


def _apply_isolation_forest(features: pd.DataFrame) -> np.ndarray:
    contamination = min(0.1, max(0.02, 5.0 / max(len(features), 1)))
    model = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=200,
    )
    return model.fit_predict(features)


def _robust_z_scores(values: pd.Series) -> pd.Series:
    median = values.median()
    mad = (np.abs(values - median)).median()
    if mad == 0:
        return pd.Series(np.zeros(len(values)), index=values.index)
    return 0.6745 * (values - median) / mad


def detect_anomalies(records: Iterable[dict]) -> List[Anomaly]:
    """Detect anomalous cost spikes across provider/account/service scopes."""

    frame = _prepare_frame(records)
    if frame.empty:
        return []

    anomalies: list[Anomaly] = []
    grouped = frame.groupby(["provider", "account", "service"], dropna=False)

    for scope, group in grouped:
        group = group.sort_values("ts").copy()
        group["rolling_mean"] = (
            group["cost_usd"].rolling(window=30, min_periods=7).mean()
        )
        group["rolling_std"] = (
            group["cost_usd"].rolling(window=30, min_periods=7).std().fillna(0.0)
        )
        group["expected"] = group["rolling_mean"].fillna(group["cost_usd"].expanding().mean())
        group["residual"] = group["cost_usd"] - group["expected"]

        valid = group.dropna(subset=["expected"])
        if valid.empty:
            continue

        if IsolationForest is not None and len(valid) >= 12:
            predictions = _apply_isolation_forest(valid[["residual", "cost_usd"]])
            scores = np.abs(valid["residual"]) / (valid["rolling_std"] + 1e-6)
            method = "isolation_forest"
            flags = (predictions == -1) & (valid["residual"] > valid["rolling_std"] * 1.5)
        else:
            scores = np.abs(_robust_z_scores(valid["residual"]))
            method = "robust_z"
            flags = scores > 3.5

        for idx in valid[flags].index:
            row = valid.loc[idx]
            anomalies.append(
                Anomaly(
                    ts=row["ts"],
                    scope=scope,
                    observed=float(row["cost_usd"]),
                    expected=float(row["expected"]),
                    score=float(scores.loc[idx]),
                    method=method,
                )
            )

    return anomalies


def detect_anomalies_from_dataframe(frame: pd.DataFrame) -> List[Anomaly]:
    """Convenience wrapper accepting a pandas DataFrame directly."""

    return detect_anomalies(frame.to_dict("records"))
