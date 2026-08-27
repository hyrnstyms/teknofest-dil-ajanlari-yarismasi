"""Declarative process-specific required-field and ambiguity profiles.

Department names/codes come from institution YAML. This module does not
duplicate the institution directory; it only references department codes.
"""

from __future__ import annotations

import re
from typing import Any

from backend.app.agents.routing_agent import normalize_turkish_text

FIELD_LABELS: dict[str, str] = {
    "person_name": "Başvuru sahibi",
    "address": "Açık adres",
    "location": "Konum / açık adres",
    "signature_present": "İmza",
    "subject": "Konu",
    "request": "Talep",
    "phone": "Telefon",
    "email": "E-posta",
    "document_number": "Belge sayısı",
    "document_date": "Belge tarihi",
    "sender_unit": "Gönderen birim",
    "recipient": "Muhatap",
    "national_id": "T.C. kimlik no",
    "permit_type": "Ruhsat türü",
    "authority_document_present": "Yetki belgesi",
}

CITIZEN_SUPPLYABLE_FIELDS = frozenset(
    {
        "person_name",
        "address",
        "location",
        "phone",
        "email",
        "subject",
        "request",
        "permit_type",
        "national_id",
    }
)

OPTIONAL_INTAKE_FIELDS = frozenset({"phone", "email", "national_id"})

YAPI_RUHSATI = "YAPI_RUHSATI"
ISYERI_ACMA_RUHSATI = "ISYERI_ACMA_RUHSATI"

PERMIT_OPTIONS = [
    {"id": YAPI_RUHSATI, "label": "Yapı ruhsatı"},
    {"id": ISYERI_ACMA_RUHSATI, "label": "İşyeri açma ruhsatı"},
]

PERMIT_DEPARTMENT_BY_OPTION = {
    YAPI_RUHSATI: "imar_sehircilik",
    ISYERI_ACMA_RUHSATI: "zabita",
}

_YAPI_MARKERS = ("yapı ruhsat", "yapi ruhsat", "imar", "iskan", "inşaat izni", "insaat izni")
_ISYERI_MARKERS = (
    "işyeri açma",
    "isyeri acma",
    "işyeri ruhsat",
    "çalışma ruhsat",
    "calisma ruhsat",
)

PROCESS_PROFILES: list[dict[str, Any]] = [
    {
        "id": "belediye_yol_onarim",
        "institution_ids": ["belediye"],
        "document_types": ["dilekce", "sikayet"],
        "process_intents": ["sikayet", "basvuru", "bildirim"],
        "department_codes": ["fen_isleri"],
        "text_any": ["yol", "kaldırım", "kaldirim", "asfalt", "çukur", "cukur", "onarım", "onarim"],
        "blocking_groups": [
            {
                "id": "location",
                "fields": ["location", "address"],
                "min_present": 1,
                "label": FIELD_LABELS["location"],
                "reason": "Yönlendirme ve saha işlemi için bildirilen yerin açık adresi gerekir.",
                "question": "Sorun bildirilen yerin açık adresini paylaşınız.",
            }
        ],
        "optional_fields": ["phone", "email"],
    },
    {
        "id": "belediye_ambiguous_ruhsat",
        "institution_ids": ["belediye"],
        "document_types": ["dilekce", "ruhsat_basvurusu", "imar_talebi"],
        "process_intents": ["basvuru", "izin_talebi", "belge_talebi", "bilgi_talebi"],
        "text_any": ["ruhsat"],
        "ambiguity": {
            "field": "permit_type",
            "question": "Başvurunuz hangi ruhsat türüyle ilgilidir?",
            "question_type": "choice",
            "options": PERMIT_OPTIONS,
            "department_by_option": PERMIT_DEPARTMENT_BY_OPTION,
        },
        "optional_fields": ["phone", "email"],
    },
]


def field_label(field: str) -> str:
    return FIELD_LABELS.get(field, field)


