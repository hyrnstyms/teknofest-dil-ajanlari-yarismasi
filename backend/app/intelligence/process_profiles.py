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
        "id": "yol_bakim_sikayeti",
        "institution_ids": ["belediye"],
        "document_types": ["dilekce", "sikayet"],
        "process_intents": ["sikayet", "basvuru", "bildirim", "talep"],
        "department_codes": ["fen_isleri"],
        "text_any": ["yol", "kaldırım", "kaldirim", "asfalt", "çukur", "cukur", "onarım", "onarim"],
        "required_fields": ["person_name", "subject", "request"],
        "optional_fields": ["phone", "email"],
        "task_type": "YOL_BAKIM_INCELEME",
        "team_code": "saha_bakim_ekibi",
        "recommended_role": "SAHA_EKIBI",
        "requires_field_visit": True,
        "allowed_clarification_targets": ["VATANDAS"],
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
    },
    {
        "id": "cop_temizlik_sikayeti",
        "institution_ids": ["belediye"],
        "document_types": ["dilekce", "sikayet"],
        "process_intents": ["sikayet", "bildirim", "talep"],
        "department_codes": ["temizlik_isleri"],
        "text_any": ["çöp", "cop", "temizlik", "atık", "atik", "moloz", "koku"],
        "required_fields": ["person_name", "subject", "request"],
        "optional_fields": ["phone", "email"],
        "task_type": "TEMIZLIK_DENETIMI",
        "team_code": "temizlik_saha_ekibi",
        "recommended_role": "SAHA_EKIBI",
        "requires_field_visit": True,
        "allowed_clarification_targets": ["VATANDAS"],
        "blocking_groups": [{
            "id": "location", "fields": ["location", "address"], "min_present": 1,
            "label": FIELD_LABELS["location"],
            "reason": "Saha ekibinin işlem yapabilmesi için konum gerekir.",
            "question": "Çöp veya temizlik sorununun olduğu açık adresi paylaşınız.",
        }],
    },
    {
        "id": "gurultu_sikayeti",
        "institution_ids": ["belediye"],
        "document_types": ["dilekce", "sikayet"],
        "process_intents": ["sikayet", "bildirim"],
        "department_codes": ["zabita"],
        "text_any": ["gürültü", "gurultu", "yüksek ses", "yuksek ses"],
        "required_fields": ["person_name", "subject", "request"],
        "optional_fields": ["phone", "email"],
        "task_type": "ZABITA_DENETIMI",
        "team_code": "denetim_ekibi",
        "recommended_role": "ZABITA_MEMURU",
        "requires_field_visit": True,
        "allowed_clarification_targets": ["VATANDAS"],
        "blocking_groups": [{
            "id": "location", "fields": ["location", "address"], "min_present": 1,
            "label": FIELD_LABELS["location"], "reason": "Denetim yeri belirtilmelidir.",
            "question": "Gürültünün kaynaklandığı açık adresi paylaşınız.",
        }],
    },
    {
        "id": "isyeri_ruhsat_basvurusu",
        "institution_ids": ["belediye"],
        "document_types": ["dilekce", "ruhsat_basvurusu", "imar_talebi"],
        "process_intents": ["basvuru", "izin_talebi", "belge_talebi", "bilgi_talebi"],
        "department_codes": ["zabita"],
        "text_any": ["işyeri ruhsat", "isyeri ruhsat", "işyeri açma", "isyeri acma", "çalışma ruhsat", "calisma ruhsat"],
        "required_fields": ["person_name", "subject", "request", "address"],
        "optional_fields": ["phone", "email"],
        "task_type": "ISYERI_RUHSAT_INCELEME",
        "team_code": "ruhsat_inceleme",
        "recommended_role": "RUHSAT_INCELEME_UZMANI",
        "requires_field_visit": False,
        "allowed_clarification_targets": ["VATANDAS"],
    },
    {
        "id": "imar_durumu_talebi",
        "institution_ids": ["belediye"],
        "document_types": ["dilekce", "imar_talebi"],
        "process_intents": ["basvuru", "bilgi_talebi", "belge_talebi"],
        "department_codes": ["imar_sehircilik"],
        "text_any": ["imar durumu", "parsel", "ada", "yapı ruhsat", "yapi ruhsat", "iskan"],
        "required_fields": ["person_name", "subject", "request"],
        "optional_fields": ["phone", "email"],
        "task_type": "IMAR_DURUMU_INCELEME",
        "team_code": "imar_inceleme",
        "recommended_role": "IMAR_UZMANI",
        "requires_field_visit": False,
        "allowed_clarification_targets": ["VATANDAS"],
    },
    {
        "id": "kacak_yapi_sikayeti",
        "institution_ids": ["belediye"],
        "document_types": ["dilekce", "sikayet"],
        "process_intents": ["sikayet", "bildirim"],
        "department_codes": ["imar_sehircilik"],
        "text_any": ["kaçak yapı", "kacak yapi", "ruhsatsız yapı", "ruhsatsiz yapi"],
        "required_fields": ["person_name", "subject", "request"],
        "optional_fields": ["phone", "email"],
        "task_type": "KACAK_YAPI_DENETIMI",
        "team_code": "yapi_kontrol",
        "recommended_role": "YAPI_KONTROL_UZMANI",
        "requires_field_visit": True,
        "allowed_clarification_targets": ["VATANDAS"],
        "blocking_groups": [{
            "id": "location", "fields": ["location", "address"], "min_present": 1,
            "label": FIELD_LABELS["location"], "reason": "Yapı denetimi için konum gerekir.",
            "question": "İddia edilen yapının açık adresini paylaşınız.",
        }],
    },
    {
        "id": "sosyal_yardim_basvurusu",
        "institution_ids": ["belediye"],
        "document_types": ["dilekce", "sosyal_yardim_basvuru"],
        "process_intents": ["basvuru", "talep"],
        "department_codes": ["yazi_isleri"],
        "text_any": ["sosyal yardım", "sosyal yardim", "yardım talebi", "yardim talebi"],
        "required_fields": ["person_name", "subject", "request"],
        "optional_fields": ["phone", "email", "address"],
        "task_type": "SOSYAL_YARDIM_ON_INCELEME",
        "team_code": "sosyal_destek",
        "recommended_role": "SOSYAL_INCELEME_UZMANI",
        "requires_field_visit": False,
        "allowed_clarification_targets": ["VATANDAS"],
    },
    {
        "id": "bilgi_edinme_basvurusu",
        "institution_ids": ["belediye"],
        "document_types": ["dilekce", "bilgi_edinme"],
        "process_intents": ["bilgi_talebi", "belge_talebi"],
        "department_codes": ["yazi_isleri"],
        "text_any": ["bilgi edinme", "bilgi talebi", "4982"],
        "required_fields": ["person_name", "subject", "request"],
        "optional_fields": ["phone", "email", "address"],
        "task_type": "BILGI_EDINME_CEVAP_HAZIRLAMA",
        "team_code": "bilgi_edinme",
        "recommended_role": "YAZI_ISLERI_UZMANI",
        "requires_field_visit": False,
        "allowed_clarification_targets": ["VATANDAS"],
    },
    {
        "id": "su_faturasi_itiraz",
        "institution_ids": ["belediye"],
        "document_types": ["dilekce", "sikayet"],
        "process_intents": ["itiraz", "basvuru"],
        "department_codes": ["su_kanal"],
        "text_any": ["su faturası", "su faturasi", "su borcu", "sayaç itiraz", "sayac itiraz"],
        "required_fields": ["person_name", "subject", "request"],
        "optional_fields": ["phone", "email", "address"],
        "task_type": "SU_FATURASI_INCELEME",
        "team_code": "abonelik_tahakkuk",
        "recommended_role": "ABONELIK_UZMANI",
        "requires_field_visit": False,
        "allowed_clarification_targets": ["VATANDAS"],
    },
    {
        "id": "kurumlar_arasi_yazi",
        "institution_ids": ["belediye"],
        "document_types": ["kurumlar_arasi_yazi"],
        "process_intents": ["iletim", "cevap", "bilgi_talebi", "bildirim", "diger"],
        "department_codes": ["yazi_isleri"],
        "required_fields": ["document_number", "document_date", "sender_unit", "recipient", "subject"],
        "optional_fields": [],
        "task_type": "KURUMSAL_YAZI_INCELEME",
        "team_code": "gelen_evrak_ve_yazisma",
        "recommended_role": "YAZI_ISLERI_UZMANI",
        "requires_field_visit": False,
        "allowed_clarification_targets": ["DIS_KURUM", "KURUM_ICI"],
        "blocking_groups": [{
            "id": "sender_unit", "fields": ["sender_unit"], "min_present": 1,
            "label": FIELD_LABELS["sender_unit"], "reason": "Eksik belgenin istenebilmesi için gönderen birim gerekir.",
            "question": "Eksik ek/belgeyi tamamlayınız.",
        }],
    },
]

# Uniform profile metadata consumed by the municipal workflow.  The values are
# derived from the declarative fields above so every profile exposes the same
# contract without duplicating its department/task identifiers.
for _profile in PROCESS_PROFILES:
    _profile.setdefault("blocking_fields", [
        field
        for group in _profile.get("blocking_groups") or []
        for field in group.get("fields") or []
    ])
    _profile.setdefault(
        "default_department", (_profile.get("department_codes") or [None])[0]
    )
    _profile.setdefault("possible_task_types", [_profile.get("task_type")])


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
    # When the classifier supplies a concrete document type, its exact
    # process profile must win over a broader keyword match.  For example an
    # incoming ``kurumlar_arasi_yazi`` may contain "bilgi talebi", but that
    # must not turn it into a citizen information-request process requiring a
    # person name or address.
    exact = [
        profile
        for profile in matched
        if document_type in (profile.get("document_types") or [])
        or document.get("document_subtype") in (profile.get("document_types") or [])
    ]
    return exact or matched


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
