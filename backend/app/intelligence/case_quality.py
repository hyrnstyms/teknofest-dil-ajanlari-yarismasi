"""Case-aware quality warnings. No database mutation."""

from __future__ import annotations

from typing import Any

from backend.app.agents.quality_agent import (
    find_unverified_outcome_claims,
    find_unverified_reference_claims,
)
from backend.app.intelligence.case_writing import official_response_claims_unverified_completion


def _action_text(action: dict[str, Any] | None) -> str:
    if not action:
        return ""
    return " ".join(
        str(action.get(key) or "")
        for key in ("result", "decision", "notes")
    )


def _draft_body(draft: dict[str, Any] | None) -> str:
    if not draft:
        return ""
    payload = draft.get("draft") if isinstance(draft.get("draft"), dict) else draft
    if isinstance(payload, dict):
        return str(payload.get("body") or draft.get("body") or "")
    return str(draft.get("body") or "")


def _draft_recipient(draft: dict[str, Any] | None) -> str | None:
    if not draft:
        return None
    payload = draft.get("draft") if isinstance(draft.get("draft"), dict) else {}
    return draft.get("recipient") or (payload.get("recipient") if isinstance(payload, dict) else None)


def check_case_aware_quality(
    *,
    draft: dict[str, Any] | None,
    department_action: dict[str, Any] | None,
    originator: dict[str, Any] | None = None,
    extraction: dict[str, Any] | None = None,
    legal_analysis: dict[str, Any] | None = None,
    routing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
        "status": "pass",
        "decision": "continue",
        "checks": {},
        "issues": [],
        "warnings": [],
        "requires_human_review": False,
        "persists": False,
    }

    def add_check(key: str, status: str, msg: str) -> None:
        result["checks"][key] = {"status": status, "message": msg}
        if status == "fail":
            result["issues"].append(msg)
            result["status"] = "fail"
            result["requires_human_review"] = True
        elif status == "warning":
            result["warnings"].append(msg)
            result["requires_human_review"] = True
            if result["status"] != "fail":
                result["status"] = "warning"

    canonical = (draft or {}).get("canonical_draft_type")
    body = _draft_body(draft)
    action = department_action if isinstance(department_action, dict) else None
    if department_action is not None and hasattr(department_action, "model_dump"):
        action = department_action.model_dump()

    if canonical == "OFFICIAL_RESPONSE":
        if not action or not action.get("verified"):
            add_check(
                "department_action_required",
                "fail",
                "Doğrulanmış birim işlemi olmadan resmî cevap üretilemez.",
            )
        else:
            add_check("department_action_required", "pass", "Doğrulanmış birim işlemi mevcut.")
            action_text = _action_text(action)
            if body and action_text and body not in action_text and not all(
                part in action_text for part in body.replace(".", " ").split() if len(part) > 8
            ):
                # Contradiction: draft asserts facts absent from the action.
                if official_response_claims_unverified_completion(body, action):
                    add_check(
                        "department_action_contradiction",
                        "fail",
                        "Taslak, birim işleminde doğrulanmayan bir tamamlanma iddiası içeriyor.",
                    )
                else:
                    add_check(
                        "department_action_grounding",
                        "pass",
                        "Resmî cevap birim işlemi metnine dayanıyor.",
                    )
            elif official_response_claims_unverified_completion(body, action):
                add_check(
                    "unsupported_completion_claim",
                    "fail",
                    "Doğrulanmamış tamamlanma / onarım iddiası engellendi.",
                )
            else:
                add_check(
                    "unsupported_completion_claim",
                    "pass",
                    "Tamamlanma iddiası birim işlemiyle sınırlı.",
                )

    if find_unverified_outcome_claims(body) and not (action and action.get("verified")):
        add_check(
            "unsupported_completion_claim",
            "fail",
            "Doğrulanmamış sonuç iddiası bulundu.",
        )

    legal_analysis = legal_analysis or {}
    evidence_blob = str(legal_analysis.get("evidence") or "")
    if re_search_law_claim(body) and not evidence_blob:
        add_check(
            "unsupported_legal_claim",
            "warning",
            "Taslakta mevzuat iddiası var ancak doğrulanmış hukuki kanıt yok.",
        )

    originator = originator or {}
    expected = originator.get("originator_name") if isinstance(originator, dict) else None
    if not expected:
        fields = (extraction or {}).get("fields") or {}
        person = fields.get("person_name") or {}
        if isinstance(person, dict):
            expected = person.get("value")
    recipient = _draft_recipient(draft)
    if expected and recipient and str(recipient).strip() != str(expected).strip():
        current_dept = originator.get("current_department_code") if isinstance(originator, dict) else None
        if current_dept and str(current_dept) in str(recipient):
            add_check(
                "incorrect_recipient",
                "fail",
                "Cevap muhatabı mevcut birim; kaynak/başvuru sahibi değil.",
            )
        elif routing and recipient == routing.get("recommended_unit"):
            add_check(
                "incorrect_recipient",
                "fail",
                "Cevap muhatabı yönlendirme önerisindeki birim; kaynak değişmemelidir.",
            )
        else:
            add_check(
                "incorrect_recipient",
                "warning",
                "Taslak muhatabı kaynak/başvuru sahibi ile eşleşmiyor.",
            )
    elif expected and recipient:
        add_check("incorrect_recipient", "pass", "Muhatap kaynak/başvuru sahibidir.")

    if find_unverified_reference_claims(body, extraction):
        add_check(
            "official_style",
            "warning",
            "Doğrulanmamış tarih/sayı biçimi resmi üslup kuralına aykırı olabilir.",
        )
    elif body:
        add_check("official_style", "pass", "Resmî üslup için bariz sahte referans yok.")

    if result["status"] == "fail":
        result["decision"] = "block"
    elif result["requires_human_review"]:
        result["decision"] = "human_review"
    return result


def re_search_law_claim(body: str) -> bool:
    import re

    return bool(re.search(r"\b\d{3,6}\s+sayılı\b", body or "", re.IGNORECASE))
