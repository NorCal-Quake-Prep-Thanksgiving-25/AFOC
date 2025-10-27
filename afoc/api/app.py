"""FastAPI application bootstrap."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import anomalies, forecasting, ingest, reports, rightsizing


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(title="AFOC API", version="0.1.0")

    # Security: explicit CORS configuration keeps dashboards working without exposing creds.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def _add_version_header(request, call_next):  # type: ignore[override]
        """Attach a version header so clients can verify the responding build."""

        response = await call_next(request)
        response.headers["X-AFOC-Version"] = app.version
        return response

    app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
    app.include_router(anomalies.router, prefix="", tags=["anomalies"])
    app.include_router(rightsizing.router, prefix="/optimize", tags=["optimize"])
    app.include_router(forecasting.router, prefix="/forecast", tags=["forecast"])
    app.include_router(reports.router, prefix="/report", tags=["report"])
    return app
