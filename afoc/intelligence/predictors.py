"""Predictive primitives powering the composable intelligence core."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import math
import random
from statistics import NormalDist
from typing import Dict, Iterable, List, Mapping, Sequence


@dataclass
class ConfidenceInterval:
    """Represents a symmetric confidence interval."""

    mean: float
    lower: float
    upper: float

    @property
    def width(self) -> float:
        return self.upper - self.lower


class BayesianForecaster:
    """Conjugate Bayesian forecaster using a normal-inverse-gamma prior."""

    def __init__(
        self,
        *,
        prior_mean: float = 1_000.0,
        prior_strength: float = 1.0,
        prior_alpha: float = 3.0,
        prior_beta: float = 500.0,
    ) -> None:
        if prior_strength <= 0:
            raise ValueError("prior_strength must be > 0")
        if prior_alpha <= 0 or prior_beta <= 0:
            raise ValueError("prior_alpha and prior_beta must be > 0")
        self._mu = float(prior_mean)
        self._kappa = float(prior_strength)
        self._alpha = float(prior_alpha)
        self._beta = float(prior_beta)

    def update(self, samples: Sequence[float], confidence: float = 0.9) -> ConfidenceInterval:
        if not samples:
            radius = self._predictive_radius(confidence)
            return ConfidenceInterval(
                mean=self._mu, lower=max(0.0, self._mu - radius), upper=self._mu + radius
            )

        n = float(len(samples))
        sample_mean = sum(samples) / n
        sum_sq = sum((value - sample_mean) ** 2 for value in samples)

        kappa_n = self._kappa + n
        mu_n = (self._kappa * self._mu + n * sample_mean) / kappa_n
        alpha_n = self._alpha + n / 2.0
        beta_n = (
            self._beta
            + 0.5 * sum_sq
            + (self._kappa * n * (sample_mean - self._mu) ** 2) / (2.0 * kappa_n)
        )

        self._mu = mu_n
        self._kappa = kappa_n
        self._alpha = alpha_n
        self._beta = beta_n

        radius = self._predictive_radius(confidence)
        lower = max(0.0, mu_n - radius)
        upper = mu_n + radius
        return ConfidenceInterval(mean=mu_n, lower=lower, upper=upper)

    def multi_step_forecast(self, steps: int, confidence: float = 0.9) -> List[ConfidenceInterval]:
        steps = max(1, int(steps))
        intervals: List[ConfidenceInterval] = []
        for _ in range(steps):
            radius = self._predictive_radius(confidence)
            intervals.append(
                ConfidenceInterval(
                    mean=self._mu,
                    lower=max(0.0, self._mu - radius),
                    upper=self._mu + radius,
                )
            )
        return intervals

    def _predictive_radius(self, confidence: float) -> float:
        clamped = min(max(confidence, 0.5), 0.999)
        z = NormalDist().inv_cdf((1.0 + clamped) / 2.0)
        scale = math.sqrt((self._beta * (self._kappa + 1.0)) / (self._alpha * self._kappa))
        return z * scale


class StreamingAnomalyDetector:
    """Maintains a rolling anomaly detector using a configurable window."""

    def __init__(
        self, *, window: int = 30, threshold: float = 3.0, warmup: int | None = None
    ) -> None:
        if window <= 1:
            raise ValueError("window must be greater than 1")
        if threshold <= 0:
            raise ValueError("threshold must be positive")
        self._window = window
        self._threshold = threshold
        self._warmup = warmup if warmup is not None else max(5, window // 2)
        self._buffer: deque[float] = deque(maxlen=window)

    def reset(self) -> None:
        self._buffer.clear()

    def detect(self, samples: Sequence[float]) -> List[int]:
        self.reset()
        anomalies: List[int] = []
        for index, value in enumerate(samples):
            if self.update(value):
                anomalies.append(index)
        return anomalies

    def update(self, value: float) -> bool:
        self._buffer.append(float(value))
        if len(self._buffer) < self._warmup:
            return False
        mean = sum(self._buffer) / len(self._buffer)
        variance = sum((item - mean) ** 2 for item in self._buffer) / max(len(self._buffer) - 1, 1)
        std = math.sqrt(variance)
        if std == 0.0:
            return False
        z = abs(value - mean) / std
        return z > self._threshold


@dataclass
class _PreferenceState:
    preferences: Dict[str, float] = field(default_factory=dict)
    baseline: float = 0.0


class ReinforcementAllocator:
    """Policy-gradient inspired allocator with entropy regularisation."""

    def __init__(
        self,
        *,
        learning_rate: float = 0.2,
        discount: float = 0.95,
        temperature: float = 0.7,
        entropy_weight: float = 0.01,
        rng: random.Random | None = None,
    ) -> None:
        if learning_rate <= 0 or discount <= 0:
            raise ValueError("learning_rate and discount must be positive")
        if temperature <= 0:
            raise ValueError("temperature must be positive")
        self._state = _PreferenceState()
        self._learning_rate = learning_rate
        self._discount = discount
        self._temperature = temperature
        self._entropy_weight = entropy_weight
        self._rng = rng or random.Random()
        self._history: List[Mapping[str, float]] = []

    def update_policy(self, action_rewards: Mapping[str, float]) -> Mapping[str, float]:
        if not action_rewards:
            return {}
        max_reward = max(action_rewards.values())
        for action, reward in action_rewards.items():
            adjusted_reward = reward + self._discount * (max_reward - reward)
            advantage = adjusted_reward - self._state.baseline
            current = self._state.preferences.get(action, 0.0)
            self._state.preferences[action] = current + self._learning_rate * advantage
            self._state.baseline = (
                1.0 - self._learning_rate
            ) * self._state.baseline + self._learning_rate * reward
        policy = self.policy(action_rewards.keys())
        self._history.append(policy)
        return policy

    def select_action(self, actions: Sequence[str], exploration: float = 0.1) -> str:
        if not actions:
            raise ValueError("actions cannot be empty")
        if self._rng.random() < exploration:  # nosec B311 - deterministic RNG injected above
            return self._rng.choice(list(actions))  # nosec B311
        policy = self.policy(actions)
        if not policy:
            return self._rng.choice(list(actions))  # nosec B311
        roll = self._rng.random()
        cumulative = 0.0
        for action, probability in policy.items():
            cumulative += probability
            if roll <= cumulative:
                return action
        return list(policy.keys())[-1]

    def policy(self, actions: Iterable[str]) -> Dict[str, float]:
        actions = list(actions)
        if not actions:
            return {}
        logits = [self._state.preferences.get(action, 0.0) for action in actions]
        max_logit = max(logits)
        exps = [math.exp((logit - max_logit) / self._temperature) for logit in logits]
        total = sum(exps) or 1.0
        base_policy = {action: value / total for action, value in zip(actions, exps)}
        entropy = -sum(p * math.log(max(p, 1e-9)) for p in base_policy.values())
        adjusted_policy = {
            action: max(0.0, probability + self._entropy_weight * entropy)
            for action, probability in base_policy.items()
        }
        normaliser = sum(adjusted_policy.values()) or 1.0
        return {action: probability / normaliser for action, probability in adjusted_policy.items()}

    @property
    def history(self) -> List[Mapping[str, float]]:
        return list(self._history)

    @property
    def state(self) -> Mapping[str, float]:
        return dict(self._state.preferences)
