"""Plain structured DTOs for case-aware intelligence.

Person 1's Case models are not imported. Integration later maps Case
records onto these dicts/models.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


QuestionType = Literal["free_text", "choice"]
DeadlineType = Literal["CALENDAR_DAY", "BUSINESS_DAY"]
DeadlineRisk = Literal["NORMAL", "APPROACHING", "CRITICAL", "OVERDUE", "UNKNOWN"]
CanonicalDraftType = Literal[
    "MISSING_INFORMATION_REQUEST",
    "INTERIM_INFORMATION",
    "OFFICIAL_RESPONSE",
    "INTERNAL_MEMO",
    "FORWARDING_COVER_LETTER",
]
IntakeWait = Literal[
    "WAIT_FOR_HUMAN_CITIZEN_INFO",
    "WAIT_FOR_HUMAN_ROUTING_CONFIRMATION",
]

VERIFIED_DEPARTMENT_ACTION_REQUIRED = "verified_department_action_required"


class MissingFieldDetail(TypedDict, total=False):
    field: str
    label: str
    reason: str
    blocking: bool
    source: str | None
    evidence: str | None
    confidence: float | None
    score: float | None
    status: str


class ClarificationPreview(BaseModel):
    needs_clarification: bool = False
    blocking: bool = False
    requested_fields: list[str] = Field(default_factory=list)
    question_type: QuestionType = "free_text"
    question: str = ""
    options: list[Any] = Field(default_factory=list)
    resume_target: str = "missing_field"
    reason: str | None = None


class RoutingRecommendation(BaseModel):
    recommended_unit: str | None = None
    recommended_department_code: str | None = None
    score: float = 0.0
    reason: str | None = None
    evidence: list[Any] = Field(default_factory=list)
    alternatives: list[Any] = Field(default_factory=list)
    requires_human_review: bool = True
    assigned: bool = False


class LegalBasis(BaseModel):
    verified: bool = False
    law_number: str | None = None
    article: str | None = None
    citation: str | None = None


class DeadlineEvaluation(BaseModel):
    applicable: bool = False
    deadline_days: int | None = None
    deadline_type: DeadlineType | None = None
    legal_basis: LegalBasis = Field(default_factory=LegalBasis)
    received_at: str | None = None
    due_at: str | None = None
    remaining_days: int | None = None
    risk_level: DeadlineRisk = "UNKNOWN"


class DepartmentActionContext(BaseModel):
    id: str | None = None
    case_id: str | None = None
    action_type: str | None = None
    result: str = ""
    decision: str = ""
    planned_date: str | None = None
    notes: str = ""
    verified: bool = False
    recorded_by_user_id: str | None = None
    created_at: str | None = None


class OriginatorContext(BaseModel):
    originator_type: str | None = None
    originator_name: str | None = None
    originator_email: str | None = None
    current_department_code: str | None = None


class CitizenResponse(BaseModel):
    """Structured evidence supplied after clarification. Not prompt text."""

    fields: dict[str, Any] = Field(default_factory=dict)
    selected_option: str | None = None
    requested_fields: list[str] = Field(default_factory=list)


class CaseIntelligenceContext(BaseModel):
    """Snapshot the Case Engine can pass into AI services."""

    institution_id: str = "belediye"
    raw_text: str = ""
    received_at: str | None = None
    created_at: str | None = None
    originator: OriginatorContext = Field(default_factory=OriginatorContext)
    document: dict[str, Any] = Field(default_factory=dict)
    extraction: dict[str, Any] = Field(default_factory=dict)
    legal_analysis: dict[str, Any] = Field(default_factory=dict)
    missing_fields: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    routing: dict[str, Any] = Field(default_factory=dict)
    clarification: dict[str, Any] = Field(default_factory=dict)
    department_action: DepartmentActionContext | None = None
    workflow_status: str | None = None
    as_of: str | None = None


class IntakeOrchestrationResult(BaseModel):
    wait_for: IntakeWait
    recommended_workflow_status: str
    blocking_missing: bool
    clarification: dict[str, Any]
    missing_information_request: dict[str, Any] | None = None
    summary: dict[str, Any] | None = None
    routing: dict[str, Any] | None = None
    official_response: None = None
    operational_priority: dict[str, Any] | None = None
    deadline_evaluation: dict[str, Any] | None = None
    assigns_case: bool = False
    commits_workflow_status: bool = False


class VerifiedDepartmentActionRequired(Exception):
    code = VERIFIED_DEPARTMENT_ACTION_REQUIRED

    def __init__(self, message: str | None = None, context: dict[str, Any] | None = None):
        self.message = message or (
            "Doğrulanmış birim işlemi olmadan resmî cevap üretilemez."
        )
        self.context = context or {}
        super().__init__(self.message)

    def as_error_detail(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "context": self.context,
        }
