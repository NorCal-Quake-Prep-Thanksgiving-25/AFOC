"""Command line interface for the composable intelligence core."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Dict, List

from .agents.budget import AllocationRequest
from .agents.forecast import ForecastRequest
from .agents.roi import OptimizationRequest
from .core import ComposableIntelligenceCore
from .security.audit_logger import AuditLogger

AUDIT = AuditLogger()  # Security: instantiate eagerly so background commands are always recorded.


def _parse_targets(pairs: List[str]) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for pair in pairs:
        if ":" not in pair:
            raise ValueError(f"Invalid target specification: {pair}")
        name, value = pair.split(":", 1)
        result[name] = float(value)
    return result


async def _run_allocate(core: ComposableIntelligenceCore, args: argparse.Namespace) -> None:
    request = AllocationRequest(total_budget=args.total, targets=_parse_targets(args.targets))
    response = await core.budget_agent.allocate(request)
    print(response.json(indent=2))
    # Security: CLI paths now emit audit events for full traceability.
    AUDIT.log(actor="cli", action="allocate", status="success", metadata={"total": args.total})


async def _run_forecast(core: ComposableIntelligenceCore, args: argparse.Namespace) -> None:
    request = ForecastRequest(historical_spend=[float(v) for v in args.history])
    response = await core.forecast_agent.forecast(request)
    print(response.json(indent=2))
    # Security: forecasting activity recorded for compliance review.
    AUDIT.log(actor="cli", action="forecast", status="success")


async def _run_optimize(core: ComposableIntelligenceCore, args: argparse.Namespace) -> None:
    request = OptimizationRequest(reward_history=[float(v) for v in args.rewards])
    response = await core.roi_engine.optimize(request)
    payload: Dict[str, object] = (
        response.model_dump()
    )  # Security: typed payload keeps CLI output aligned with signed API payloads for forensics.
    if args.quantum_only and payload.get("quantum_summary"):
        print(json.dumps(payload["quantum_summary"], indent=2))
    else:
        print(response.json(indent=2))
    # Security: include optimisation mode for forensic clarity.
    AUDIT.log(
        actor="cli",
        action="optimize",
        status="success",
        metadata={"quantum": bool(payload.get("quantum_summary"))},
    )


async def _run_audit(core: ComposableIntelligenceCore) -> None:
    alert = await core.security_guardian.audit()
    print(alert.json(indent=2))
    # Security: auditing results captured to create immutable evidence trail.
    AUDIT.log(actor="cli", action="audit", status="success")


async def _run_health(core: ComposableIntelligenceCore) -> None:
    print(json.dumps(core.healthcheck(), indent=2))
    # Security: health checks recorded to detect unusual probing.
    AUDIT.log(actor="cli", action="health", status="success")


async def _run_ingest(core: ComposableIntelligenceCore, args: argparse.Namespace) -> None:
    if args.file:
        payload = json.loads(Path(args.file).read_text())
        records = payload if isinstance(payload, list) else [payload]
    else:
        records = [
            {
                "id": item.split(":", 2)[0],
                "workload": item.split(":", 2)[0],
                "amount": float(item.split(":", 2)[1]),
            }
            for item in args.records
        ]
    report = core.ingest_collector_payload(records, source=args.source)
    print(json.dumps(report.__dict__, default=str, indent=2))
    # Security: ingestion pipeline logging guards against silent tampering.
    AUDIT.log(
        actor="cli", action="ingest", status="success", metadata={"ingested": report.ingested}
    )


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Composable Intelligence Core CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    allocate = sub.add_parser("allocate", help="Optimize budget allocation")
    allocate.add_argument("--total", type=float, required=True)
    allocate.add_argument("--targets", nargs="+", required=True, help="phase:weight pairs")

    forecast = sub.add_parser("forecast", help="Run Bayesian forecast")
    forecast.add_argument("--history", nargs="+", required=True, help="Historical spend values")

    optimize = sub.add_parser("optimize", help="Run ROI optimization")
    optimize.add_argument("--rewards", nargs="+", required=True, help="Reward history")
    optimize.add_argument(
        "--quantum-only",
        action="store_true",
        help="Show only the quantum optimisation summary when available",
    )

    sub.add_parser("audit", help="Run security audit")
    sub.add_parser("health", help="Show system health")

    ingest = sub.add_parser("ingest", help="Ingest spend records")
    ingest.add_argument("--source", default="cli", help="Source label for ingestion")
    group = ingest.add_mutually_exclusive_group(required=True)
    group.add_argument("--records", nargs="+", help="Inline records in id:amount format")
    group.add_argument("--file", help="JSON file containing records")

    args = parser.parse_args(argv)
    core = ComposableIntelligenceCore()
    global AUDIT
    AUDIT = AuditLogger()
    if args.command == "allocate":
        asyncio.run(_run_allocate(core, args))
    elif args.command == "forecast":
        asyncio.run(_run_forecast(core, args))
    elif args.command == "optimize":
        asyncio.run(_run_optimize(core, args))
    elif args.command == "audit":
        asyncio.run(_run_audit(core))
    elif args.command == "health":
        asyncio.run(_run_health(core))
    elif args.command == "ingest":
        asyncio.run(_run_ingest(core, args))


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
