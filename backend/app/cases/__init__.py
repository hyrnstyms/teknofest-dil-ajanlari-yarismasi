"""Deterministic Case engine. AI agents never write these tables directly.

Hook exports are resolved lazily so importing ``cases.errors`` during auth token
validation does not create an ``auth.dependencies``/``cases.hooks`` cycle.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "notify_analysis_completed",
    "notify_analysis_started",
    "on_citizen_info_received",
]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from backend.app.cases import hooks

        return getattr(hooks, name)
    raise AttributeError(name)
