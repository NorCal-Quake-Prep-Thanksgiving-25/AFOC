"""ROI engine powered by a reinforcement-learning allocator."""

from __future__ import annotations

from typing import Dict, List, Mapping

import random
from ..intelligence import ReinforcementAllocator
from ..pydantic_compat import BaseModel, Field

from .event_bus import AgentEvent, AsyncEventBus


class OptimizationRequest(BaseModel):
    reward_history: List[float] = Field(default_factory=list)
    actions: List[str] = Field(
        default_factory=lambda: ["architecture", "implementation", "optimization"]
    )
    exploration: float = Field(default=0.1, ge=0.0, le=1.0)


class OptimizationResponse(BaseModel):
    policy: Dict[str, float]
    selected_action: str
    expected_reward: float
    policy_confidence: float
    advantage: float


class ROIEngine:
    """Simple Q-learning loop to balance allocations."""

    def __init__(
        self, event_bus: AsyncEventBus | None = None, *, rng: random.Random | None = None
    ) -> None:
        self._event_bus = event_bus
        self._rng = rng or random.Random()  # nosec B311 - stochastic policy search
        self._allocator = ReinforcementAllocator(rng=self._rng)
        if event_bus:
            event_bus.subscribe("optimization.completed", self._noop)

    def bind_event_bus(self, event_bus: AsyncEventBus) -> None:
        self._event_bus = event_bus
        event_bus.subscribe("optimization.completed", self._noop)

    async def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        rewards = self._zip_rewards(request.actions, request.reward_history)
        policy = self._allocator.update_policy(rewards)
        action = self._allocator.select_action(request.actions, exploration=request.exploration)
        expected = self._expected_return(policy, rewards)
        advantage = rewards.get(action, expected) - expected
        response = OptimizationResponse(
            policy=policy,
            selected_action=action,
            expected_reward=expected,
            policy_confidence=policy.get(action, 0.0),
            advantage=advantage,
        )
        if self._event_bus:
            await self._event_bus.publish(
                AgentEvent(type="optimization.completed", payload=response.dict())
            )
        return response

    def _zip_rewards(self, actions: List[str], rewards: List[float]) -> Mapping[str, float]:
        return {action: float(reward) for action, reward in zip(actions, rewards)}

    def _expected_return(self, policy: Mapping[str, float], rewards: Mapping[str, float]) -> float:
        return sum(policy.get(action, 0.0) * rewards.get(action, 0.0) for action in policy)

    async def _noop(self, event: AgentEvent) -> None:  # pragma: no cover - async hook
        return None

    @property
    def policy_history(self) -> List[Mapping[str, float]]:
        return self._allocator.history

    @property
    def preference_state(self) -> Mapping[str, float]:
        return self._allocator.state
