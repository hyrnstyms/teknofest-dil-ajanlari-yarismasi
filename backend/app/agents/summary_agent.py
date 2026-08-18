import json
from typing import Dict, Any, Optional
from backend.app.llm.base import LLMClient

class SummaryAgent:
    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm

    def summarize(
        self,
        raw_text: str,
        document_analysis: Dict[str, Any],
        extracted_fields: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        result = {
            "short_summary": None,
            "summary_mode": "unavailable",
            "structured_summary": {
                "applicant": None,
                "subject": None,
                "request": None,
                "important_dates": [],
                "important_entities": []
            },
            "source_map": {},
            "warnings": [],
            "needs_human_review": False
        }
        
        # Safe extraction of already verified fields
        applicant = extracted_fields.get("person_name", {}).get("value")
        subject = extracted_fields.get("subject", {}).get("value")
        request_text = extracted_fields.get("request", {}).get("value")
        doc_date = extracted_fields.get("document_date", {}).get("value")
        institution = extracted_fields.get("institution", {}).get("value")
        
        # Populate structured summary deterministically
        if applicant:
            result["structured_summary"]["applicant"] = applicant
            result["source_map"]["applicant"] = "extraction.person_name"
            
        if subject:
            result["structured_summary"]["subject"] = subject
            result["source_map"]["subject"] = "extraction.subject"
            
        if request_text:
            result["structured_summary"]["request"] = request_text
            result["source_map"]["request"] = "extraction.request"
        
        if doc_date:
            result["structured_summary"]["important_dates"].append(doc_date)
            result["source_map"]["important_dates"] = "extraction.document_date"
            
        if institution:
            result["structured_summary"]["important_entities"].append(institution)
            result["source_map"]["important_entities"] = "extraction.institution"
            
        # Try deterministic short summary
        if applicant and subject:
            det_summary = f"{applicant} tarafından {subject} konusunda başvuru yapılmıştır."
            if request_text:
                if not request_text.strip().endswith("."):
                    det_summary += f" Başvuruda {request_text.lower()} talep edilmektedir."
                else:
                    det_summary += f" {request_text}"
                    
            result["short_summary"] = det_summary
            result["summary_mode"] = "deterministic"
            result["source_map"]["short_summary"] = "deterministic_template"
        
        # If deterministic fails and we have an LLM, try semantic fallback
        if not result["short_summary"] and raw_text and self.llm:
            prompt = f"""Lütfen aşağıdaki metni çok kısa bir şekilde özetle (1-2 cümle).
Tüm doğal dil cevabını Türkçe üret.
Kaynakta veya doğrulanmış alanlarda bulunmayan bilgi (yeni kişi, kurum, karar, vb.) ekleme. Sadece JSON formatında döndür:
{{"short_summary": "özet metni"}}

METİN:
{raw_text[:2000]}
"""
            try:
                response = self.llm.chat([{"role": "user", "content": prompt}])
                
                # Robust JSON parse
                start_idx = response.find("{")
                end_idx = response.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    json_str = response[start_idx:end_idx+1]
                    parsed = json.loads(json_str)
                    
                    if isinstance(parsed, dict) and "short_summary" in parsed:
                        result["short_summary"] = parsed["short_summary"]
                        result["summary_mode"] = "llm_grounded"
                        result["source_map"]["short_summary"] = "llm_generation"
                        
                        # Grounding validation (basic check)
                        # Check if any new dates or institutions were hallucinated
                        # In MVP we just flag for human review if it's LLM generated
                        result["needs_human_review"] = True
                        result["warnings"].append("Özet LLM tarafından üretildi, manuel kontrol önerilir.")
                else:
                    raise ValueError("JSON bulunamadı")
                    
            except Exception as e:
                result["warnings"].append("LLM özet üretimi sırasında hata oluştu veya JSON formatı geçersiz.")
                
        # If still no short summary could be generated
        if not result["short_summary"]:
            result["warnings"].append("Belgeyi güvenilir şekilde özetlemek için yeterli bilgi bulunamadı.")
            
        return result
