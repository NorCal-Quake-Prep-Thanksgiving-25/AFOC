"""ROI engine with reinforcement learning inspired allocator."""
from __future__ import annotations

from typing import Dict, List

import random
from ..pydantic_compat import BaseModel, Field

from .event_bus import AgentEvent, AsyncEventBus


class OptimizationRequest(BaseModel):
    reward_history: List[float] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=lambda: ["architecture", "implementation", "optimization"])
    exploration: float = Field(default=0.1, ge=0.0, le=1.0)


class OptimizationResponse(BaseModel):
    policy: Dict[str, float]
    selected_action: str
    expected_reward: float


class ROIEngine:
    """Simple Q-learning loop to balance allocations."""

    def __init__(self, event_bus: AsyncEventBus | None = None) -> None:
        self._event_bus = event_bus
        self._q_values: Dict[str, float] = {}
        if event_bus:
            event_bus.subscribe("optimization.completed", self._noop)

    def bind_event_bus(self, event_bus: AsyncEventBus) -> None:
        self._event_bus = event_bus
        event_bus.subscribe("optimization.completed", self._noop)

    async def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        for action, reward in zip(request.actions, request.reward_history):
            self._q_values.setdefault(action, 0.0)
            self._q_values[action] = self._q_values[action] * 0.8 + 0.2 * reward
        if random.random() < request.exploration or not self._q_values:
            action = random.choice(request.actions)
        else:
            action = max(self._q_values, key=self._q_values.get)
        expected = self._q_values.get(action, 0.0)
        policy = self._softmax_policy(request.actions)
        response = OptimizationResponse(policy=policy, selected_action=action, expected_reward=expected)
        if self._event_bus:
            await self._event_bus.publish(
                AgentEvent(type="optimization.completed", payload=response.dict())
            )
        return response

    def _softmax_policy(self, actions: List[str]) -> Dict[str, float]:
        scores = [self._q_values.get(action, 0.0) for action in actions]
        max_score = max(scores) if scores else 0.0
        exps = [pow(2.71828, score - max_score) for score in scores]
        total = sum(exps) or 1.0
        return {action: value / total for action, value in zip(actions, exps)}

    async def _noop(self, event: AgentEvent) -> None:  # pragma: no cover - async hook
        return None
