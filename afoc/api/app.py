"""FastAPI application bootstrap."""

from fastapi import FastAPI

from .routers import anomalies, forecasting, ingest, reports, rightsizing


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(title="AFOC API")
    app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
    app.include_router(anomalies.router, prefix="/anomalies", tags=["anomalies"])
    app.include_router(rightsizing.router, prefix="/rightsizing", tags=["rightsizing"])
    app.include_router(forecasting.router, prefix="/forecasting", tags=["forecasting"])
    app.include_router(reports.router, prefix="/reports", tags=["reports"])
    return app
