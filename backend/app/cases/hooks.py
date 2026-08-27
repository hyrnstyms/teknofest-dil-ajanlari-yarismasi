"""Process-intelligence hooks for Person 2. These never write Case tables themselves."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.app.auth.dependencies import CurrentUser

_citizen_info_listeners: list[Callable[[str, dict[str, Any]], None]] = []


def on_citizen_info_received(listener: Callable[[str, dict[str, Any]], None]) -> Callable[[str, dict[str, Any]], None]:
    """Register a callback invoked after citizen info is stored.

    Person 2 may use this to schedule re-analysis. The Case Engine does not
    rerun AI. The callback MUST NOT open nested Case writes on the same
    session; use a follow-up service call.
    """
    _citizen_info_listeners.append(listener)
    return listener


def emit_citizen_info_received(case_id: str, payload: dict[str, Any]) -> None:
    for listener in list(_citizen_info_listeners):
        listener(case_id, payload)


def notify_analysis_started(case_id: str, actor: CurrentUser | None = None) -> dict[str, Any]:
    """Person 2 integration: RECEIVED -> ANALYZING."""
    from backend.app.cases.runtime import get_case_engine

    return get_case_engine().mark_analysis_started(case_id, actor)


def notify_analysis_completed(case_id: str, actor: CurrentUser | None = None) -> dict[str, Any]:
    """Person 2 integration: ANALYZING -> WAITING_INITIAL_REVIEW."""
    from backend.app.cases.runtime import get_case_engine

    return get_case_engine().mark_analysis_completed(case_id, actor)
