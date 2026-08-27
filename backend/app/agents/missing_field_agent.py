from typing import Any, Dict

# Canonical mapping rules based on document_type.
# Using "*" for process_intent means it applies to all intents for that document_type.
REQUIREMENT_RULES = {
    ("dilekce", "*"): {
        "required_fields": ["person_name", "address", "signature_present", "subject", "request"],
    },
    ("bilgi_edinme", "*"): {
        "required_fields": ["person_name", "address", "signature_present", "request"],
    },
    ("sosyal_yardim_basvuru", "*"): {
        "required_fields": ["person_name", "address", "signature_present", "phone"],
    },
    ("tapu_kadastro_basvuru", "*"): {
        "required_fields": ["person_name", "signature_present", "request"],
    },
    ("ihale_itirazi", "*"): {
        "required_fields": ["person_name", "address", "signature_present", "subject", "request", "document_date"],
    },
    ("kurumlar_arasi_yazi", "*"): {
        "required_fields": ["document_number", "document_date", "sender_unit", "recipient", "subject", "signature_present"],
    },
    ("*", "*"): {
        "required_fields": ["person_name", "signature_present", "subject", "request"], # Generic fallback
    }
}

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
        
        # Profile lookup first
        if institution_profile and getattr(institution_profile, "evrak_turleri", None):
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
            
        required = rule.get("required_fields", [])
        result["required_fields"] = required
        result["requirement_source"] = req_source
            
        required = rule.get("required_fields", [])
        result["required_fields"] = required
        
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
                        result["field_results"][field] = {"status": "present", "value": val}
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
