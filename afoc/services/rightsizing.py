"""Resource right-sizing analysis utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, MutableMapping, Optional, Sequence

try:  # pragma: no cover - optional dependency for global optimisation
    from ortools.sat.python import cp_model
except ImportError:  # pragma: no cover - exercised via fallback tests
    cp_model = None  # type: ignore

_DEFAULT_HEADROOM = 0.15


@dataclass(frozen=True)
class ResourceOption:
    """Describe a possible instance configuration."""

    instance_type: str
    price: float
    cpu_capacity: float
    memory_capacity: float


@dataclass(frozen=True)
class RightsizingResult:
    """Structured right-sizing recommendation."""

    resource_id: str
    current_type: str
    current_price: float
    recommended_type: str
    recommended_price: float
    estimated_savings: float
    headroom: float
    policy: str
    method: str
    demand_cpu: float
    demand_memory: float

    def to_dict(self) -> Dict[str, float | str]:
        """Return a serialisable representation."""

        return {
            "resource_id": self.resource_id,
            "current_type": self.current_type,
            "current_price": self.current_price,
            "recommended_type": self.recommended_type,
            "recommended_price": self.recommended_price,
            "estimated_savings": self.estimated_savings,
            "headroom": self.headroom,
            "policy": self.policy,
            "method": self.method,
            "demand_cpu": self.demand_cpu,
            "demand_memory": self.demand_memory,
        }


def _normalise_percentage(value: Optional[float]) -> float:
    if value is None:
        return 0.0
    if value > 1:
        return value / 100.0
    return max(value, 0.0)


def _extract_options(record: Mapping[str, object]) -> List[ResourceOption]:
    metadata = record.get("metadata") if isinstance(record, Mapping) else None
    base_price = float(record.get("price", 0.0))  # type: ignore[arg-type]
    base_cpu = float(record.get("cpu_capacity", record.get("cpu_units", 1.0)))  # type: ignore[arg-type]
    base_memory = float(record.get("memory_capacity", record.get("memory_gib", 1.0)))  # type: ignore[arg-type]
    base_type = str(record.get("instance_type", record.get("resource_type", "unknown")))

    options: list[ResourceOption] = [
        ResourceOption(
            instance_type=base_type,
            price=base_price,
            cpu_capacity=max(base_cpu, 0.1),
            memory_capacity=max(base_memory, 0.1),
        )
    ]

    if isinstance(metadata, Mapping):
        raw_options = metadata.get("options", [])
        if isinstance(raw_options, Sequence):
            for item in raw_options:
                if not isinstance(item, Mapping):
                    continue
                options.append(
                    ResourceOption(
                        instance_type=str(item.get("instance_type", base_type)),
                        price=float(item.get("price", base_price)),
                        cpu_capacity=max(
                            float(
                                item.get(
                                    "cpu_capacity",
                                    item.get("cpu_units", base_cpu),
                                )
                            ),
                            0.1,
                        ),
                        memory_capacity=max(
                            float(
                                item.get(
                                    "memory_capacity",
                                    item.get("memory_gib", base_memory),
                                )
                            ),
                            0.1,
                        ),
                    )
                )

    unique: MutableMapping[str, ResourceOption] = {}
    ordered: list[ResourceOption] = []
    for option in options:
        if option.instance_type in unique:
            continue
        unique[option.instance_type] = option
        ordered.append(option)
    return ordered


def _compute_demand(
    option: ResourceOption,
    p95_cpu: Optional[float],
    p95_mem: Optional[float],
    headroom: float,
) -> tuple[float, float]:
    cpu_ratio = _normalise_percentage(p95_cpu)
    mem_ratio = _normalise_percentage(p95_mem)
    demand_cpu = option.cpu_capacity * cpu_ratio * (1.0 + headroom)
    demand_mem = option.memory_capacity * mem_ratio * (1.0 + headroom)
    return demand_cpu, demand_mem


def _choose_option_greedy(
    options: Sequence[ResourceOption],
    demand_cpu: float,
    demand_mem: float,
) -> ResourceOption:
    feasible = [
        option
        for option in options
        if option.cpu_capacity >= demand_cpu and option.memory_capacity >= demand_mem
    ]
    if not feasible:
        return options[-1]
    return min(
        feasible,
        key=lambda option: (option.price, option.cpu_capacity, option.memory_capacity),
    )


def _solve_with_cpsat(
    catalog: Mapping[str, Sequence[ResourceOption]],
    demand: Mapping[str, tuple[float, float]],
) -> Dict[str, ResourceOption]:
    if cp_model is None:  # pragma: no cover - fallback exercised elsewhere
        return {
            resource_id: _choose_option_greedy(options, *demand[resource_id])
            for resource_id, options in catalog.items()
        }

    model = cp_model.CpModel()
    decision_vars: Dict[tuple[str, int], cp_model.IntVar] = {}

    scaled_catalog: Dict[str, Sequence[ResourceOption]] = {
        resource_id: list(options) for resource_id, options in catalog.items()
    }
    for resource_id, options in scaled_catalog.items():
        for index, option in enumerate(options):
            decision_vars[(resource_id, index)] = model.NewBoolVar(
                f"select_{resource_id}_{index}"
            )

    for resource_id, options in scaled_catalog.items():
        vars_for_resource = [
            decision_vars[(resource_id, idx)] for idx in range(len(options))
        ]
        model.Add(sum(vars_for_resource) == 1)

        cpu_demand, mem_demand = demand[resource_id]
        cpu_scaled = int(round(cpu_demand * 100))
        mem_scaled = int(round(mem_demand * 100))
        model.Add(
            sum(
                int(round(option.cpu_capacity * 100))
                * decision_vars[(resource_id, idx)]
                for idx, option in enumerate(options)
            )
            >= cpu_scaled
        )
        model.Add(
            sum(
                int(round(option.memory_capacity * 100))
                * decision_vars[(resource_id, idx)]
                for idx, option in enumerate(options)
            )
            >= mem_scaled
        )

    model.Minimize(
        sum(
            int(round(option.price * 10000)) * decision_vars[(resource_id, idx)]
            for resource_id, options in scaled_catalog.items()
            for idx, option in enumerate(options)
        )
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5
    status = solver.Solve(model)
    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    ):  # pragma: no cover - rarely triggered
        return {
            resource_id: _choose_option_greedy(options, *demand[resource_id])
            for resource_id, options in catalog.items()
        }

    selection: Dict[str, ResourceOption] = {}
    for resource_id, options in scaled_catalog.items():
        for idx, option in enumerate(options):
            if solver.BooleanValue(decision_vars[(resource_id, idx)]):
                selection[resource_id] = option
                break
        else:  # pragma: no cover - solver guarantees assignment
            selection[resource_id] = options[-1]
    return selection


def generate_recommendations(
    resource_inventory: Sequence[Mapping[str, object]],
    utilization: Sequence[Mapping[str, object]],
    *,
    headroom: float = _DEFAULT_HEADROOM,
    policy: str = "cost",
) -> List[Dict[str, float | str]]:
    """Generate right-sizing recommendations for the provided resources."""

    if headroom < 0:
        raise ValueError("headroom must be non-negative")

    inventory_map: Dict[str, Mapping[str, object]] = {}
    for record in resource_inventory:
        resource_id = str(record.get("resource_id"))
        if not resource_id:
            continue
        inventory_map[resource_id] = record

    utilization_map: Dict[str, Mapping[str, object]] = {
        str(item.get("resource_id")): item
        for item in utilization
        if item.get("resource_id")
    }

    catalog: Dict[str, List[ResourceOption]] = {}
    demand: Dict[str, tuple[float, float]] = {}

    for resource_id, resource in inventory_map.items():
        options = _extract_options(resource)
        catalog[resource_id] = options
        current_option = options[0]
        metrics = utilization_map.get(resource_id, {})
        demand_cpu, demand_mem = _compute_demand(
            current_option,
            metrics.get("p95_cpu"),  # type: ignore[arg-type]
            metrics.get("p95_mem"),  # type: ignore[arg-type]
            headroom,
        )
        demand[resource_id] = (demand_cpu, demand_mem)

    if not catalog:
        return []

    if policy.lower() == "cp_sat":
        chosen = _solve_with_cpsat(catalog, demand)
        method = "cp_sat" if cp_model is not None else "greedy"
    else:
        chosen = {
            resource_id: _choose_option_greedy(options, *demand[resource_id])
            for resource_id, options in catalog.items()
        }
        method = "greedy"

    results: list[RightsizingResult] = []
    for resource_id, resource in inventory_map.items():
        options = catalog[resource_id]
        selected = chosen[resource_id]
        current = options[0]
        demand_cpu, demand_mem = demand[resource_id]
        estimated_savings = max(0.0, float(current.price) - float(selected.price))
        results.append(
            RightsizingResult(
                resource_id=resource_id,
                current_type=current.instance_type,
                current_price=float(current.price),
                recommended_type=selected.instance_type,
                recommended_price=float(selected.price),
                estimated_savings=estimated_savings,
                headroom=headroom,
                policy=policy,
                method=method,
                demand_cpu=demand_cpu,
                demand_memory=demand_mem,
            )
        )

    return [item.to_dict() for item in results]


__all__ = [
    "RightsizingResult",
    "generate_recommendations",
]
