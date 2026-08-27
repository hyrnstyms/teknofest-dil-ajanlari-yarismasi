"""Request/response schemas for Case APIs. No role/institution fields on writes."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class CreateCaseRequest(BaseModel):
    source_type: Literal["VATANDAS", "DIS_KURUM", "KURUM_ICI"]
    source_channel: Literal["WEB_FORM", "FIZIKI_EVRAK", "EPOSTA", "KEP", "EBYS", "KURUM_ICI"]
    originator_type: Literal["VATANDAS", "DIS_KURUM", "KURUM_ICI"]
    originator_name: str = Field(min_length=1, max_length=256)
    originator_email: str | None = None
    originator_phone: str | None = None
    analysis_id: str | None = None
    priority: str | None = None
    received_at: datetime | None = None
    confirmed: bool = False


class VersionedAction(BaseModel):
    expected_version: int
    confirmed: bool = False


class RouteCaseRequest(VersionedAction):
    department_code: str | None = None
    target_department_code: str | None = None
    reason: str | None = None
    routing_snapshot: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def resolve_department_code(self) -> "RouteCaseRequest":
        code = (self.department_code or self.target_department_code or "").strip()
        if not code:
            raise ValueError("department_code gereklidir.")
        self.department_code = code
        return self


class DepartmentActionRequest(VersionedAction):
    action_type: str = Field(min_length=1, max_length=64)
    result: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    planned_date: date | None = None
    notes: str = ""


class CitizenRequestCreate(VersionedAction):
    question: str = Field(min_length=1)
    requested_fields: list[str] = Field(min_length=1)
    question_type: str = "free_text"
    options: list[Any] = Field(default_factory=list)
    blocking: bool = True
    resume_target: str = "READY_TO_ROUTE"


class TaskAssignmentRequest(VersionedAction):
    assigned_user_id: str = Field(min_length=1)
    reason: str | None = None


class TaskStatusRequest(VersionedAction):
    status: Literal["ASSIGNED", "IN_PROGRESS", "WAITING_INFO", "DONE"]
    reason: str | None = None


class InformationRequestCreate(VersionedAction):
    requested_fields: list[str] = Field(min_length=1)
    reason: str = Field(min_length=1)
    target_type: Literal["VATANDAS", "DIS_KURUM", "KURUM_ICI"] | None = None
    target_name: str | None = None
    target_department: str | None = None


class SaveDraftRequest(VersionedAction):
    draft_type: str
    content: dict[str, Any] = Field(default_factory=dict)
    grounded_action_id: str | None = None


class CompleteCaseRequest(VersionedAction):
    draft_id: str


class CompleteInfoRequest(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)
