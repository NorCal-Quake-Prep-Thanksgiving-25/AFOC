"""ML lifecycle helpers with graceful fallbacks when MLflow is unavailable."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Mapping, MutableMapping

from ..logging import get_logger

try:  # pragma: no cover - optional dependency
    import mlflow
except Exception:  # pragma: no cover - fallback when mlflow missing
    mlflow = None  # type: ignore


logger = get_logger(__name__)


@dataclass
class ForecastLogPayload:
    """Payload describing a forecast operation for logging."""

    history: Iterable[float]
    predictions: Iterable[float]
    diagnostics: Mapping[str, float]
    tags: Mapping[str, str]


class MLLifecycleManager:
    """Handles optional MLflow logging."""

    def __init__(
        self,
        *,
        tracking_uri: str | None = None,
        experiment_name: str = "afoc-intelligence",
    ) -> None:
        self._enabled = mlflow is not None
        self._tracking_uri = tracking_uri or os.getenv("AFOC_MLFLOW_TRACKING_URI")
        self._experiment_name = experiment_name
        if self._enabled and self._tracking_uri:
            try:  # pragma: no cover - optional dependency
                mlflow.set_tracking_uri(self._tracking_uri)
                mlflow.set_experiment(self._experiment_name)
            except Exception as exc:  # pragma: no cover - runtime guard
                logger.warning("Failed to configure MLflow", error=str(exc))
                self._enabled = False

    def log_forecast(self, payload: ForecastLogPayload) -> None:
        if not self._enabled:
            logger.debug("Skipping MLflow logging; tracker disabled")
            return
        metrics: MutableMapping[str, float] = dict(payload.diagnostics)
        metrics["history_len"] = float(len(list(payload.history)))
        metrics["prediction_len"] = float(len(list(payload.predictions)))
        try:  # pragma: no cover - optional dependency
            with mlflow.start_run(run_name=payload.tags.get("run_name", "forecast"), nested=True):
                mlflow.log_metrics(metrics)
                mlflow.set_tags(dict(payload.tags))
        except Exception as exc:  # pragma: no cover - runtime guard
            logger.warning("Failed to log forecast to MLflow", error=str(exc))


default_ml_tracker = MLLifecycleManager()
