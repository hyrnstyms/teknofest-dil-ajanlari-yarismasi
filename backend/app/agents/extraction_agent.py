import json
import re
from typing import Any

from backend.app.llm.base import LLMClient
from backend.app.llm.factory import create_llm_client


class ExtractionAgent:
    """
    Belge içinden structured ve source-grounded
    bilgi çıkarımı yapan agent.
    """

    def __init__(
        self,
        llm: LLMClient | None = None,
    ):
        self.llm = llm or create_llm_client()

    def extract(
        self,
        text: str,
        document_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        
        text = str(text or "").strip()
        document_context = document_context or {}

        warnings = []
        needs_human_review = False

        if not text:
            return self._empty_result("Metin boş.")

        fields = {}

        # ---------------------------------------------
        # 1. DETERMINISTIC EXTRACTION
        # ---------------------------------------------

        # Email
        email_val, email_ev = self._extract_email(text)
        if email_val:
            fields["email"] = self._format_field(email_val, email_ev, "regex")

        # Phone
        phone_val, phone_ev = self._extract_phone(text)
        if phone_val:
            fields["phone"] = self._format_field(phone_val, phone_ev, "regex")

        # National ID
        tc_val, tc_ev, tc_invalid = self._extract_national_id(text)
        if tc_val:
            fields["national_id"] = self._format_field(tc_val, tc_ev, "deterministic")
        elif tc_invalid:
            warnings.append("invalid_national_id_candidate")
            needs_human_review = True

        # Document Number
        doc_no_val, doc_no_ev = self._extract_document_number(text)
        if doc_no_val:
            fields["document_number"] = self._format_field(doc_no_val, doc_no_ev, "deterministic")

        # Document Date
        doc_date_val, doc_date_ev = self._extract_document_date(text)
        if doc_date_val:
            fields["document_date"] = self._format_field(doc_date_val, doc_date_ev, "deterministic")

        # Attachments
        attachments = self._extract_attachments(text)
        if attachments:
            fields["attachments"] = {
                "value": attachments,
                "evidence": [a["evidence"] for a in attachments],
                "source": "document",
                "method": "deterministic",
                "validated": True,
            }

        # Signature Present
        sig_val, sig_status, sig_ev = self._extract_signature_present(text)
        fields["signature_present"] = {
            "value": sig_val,
            "status": sig_status,
            "evidence": sig_ev,
            "source": "document",
            "method": "deterministic",
            "validated": True,
        }

        # Authority Document
        auth_val, auth_status, auth_ev = self._extract_authority_present(text)
        fields["authority_document_present"] = {
            "value": auth_val,
            "status": auth_status,
            "evidence": auth_ev,
            "source": "document",
            "method": "deterministic",
            "validated": True,
        }

        # ---------------------------------------------
        # 2. DOCUMENT CONTEXT REUSE
        # ---------------------------------------------
        # The user requested that we check the real schema of DocumentAgent.
        # Often it's 'subject_excerpt' and 'request_excerpt' or 'process_intent'
        
        subject_excerpt = document_context.get("subject_excerpt")
        if subject_excerpt:
            fields["subject"] = self._format_field(subject_excerpt, subject_excerpt, "document_agent")

        request_excerpt = document_context.get("request_excerpt")
        if request_excerpt:
            fields["request"] = self._format_field(request_excerpt, request_excerpt, "document_agent")

        # ---------------------------------------------
        # 2.5 DETERMINISTIC SEMANTIC FALLBACK
        # ---------------------------------------------
        
        # Person Name
        person_name_val, person_name_ev = self._extract_person_name(text)
        if person_name_val:
            fields["person_name"] = self._format_field(person_name_val, person_name_ev, "deterministic")

        # Address
        address_val, address_ev = self._extract_address(text)
        if address_val:
            fields["address"] = self._format_field(address_val, address_ev, "deterministic")

        # Recipient
        recipient_val, recipient_ev = self._extract_recipient(text)
        if recipient_val:
            fields["recipient"] = self._format_field(recipient_val, recipient_ev, "deterministic")
            
        # Subject heuristic fallback (if not found in document_context)
        if "subject" not in fields:
            subject_val, subject_ev = self._extract_subject(text)
            if subject_val:
                fields["subject"] = self._format_field(subject_val, subject_ev, "heuristic")
                
        # Request heuristic fallback (if not found in document_context)
        if "request" not in fields:
            request_val, request_ev = self._extract_request(text)
            if request_val:
                fields["request"] = self._format_field(request_val, request_ev, "heuristic")

        # ---------------------------------------------
        # 3. LLM EXTRACTION (SEMANTIC)
        # ---------------------------------------------

        semantic_candidates = ["person_name", "address", "institution", "sender_unit", "recipient", "subject", "request"]
        target_semantic = [k for k in semantic_candidates if k not in fields]
        target_semantic.append("other_entities")

        llm_fields = self._extract_with_llm(text, target_semantic)

        if not llm_fields:
            warnings.append("semantic_extraction_unavailable")
            needs_human_review = True
        else:
            for k in target_semantic:
                item = llm_fields.get(k)
                if isinstance(item, dict) and item.get("value"):
                    ev = str(item.get("evidence", "")).strip()
                    val = str(item.get("value", "")).strip()

                    if ev and self._validate_evidence(ev, text):
                        fields[k] = self._format_field(val, ev, "llm")
                    elif val and self._validate_evidence(val, text):
                        fields[k] = self._format_field(val, val, "llm")
                    else:
                        warnings.append(f"evidence_validation_failed_for_{k}")

            # other_entities
            other = llm_fields.get("other_entities")
            if isinstance(other, list):
                valid_entities = []
                for ent in other:
                    if isinstance(ent, dict):
                        ev = str(ent.get("evidence", "")).strip()
                        if ev and self._validate_evidence(ev, text):
                            valid_entities.append(ent)
                if valid_entities:
                    fields["other_entities"] = {
                        "value": valid_entities,
                        "evidence": [e.get("evidence", "") for e in valid_entities],
                        "source": "document",
                        "method": "llm",
                        "validated": True,
                    }

        return {
            "fields": fields,
            "warnings": warnings,
            "needs_human_review": needs_human_review,
            "llm": {
                "provider": self.llm.get_provider_name() if getattr(self, "llm", None) else "unknown",
                "model": self.llm.get_model_name() if getattr(self, "llm", None) else "unknown",
            },
        }

    # =====================================================
    # DETERMINISTIC EXTRACTORS
    # =====================================================

    def _extract_email(self, text: str) -> tuple[str | None, str | None]:
        match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        if match:
            return match.group(0), match.group(0)
        return None, None

    def _extract_phone(self, text: str) -> tuple[str | None, str | None]:
        match = re.search(r"(?:0|\+90)?\s*\(?5\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{2}[-.\s]?\d{2}", text)
        if match:
            evidence = match.group(0)
            digits = re.sub(r"\D", "", evidence)
            if digits.startswith("90"):
                digits = digits[2:]
            if not digits.startswith("0"):
                digits = "0" + digits
            return digits, evidence
        return None, None

    def _extract_national_id(self, text: str) -> tuple[str | None, str | None, bool]:
        matches = re.findall(r"\b\d{11}\b", text)
        invalid_candidate = False
        
        for m in matches:
            if self._is_valid_tc(m):
                return m, m, False
            invalid_candidate = True
            
        return None, None, invalid_candidate

    def _is_valid_tc(self, tc: str) -> bool:
        if not tc or len(tc) != 11 or not tc.isdigit():
            return False
        if tc[0] == "0":
            return False
        digits = [int(c) for c in tc]
        sum_odd = sum(digits[0:9:2])
        sum_even = sum(digits[1:8:2])
        check1 = (sum_odd * 7 - sum_even) % 10
        if check1 != digits[9]:
            return False
        check2 = sum(digits[0:10]) % 10
        if check2 != digits[10]:
            return False
        return True

    def _extract_document_number(self, text: str) -> tuple[str | None, str | None]:
        # User requested stronger marker checks and preventing common numbers.
        match = re.search(r"(?:Sayı|Belge No|Evrak No|Referans No|Referans|Başvuru No)[\s:]+([^\n]+)", text, re.IGNORECASE)
        if not match:
            return None, None
            
        cand = match.group(1).strip()
        
        # Phone check
        if re.match(r"^(?:0|\+90)?\s*\(?5\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{2}[-.\s]?\d{2}$", cand):
            return None, None
            
        # Date check
        if re.match(r"^\d{1,4}[./-]\d{1,2}[./-]\d{1,4}$", cand):
            return None, None
            
        # 11-digit TC check
        if len(cand) == 11 and cand.isdigit():
            return None, None
            
        # Common law numbers check
        if cand in ["4982", "3071"] and "sayılı" in text.lower():
            return None, None
            
        return cand, match.group(0).strip()

    def _extract_document_date(self, text: str) -> tuple[str | None, str | None]:
        match = re.search(r"(?:Tarih)[\s:]+([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})", text, re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()
            parts = re.split(r"[./-]", date_str)
            if len(parts) == 3:
                day, month, year = parts
                if len(year) == 2:
                    year = "20" + year
                if len(year) == 4 and len(month) <= 2 and len(day) <= 2:
                    normalized = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    return normalized, match.group(0).strip()
            return date_str, match.group(0).strip()
        return None, None

    def _extract_attachments(self, text: str) -> list[dict[str, str]]:
        attachments = []
        matches = re.finditer(r"(?:\bEk|\bEkler|\bEK-\d+)[\s:]+(.+)", text, re.IGNORECASE)
        for m in matches:
            line = m.group(1).strip()
            if "yoktur" not in line.lower():
                attachments.append({
                    "name": line,
                    "evidence": m.group(0).strip()
                })
        return attachments

    def _extract_signature_present(self, text: str) -> tuple[bool | None, str, str | None]:
        lower_text = text.lower()
        indicators = ["imza", "imzalıdır", "e-imza", "elektronik imza", "elektronik olarak imzalanmıştır"]
        for ind in indicators:
            if ind in lower_text:
                match = re.search(re.escape(ind), text, re.IGNORECASE)
                evidence = match.group(0) if match else ind
                return True, "present", evidence
        return None, "unknown", None

    def _extract_authority_present(self, text: str) -> tuple[bool | None, str, str | None]:
        lower_text = text.lower()
        indicators = ["yetki belgesi", "vekaletname", "vekalet", "imza sirküsü", "yetkilendirme belgesi"]
        for ind in indicators:
            if ind in lower_text:
                match = re.search(re.escape(ind), text, re.IGNORECASE)
                evidence = match.group(0) if match else ind
                return True, "present", evidence
        return None, "unknown", None

    def _is_invalid_person(self, val: str) -> bool:
        lower_val = val.lower()
        if "müdür" in lower_val or "sayın" in lower_val or "muhatap" in lower_val:
            return True
        if "[" in val and "]" in val:
            return True
        if "makamına" in lower_val or "birimine" in lower_val or "başkanlığına" in lower_val or "bakanlığına" in lower_val:
            return True
        return False

    def _extract_person_name(self, text: str) -> tuple[str | None, str | None]:
        # Check placeholders
        if "[AD_SOYAD]" in text or "[AD]" in text or "[SOYAD]" in text:
            # Maybe return it directly if expected, or skip. User says:
            # "gibi sentetik değerler varsa sistem bunları gerçek kişi gibi hallucinate etmesin; dataset gerçekten placeholder bekliyorsa mevcut değer korunabilir."
            # We'll skip for now if it's purely placeholder in deterministic search, but if they are exactly the match, we might extract them if they are markers.
            pass

        # Try separate Ad and Soyad
        ad_match = re.search(r"(?:^|\n)\s*Ad\s*:\s*([^\n]+)", text, re.IGNORECASE)
        soyad_match = re.search(r"(?:^|\n)\s*Soyad\s*:\s*([^\n]+)", text, re.IGNORECASE)
        if ad_match and soyad_match:
            ad = ad_match.group(1).strip()
            soyad = soyad_match.group(1).strip()
            if not self._is_invalid_person(ad) and not self._is_invalid_person(soyad):
                val = f"{ad} {soyad}"
                # evidence is both
                ev = f"{ad_match.group(0).strip()} {soyad_match.group(0).strip()}"
                return val, ev

        # Combined markers
        match = re.search(r"(?:Ad Soyad|Adı Soyadı|Başvuru Sahibi|Başvuran|İmza / Ad Soyad)[\s:]+([^\n]+)", text, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            if not self._is_invalid_person(val):
                return val, match.group(0).strip()
                
        # Look for typical signature block at the bottom
        # This is a bit heuristic, but let's look for "İmza\n<Name Surname>" or similar.
        sig_match = re.search(r"(?:^|\n)\s*İmza\s*\n\s*([A-Za-zÇŞĞÜÖİçşğüöı\s]{3,40})(?:\n|$)", text, re.IGNORECASE)
        if sig_match:
            val = sig_match.group(1).strip()
            if not self._is_invalid_person(val):
                return val, sig_match.group(0).strip()
                
        return None, None

    def _extract_address(self, text: str) -> tuple[str | None, str | None]:
        marker_pattern = re.compile(r"(?:Adres|İkamet Adresi|Tebligat Adresi)[\s:]+", re.IGNORECASE)
        match = marker_pattern.search(text)
        if not match:
            return None, None
            
        start_idx = match.end()
        evidence_start_idx = match.start()
        rest_of_text = text[start_idx:]
        
        boundary_markers = [
            r"Telefon:", r"Tel:", r"E-posta:", r"E-mail:", r"Email:", r"T\.C\. Kimlik No:", r"TC:", r"Tarih:", 
            r"Sayı:", r"Konu:", r"Ek:", r"Ekler:", r"EK-\d+", r"Başvuru Sahibi:", r"İmza:", r"Ad Soyad:", r"Adı Soyadı:"
        ]
        
        boundary_regex = r"(?:\n\s*\n|\n\s*(?:" + "|".join(boundary_markers) + r"))"
        end_match = re.search(boundary_regex, rest_of_text, re.IGNORECASE)
        if end_match:
            end_idx = end_match.start()
        else:
            end_idx = len(rest_of_text)
            
        address_val = rest_of_text[:end_idx].strip()
        evidence_val = text[evidence_start_idx : start_idx + end_idx].strip()
        
        if address_val:
            return address_val, evidence_val
        return None, None

    def _extract_recipient(self, text: str) -> tuple[str | None, str | None]:
        match = re.search(r"^([^\n]+(?:Birimine|Müdürlüğüne|Başkanlığına|Bakanlığına|Kurumuna|Makamına)[^\n]*)$", text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip(), match.group(0).strip()
        return None, None
        
    def _extract_subject(self, text: str) -> tuple[str | None, str | None]:
        match = re.search(r"(?:^|\n)\s*(?:Konu|KONU)[\s:]+([^\n]+)", text)
        if match:
            val = match.group(1).strip()
            lower_val = val.lower()
            # Reject if it's a recipient misidentified as subject
            if "makamına" in lower_val or "müdürlüğüne" in lower_val or "birimine" in lower_val:
                return None, None
            return val, match.group(0).strip()
        return None, None
        
    def _extract_request(self, text: str) -> tuple[str | None, str | None]:
        markers = [
            r"arz ederim", r"talep ediyorum", r"talep ederim", r"gereğini arz ederim",
            r"bilgilerin tarafıma verilmesini", r"başvuruyorum", r"itiraz ediyorum", 
            r"şikayet ediyorum", r"izin verilmesini"
        ]
        # Build regex to find sentence containing any of the markers
        for marker in markers:
            # Find the marker in text
            pattern = re.compile(r"([^\.\n]*?" + re.escape(marker) + r"[^\.\n]*\.?)", re.IGNORECASE)
            match = pattern.search(text)
            if match:
                val = match.group(1).strip()
                return val, val
                
        return None, None

    # =====================================================
    # LLM EXTRACTION
    # =====================================================

    def _extract_with_llm(self, text: str, target_fields: list[str]) -> dict[str, Any]:
        if not target_fields:
            return {}
            
        field_descriptions = {
            "person_name": "- person_name: Başvuru sahibi / Gönderen kişi",
            "address": "- address: Adres",
            "institution": "- institution: Kamu kurumu / T.C. X Kurumu",
            "sender_unit": "- sender_unit: Gönderen birim",
            "recipient": "- recipient: Hitap edilen muhatap / Alıcı birim (Örn: Bilgi Edinme Birimine)",
            "subject": "- subject: Konu",
            "request": "- request: Talep (Örn: \"... verilmesini arz ederim\")",
            "other_entities": "- other_entities: (Tarih, mekan vb. ek varlıklar liste halinde. type: organization|date|location)"
        }
        
        fields_prompt = "\n".join([field_descriptions[k] for k in target_fields if k in field_descriptions])

        system_prompt = f"""
Sen kamu evrakı bilgi çıkarım sistemisin.
Görev: Metindeki ilgili alanları JSON olarak çıkarmak.

KURALLAR:
1. SADECE metinde yer alan bilgileri çıkar.
2. value normalize edilebilir, ancak evidence metindeki EXACT (birebir aynı) ifade olmak zorundadır.
3. Bulamadığın alanlar için json key üretme veya boş string/null bırak.
4. SADECE JSON formatında çıktı ver.

ÇIKARILACAK ALANLAR (SADECE BUNLARI ÇIKAR):
{fields_prompt}

FORMAT ÖRNEĞİ (SADECE İSTENEN ALANLAR İÇİN):
{{
    "hedef_alan_1": {{"value": "Örnek Değer", "evidence": "Örnek Değer"}}
}}
"""
        user_prompt = f"EVRAK METNİ:\n{text}\n\nLütfen yukarıdaki evrak için bilgileri çıkar."

        try:
            raw = self.llm.chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.0,
                max_tokens=500,
                json_mode=True,
            )
        except Exception:
            # LLM failure is caught here, we return empty so deterministic fallback is retained.
            return {}

        return self._parse_json_object(raw)

    def _parse_json_object(self, raw: str) -> dict[str, Any]:
        if not raw:
            return {}
        cleaned = str(raw).strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            res = json.loads(cleaned)
            if isinstance(res, dict):
                return res
        except json.JSONDecodeError:
            pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                res = json.loads(cleaned[start:end + 1])
                if isinstance(res, dict):
                    return res
            except json.JSONDecodeError:
                pass

        return {}

    # =====================================================
    # UTILS
    # =====================================================

    def _format_field(self, value: Any, evidence: str, method: str) -> dict[str, Any]:
        return {
            "value": value,
            "evidence": evidence,
            "source": "document",
            "method": method,
            "validated": True,
        }

    def _validate_evidence(self, evidence: str, source_text: str) -> bool:
        normalized_ev = self._normalize_text(evidence)
        normalized_source = self._normalize_text(source_text)
        if not normalized_ev:
            return False
        return normalized_ev in normalized_source

    def _normalize_text(self, text: str) -> str:
        return " ".join(str(text).lower().split())

    def _empty_result(self, message: str) -> dict[str, Any]:
        return {
            "fields": {},
            "warnings": [message],
            "needs_human_review": True,
            "llm": {
                "provider": getattr(self, "llm", None).get_provider_name() if getattr(self, "llm", None) else "unknown",
                "model": getattr(self, "llm", None).get_model_name() if getattr(self, "llm", None) else "unknown",
            },
        }
