"""ROI engine powered by a reinforcement-learning allocator."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

import random
from ..datatypes import QuantumOptimizationSummary
from ..intelligence import QuantumOptimizer, ReinforcementAllocator
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
    quantum_summary: Dict[str, Any] | None = Field(default=None)


class ROIEngine:
    """Simple Q-learning loop to balance allocations."""

    def __init__(
        self,
        event_bus: AsyncEventBus | None = None,
        *,
        rng: random.Random | None = None,
        quantum_optimizer: QuantumOptimizer | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._rng = rng or random.Random()  # nosec B311 - stochastic policy search
        self._allocator = ReinforcementAllocator(rng=self._rng)
        self._quantum = quantum_optimizer or QuantumOptimizer(rng=self._rng)
        if event_bus:
            event_bus.subscribe("optimization.completed", self._noop)

    def bind_event_bus(self, event_bus: AsyncEventBus) -> None:
        self._event_bus = event_bus
        event_bus.subscribe("optimization.completed", self._noop)

    async def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        actions = request.actions or ["architecture", "implementation", "optimization"]
        rewards = self._zip_rewards(actions, request.reward_history)
        policy = dict(self._allocator.update_policy(rewards))
        action = self._allocator.select_action(actions, exploration=request.exploration)
        expected = self._expected_return(policy, rewards)
        advantage = rewards.get(action, expected) - expected
        quantum_summary = self._run_quantum_refinement(policy, rewards)
        if quantum_summary and quantum_summary.recommended_action:
            action = quantum_summary.recommended_action
            expected = rewards.get(action, expected)
            policy[action] = quantum_summary.state_probabilities.get(
                action, policy.get(action, 0.0)
            )
        response = OptimizationResponse(
            policy=policy,
            selected_action=action,
            expected_reward=expected,
            policy_confidence=policy.get(action, 0.0),
            advantage=advantage,
            quantum_summary=quantum_summary.as_payload() if quantum_summary else None,
        )
        if self._event_bus:
            await self._event_bus.publish(
                AgentEvent(type="optimization.completed", payload=response.dict())
            )
        return response

    def _zip_rewards(self, actions: List[str] | None, rewards: List[float]) -> Mapping[str, float]:
        resolved_actions = (
            actions if actions else ["architecture", "implementation", "optimization"]
        )
        return {action: float(reward) for action, reward in zip(resolved_actions, rewards)}

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

    def quantum_capabilities(self) -> Mapping[str, bool]:
        return self._quantum.capabilities

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _run_quantum_refinement(
        self, policy: Mapping[str, float], rewards: Mapping[str, float]
    ) -> QuantumOptimizationSummary | None:
        try:
            result = self._quantum.refine_policy(policy, rewards)
        except Exception:
            return None
        if not result.state_probabilities:
            return None
        summary = QuantumOptimizationSummary(
            backend=result.backend,
            method=result.method,
            shots=result.shots,
            objective_value=result.objective_value,
            recommended_action=result.recommended_action,
            converged=result.converged,
            state_probabilities=dict(result.state_probabilities),
        )
        return summary
