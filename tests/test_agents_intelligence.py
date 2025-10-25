"""Regression tests for the upgraded intelligence agents."""

from __future__ import annotations

import asyncio
import random

from afoc.agents import (
    AgentEvent,
    AsyncEventBus,
    EventBusMetrics,
    ForecastAgent,
    ForecastRequest,
    ROIEngine,
    OptimizationRequest,
)


def test_forecast_agent_produces_confident_predictions() -> None:
    agent = ForecastAgent()
    request = ForecastRequest(
        historical_spend=[900.0, 950.0, 1000.0, 1100.0, 1200.0],
        projected_events=4,
        confidence=0.9,
    )
    result = asyncio.run(agent.forecast(request))
    assert len(result.predictions) == 4
    assert result.upper >= result.mean >= result.lower
    # Ensure intervals are serialized for downstream APIs
    assert all({"mean", "lower", "upper"} <= interval.keys() for interval in result.intervals)


def test_roi_engine_learns_preference_structure() -> None:
    rng = random.Random(42)
    engine = ROIEngine(rng=rng)
    request = OptimizationRequest(
        actions=["architecture", "implementation", "optimization"],
        reward_history=[0.1, 0.9, 0.3],
        exploration=0.0,
    )
    # Run a few iterations to allow the allocator to converge
    for _ in range(3):
        result = asyncio.run(engine.optimize(request))
    assert result.selected_action == "implementation"
    assert result.policy[result.selected_action] == result.policy_confidence
    assert result.advantage > -1.0  # sanity bound on the learnt signal


def test_event_bus_records_metrics() -> None:
    bus = AsyncEventBus()
    captured: list[int] = []

    async def handler(event: AgentEvent) -> None:
        captured.append(event.payload["value"])

    bus.subscribe("test", handler)
    asyncio.run(bus.publish(AgentEvent(type="test", payload={"value": 7})))
    metrics = bus.metrics()
    assert captured == [7]
    assert isinstance(metrics, EventBusMetrics)
    assert metrics.published == 1
    assert metrics.delivered == 1
    assert metrics.subscribers >= 1
