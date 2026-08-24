import json
import re
from typing import Any

from backend.app.llm.base import LLMClient
from backend.app.llm.factory import create_llm_client
from backend.app.agents.priority_agent import PriorityAgent


ALLOWED_DOCUMENT_TYPES = {
    "dilekce",
    "resmi_yazi",
    "form",
    "tutanak",
    "rapor",
    "karar",
    "tebligat",
    "eposta",
    "diger",
}


ALLOWED_PROCESS_INTENTS = {
    "bilgi_talebi",
    "belge_talebi",
    "basvuru",
    "sikayet",
    "itiraz",
    "izin_talebi",
    "bildirim",
    "cevap",
    "iletim",
    "diger",
}


class DocumentAgent:

    def __init__(
        self,
        llm: LLMClient | None = None,
    ):
        self.llm = (
            llm
            or create_llm_client()
        )
        self.priority_agent = PriorityAgent()

    def analyze(
        self,
        text: str,
    ) -> dict[str, Any]:

        text = str(
            text or ""
        ).strip()

        if not text:
            return self._empty_result(
                "Evrak metni boş."
            )

        priority = self.priority_agent.assess(text)

        # ---------------------------------------------
        # 1. LLM classification
        # ---------------------------------------------

        raw_result = (
            self._classify_with_llm(
                text
            )
        )

        # Küçük modelin kullandığı farklı
        # ifadeleri bizim enum'lara dönüştür.
        generated = (
            self._normalize_llm_result(
                raw_result
            )
        )

        classification_mode = "llm"

        # ---------------------------------------------
        # 2. LLM classification geçersizse fallback
        # ---------------------------------------------

        if not self._is_valid_classification(
            generated
        ):
            generated = (
                self._heuristic_classification(
                    text
                )
            )

            classification_mode = (
                "heuristic_fallback"
            )

        document_type = (
            generated.get(
                "document_type",
                "diger",
            )
        )

        process_intent = (
            generated.get(
                "process_intent",
                "diger",
            )
        )

        # ---------------------------------------------
        # 3. LLM evidence doğrulaması
        # ---------------------------------------------

        validated_evidence = (
            self._validate_evidence(
                evidence=generated.get(
                    "evidence",
                    [],
                ),
                source_text=text,
            )
        )

        evidence_mode = "llm"

        # ---------------------------------------------
        # 4. Model evidence çıkaramadıysa
        #    kaynak metinden deterministik çıkar.
        # ---------------------------------------------

        if not validated_evidence:
            validated_evidence = (
                self._extract_evidence_fallback(
                    text=text,
                    document_type=document_type,
                    process_intent=process_intent,
                )
            )

            evidence_mode = (
                "deterministic_fallback"
            )

        subject_excerpt = (
            self._get_evidence_by_field(
                validated_evidence,
                "subject",
            )
        )

        request_excerpt = (
            self._get_evidence_by_field(
                validated_evidence,
                "request",
            )
        )

        # ---------------------------------------------
        # 5. Human review
        # ---------------------------------------------

        needs_human_review = (
            document_type == "diger"
            or process_intent == "diger"
        )

        return {
            "document_type": (
                document_type
            ),

            "process_intent": (
                process_intent
            ),

            "subject_excerpt": (
                subject_excerpt
            ),

            "request_excerpt": (
                request_excerpt
            ),

            "evidence": (
                validated_evidence
            ),

            "classification_mode": (
                classification_mode
            ),

            "evidence_mode": (
                evidence_mode
            ),

            "needs_human_review": (
                needs_human_review
            ),

            **priority,

            # Debug / geliştirme sırasında yararlı.
            "raw_llm_result": (
                raw_result
            ),

            "llm": (
                self._llm_info()
            ),
        }

    # =====================================================
    # LLM
    # =====================================================

    def _classify_with_llm(
        self,
        text: str,
    ) -> dict[str, Any]:

        system_prompt = """
Sen kamu kurumlarına gelen evrakları sınıflandıran
bir evrak analiz sistemisin.

SADECE aşağıdaki document_type değerlerini kullan:

dilekce
resmi_yazi
form
tutanak
rapor
karar
tebligat
eposta
diger

SADECE aşağıdaki process_intent değerlerini kullan:

bilgi_talebi
belge_talebi
basvuru
sikayet
itiraz
izin_talebi
bildirim
cevap
iletim
diger

KESİN KURALLAR:

1. Sadece verilen evrak metnini kullan.

2. Evrakta olmayan bilgi veya amaç uydurma.

3. Emin değilsen diger seç.

4. evidence içindeki text alanı evrakta gerçekten
   geçen ifade olmalıdır.

5. subject:
   Evrakın ana konusunu gösteren kaynak ifadesi.

6. request:
   Gönderenin temel talebini gösteren kaynak ifadesi.

7. Talep yoksa request evidence oluşturma.

8. JSON dışında hiçbir şey yazma.

SADECE:

{
    "document_type": "dilekce",
    "process_intent": "bilgi_talebi",
    "evidence": [
        {
            "field": "subject",
            "text": "kaynak metindeki ifade"
        },
        {
            "field": "request",
            "text": "kaynak metindeki ifade"
        }
    ]
}
"""

        user_prompt = f"""
EVRAK:

{text}

Evrakı sınıflandır.
"""

        raw = self.llm.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=300,
            json_mode=True,
        )

        return self._parse_json_object(
            raw
        )

    # =====================================================
    # JSON PARSE
    # =====================================================

    @staticmethod
    def _parse_json_object(
        raw: str,
    ) -> dict[str, Any]:

        if not raw:
            return {}

        cleaned = (
            str(raw)
            .strip()
        )

        # Model bazen ```json ... ``` döndürebilir.
        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(
            r"\s*```$",
            "",
            cleaned,
        )

        try:
            result = json.loads(
                cleaned
            )

            if isinstance(
                result,
                dict,
            ):
                return result

        except json.JSONDecodeError:
            pass

        # JSON öncesi/sonrası açıklama eklediyse
        # ilk { ve son } arasını dene.
        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if (
            start != -1
            and end != -1
            and end > start
        ):
            candidate = (
                cleaned[
                    start:end + 1
                ]
            )

            try:
                result = json.loads(
                    candidate
                )

                if isinstance(
                    result,
                    dict,
                ):
                    return result

            except json.JSONDecodeError:
                pass

        return {}

    # =====================================================
    # SMALL MODEL NORMALIZATION
    # =====================================================

    def _normalize_llm_result(
        self,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Qwen gibi küçük modellerin:

        dilekçe
        dilekçe_formu
        bilgi edinme
        bilgi_edinme

        gibi döndürdüğü ifadeleri bizim
        standart enum'lara dönüştürür.
        """

        if not isinstance(
            result,
            dict,
        ):
            return {}

        raw_document_type = (
            self._normalize_label(
                result.get(
                    "document_type",
                    "",
                )
            )
        )

        raw_intent = (
            self._normalize_label(
                result.get(
                    "process_intent",
                    "",
                )
            )
        )

        document_aliases = {
            "dilekce": "dilekce",
            "dilekce_formu": "dilekce",
            "dilekce_belgesi": "dilekce",

            "resmi_yazi": "resmi_yazi",
            "resmiyazi": "resmi_yazi",
            "kurumsal_yazi": "resmi_yazi",

            "form": "form",
            "form_belgesi": "form",

            "tutanak": "tutanak",
            "rapor": "rapor",
            "karar": "karar",

            "tebligat": "tebligat",
            "teblig": "tebligat",

            "eposta": "eposta",
            "e_posta": "eposta",
            "email": "eposta",

            "diger": "diger",
            "belirsiz": "diger",
        }

        intent_aliases = {
            "bilgi_talebi": (
                "bilgi_talebi"
            ),

            "bilgi_edinme": (
                "bilgi_talebi"
            ),

            "bilgi_edinme_talebi": (
                "bilgi_talebi"
            ),

            "bilgi_isteme": (
                "bilgi_talebi"
            ),

            "belge_talebi": (
                "belge_talebi"
            ),

            "belge_isteme": (
                "belge_talebi"
            ),

            "basvuru": "basvuru",

            "genel_basvuru": (
                "basvuru"
            ),

            "sikayet": "sikayet",
            "itiraz": "itiraz",

            "izin_talebi": (
                "izin_talebi"
            ),

            "izin": (
                "izin_talebi"
            ),

            "bildirim": "bildirim",
            "cevap": "cevap",
            "yanit": "cevap",
            "iletim": "iletim",
            "yonlendirme": "iletim",

            "diger": "diger",
            "belirsiz": "diger",
        }

        document_type = (
            document_aliases.get(
                raw_document_type,
                raw_document_type,
            )
        )

        process_intent = (
            intent_aliases.get(
                raw_intent,
                raw_intent,
            )
        )

        evidence = result.get(
            "evidence",
            [],
        )

        if not isinstance(
            evidence,
            list,
        ):
            evidence = []

        return {
            "document_type": (
                document_type
            ),

            "process_intent": (
                process_intent
            ),

            "evidence": (
                evidence
            ),
        }

    @staticmethod
    def _normalize_label(
        value: Any,
    ) -> str:

        text = str(
            value or ""
        ).strip().lower()

        replacements = {
            "ç": "c",
            "ğ": "g",
            "ı": "i",
            "ö": "o",
            "ş": "s",
            "ü": "u",
        }

        for old, new in (
            replacements.items()
        ):
            text = text.replace(
                old,
                new,
            )

        text = re.sub(
            r"[^a-z0-9]+",
            "_",
            text,
        )

        return text.strip("_")

    # =====================================================
    # CLASSIFICATION VALIDATION
    # =====================================================

    @staticmethod
    def _is_valid_classification(
        result: dict[str, Any],
    ) -> bool:

        if not isinstance(
            result,
            dict,
        ):
            return False

        document_type = result.get(
            "document_type"
        )

        process_intent = result.get(
            "process_intent"
        )

        return (
            document_type
            in ALLOWED_DOCUMENT_TYPES
            and process_intent
            in ALLOWED_PROCESS_INTENTS
        )

    # =====================================================
    # EVIDENCE VALIDATION
    # =====================================================

    def _validate_evidence(
        self,
        evidence: list[dict[str, Any]],
        source_text: str,
    ) -> list[dict[str, str]]:

        if not isinstance(
            evidence,
            list,
        ):
            return []

        normalized_source = (
            self._normalize_text(
                source_text
            )
        )

        allowed_fields = {
            "document_type",
            "process_intent",
            "subject",
            "request",
        }

        validated = []

        seen = set()

        for item in evidence:

            if not isinstance(
                item,
                dict,
            ):
                continue

            field = str(
                item.get(
                    "field",
                    "",
                )
            ).strip()

            evidence_text = str(
                item.get(
                    "text",
                    "",
                )
            ).strip()

            if (
                field
                not in allowed_fields
            ):
                continue

            if not evidence_text:
                continue

            normalized_evidence = (
                self._normalize_text(
                    evidence_text
                )
            )

            # Model paraphrase yaptıysa kabul etme.
            if (
                normalized_evidence
                not in normalized_source
            ):
                continue

            key = (
                field,
                normalized_evidence,
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            validated.append(
                {
                    "field": field,
                    "text": evidence_text,
                }
            )

        return validated

    # =====================================================
    # DETERMINISTIC EVIDENCE FALLBACK
    # =====================================================

    def _extract_evidence_fallback(
        self,
        text: str,
        document_type: str,
        process_intent: str,
    ) -> list[dict[str, str]]:
        """
        LLM evidence çıkaramazsa kaynak metindeki
        cümlelerden konu ve temel talebi seçer.
    
        Yeni metin üretmez.
        """
    
        sentences = self._split_sentences(
            text
        )
    
        if not sentences:
            return []
    
        evidence = []
    
        # -------------------------------------------------
        # 1. Talep cümlesini bul
        # -------------------------------------------------
    
        # Daha güçlü talep ifadeleri önce.
        strong_request_markers = [
            "verilmesini arz ederim",
            "bildirilmesini arz ederim",
            "gönderilmesini arz ederim",
            "sunulmasını arz ederim",
            "gereğini arz ederim",
            "talep ederim",
            "rica ederim",
        ]
    
        weak_request_markers = [
            "verilmesini",
            "bildirilmesini",
            "gönderilmesini",
            "istiyorum",
            "istemekteyim",
            "talep",
        ]
    
        request_sentence = None
    
        # Önce güçlü talep cümlesini ara.
        for sentence in sentences:
    
            normalized = (
                self._normalize_text(
                    sentence
                )
            )
    
            if any(
                marker in normalized
                for marker
                in strong_request_markers
            ):
                request_sentence = (
                    sentence.strip()
                )
                break
    
        # Bulamazsa daha genel ifadeleri dene.
        if not request_sentence:
    
            for sentence in sentences:
    
                normalized = (
                    self._normalize_text(
                        sentence
                    )
                )
    
                if any(
                    marker in normalized
                    for marker
                    in weak_request_markers
                ):
                    request_sentence = (
                        sentence.strip()
                    )
                    break
    
        # -------------------------------------------------
        # 2. Konu cümlesini bul
        # -------------------------------------------------
    
        subject_sentence = None
    
        subject_markers = [
            "hakkında",
            "ilişkin",
            "konusunda",
            "bilgi edinmek",
            "bilgi almak",
        ]
    
        # Muhatap / başlık gibi satırları konu sayma.
        excluded_subject_patterns = [
            "birimine",
            "müdürlüğüne",
            "başkanlığına",
            "bakanlığına",
            "rektörlüğüne",
            "makamına",
        ]
    
        for sentence in sentences:
    
            # Talep cümlesini konu olarak tekrar kullanma.
            if (
                request_sentence
                and sentence.strip()
                == request_sentence
            ):
                continue
    
            normalized = (
                self._normalize_text(
                    sentence
                )
            )
    
            if any(
                excluded in normalized
                for excluded
                in excluded_subject_patterns
            ):
                continue
    
            if any(
                marker in normalized
                for marker
                in subject_markers
            ):
                subject_sentence = (
                    sentence.strip()
                )
                break
    
        # -------------------------------------------------
        # 3. Eğer ayrı konu bulunamadıysa,
        #    talep cümlesini konu evidence olarak kullanma.
        #    Subject boş kalabilir; bu yanlış bilgi
        #    üretmekten daha güvenlidir.
        # -------------------------------------------------
    
        if subject_sentence:
    
            evidence.append(
                {
                    "field": "subject",
                    "text": (
                        subject_sentence
                    ),
                }
            )
    
        if request_sentence:
    
            evidence.append(
                {
                    "field": "request",
                    "text": (
                        request_sentence
                    ),
                }
            )
    
        return evidence
    
    @staticmethod
    def _split_sentences(
        text: str,
    ) -> list[str]:

        parts = re.split(
            r"(?<=[.!?])\s+|\n+",
            str(text),
        )

        return [
            part.strip()
            for part in parts
            if part.strip()
        ]

    # =====================================================
    # HEURISTIC CLASSIFICATION
    # =====================================================

    def _heuristic_classification(
        self,
        text: str,
    ) -> dict[str, Any]:

        normalized = (
            self._normalize_text(
                text
            )
        )

        document_type = "diger"

        if (
            "dilekce" in self._normalize_label(
                normalized
            )
            or "arz ederim" in normalized
            or "geregini arz" in self._normalize_label(
                normalized
            )
        ):
            document_type = "dilekce"

        elif "tutanak" in normalized:
            document_type = "tutanak"

        elif "rapor" in normalized:
            document_type = "rapor"

        elif "karar" in normalized:
            document_type = "karar"

        elif (
            "tebligat" in normalized
            or "teblig olunur"
            in self._normalize_label(
                normalized
            )
        ):
            document_type = "tebligat"

        elif (
            "sayi:" in self._normalize_label(
                normalized
            )
            and "konu:" in normalized
        ):
            document_type = (
                "resmi_yazi"
            )

        process_intent = "diger"

        normalized_ascii = (
            self._normalize_label(
                normalized
            )
        )

        if (
            "bilgi_edinme"
            in normalized_ascii
            or "bilgi_talep"
            in normalized_ascii
        ):
            process_intent = (
                "bilgi_talebi"
            )

        elif (
            "itiraz"
            in normalized_ascii
        ):
            process_intent = "itiraz"

        elif (
            "sikayet"
            in normalized_ascii
        ):
            process_intent = "sikayet"

        elif (
            "izin_talep"
            in normalized_ascii
        ):
            process_intent = (
                "izin_talebi"
            )

        elif (
            "belge_talep"
            in normalized_ascii
        ):
            process_intent = (
                "belge_talebi"
            )

        elif (
            "basvur"
            in normalized_ascii
            or "talep_ederim"
            in normalized_ascii
        ):
            process_intent = (
                "basvuru"
            )

        return {
            "document_type": (
                document_type
            ),

            "process_intent": (
                process_intent
            ),

            "evidence": [],
        }

    # =====================================================
    # HELPERS
    # =====================================================

    @staticmethod
    def _get_evidence_by_field(
        evidence: list[dict[str, str]],
        field: str,
    ) -> str | None:

        for item in evidence:

            if (
                item.get("field")
                == field
            ):
                return item.get(
                    "text"
                )

        return None

    @staticmethod
    def _normalize_text(
        text: str,
    ) -> str:

        return " ".join(
            str(text)
            .lower()
            .split()
        )

    def _empty_result(
        self,
        message: str,
    ) -> dict[str, Any]:

        return {
            "document_type": "diger",
            "process_intent": "diger",
            "subject_excerpt": None,
            "request_excerpt": None,
            "evidence": [],
            "classification_mode": (
                "none"
            ),
            "evidence_mode": "none",
            "needs_human_review": True,
            **self.priority_agent.assess(""),
            "error": message,
            "llm": (
                self._llm_info()
            ),
        }

    def _llm_info(
        self,
    ) -> dict[str, str]:

        return {
            "provider": (
                self.llm
                .get_provider_name()
            ),
            "model": (
                self.llm
                .get_model_name()
            ),
        }