def _text_blob(raw_text: str, document: dict[str, Any], extracted_fields: dict[str, Any]) -> str:
    parts = [raw_text or ""]
    for key in ("subject_excerpt", "request_excerpt", "process_intent", "document_type"):
        value = document.get(key) if document else None
        if value:
            parts.append(str(value))
    for key in ("subject", "request", "address", "location"):
        field = extracted_fields.get(key) if extracted_fields else None
        if isinstance(field, dict) and field.get("value"):
            parts.append(str(field["value"]))
        elif isinstance(field, str):
            parts.append(field)
    return normalize_turkish_text(" ".join(parts))


def _contains_any(norm_text: str, tokens: list[str]) -> bool:
    for token in tokens:
        norm = normalize_turkish_text(token)
        if not norm:
            continue
        if re.search(r"\b" + re.escape(norm) + r"[a-zçğıöşü]*\b", norm_text):
            return True
    return False


def _list_match(value: str | None, allowed: list[str] | None) -> bool:
    if not allowed:
        return True
    if not value:
        return False
    return value in allowed


def matching_profiles(
    *,
    institution_id: str | None,
    document_type: str | None,
    process_intent: str | None,
    candidate_department: str | None,
    raw_text: str = "",
    document: dict[str, Any] | None = None,
    extracted_fields: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    document = document or {}
    extracted_fields = extracted_fields or {}
    norm_text = _text_blob(raw_text, document, extracted_fields)
    matched: list[dict[str, Any]] = []
    for profile in PROCESS_PROFILES:
        if not _list_match(institution_id, profile.get("institution_ids")):
            continue
        types = profile.get("document_types")
        if types and document_type not in types and document.get("document_subtype") not in types:
            # Keyword-driven profiles may still match on text.
            if not profile.get("text_any"):
                continue
        if profile.get("process_intents") and process_intent:
            if process_intent not in profile["process_intents"] and not profile.get("text_any"):
                continue
        dept_codes = profile.get("department_codes")
        if dept_codes and candidate_department and candidate_department not in dept_codes:
            continue
        tokens = profile.get("text_any") or []
        if tokens and not _contains_any(norm_text, tokens):
            continue
        matched.append(profile)
    return matched


def detect_permit_ambiguity(
    *,
    institution_id: str | None,
    raw_text: str = "",
    document: dict[str, Any] | None = None,
    extracted_fields: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    extracted_fields = extracted_fields or {}
    permit = _field_value(extracted_fields.get("permit_type"))
    if permit in PERMIT_DEPARTMENT_BY_OPTION:
        return None

    document = document or {}
    if institution_id and institution_id not in ("belediye",):
        return None

    norm_text = _text_blob(raw_text, document, extracted_fields)
    if "ruhsat" not in norm_text:
        return None

    yapi = any(normalize_turkish_text(marker) in norm_text for marker in _YAPI_MARKERS)
    isyeri = any(normalize_turkish_text(marker) in norm_text for marker in _ISYERI_MARKERS)
    if yapi and not isyeri:
        return None
    if isyeri and not yapi:
        return None
    return {
        "field": "permit_type",
        "question": "Başvurunuz hangi ruhsat türüyle ilgilidir?",
        "question_type": "choice",
        "options": PERMIT_OPTIONS,
        "department_by_option": PERMIT_DEPARTMENT_BY_OPTION,
        "blocking": True,
    }


def _field_value(field_data: Any) -> Any:
    if field_data is None:
        return None
    if isinstance(field_data, dict):
        return field_data.get("value")
    return field_data


def field_is_present(extracted_fields: dict[str, Any], field: str) -> bool:
    data = extracted_fields.get(field)
    if data is None:
        return False
    if isinstance(data, dict):
        if data.get("status") in {"missing", "unknown"}:
            return False
        value = data.get("value")
        if value is None or value == "" or value is False:
            return False
        if isinstance(value, (list, dict)) and len(value) == 0:
            return False
        return True
    return bool(data)


def unresolved_blocking_groups(
    profiles: list[dict[str, Any]],
    extracted_fields: dict[str, Any],
) -> list[dict[str, Any]]:
    unresolved: list[dict[str, Any]] = []
    for profile in profiles:
        for group in profile.get("blocking_groups") or []:
            present = sum(
                1 for field in group["fields"] if field_is_present(extracted_fields, field)
            )
            if present < int(group.get("min_present") or 1):
                unresolved.append({**group, "profile_id": profile["id"]})
    return unresolved
