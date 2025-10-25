"""Budget allocation agent leveraging constraint solving."""

from __future__ import annotations

from typing import Dict, List, Tuple

try:  # pragma: no cover - optional dependency
    import numpy as np
except Exception:  # pragma: no cover - fallback
    np = None
from ..pydantic_compat import BaseModel, Field

from .event_bus import AgentEvent, AsyncEventBus

try:  # pragma: no cover - optional dependency
    from ortools.linear_solver import pywraplp  # type: ignore
except Exception:  # pragma: no cover - fallback path
    pywraplp = None


class AllocationRequest(BaseModel):
    """Incoming request describing budget constraints."""

    total_budget: float = Field(gt=0)
    targets: Dict[str, float]
    min_quality: float = Field(default=0.7, ge=0.0, le=1.0)
    risk_tolerance: float = Field(default=0.5, ge=0.0, le=1.0)


class AllocationResponse(BaseModel):
    """Optimized allocation response."""

    allocations: Dict[str, float]
    efficiency_gain: float
    diagnostics: Dict[str, float]


class BudgetAgent:
    """Allocates budget using OR-Tools when available, otherwise heuristics."""

    def __init__(self, event_bus: AsyncEventBus | None = None) -> None:
        self._event_bus = event_bus
        self._history: List[Tuple[AllocationRequest, AllocationResponse]] = []
        if event_bus:
            event_bus.subscribe("allocation.completed", self._record_event)

    def bind_event_bus(self, event_bus: AsyncEventBus) -> None:
        self._event_bus = event_bus
        event_bus.subscribe("allocation.completed", self._record_event)

    async def allocate(self, request: AllocationRequest) -> AllocationResponse:
        if pywraplp is not None:
            response = self._solve_with_ortools(request)
        else:
            response = self._solve_with_heuristics(request)
        self._history.append((request, response))
        if self._event_bus:
            await self._event_bus.publish(
                AgentEvent(type="allocation.completed", payload=response.dict())
            )
        return response

    def _solve_with_ortools(self, request: AllocationRequest) -> AllocationResponse:
        solver = pywraplp.Solver.CreateSolver("GLOP")
        variables = {name: solver.NumVar(0, request.total_budget, name) for name in request.targets}
        solver.Add(sum(variables.values()) == request.total_budget)
        objective = solver.Objective()
        for name, target in request.targets.items():
            weight = max(0.1, target)
            objective.SetCoefficient(variables[name], weight)
        objective.SetMaximization()
        solver.Solve()
        allocations = {name: variables[name].solution_value() for name in variables}
        diagnostics = {"status": float(solver.status())}
        efficiency_gain = sum(allocations.values()) / request.total_budget
        return AllocationResponse(
            allocations=allocations,
            efficiency_gain=efficiency_gain,
            diagnostics=diagnostics,
        )

    def _solve_with_heuristics(self, request: AllocationRequest) -> AllocationResponse:
        values = list(request.targets.values())
        if np is not None:
            weights = np.array(values, dtype=float)
            weights = np.maximum(weights, 1e-3)
            weights = weights / weights.sum()
            total = request.total_budget
            allocations = {
                name: float(total * weight) for name, weight in zip(request.targets.keys(), weights)
            }
            std_dev = float(weights.std())
        else:
            total_weight = sum(max(v, 1e-3) for v in values)
            allocations = {}
            std_accumulator = 0.0
            average = total_weight / max(len(values), 1)
            for name, target in request.targets.items():
                normalized = max(target, 1e-3) / total_weight
                allocations[name] = float(request.total_budget * normalized)
                std_accumulator += (normalized - average) ** 2
            std_dev = (std_accumulator / max(len(values), 1)) ** 0.5
        diagnostics = {"solver": "heuristic", "risk": request.risk_tolerance}
        efficiency_gain = float(std_dev * request.risk_tolerance + 1.0)
        return AllocationResponse(
            allocations=allocations,
            efficiency_gain=efficiency_gain,
            diagnostics=diagnostics,
        )

    async def _record_event(self, event: AgentEvent) -> None:  # pragma: no cover - async hook
        # Currently a placeholder for analytics aggregation.
        return None

    @property
    def history(self) -> List[Tuple[AllocationRequest, AllocationResponse]]:
        return list(self._history)
