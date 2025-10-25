"""GraphQL schema exposing the composable core."""
from __future__ import annotations

from typing import Any, Dict

try:  # pragma: no cover - optional dependency
    from fastapi import APIRouter
    from strawberry.fastapi import GraphQLRouter
    import strawberry
except Exception:  # pragma: no cover - fallback
    APIRouter = None  # type: ignore
    GraphQLRouter = None  # type: ignore
    strawberry = None  # type: ignore

from .core import ComposableIntelligenceCore


def build_graphql_router(core: ComposableIntelligenceCore | None = None) -> Any:
    if strawberry is None:
        raise RuntimeError("strawberry-graphql is required for the GraphQL interface")

    core = core or ComposableIntelligenceCore()

    @strawberry.type
    class Query:
        @strawberry.field
        async def forecast(self, history: list[float]) -> Dict[str, float]:
            request = core.forecast_agent_request_model(historical_spend=history)
            response = await core.forecast_agent.forecast(request)
            return response.dict()

        @strawberry.field
        async def allocate(self, total: float, targets: Dict[str, float]) -> Dict[str, float]:
            request = core.budget_agent_request_model(total_budget=total, targets=targets)
            response = await core.budget_agent.allocate(request)
            return response.dict()

    schema = strawberry.Schema(query=Query)
    return GraphQLRouter(schema)
