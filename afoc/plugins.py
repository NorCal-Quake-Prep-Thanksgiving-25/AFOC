"""Plugin registry for composable integrations."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Dict, Iterable, Mapping


class PluginRegistry:
    """Simple pluggable registry that supports lazy factories."""

    def __init__(self) -> None:
        self._factories: Dict[str, Callable[..., Any]] = {}

    def register(self, name: str, factory: Callable[..., Any]) -> None:
        key = name.lower()
        if key in self._factories:
            raise ValueError(f"Plugin '{name}' already registered")
        self._factories[key] = factory

    def update(self, plugins: Mapping[str, Callable[..., Any]]) -> None:
        for name, factory in plugins.items():
            self.register(name, factory)

    def unregister(self, name: str) -> None:
        key = name.lower()
        self._factories.pop(key, None)

    def create(self, name: str, /, **kwargs: Any) -> Any:
        factory = self._factories.get(name.lower())
        if factory is None:
            raise KeyError(f"Plugin '{name}' is not registered")
        return factory(**kwargs)

    def __contains__(self, name: str) -> bool:  # pragma: no cover - trivial
        return name.lower() in self._factories

    def __iter__(self) -> Iterable[str]:  # pragma: no cover - trivial
        return iter(self._factories)


registry = PluginRegistry()
"""Global plugin registry used by the composable intelligence core."""
