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
            "structured_summary": {
                "applicant": None,
                "subject": None,
                "request": None,
                "important_dates": [],
                "important_entities": []
            },
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
        result["structured_summary"]["applicant"] = applicant
        result["structured_summary"]["subject"] = subject
        result["structured_summary"]["request"] = request_text
        
        if doc_date:
            result["structured_summary"]["important_dates"].append(doc_date)
        if institution:
            result["structured_summary"]["important_entities"].append(institution)
            
        # Try deterministic short summary
        if applicant and request_text:
            # We can create a deterministic summary
            result["short_summary"] = f"{applicant} tarafından sunulan {request_text.lower()} hakkındaki belge."
        
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
                parsed = json.loads(response)
                if isinstance(parsed, dict) and "short_summary" in parsed:
                    result["short_summary"] = parsed["short_summary"]
            except Exception as e:
                result["warnings"].append("LLM özet üretimi sırasında hata oluştu veya çevrimdışı.")
                
        # If still no short summary could be generated
        if not result["short_summary"]:
            result["warnings"].append("Belgeyi güvenilir şekilde özetlemek için yeterli bilgi bulunamadı.")
            
        return result
