"""Resume after structured citizen information. Pure service, no DB."""

from __future__ import annotations

from typing import Any

from backend.app.agents.missing_field_agent import MissingFieldAgent
from backend.app.agents.routing_agent import RoutingAgent
from backend.app.intelligence.clarification import ClarificationAgent
from backend.app.intelligence.contracts import CaseIntelligenceContext, CitizenResponse
from backend.app.intelligence.process_profiles import (
    PERMIT_DEPARTMENT_BY_OPTION,
    PERMIT_OPTIONS,
    field_label,
)


def _as_field_evidence(value: Any, source: str = "citizen_response") -> dict[str, Any]:
    if isinstance(value, dict) and "value" in value:
        payload = dict(value)
        payload.setdefault("validated", True)
        payload.setdefault("status", "present")
        payload.setdefault("source", source)
        return payload
    return {
        "value": value,
        "validated": True,
        "status": "present",
        "source": source,
        "evidence": "citizen_response",
    }


def merge_citizen_evidence(
    extraction: dict[str, Any],
    citizen: CitizenResponse,
    requested_fields: list[str] | None = None,
) -> dict[str, Any]:
    merged = dict(extraction or {})
    fields = dict(merged.get("fields") or {})
    for key, value in (citizen.fields or {}).items():
        if requested_fields is not None and key not in requested_fields:
            continue
        
        existing = fields.get(key)
        # Prevent silent overwrite of a contradictory validated field
        if existing and isinstance(existing, dict) and existing.get("validated") and existing.get("value"):
            if str(existing.get("value")).strip().lower() != str(value).strip().lower():
                # Contradiction: do not overwrite silently. Mark for human review.
                fields[key] = {
                    "value": f"{existing['value']} (Vatandaş itirazı: {value})",
                    "status": "uncertain",
                    "validated": False,
                    "source": "contradiction_review_required"
                }
                continue
                
        fields[key] = _as_field_evidence(value)
        
    if citizen.selected_option:
        option = citizen.selected_option
        if option in PERMIT_DEPARTMENT_BY_OPTION:
            fields["permit_type"] = _as_field_evidence(option)
        elif "permit_type" not in fields:
            fields["permit_type"] = _as_field_evidence(option)
    merged["fields"] = fields
    return merged


def resume_after_citizen_info(
    prior: CaseIntelligenceContext | dict[str, Any],
    citizen_response: CitizenResponse | dict[str, Any],
    *,
    missing_field_agent: MissingFieldAgent | None = None,
    routing_agent: RoutingAgent | None = None,
    clarification_agent: ClarificationAgent | None = None,
) -> dict[str, Any]:
    """Reevaluate only missing-field, clarification and routing.

    Citizen content is stored as structured extraction evidence. It is never
    concatenated into system instructions.
    """
    context = (
        prior
        if isinstance(prior, CaseIntelligenceContext)
        else CaseIntelligenceContext.model_validate(prior)
    )
    citizen = (
        citizen_response
        if isinstance(citizen_response, CitizenResponse)
        else CitizenResponse.model_validate(citizen_response)
    )

    institution_id = context.institution_id
    missing_field_agent = missing_field_agent or MissingFieldAgent()
    routing_agent = routing_agent or RoutingAgent(institution=institution_id)
    clarification_agent = clarification_agent or ClarificationAgent()

    clarification_prior = context.clarification or {}
    requested_fields = clarification_prior.get("requested_fields")
    
    extraction = merge_citizen_evidence(context.extraction, citizen, requested_fields)
    extracted_fields = extraction.get("fields") or {}
    document = dict(context.document or {})
    document_type = document.get("document_type") or ""
    process_intent = document.get("process_intent") or ""
    permit_type = (extracted_fields.get("permit_type") or {}).get("value")
    candidate = PERMIT_DEPARTMENT_BY_OPTION.get(str(permit_type)) if permit_type else None

    missing = missing_field_agent.check_missing_fields(
        document_type=document_type,
        process_intent=process_intent,
        extracted_fields=extracted_fields,
        legal_analysis=context.legal_analysis,
        document_subtype=document.get("document_subtype"),
        institution_profile=getattr(routing_agent, "_profile", None),
        institution_id=institution_id,
        candidate_department=candidate,
        raw_text=context.raw_text,
        document=document,
    )

    clarification = clarification_agent.preview(
        missing_fields=missing,
        institution_id=institution_id,
        document_type=document_type,
        process_intent=process_intent,
        candidate_department=candidate,
        raw_text=context.raw_text,
        document=document,
        extracted_fields=extracted_fields,
        routing=context.routing,
    )

    routing = None
    if not clarification.get("blocking"):
        subject = document.get("subject_excerpt") or ""
        request = document.get("request_excerpt") or ""
        if permit_type:
            permit_label = next(
                (
                    option["label"]
                    for option in PERMIT_OPTIONS
                    if option["id"] == permit_type
                ),
                str(permit_type),
            )
            request = f"{request} {field_label('permit_type')}: {permit_label}".strip()
        routing = routing_agent.route(
            document_type,
            process_intent,
            subject,
            request,
            extracted_fields,
            document_subtype=document.get("document_subtype"),
        )
        if candidate:
            unit = next(
                (
                    item
                    for item in getattr(routing_agent, "_units", [])
                    if item.get("unit_id") == candidate
                ),
                {},
            )
            routing.update(
                {
                    "recommended_department_code": candidate,
                    "recommended_unit": unit.get("name") or candidate,
                    "reason": "Vatandaşın doğrulanmış ruhsat türü yanıtına göre sorumlu birim.",
                    "requires_human_review": True,
                    "needs_human_review": True,
                }
            )
        routing["assigned"] = False

    return {
        "extraction": extraction,
        "missing_fields": missing,
        "clarification": clarification,
        "routing": routing,
        "resolved": not bool(clarification.get("blocking")),
        "citizen_evidence_fields": sorted(extraction.get("fields") or {}),
        "reevaluated": ["missing_field", "clarification"]
        + (["routing"] if routing is not None else []),
    }
