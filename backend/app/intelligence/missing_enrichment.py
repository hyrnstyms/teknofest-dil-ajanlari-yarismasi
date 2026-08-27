"""Additive missing-field metadata for case-aware consumers."""

from __future__ import annotations

from typing import Any

from backend.app.intelligence.process_profiles import (
    CITIZEN_SUPPLYABLE_FIELDS,
    OPTIONAL_INTAKE_FIELDS,
    detect_permit_ambiguity,
    field_is_present,
    field_label,
    matching_profiles,
    unresolved_blocking_groups,
)


def enrich_missing_field_result(
    result: dict[str, Any],
    *,
    document_type: str = "",
    process_intent: str = "",
    extracted_fields: dict[str, Any] | None = None,
    institution_id: str | None = None,
    candidate_department: str | None = None,
    raw_text: str = "",
    document: dict[str, Any] | None = None,
) -> dict[str, Any]:
    extracted_fields = extracted_fields or {}
    document = document or {}
    profiles = matching_profiles(
        institution_id=institution_id,
        document_type=document_type,
        process_intent=process_intent,
        candidate_department=candidate_department,
        raw_text=raw_text,
        document=document,
        extracted_fields=extracted_fields,
    )
    blocking_groups = unresolved_blocking_groups(profiles, extracted_fields)
    permit_ambiguity = detect_permit_ambiguity(
        institution_id=institution_id,
        raw_text=raw_text,
        document=document,
        extracted_fields=extracted_fields,
    )

    details: list[dict[str, Any]] = []
    blocking_fields: list[str] = []

    for field in result.get("required_fields") or []:
        field_result = dict(result.get("field_results", {}).get(field) or {})
        status = field_result.get("status") or "missing"
        citizen = field in CITIZEN_SUPPLYABLE_FIELDS
        optional = field in OPTIONAL_INTAKE_FIELDS
        blocking = status == "missing" and citizen and not optional
        if blocking:
            blocking_fields.append(field)
        detail = {
            "field": field,
            "label": field_label(field),
            "reason": field_result.get("reason")
            or ("Zorunlu alan eksik." if status == "missing" else ""),
            "blocking": blocking,
            "source": "requirement_rule",
            "evidence": None,
            "confidence": None,
            "score": field_result.get("score"),
            "status": status,
        }
        details.append(detail)
        field_result.update(
            {
                "label": detail["label"],
                "blocking": blocking,
                "source": "requirement_rule",
            }
        )
        result.setdefault("field_results", {})[field] = field_result

    for group in blocking_groups:
        field = group["fields"][0]
        if any(item["field"] == field and item.get("blocking") for item in details):
            continue
        if field_is_present(extracted_fields, field):
            continue
        blocking_fields.append(field)
        details.append(
            {
                "field": field,
                "label": group.get("label") or field_label(field),
                "reason": group.get("reason") or "Süreç için gerekli bilgi eksik.",
                "blocking": True,
                "source": group.get("profile_id"),
                "evidence": None,
                "confidence": None,
                "score": None,
                "status": "missing",
            }
        )

    optional_missing: list[str] = []
    for profile in profiles:
        for field in profile.get("optional_fields") or []:
            if field_is_present(extracted_fields, field):
                continue
            if field in (result.get("required_fields") or []):
                continue
            optional_missing.append(field)
            details.append(
                {
                    "field": field,
                    "label": field_label(field),
                    "reason": "İsteğe bağlı iletişim bilgisi eksik; süreci durdurmaz.",
                    "blocking": False,
                    "source": profile.get("id"),
                    "evidence": None,
                    "confidence": None,
                    "score": None,
                    "status": "missing_optional",
                }
            )

    if permit_ambiguity:
        field = permit_ambiguity["field"]
        blocking_fields.append(field)
        details.append(
            {
                "field": field,
                "label": field_label(field),
                "reason": "Ruhsat türü birden fazla birime güvenli biçimde eşlenemiyor.",
                "blocking": True,
                "source": "process_ambiguity",
                "evidence": "ruhsat",
                "confidence": None,
                "score": None,
                "status": "ambiguous",
            }
        )

    unique_blocking = list(dict.fromkeys(blocking_fields))
    result["missing_field_details"] = details
    result["blocking_fields"] = unique_blocking
    result["has_blocking_missing"] = bool(unique_blocking)
    result["optional_missing_fields"] = list(dict.fromkeys(optional_missing))
    result["process_profile_ids"] = [p["id"] for p in profiles]
    result["permit_ambiguity"] = permit_ambiguity
    return result
