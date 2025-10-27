"""Backward compatibility shim for the legacy orchestrator import."""

from __future__ import annotations

from .orchestrator.scheduler import OrchestratorAgent as Agent

__all__ = ["Agent"]
