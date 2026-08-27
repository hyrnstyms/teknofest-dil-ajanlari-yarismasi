"""Centralized Case state machine. No durable ROUTED status."""

from __future__ import annotations

from backend.app.cases.enums import (
    STATUS_ANALYZING,
    STATUS_CLOSED,
    STATUS_COMPLETED,
    STATUS_IN_DEPARTMENT,
    STATUS_IN_PROGRESS,
    STATUS_READY_TO_ROUTE,
    STATUS_RECEIVED,
    STATUS_RESPONSE_DRAFTED,
    STATUS_WAITING_CITIZEN_INFO,
    STATUS_WAITING_FINAL_APPROVAL,
    STATUS_WAITING_INITIAL_REVIEW,
)
from backend.app.cases.errors import invalid_case_transition

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    STATUS_RECEIVED: frozenset({STATUS_ANALYZING}),
    STATUS_ANALYZING: frozenset({STATUS_WAITING_INITIAL_REVIEW, STATUS_WAITING_CITIZEN_INFO}),
    STATUS_WAITING_CITIZEN_INFO: frozenset({STATUS_ANALYZING, STATUS_READY_TO_ROUTE}),
    STATUS_WAITING_INITIAL_REVIEW: frozenset({STATUS_WAITING_CITIZEN_INFO, STATUS_READY_TO_ROUTE}),
    STATUS_READY_TO_ROUTE: frozenset({STATUS_IN_DEPARTMENT}),
    STATUS_IN_DEPARTMENT: frozenset({STATUS_IN_PROGRESS}),
    STATUS_IN_PROGRESS: frozenset({STATUS_RESPONSE_DRAFTED}),
    STATUS_RESPONSE_DRAFTED: frozenset({STATUS_WAITING_FINAL_APPROVAL}),
    STATUS_WAITING_FINAL_APPROVAL: frozenset({STATUS_RESPONSE_DRAFTED, STATUS_COMPLETED}),
    STATUS_COMPLETED: frozenset({STATUS_CLOSED}),
    STATUS_CLOSED: frozenset(),
}


class CaseWorkflowService:
    @staticmethod
    def assert_transition(current_status: str, target_status: str) -> None:
        if current_status == STATUS_CLOSED:
            raise invalid_case_transition(current_status, target_status)
        allowed = ALLOWED_TRANSITIONS.get(current_status, frozenset())
        if target_status not in allowed:
            raise invalid_case_transition(current_status, target_status)

    @staticmethod
    def can_transition(current_status: str, target_status: str) -> bool:
        if current_status == STATUS_CLOSED:
            return False
        return target_status in ALLOWED_TRANSITIONS.get(current_status, frozenset())
