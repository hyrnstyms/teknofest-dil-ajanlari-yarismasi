"""Case-aware writing scenarios. Legacy WritingAgent.draft is unchanged."""

from __future__ import annotations

import re
from typing import Any

from backend.app.intelligence.contracts import (
    CanonicalDraftType,
    VerifiedDepartmentActionRequired,
)
from backend.app.intelligence.process_profiles import field_label
from backend.app.agents.quality_agent import (
    find_unverified_outcome_claims,
    find_unverified_reference_claims,
    QualityAgent,
)
from backend.app.agents.writing_agent import WritingAgent, WritingContext

_LEGACY_BY_CANONICAL: dict[str, str] = {
    "MISSING_INFORMATION_REQUEST": "eksik_bilgi_talebi",
    "INTERIM_INFORMATION": "bilgilendirme_metni",
    "OFFICIAL_RESPONSE": "cevap_yazisi",
    "INTERNAL_MEMO": "diger",
    "FORWARDING_COVER_LETTER": "ust_yazi",
}

_COMPLETION_RE = re.compile(
    r"\b(tamamlanm[ıi][sş]t[ıi]r|onar[ıi]m tamam|i[sş]lem tamam|sonu[cç]lanm[ıi][sş]t[ıi]r)\b",
    re.IGNORECASE,
)


def _originator_recipient(originator: dict[str, Any] | Any, extraction: dict[str, Any]) -> str | None:
    if originator is None:
        name = None
        originator_type = None
    elif hasattr(originator, "originator_name"):
        name = originator.originator_name
        originator_type = originator.originator_type
    else:
        name = originator.get("originator_name")
        originator_type = originator.get("originator_type")
    if name:
        return name
    fields = (extraction or {}).get("fields") or {}
    person = fields.get("person_name") or {}
    if isinstance(person, dict) and person.get("value"):
        return str(person["value"])
    if originator_type == "KURUM_ICI":
        unit = fields.get("sender_unit") or {}
        if isinstance(unit, dict) and unit.get("value"):
            return str(unit["value"])
    return None


def _action_payload(action: Any) -> dict[str, Any]:
    if action is None:
        return {}
    if hasattr(action, "model_dump"):
        return action.model_dump()
    return dict(action)


def _verified_action(action: Any) -> dict[str, Any] | None:
    payload = _action_payload(action)
    if not payload:
        return None
    if not payload.get("verified"):
        return None
    if not (str(payload.get("result") or "").strip() or str(payload.get("decision") or "").strip()):
        return None
    return payload


def _grounded_official_body(action: dict[str, Any]) -> str:
    result = str(action.get("result") or "").strip()
    decision = str(action.get("decision") or "").strip()
    sentences = [part for part in (result, decision) if part]
    body = " ".join(sentences)
    if not body.endswith("."):
        body += "."
    return body


def _missing_request_body(clarification: dict[str, Any], missing_fields: dict[str, Any]) -> str:
    question = str(clarification.get("question") or "").strip()
    if question:
        return question
    fields = clarification.get("requested_fields") or missing_fields.get("blocking_fields") or []
    labels = ", ".join(field_label(field) for field in fields)
    return (
        "Başvurunun değerlendirilmesine devam edilebilmesi için "
        f"şu bilgilerin tamamlanması gerekmektedir: {labels}."
    )


