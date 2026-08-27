"""Real Case/Auth integration for Copilot reads and confirmed writes."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from backend.app.auth.dependencies import CurrentUser
from backend.app.cases.departments import assert_department
from backend.app.cases.errors import validation_error, verified_department_action_required
from backend.app.cases.runtime import get_case_engine
from backend.app.db.case_models import CaseIdempotencyKey
from backend.app.db.repository import AnalysisRepository
from backend.app.intelligence.case_quality import check_case_aware_quality
from backend.app.intelligence.case_writing import CaseWritingService
from backend.app.intelligence.contracts import OriginatorContext


def user_context(user: CurrentUser) -> dict[str, Any]:
    department = assert_department(user.institution_id, user.department_code)
    return {
        "id": user.id,
        "name": user.name,
        "role": user.role,
        "institution_id": user.institution_id,
        "department_code": user.department_code,
        "department_name": department["name"],
        "_current_user": user,
    }


def load_case_state(user: CurrentUser, case_id: str) -> dict[str, Any]:
    engine = get_case_engine()
    aggregate = engine.get_case_aggregate(user, case_id)
    case = dict(aggregate["case"])
    stored: dict[str, Any] = {}
    if case.get("analysis_id"):
        stored = AnalysisRepository(engine=engine.engine).get_analysis(case["analysis_id"]) or {}
    state = dict(stored)
    state.update(case)
    analysis = aggregate.get("analysis") or {}
    state.update(
        {
            "case_id": case["id"],
            "status": case["workflow_status"],
            "permissions": aggregate.get("permissions") or [],
            "events": aggregate.get("events") or [],
            "department_actions": aggregate.get("department_actions") or [],
            "drafts": aggregate.get("drafts") or [],
            "deadline": aggregate.get("deadline") or {},
            "routing": analysis.get("routing") or stored.get("routing") or {},
            "clarification": analysis.get("clarification")
            or stored.get("clarification")
            or {},
        }
    )
    return state


def _fingerprint(action_type: str, case_id: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        {"type": action_type, "case_id": case_id, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _create_official_draft(
    user: CurrentUser,
    case_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    engine = get_case_engine()
    state = load_case_state(user, case_id)
    actions = [item for item in state.get("department_actions") or [] if item.get("verified")]
    if not actions:
        raise verified_department_action_required()
    action = actions[-1]
    originator = OriginatorContext(
        originator_type=state.get("originator_type"),
        originator_name=state.get("originator_name"),
        originator_email=state.get("originator_email"),
        current_department_code=state.get("current_department_code"),
    )
    preview = CaseWritingService().draft_official_response(
        department_action=action,
        originator=originator,
        extraction=state.get("extraction") or {},
        routing=state.get("routing") or {},
        summary=state.get("summary") or {},
        legal_analysis=state.get("legal_analysis") or {},
        document=state.get("document") or {},
        case_id=case_id,
    )
    if preview.get("allowed") is False:
        raise verified_department_action_required()
    quality = check_case_aware_quality(
        draft=preview,
        department_action=action,
        originator=originator.model_dump(),
        extraction=state.get("extraction") or {},
        legal_analysis=state.get("legal_analysis") or {},
        routing=state.get("routing") or {},
    )
    if quality.get("status") == "fail":
        raise validation_error("Resmî cevap kalite kontrolünden geçemedi.", quality=quality)
    return engine.save_draft(
        user,
        case_id,
        draft_type="OFFICIAL_RESPONSE",
        content=dict(preview.get("draft") or {}),
        grounded_action_id=action["id"],
        expected_version=int(payload["expected_version"]),
        confirmed=True,
    )


def execute_confirmed_action(
    user: CurrentUser,
    *,
    action_id: str,
    action_type: str,
    case_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Execute one allowlisted action and replay duplicate confirmations safely."""

    engine = get_case_engine()
    fingerprint = _fingerprint(action_type, case_id, payload)
    with engine.session_factory() as session:
        existing = session.query(CaseIdempotencyKey).filter_by(
            actor_user_id=user.id,
            key=action_id,
        ).one_or_none()
        if existing is not None:
            if existing.request_fingerprint != fingerprint:
                raise validation_error("Onay anahtarı farklı bir işlem için kullanılamaz.")
            return dict(existing.response_json or {})

    try:
        expected_version = int(payload.get("expected_version"))
    except (TypeError, ValueError) as exc:
        raise validation_error("Copilot işlemi için expected_version gereklidir.") from exc
    if action_type == "ROUTE_CASE":
        result = engine.route_case(
            user,
            case_id,
            department_code=str(payload.get("department_code") or ""),
            expected_version=expected_version,
            confirmed=True,
            reason=payload.get("reason"),
            routing_snapshot=dict(payload.get("routing_snapshot") or {}),
        )
    elif action_type == "START_CASE":
        result = engine.start_case(user, case_id, expected_version, True)
    elif action_type == "REQUEST_CITIZEN_INFO":
        result = engine.create_citizen_request(
            user,
            case_id,
            payload,
            expected_version,
            True,
        )
    elif action_type == "CREATE_OFFICIAL_DRAFT":
        result = _create_official_draft(user, case_id, payload)
    elif action_type == "APPROVE_DRAFT":
        result = engine.approve_draft(
            user,
            case_id,
            str(payload.get("draft_id") or ""),
            expected_version,
            True,
        )
    elif action_type == "FINALIZE_CASE":
        result = engine.complete_case(
            user,
            case_id,
            str(payload.get("draft_id") or ""),
            expected_version,
            True,
        )
    else:
        raise validation_error("Desteklenmeyen Copilot işlemi.", action_type=action_type)

    fresh = load_case_state(user, case_id)
    response = {
        "success": True,
        "message": "İşlem Case Engine tarafından doğrulandı ve kaydedildi.",
        "case": fresh,
        "result": result,
    }
    with engine.session_factory.begin() as session:
        session.add(
            CaseIdempotencyKey(
                id=str(uuid.uuid4()),
                actor_user_id=user.id,
                key=action_id,
                request_fingerprint=fingerprint,
                response_json=response,
            )
        )
    return response
