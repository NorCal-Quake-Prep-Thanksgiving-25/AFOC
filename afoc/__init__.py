"""Autonomous Fiscal Orchestration Core package."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

__all__ = ["create_app"]


def create_app() -> "FastAPI":
    """Return the FastAPI application factory lazily."""

    from .api.app import create_app as _create_app

    return _create_app()
