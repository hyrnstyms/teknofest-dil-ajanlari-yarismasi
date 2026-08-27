"""Persistence bridge between the Analysis work product and Case lifecycle.

The intelligence services remain pure and never mutate Case tables.  This
module is the explicit application-service boundary that persists their
outputs and advances the deterministic Case Engine when appropriate.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select

from backend.app.auth.dependencies import CurrentUser
from backend.app.cases.enums import STATUS_ANALYZING
from backend.app.db.case_models import CaseRecord
from backend.app.db.repository import AnalysisRepository
from backend.app.intelligence.contracts import (
    CaseIntelligenceContext,
    CitizenResponse,
    OriginatorContext,
)
from backend.app.intelligence.orchestration import CaseAwareOrchestrator
from backend.app.intelligence.resume import resume_after_citizen_info


logger = logging.getLogger(__name__)


def _context(
    state: dict[str, Any],
    *,
    institution_id: str,
    received_at: str,
    originator: OriginatorContext,
) -> CaseIntelligenceContext:
    return CaseIntelligenceContext(
        institution_id=institution_id,
        raw_text=str(state.get("raw_text") or ""),
        received_at=received_at,
        # created_at is retained as provenance only. LegalDeadlineService does
        # not use it as a substitute for the reliable Case receipt timestamp.
        created_at=state.get("created_at"),
        originator=originator,
        document=dict(state.get("document") or {}),
        extraction=dict(state.get("extraction") or {}),
        legal_analysis=dict(state.get("legal_analysis") or {}),
        missing_fields=dict(state.get("missing_fields") or {}),
        summary=dict(state.get("summary") or {}),
        routing=dict(state.get("routing") or {}),
        clarification=dict(state.get("clarification") or {}),
    )


def persist_initial_intelligence(
    *,
    engine: Any,
    user: CurrentUser,
    case: dict[str, Any],
    analysis_id: str,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate the already-produced Analysis snapshot and persist the bridge.

    The legacy workflow has already performed document/extraction/legal work.
    The case-aware orchestrator consumes those results rather than rerunning the
    full document pipeline.
    """

    context = _context(
        state,
        institution_id=user.institution_id,
        received_at=case["received_at"],
        originator=OriginatorContext(
            originator_type=case.get("originator_type"),
            originator_name=case.get("originator_name"),
            originator_email=case.get("originator_email"),
            current_department_code=case.get("current_department_code"),
        ),
    )
    outcome = CaseAwareOrchestrator(user.institution_id).evaluate_first_stage(context)
    updated = dict(state)
    updated["case_orchestration"] = outcome
    updated["clarification"] = outcome.get("clarification") or {}
    updated["deadline_evaluation"] = outcome.get("deadline_evaluation") or {}
    if outcome.get("summary"):
        updated["summary"] = outcome["summary"]
    if outcome.get("routing"):
        updated["routing"] = outcome["routing"]
    updated["case_id"] = case["id"]
    updated["tracking_code"] = case["tracking_code"]
    AnalysisRepository(engine=engine.engine).update_analysis(analysis_id, updated)
    state.clear()
    state.update(updated)
    return outcome


def resume_case_after_citizen_info(case_id: str, payload: dict[str, Any]) -> None:
    """Persist structured citizen evidence and refresh routing from fresh state."""

    from backend.app.cases.runtime import get_case_engine

    engine = get_case_engine()
    with engine.session_factory() as session:
        case = session.scalar(select(CaseRecord).where(CaseRecord.id == case_id))
        if case is None or not case.analysis_id:
            return
        analysis_id = case.analysis_id
        institution_id = case.institution_id
        received_at = case.received_at.isoformat()
        originator = OriginatorContext(
            originator_type=case.originator_type,
            originator_name=case.originator_name,
            originator_email=case.originator_email,
            current_department_code=case.current_department_code,
        )

    repository = AnalysisRepository(engine=engine.engine)
    prior = repository.get_analysis(analysis_id)
    if not prior:
        return
    answers = dict(payload.get("answers") or {})
    clarification = dict(prior.get("clarification") or {})
    selected = answers.get("permit_type") if "permit_type" in answers else None
    context = _context(
        prior,
        institution_id=institution_id,
        received_at=received_at,
        originator=originator,
    )
    resumed = resume_after_citizen_info(
        context,
        CitizenResponse(
            fields=answers,
            selected_option=str(selected) if selected is not None else None,
            requested_fields=list(clarification.get("requested_fields") or []),
        ),
    )
    updated = dict(prior)
    updated.update(
        {
            "extraction": resumed["extraction"],
            "missing_fields": resumed["missing_fields"],
            "clarification": resumed["clarification"],
            "routing": resumed.get("routing") or {},
            "citizen_evidence_fields": resumed["citizen_evidence_fields"],
            "case_orchestration": {
                **dict(prior.get("case_orchestration") or {}),
                "blocking_missing": not resumed["resolved"],
                "clarification": resumed["clarification"],
                "routing": resumed.get("routing"),
                "reevaluated": resumed["reevaluated"],
            },
        }
    )
    repository.update_analysis(analysis_id, updated)

    # A missing-field resume returns the Case to ANALYZING. Once the focused
    # reevaluation completes, return it to human review. Routing resumes go
    # directly to READY_TO_ROUTE in the Case Engine and need no extra mutation.
    if payload.get("resume_target") == STATUS_ANALYZING:
        engine.mark_analysis_completed(
            case_id,
            user=None,
            ready_to_route=bool(resumed["resolved"] and resumed.get("routing")),
        )


def register_intelligence_hooks() -> None:
    """Register the bridge once even under repeated app imports in tests."""

    from backend.app.cases import hooks

    if resume_case_after_citizen_info not in hooks._citizen_info_listeners:
        hooks.on_citizen_info_received(resume_case_after_citizen_info)
