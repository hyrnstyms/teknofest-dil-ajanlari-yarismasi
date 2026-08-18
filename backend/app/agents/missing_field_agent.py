from typing import Any, Dict

REQUIREMENT_RULES = {
    ("dilekce", "bilgi_talebi"): {
        "required_fields": ["person_name", "address", "signature_present"],
        "source_type": "deterministic_rule",
        "rule_id": "rule_dilekce_bilgi",
        "description": "Bilgi edinme başvurularında isim, adres ve imza zorunludur."
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
        legal_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        
        result = {
            "required_fields": [],
            "present_fields": [],
            "missing_fields": [],
            "uncertain_fields": [],
            "field_results": {},
            "legal_basis": [],
            "warnings": [],
            "needs_human_review": False
        }
        
        rule_key = (document_type, process_intent)
        rule = REQUIREMENT_RULES.get(rule_key)
        
        if rule:
            required = rule["required_fields"]
            
            # Check legal evidence
            legal_evidence_found = False
            if legal_analysis and "evidence" in legal_analysis and legal_analysis["evidence"]:
                # Only use valid evidence, never hallucinate specific laws
                for ev in legal_analysis["evidence"]:
                    result["legal_basis"].append({
                        "evidence": ev,
                        "validated": True,
                        "source_type": "verified_legal_evidence"
                    })
                legal_evidence_found = True
            
            if not legal_evidence_found:
                result["warnings"].append("Zorunlu alanlara ilişkin doğrulanmış mevzuat dayanağı bulunamadı.")
                
        else:
            required = []
            result["warnings"].append(f"'{process_intent}' işlemi için tanımlanmış eksik alan kuralı bulunamadı.")
            
        result["required_fields"] = required
        
        # 2. Check each required field against extracted_fields
        for field in required:
            field_data = extracted_fields.get(field)
            
            if field_data is None:
                # the field key doesn't even exist in extracted output
                if field in ["signature_present", "authority_document_present"]:
                    result["uncertain_fields"].append(field)
                    result["warnings"].append(f"{field} durumu yalnızca metin üzerinden doğrulanamadı.")
                    result["needs_human_review"] = True
                    result["field_results"][field] = {
                        "status": "uncertain",
                        "reason": "Alan extracted_fields içinde yok."
                    }
                else:
                    result["missing_fields"].append(field)
                    result["warnings"].append(f"{field} bilgisi belgede bulunamadı.")
                    result["field_results"][field] = {
                        "status": "missing",
                        "reason": "Alan extracted_fields içinde yok."
                    }
                continue
                
            val = field_data.get("value")
            status = field_data.get("status")
            
            if field in ["signature_present", "authority_document_present"]:
                if status == "unknown" or val is None:
                    result["uncertain_fields"].append(field)
                    result["warnings"].append(f"{field} durumu yalnızca metin üzerinden doğrulanamadı.")
                    result["needs_human_review"] = True
                    result["field_results"][field] = {
                        "status": "uncertain",
                        "value": val,
                        "reason": "Değer None veya unknown."
                    }
                elif val is True:
                    result["present_fields"].append(field)
                    result["field_results"][field] = {
                        "status": "present",
                        "value": True
                    }
                elif val is False:
                    result["missing_fields"].append(field)
                    result["warnings"].append(f"{field} belgede eksik (False).")
                    result["field_results"][field] = {
                        "status": "missing",
                        "value": False,
                        "reason": "Açıkça False olarak belirtilmiş."
                    }
            else:
                if val:
                    result["present_fields"].append(field)
                    result["field_results"][field] = {
                        "status": "present",
                        "value": val
                    }
                else:
                    result["missing_fields"].append(field)
                    result["warnings"].append(f"{field} bilgisi belgede bulunamadı.")
                    result["field_results"][field] = {
                        "status": "missing",
                        "value": val,
                        "reason": "Değer boş veya yok."
                    }
                    
        return result
