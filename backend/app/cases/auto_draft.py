"""Application service for DepartmentAction -> grounded CaseDraft."""
from __future__ import annotations
import logging
from typing import Any
from backend.app.auth.dependencies import CurrentUser
from backend.app.intelligence.case_writing import CaseWritingService
logger = logging.getLogger(__name__)

def generate_official_response_after_action(*, engine: Any, user: CurrentUser, case_id: str, action_result: dict[str, Any]) -> dict[str, Any]:
    """Persist one grounded response; report failure without undoing human truth."""
    action_id = str(action_result.get("id") or "")
    try:
        aggregate = engine.get_case_aggregate(user, case_id)
        existing = next((draft for draft in aggregate.get("drafts", []) if draft.get("draft_type") == "OFFICIAL_RESPONSE" and draft.get("grounded_action_id") == action_id), None)
        if existing:
            return {"status": "ready", "draft": existing, "idempotent": True}
        case = aggregate["case"]
        analysis = aggregate.get("analysis") or {}
        generated = CaseWritingService().draft_official_response(
            department_action=action_result,
            originator={"originator_type": case.get("originator_type"), "originator_name": case.get("originator_name")},
            routing=analysis.get("routing") or {},
            summary=analysis.get("summary") or {},
            document={"document_type": analysis.get("document_type") or "dilekce", "process_intent": analysis.get("process_intent") or "basvuru"},
            case_id=case_id,
            institution_id=case.get("institution_id") or "belediye",
        )
        if not generated.get("allowed") or not generated.get("draft"):
            return {"status": "failed", "message": "Taslak oluşturulamadı."}
        saved = engine.save_draft(user, case_id, draft_type="OFFICIAL_RESPONSE", content=generated["draft"], grounded_action_id=action_id, expected_version=action_result["case"]["version"], confirmed=True)
        return {"status": "ready", "draft": saved["draft"], "case": saved["case"]}
    except Exception as exc:
        logger.exception("Automatic grounded Case draft failed for %s", case_id)
        return {"status": "failed", "message": "Taslak oluşturulamadı.", "detail": type(exc).__name__}
