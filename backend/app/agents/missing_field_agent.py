import re
from typing import Any, Dict

from backend.app.agents.routing_agent import normalize_turkish_text

# Canonical mapping rules based on document_type.
# Using "*" for process_intent means it applies to all intents for that document_type.
REQUIREMENT_RULES = {
    ("dilekce", "*"): {
        "required_fields": ["signature_present", "subject", "request"],
    },
    ("bilgi_edinme", "*"): {
        "required_fields": ["signature_present", "request"],
    },
    ("sosyal_yardim_basvuru", "*"): {
        "required_fields": ["signature_present", "phone"],
    },
    ("tapu_kadastro_basvuru", "*"): {
        "required_fields": ["signature_present", "request"],
    },
    ("ihale_itirazi", "*"): {
        "required_fields": ["signature_present", "subject", "request", "document_date"],
    },
    ("kurumlar_arasi_yazi", "*"): {
        "required_fields": ["document_number", "document_date", "sender_unit", "recipient", "subject", "signature_present"],
    },
    ("*", "*"): {
        "required_fields": ["signature_present", "subject", "request"], # Generic fallback
    }
}


_PARCEL_REFERENCE_RE = re.compile(
    r"\b\d+\s+ada\s+\d+\s+parsel[a-zçğıöşü]*\b"
)
_APPEAL_RE = re.compile(r"\bitiraz[a-zçğıöşü]*\b")
_PARCEL_MISSING_MARKERS = (
    "ada ve parseli bilmiyorum",
    "ada parseli bilmiyorum",
    "ada ve parsel bilgisi yok",
    "ada parsel bilgisi yok",
    "parsel bilgisi belirtilmemiş",
    "parsel numarası belirtilmemiş",
)
_CONTESTED_ACTION_MISSING_MARKERS = (
    "hangi işleme itiraz ettiğim yok",
    "itiraz ettiğim işlem yok",
    "itiraz konusu belirtilmemiş",
    "itiraz edilen işlem belirtilmemiş",
)


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _contextual_required_fields(
    document_subtype: str | None,
    process_intent: str,
    raw_text: str,
) -> list[str]:
    """Return domain fields required independently of the base profile source."""

    norm_text = normalize_turkish_text(raw_text)
    required: list[str] = []
    parcel_domain = document_subtype == "imar_talebi" or any(
        marker in norm_text
        for marker in ("imar durumu", "yapı ruhsat", "iskan")
    )
    parcel_observable = bool(_PARCEL_REFERENCE_RE.search(norm_text)) or _contains_any(
        norm_text,
        _PARCEL_MISSING_MARKERS,
    )
    if parcel_domain and parcel_observable:
        required.append("parcel")

    appeal_domain = (
        document_subtype == "ihale_itirazi"
        or process_intent == "itiraz"
        or bool(_APPEAL_RE.search(norm_text))
    )
    # Upstream intent/subtype alone is not evidence that an appeal target is
    # absent.  Require an explicit appeal expression in the source text; the
    # evidence check below then separates named targets from explicit gaps.
    if appeal_domain and _APPEAL_RE.search(norm_text):
        required.append("contested_action")

    # Person Name
    name_observable = _contains_any(norm_text, ("ismimi vermek", "adımı gizli", "isim yok", "adımı vermek", "anonim"))
    if name_observable:
        required.append("person_name")

    # Address
    address_observable = _contains_any(norm_text, ("adresimi vermek", "adresim gizli", "adres yok", "ikametgahım yok"))
    if address_observable:
        required.append("address")

    return required


def _contextual_field_evidence(field: str, raw_text: str) -> str | None:
    """Recognize explicit values for contextual fields missing from extraction."""

    norm_text = normalize_turkish_text(raw_text)
    if field == "parcel":
        match = _PARCEL_REFERENCE_RE.search(norm_text)
        return match.group(0) if match else None

    if field == "contested_action":
        if not _APPEAL_RE.search(norm_text):
            return None
        explicitly_missing = _contains_any(
            norm_text,
            _CONTESTED_ACTION_MISSING_MARKERS,
        )
        if explicitly_missing:
            return None
        return "İtiraz konusu belge metninde belirtilmiş."

    return None


