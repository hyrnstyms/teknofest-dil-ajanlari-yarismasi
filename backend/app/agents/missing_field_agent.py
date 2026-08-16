from typing import Any, Dict

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
            "legal_basis": [],
            "warnings": [],
            "needs_human_review": False
        }
        
        # 1. Determine Required Fields based on deterministic rules or legal_analysis
        required = []
        
        # Default fallback rules for MVP
        if document_type == "dilekce" and process_intent == "bilgi_talebi":
            required = ["person_name", "address", "signature_present"]
            
            # Use legal evidence if it exists, otherwise add a warning
            legal_evidence_found = False
            if legal_analysis and "evidence" in legal_analysis and legal_analysis["evidence"]:
                # Check if legal_analysis has validated evidence we can use
                # Simplified assumption: if there are sources, we link them
                sources = legal_analysis.get("sources", [])
                for src in sources:
                    if src.get("law_number"):
                        result["legal_basis"].append({
                            "law_number": src.get("law_number", "4982"),
                            "article": src.get("article", "6"),
                            "evidence": src.get("text", "Başvuru sahibinin adı ve adresi zorunludur."),
                            "validated": True
                        })
                        legal_evidence_found = True
                        break
            
            if not legal_evidence_found:
                result["warnings"].append("Zorunlu alanlara ilişkin doğrulanmış mevzuat dayanağı bulunamadı.")
        else:
            # For other intents not covered by MVP fallback rules
            result["warnings"].append(f"'{process_intent}' işlemi için tanımlanmış eksik alan kuralı bulunamadı.")
            
        result["required_fields"] = required
        
        # 2. Check each required field against extracted_fields
        for field in required:
            field_data = extracted_fields.get(field, {})
            
            if not field_data:
                # the field key doesn't even exist in extracted output
                if field in ["signature_present", "authority_document_present"]:
                    result["uncertain_fields"].append(field)
                    result["warnings"].append(f"{field} durumu yalnızca metin üzerinden doğrulanamadı.")
                    result["needs_human_review"] = True
                else:
                    result["missing_fields"].append(field)
                    result["warnings"].append(f"{field} bilgisi belgede bulunamadı.")
                continue
                
            val = field_data.get("value")
            status = field_data.get("status")
            
            if field in ["signature_present", "authority_document_present"]:
                if status == "unknown" or val is None:
                    result["uncertain_fields"].append(field)
                    result["warnings"].append(f"{field} durumu yalnızca metin üzerinden doğrulanamadı.")
                    result["needs_human_review"] = True
                elif val is True:
                    result["present_fields"].append(field)
                else:
                    result["missing_fields"].append(field)
                    result["warnings"].append(f"{field} belgede eksik.")
            else:
                if val:
                    result["present_fields"].append(field)
                else:
                    result["missing_fields"].append(field)
                    result["warnings"].append(f"{field} bilgisi belgede bulunamadı.")
                    
        return result
