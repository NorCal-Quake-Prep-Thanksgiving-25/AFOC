"""Quantum and quantum-inspired optimizers for fiscal allocation."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Sequence

try:  # pragma: no cover - optional heavy dependency
    from qiskit import QuantumCircuit  # type: ignore
    from qiskit.primitives import Sampler  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - gracefully degrade when unavailable
    QuantumCircuit = None  # type: ignore
    Sampler = None  # type: ignore

try:  # pragma: no cover - optional heavy dependency
    import pennylane as qml  # type: ignore
    from pennylane import numpy as pnp  # type: ignore
except Exception:  # pragma: no cover - gracefully degrade when unavailable
    qml = None  # type: ignore
    pnp = None  # type: ignore


@dataclass
class QuantumOptimizationResult:
    """Internal transport object returned by the quantum optimizers."""

    backend: str
    method: str
    shots: int
    objective_value: float
    recommended_action: str | None
    state_probabilities: Mapping[str, float]
    converged: bool


class QuantumOptimizer:
    """Optional quantum solver that refines allocation policies."""

    def __init__(
        self,
        *,
        shots: int = 512,
        rng: random.Random | None = None,
    ) -> None:
        self.shots = max(32, int(shots))
        if rng is None:
            self._rng = random.Random()  # nosec B311 - deterministic fallback for reproducibility
        else:
            self._rng = rng

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def refine_policy(
        self, policy: Mapping[str, float], rewards: Mapping[str, float]
    ) -> QuantumOptimizationResult:
        actions = list(policy.keys())
        if not actions:
            return QuantumOptimizationResult(
                backend="quantum-inspired",
                method="degenerate",
                shots=self.shots,
                objective_value=0.0,
                recommended_action=None,
                state_probabilities={},
                converged=False,
            )

        weights = [max(policy[action], 0.0) * float(rewards.get(action, 0.0)) for action in actions]
        backend = self._select_backend()

        if backend == "qiskit":  # pragma: no branch - deterministic path selection
            try:
                return self._run_qiskit(actions, weights)
            except Exception:
                backend = "quantum-inspired"
        if backend == "pennylane":
            try:
                return self._run_pennylane(actions, weights)
            except Exception:
                backend = "quantum-inspired"
        return self._run_quantum_inspired(actions, weights, backend)

    @property
    def capabilities(self) -> Mapping[str, bool]:
        return {
            "qiskit": bool(QuantumCircuit and Sampler),
            "pennylane": bool(qml),
            "quantum_inspired": True,
        }

    # ------------------------------------------------------------------
    # Backends
    # ------------------------------------------------------------------
    def _run_qiskit(
        self, actions: Sequence[str], weights: Sequence[float]
    ) -> QuantumOptimizationResult:
        if QuantumCircuit is None or Sampler is None:
            raise RuntimeError("Qiskit backend not available")

        qubits = len(actions)
        circuit = QuantumCircuit(qubits)
        normaliser = max(max(weights), 1.0)
        for index, weight in enumerate(weights):
            angle = (weight / normaliser) * math.pi
            circuit.ry(angle, index)
        circuit.measure_all()

        sampler = Sampler()
        result = sampler.run(circuit, shots=self.shots).result()
        probabilities = self._collapse_probabilities(actions, result.quasi_dists[0].items())
        recommended = max(probabilities, key=lambda action: probabilities[action])
        objective = sum(probabilities[action] * weights[idx] for idx, action in enumerate(actions))
        return QuantumOptimizationResult(
            backend="qiskit",
            method="amplitude-encoding",
            shots=self.shots,
            objective_value=float(objective),
            recommended_action=recommended,
            state_probabilities=probabilities,
            converged=True,
        )

    def _run_pennylane(
        self, actions: Sequence[str], weights: Sequence[float]
    ) -> QuantumOptimizationResult:
        if qml is None or pnp is None:
            raise RuntimeError("PennyLane backend not available")

        qubits = len(actions)
        device = qml.device("default.qubit", wires=qubits, shots=self.shots)
        normaliser = max(max(weights), 1.0)

        @qml.qnode(device)  # type: ignore[misc]
        def circuit(params: Sequence[float]) -> Sequence[float]:
            for wire, param in enumerate(params):
                qml.RY(param, wires=wire)
            return qml.probs(wires=range(qubits))

        params = [((weight / normaliser) * math.pi) for weight in weights]
        probs = circuit(params)
        distribution = self._collapse_probabilities(actions, enumerate(probs))
        recommended = max(distribution, key=lambda action: distribution[action])
        objective = sum(distribution[action] * weights[idx] for idx, action in enumerate(actions))
        return QuantumOptimizationResult(
            backend="pennylane",
            method="probability-amplitudes",
            shots=self.shots,
            objective_value=float(objective),
            recommended_action=recommended,
            state_probabilities=distribution,
            converged=True,
        )

    def _run_quantum_inspired(
        self, actions: Sequence[str], weights: Sequence[float], backend_name: str
    ) -> QuantumOptimizationResult:
        # Softmax-inspired sampling approximates amplitude estimation and always available.
        temperature = max(sum(weights) / len(actions) if actions else 1.0, 1e-9)
        scaled = [math.exp(weight / temperature) for weight in weights]
        total = sum(scaled) or 1.0
        probabilities = {action: value / total for action, value in zip(actions, scaled)}
        recommended = max(probabilities, key=lambda action: probabilities[action])
        objective = sum(probabilities[action] * weights[idx] for idx, action in enumerate(actions))
        return QuantumOptimizationResult(
            backend=backend_name,
            method="quantum-inspired-softmax",
            shots=self.shots,
            objective_value=float(objective),
            recommended_action=recommended,
            state_probabilities=probabilities,
            converged=True,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _select_backend(self) -> str:
        if QuantumCircuit is not None and Sampler is not None:
            return "qiskit"
        if qml is not None and pnp is not None:
            return "pennylane"
        return "quantum-inspired"

    def _collapse_probabilities(
        self, actions: Sequence[str], quasi_distribution: Iterable
    ) -> Dict[str, float]:
        totals: Dict[str, float] = {action: 0.0 for action in actions}
        for index, probability in quasi_distribution:
            bits = self._bitstring(index, len(actions))
            for bit_index, action in enumerate(actions):
                if bits[bit_index] == "1":
                    totals[action] += float(probability)
        normaliser = sum(totals.values()) or 1.0
        return {key: value / normaliser for key, value in totals.items()}

    def _bitstring(self, value: int | str, length: int) -> str:
        if isinstance(value, str):
            bits = value[::-1]
        else:
            bits = format(int(value), f"0{length}b")
        if len(bits) < length:
            bits = bits.rjust(length, "0")
        return bits[:length]
