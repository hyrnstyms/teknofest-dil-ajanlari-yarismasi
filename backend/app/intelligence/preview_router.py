"""Preview-only FastAPI router for case-aware AI operations.

This module MUST NOT be imported from ``backend.app.main`` on this branch.
Person 1 / integration mounts it once:

    from backend.app.intelligence.preview_router import router as ai_preview_router
    app.include_router(ai_preview_router)

Endpoints are side-effect free. They accept an analysis/case snapshot in the
JSON body because this branch has no Case persistence. No tables are written.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from backend.app.intelligence.case_quality import check_case_aware_quality
from backend.app.intelligence.case_writing import CaseWritingService
from backend.app.intelligence.clarification import ClarificationAgent
from backend.app.intelligence.contracts import (
    CaseIntelligenceContext,
    VerifiedDepartmentActionRequired,
)
from backend.app.intelligence.deadline import LegalDeadlineService

router = APIRouter(prefix="/api/cases", tags=["ai-preview"])
_clarification = ClarificationAgent()
_deadlines = LegalDeadlineService()
_writing = CaseWritingService()


class PreviewRequest(BaseModel):
    """Snapshot supplied by Case Engine / tests. Not loaded from DB here."""

    context: dict[str, Any] = Field(default_factory=dict)


def _context(body: PreviewRequest) -> CaseIntelligenceContext:
    try:
        return CaseIntelligenceContext.model_validate(body.context or {})
    except ValidationError as exc:
        errors = [
            {"loc": list(error.get("loc") or []), "type": error.get("type")}
            for error in exc.errors()
        ]
        raise HTTPException(
            status_code=422,
            detail={
                "code": "validation_error",
                "message": "AI önizleme girdisi geçersiz.",
                "context": {"errors": errors},
            },
        ) from exc


@router.post("/{case_id}/ai/clarification-preview")
def clarification_preview(case_id: str, body: PreviewRequest) -> dict[str, Any]:
    ctx = _context(body)
    document = ctx.document or {}
    extracted = (ctx.extraction or {}).get("fields") or {}
    result = _clarification.preview(
        missing_fields=ctx.missing_fields,
        institution_id=ctx.institution_id,
        document_type=document.get("document_type") or "",
        process_intent=document.get("process_intent") or "",
        raw_text=ctx.raw_text,
        document=document,
        extracted_fields=extracted,
        routing=ctx.routing,
    )
    result["case_id"] = case_id
    result["persisted"] = False
    return result


@router.post("/{case_id}/ai/deadline-evaluation")
def deadline_evaluation(case_id: str, body: PreviewRequest) -> dict[str, Any]:
    ctx = _context(body)
    result = _deadlines.evaluate(
        legal_analysis=ctx.legal_analysis,
        received_at=ctx.received_at,
        created_at=ctx.created_at,
        as_of=ctx.as_of,
    )
    result["case_id"] = case_id
    result["persisted"] = False
    result["operational_priority_separate"] = True
    return result


@router.post("/{case_id}/ai/official-response-preview")
def official_response_preview(case_id: str, body: PreviewRequest) -> dict[str, Any]:
    ctx = _context(body)
    try:
        draft = _writing.draft_official_response(
            department_action=ctx.department_action,
            originator=ctx.originator,
            extraction=ctx.extraction,
            routing=ctx.routing,
            summary=ctx.summary,
            legal_analysis=ctx.legal_analysis,
            document=ctx.document,
            case_id=case_id,
        )
        if draft.get("allowed") is False:
            error = VerifiedDepartmentActionRequired(context={"case_id": case_id})
            raise HTTPException(status_code=409, detail=error.as_error_detail())
    except VerifiedDepartmentActionRequired as exc:
        raise HTTPException(status_code=409, detail=exc.as_error_detail()) from exc

    quality = check_case_aware_quality(
        draft=draft,
        department_action=ctx.department_action,
        originator=ctx.originator.model_dump() if ctx.originator else {},
        extraction=ctx.extraction,
        legal_analysis=ctx.legal_analysis,
        routing=ctx.routing,
    )
    if quality.get("status") == "fail":
        draft["quality"] = quality
        draft["blocked"] = True
    else:
        draft["quality"] = quality
        draft["blocked"] = False
    draft["case_id"] = case_id
    draft["persisted"] = False
    return draft
