import json
import re
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
            "needs_human_review": False,
            "llm": self._llm_metadata(),
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
            result["source_map"]["applicant"] = "extraction.fields.person_name"
            
        if subject:
            result["structured_summary"]["subject"] = subject
            result["source_map"]["subject"] = "extraction.fields.subject"
            
        if request_text:
            result["structured_summary"]["request"] = request_text
            result["source_map"]["request"] = "extraction.fields.request"
        
        if doc_date:
            result["structured_summary"]["important_dates"].append(doc_date)
            result["source_map"]["important_dates"] = "extraction.fields.document_date"
            
        if institution:
            result["structured_summary"]["important_entities"].append(institution)
            result["source_map"]["important_entities"] = "extraction.fields.institution"
            
        # Try deterministic short summary
        if applicant and subject:
            det_summary = f"{applicant} tarafından {subject} konusunda başvuru yapılmıştır."
            if request_text:
                req_clean = request_text.strip()
                if self._is_complete_request_sentence(req_clean):
                    if not req_clean.endswith("."):
                        req_clean += "."
                    # Capitalize first letter properly if not already capitalized
                    if len(req_clean) > 0:
                        req_clean = req_clean[0].upper() + req_clean[1:]
                    det_summary += f" {req_clean}"
                else:
                    if req_clean.endswith("."):
                        req_clean = req_clean[:-1]
                    det_summary += f" Başvuruda {req_clean.lower()} talep edilmektedir."
                    
            result["short_summary"] = det_summary
            result["summary_mode"] = "deterministic"
            result["source_map"]["short_summary"] = "deterministic_template"
            result["llm"]["status"] = "not_required"
        
        # If deterministic fails and we have an LLM, try semantic fallback
        if not result["short_summary"] and raw_text and self.llm:
            system_prompt = (
                "Sen verilen kamu evrakını, kullanıcı talimatlarına göre "
                "Türkçe ve kaynakla sınırlı biçimde özetleyen bir bileşensin."
            )
            user_prompt = f"""Lütfen aşağıdaki metni çok kısa bir şekilde özetle (1-2 cümle).
Tüm doğal dil cevabını Türkçe üret.
Kaynakta veya doğrulanmış alanlarda bulunmayan bilgi (yeni kişi, kurum, karar, vb.) ekleme. Sadece JSON formatında döndür:
{{"short_summary": "özet metni"}}

METİN:
{raw_text[:2000]}
"""
            result["llm"]["attempted"] = True
            try:
                response = self.llm.chat(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.0,
                    max_tokens=180,
                    json_mode=True,
                )

                if not str(response or "").strip():
                    result["llm"]["status"] = "empty_response"
                    result["llm"]["error"] = "LLM boş yanıt döndürdü."
                    result["warnings"].append(
                        "LLM özet üretimi boş yanıt döndürdü."
                    )
                else:
                    parsed = self._parse_json_object(response)
                    if parsed is None:
                        result["llm"]["status"] = "invalid_json"
                        result["llm"]["error"] = "Geçerli JSON nesnesi bulunamadı."
                        result["warnings"].append(
                            "LLM özeti geçerli JSON formatında döndürmedi."
                        )
                    else:
                        summary_value = parsed.get("short_summary")
                        if isinstance(summary_value, str) and summary_value.strip():
                            result["short_summary"] = summary_value.strip()
                            result["summary_mode"] = "llm_grounded"
                            result["source_map"]["short_summary"] = "llm_generation"
                            result["needs_human_review"] = True
                            result["llm"]["status"] = "success"
                            result["warnings"].append(
                                "Özet LLM tarafından üretildi, manuel kontrol önerilir."
                            )
                        else:
                            result["llm"]["status"] = "invalid_schema"
                            result["llm"]["error"] = (
                                "Yanıtta dolu short_summary alanı bulunamadı."
                            )
                            result["warnings"].append(
                                "LLM yanıtında dolu short_summary alanı bulunamadı."
                            )

            except Exception as exc:
                error_text = f"{type(exc).__name__}: {exc}"[:300]
                result["llm"]["status"] = "error"
                result["llm"]["error"] = error_text
                result["warnings"].append(
                    f"LLM özet üretimi başarısız oldu: {error_text}"
                )
                
        # If still no short summary could be generated
        if not result["short_summary"]:
            result["warnings"].append("Belgeyi güvenilir şekilde özetlemek için yeterli bilgi bulunamadı.")
            result["needs_human_review"] = True

            if not self.llm and raw_text:
                result["warnings"].append(
                    "LLM istemcisi bulunmadığı için semantic özet fallback'i çalıştırılamadı."
                )
            
        return result

    def _llm_metadata(self) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {
            "provider": None,
            "model": None,
            "attempted": False,
            "status": "unavailable" if self.llm is None else "available",
            "error": None,
        }

        if self.llm is None:
            return metadata

        try:
            metadata["provider"] = self.llm.get_provider_name()
            metadata["model"] = self.llm.get_model_name()
        except Exception as exc:
            metadata["status"] = "metadata_error"
            metadata["error"] = f"{type(exc).__name__}: {exc}"[:300]

        return metadata

    @staticmethod
    def _is_complete_request_sentence(text: str) -> bool:
        text = text.lower().strip()
        suffixes = ["istiyorum", "arz ederim", "rica ederim", "talep ediyorum", "talep eder", "arz eder", "rica eder", "talep edilmektedir", "bildiririm"]
        return any(text.endswith(s) or text.endswith(s + ".") for s in suffixes)

    @staticmethod
    def _parse_json_object(response: str) -> Dict[str, Any] | None:
        cleaned = str(response or "").strip()
        if not cleaned:
            return None

        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx == -1 or end_idx <= start_idx:
            return None

        try:
            parsed = json.loads(cleaned[start_idx:end_idx + 1])
        except json.JSONDecodeError:
            return None

        return parsed if isinstance(parsed, dict) else None