class MissingFieldAgent:
    def __init__(self):
        pass

    def check_missing_fields(
        self,
        document_type: str,
        process_intent: str,
        extracted_fields: Dict[str, Any],
        legal_analysis: Dict[str, Any] = None,
        document_subtype: str | None = None,
        institution_profile: Any = None,
        institution_id: str | None = None,
        candidate_department: str | None = None,
        raw_text: str = "",
        document: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        
        result = {
            "required_fields": [],
            "present_fields": [],
            "missing_fields": [],
            "uncertain_fields": [],
            "field_results": {},
            "legal_basis": [],
            "warnings": [],
            "needs_human_review": False,
            "requirement_source": "generic_fallback"
        }
        
        document_type = document_type or ""
        process_intent = process_intent or ""
        
        # 1. Find the rule
        rule = None
        req_source = ""

        # Municipal process profiles are more specific than the historical
        # document-type fallback.  In particular, a generic petition does not
        # automatically need an address unless its concrete process requires
        # one (for example, a field inspection).
        if institution_id:
            from backend.app.intelligence.process_profiles import matching_profiles

            profiles = matching_profiles(
                institution_id=institution_id,
                document_type=document_type,
                process_intent=process_intent,
                candidate_department=candidate_department,
                raw_text=raw_text,
                document=document or {
                    "document_type": document_type,
                    "process_intent": process_intent,
                    "document_subtype": document_subtype,
                },
                extracted_fields=extracted_fields,
            )
            profile = next((item for item in profiles if item.get("required_fields")), None)
            if profile:
                rule = {"required_fields": list(profile["required_fields"])}
                req_source = f"process_profile:{profile['id']}"

        # Profile lookup first
        if not rule and institution_profile and getattr(institution_profile, "evrak_turleri", None):
            # Try to match subtype
            if document_subtype and not rule:
                for et in institution_profile.evrak_turleri:
                    if isinstance(et, dict) and str(et.get("id")) == document_subtype and "required_fields" in et:
                        rule = {"required_fields": et["required_fields"]}
                        req_source = "profile"
                        break
            
            # Try to match type
            if document_type and not rule:
                for et in institution_profile.evrak_turleri:
                    if isinstance(et, dict) and str(et.get("id")) == document_type and "required_fields" in et:
                        rule = {"required_fields": et["required_fields"]}
                        req_source = "profile_fallback"
                        break
                        
        # Legacy fallback
        if not rule and document_subtype:
            rule = REQUIREMENT_RULES.get((document_subtype, process_intent))
            if not rule:
                rule = REQUIREMENT_RULES.get((document_subtype, "*"))
            if rule: req_source = "legacy_fallback"
            
        if not rule:
            rule = REQUIREMENT_RULES.get((document_type, process_intent))
            if rule: req_source = "legacy_fallback"
            
        if not rule:
            rule = REQUIREMENT_RULES.get((document_type, "*"))
            if rule: req_source = "legacy_fallback"
            
        if not rule:
            rule = REQUIREMENT_RULES.get(("*", "*"))
            req_source = "generic_fallback"
            
        required = list(rule.get("required_fields", []))
        
        # Sadece somut deger varsa (extracted) VEYA acik eksiklik ifadesi varsa (yukarida tespit edildi) zorunlu tut
        if "person_name" in extracted_fields and extracted_fields["person_name"]:
            if "person_name" not in required:
                required.append("person_name")
        if "address" in extracted_fields and extracted_fields["address"]:
            if "address" not in required:
                required.append("address")
                
        required.extend(
            field
            for field in _contextual_required_fields(
                document_subtype=document_subtype,
                process_intent=process_intent,
                raw_text=raw_text,
            )
            if field not in required
        )
        result["required_fields"] = required
        result["requirement_source"] = req_source
        
        # We also check legal_analysis evidence if provided
        if legal_analysis and "evidence" in legal_analysis and legal_analysis["evidence"]:
            for ev in legal_analysis["evidence"]:
                result["legal_basis"].append({
                    "evidence": ev,
                    "validated": True,
                    "source_type": "verified_legal_evidence"
                })
        
        # 2. Check each required field against extracted_fields
        for field in required:
            field_data = extracted_fields.get(field)
            contextual_evidence = None
            if field_data is None:
                contextual_evidence = _contextual_field_evidence(field, raw_text)
                if contextual_evidence:
                    field_data = {
                        "value": contextual_evidence,
                        "status": "present",
                    }
            
            # Unbox the value safely
            val = None
            status = None
            
            if field_data is not None:
                if isinstance(field_data, dict):
                    val = field_data.get("value")
                    status = field_data.get("status")
                else:
                    val = field_data
                    
            if field_data is None:
                # The field wasn't even extracted
                if field in ["signature_present", "authority_document_present"]:
                    result["uncertain_fields"].append(field)
                    result["field_results"][field] = {"status": "uncertain", "reason": "No reliable evidence found."}
                    result["needs_human_review"] = True
                else:
                    result["missing_fields"].append(field)
                    result["field_results"][field] = {"status": "missing", "reason": "Not extracted."}
            else:
                if field in ["signature_present", "authority_document_present"]:
                    if status == "unknown" or val is None:
                        result["uncertain_fields"].append(field)
                        result["field_results"][field] = {"status": "uncertain", "reason": "Status is unknown."}
                        result["needs_human_review"] = True
                    elif val is True or val == "present":
                        result["present_fields"].append(field)
                        result["field_results"][field] = {"status": "present", "value": True}
                    elif val is False or val == "missing":
                        result["missing_fields"].append(field)
                        result["field_results"][field] = {"status": "missing", "value": False, "reason": "Explicit absence."}
                    else:
                        result["present_fields"].append(field)
                        result["field_results"][field] = {
                            "status": "present",
                            "value": val,
                            **(
                                {"evidence": contextual_evidence}
                                if contextual_evidence
                                else {}
                            ),
                        }
                else:
                    # Textual fields
                    if status == "unknown":
                        result["uncertain_fields"].append(field)
                        result["field_results"][field] = {"status": "uncertain", "reason": "Extraction returned unknown."}
                        result["needs_human_review"] = True
                    elif status == "missing" or val is None or val == "" or (isinstance(val, (list, dict)) and len(val) == 0):
                        result["missing_fields"].append(field)
                        result["field_results"][field] = {"status": "missing", "reason": "Empty or missing."}
                    else:
                        result["present_fields"].append(field)
                        result["field_results"][field] = {"status": "present", "value": val}

        from backend.app.intelligence.missing_enrichment import enrich_missing_field_result

        return enrich_missing_field_result(
            result,
            document_type=document_type,
            process_intent=process_intent,
            extracted_fields=extracted_fields,
            institution_id=institution_id,
            candidate_department=candidate_department,
            raw_text=raw_text,
            document=document or {"document_type": document_type, "process_intent": process_intent, "document_subtype": document_subtype},
        )
