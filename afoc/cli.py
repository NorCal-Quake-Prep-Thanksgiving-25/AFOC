"""Command line interface for the composable intelligence core."""

from __future__ import annotations

import argparse
import asyncio
from typing import Dict, List

from .agents.budget import AllocationRequest
from .agents.forecast import ForecastRequest
from .agents.roi import OptimizationRequest
from .core import ComposableIntelligenceCore


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


async def _run_forecast(core: ComposableIntelligenceCore, args: argparse.Namespace) -> None:
    request = ForecastRequest(historical_spend=[float(v) for v in args.history])
    response = await core.forecast_agent.forecast(request)
    print(response.json(indent=2))


async def _run_optimize(core: ComposableIntelligenceCore, args: argparse.Namespace) -> None:
    request = OptimizationRequest(reward_history=[float(v) for v in args.rewards])
    response = await core.roi_engine.optimize(request)
    print(response.json(indent=2))


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

    args = parser.parse_args(argv)
    core = ComposableIntelligenceCore()
    if args.command == "allocate":
        asyncio.run(_run_allocate(core, args))
    elif args.command == "forecast":
        asyncio.run(_run_forecast(core, args))
    elif args.command == "optimize":
        asyncio.run(_run_optimize(core, args))


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