class CaseWritingService:
    """Lifecycle-aware drafts. Does not persist and does not assign Cases."""
    
    def __init__(self, writing_agent: WritingAgent | None = None):
        self.writing_agent = writing_agent or WritingAgent()

    def draft_for_intake(
        self,
        *,
        clarification: dict[str, Any] | None = None,
        missing_fields: dict[str, Any] | None = None,
        routing: dict[str, Any] | None = None,
        originator: Any = None,
        extraction: dict[str, Any] | None = None,
        allow_official_response: bool = False,
    ) -> dict[str, Any]:
        del routing, allow_official_response
        clarification = clarification or {}
        missing_fields = missing_fields or {}
        recipient = _originator_recipient(originator, extraction or {})
        if clarification.get("blocking") or missing_fields.get("has_blocking_missing"):
            body = _missing_request_body(clarification, missing_fields)
            return self._result(
                "MISSING_INFORMATION_REQUEST",
                subject="Eksik Bilginin Tamamlanması",
                body=body,
                recipient=recipient,
            )
        return self._result(
            "INTERIM_INFORMATION",
            subject="Başvuru Hk.",
            body=(
                "Başvurunuz kayıt altına alınmış olup ilgili birime yönlendirme "
                "önerisi insan onayı beklenmektedir. Kesin işlem sonucu "
                "bildirilmemiştir."
            ),
            recipient=recipient,
        )

    def draft_official_response(
        self,
        *,
        department_action: Any,
        originator: Any = None,
        extraction: dict[str, Any] | None = None,
        routing: dict[str, Any] | None = None,
        summary: dict[str, Any] | None = None,
        legal_analysis: dict[str, Any] | None = None,
        document: dict[str, Any] | None = None,
        case_id: str | None = None,
    ) -> dict[str, Any]:
        action = _verified_action(department_action)
        
        # Guard: Official response requires verified department action
        if action is None or not action.get("verified"):
            return {
                "allowed": False,
                "draft": None,
                "reason": "verified_department_action_required"
            }
            
        if case_id and action.get("case_id") and str(action.get("case_id")) != str(case_id):
            return {
                "allowed": False,
                "draft": None,
                "reason": "verified_department_action_required"
            }
            
        recipient = _originator_recipient(originator, extraction or {})
        body = _grounded_official_body(action)
        
        doc = document or {}
        context = WritingContext(
            institution_id="belediye",
            document_type=doc.get("document_type", ""),
            document_subtype=doc.get("document_subtype"),
            process_intent=doc.get("process_intent", ""),
            document_summary=(summary or {}).get("short_summary", ""),
            extracted_fields=(extraction or {}).get("fields", {}),
            verified_facts=[body],
            missing_fields=[],
            uncertain_fields=[],
            legal_evidence=(legal_analysis or {}).get("evidence", []),
            legal_context="",
            document_legal_references=[],
            routing=routing or {},
            recipient=recipient,
        )
        
        draft_result = self.writing_agent.draft(context=context)
        
        return self._result(
            "OFFICIAL_RESPONSE",
            subject=draft_result.get("draft", {}).get("subject", "Başvurunuz Hk."),
            body=draft_result.get("draft", {}).get("body", body),
            recipient=recipient,
            grounded_in_action=True,
            department_action_id=action.get("id"),
        )

    def draft_internal(
        self,
        draft_type: CanonicalDraftType,
        *,
        body: str,
        subject: str,
        originator: Any = None,
        extraction: dict[str, Any] | None = None,
        department_action: Any = None,
    ) -> dict[str, Any]:
        if draft_type == "OFFICIAL_RESPONSE":
            return self.draft_official_response(
                department_action=department_action,
                originator=originator,
                extraction=extraction,
            )
        recipient = _originator_recipient(originator, extraction or {})
        return self._result(draft_type, subject=subject, body=body, recipient=recipient)

    @staticmethod
    def _result(
        canonical: str,
        *,
        subject: str,
        body: str,
        recipient: str | None,
        grounded_in_action: bool = False,
        department_action_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "draft_type": _LEGACY_BY_CANONICAL.get(canonical, "diger"),
            "canonical_draft_type": canonical,
            "draft_generation_mode": "case_aware_deterministic",
            "draft": {"subject": subject, "body": body, "recipient": recipient},
            "body": body,
            "recipient": recipient,
            "requires_human_approval": True,
            "grounded_in_action": grounded_in_action,
            "department_action_id": department_action_id,
            "assigns_case": False,
            "allowed": True,
        }


def official_response_claims_unverified_completion(body: str, action: dict[str, Any] | None) -> bool:
    if not _COMPLETION_RE.search(body or ""):
        return bool(find_unverified_outcome_claims(body)) and not action
    verified_text = " ".join(
        [
            str((action or {}).get("result") or ""),
            str((action or {}).get("decision") or ""),
        ]
    )
    if _COMPLETION_RE.search(verified_text):
        return False
    return True
