import json
import re
from typing import Any

from backend.app.llm.base import LLMClient
from backend.app.llm.factory import create_llm_client
from backend.app.agents.priority_agent import PriorityAgent
from backend.app.institutions.profile_loader import InstitutionProfile


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
        institution_profile: InstitutionProfile | None = None,
    ):
        self.llm = (
            llm
            or create_llm_client(
                "document_agent"
            )
        )
        self.priority_agent = PriorityAgent()
        # InstitutionProfile — allowed subtype listesi buradan türetilir.
        # None ise subtype sınıflandırması atlanır; broad type davranışı korunur.
        self.institution_profile = institution_profile

    def analyze(
        self,
        text: str,
    ) -> dict[str, Any]:
        """
        Evrakı sınıflandırır.

        Çıktı (yeni alanlar italik):
            document_type     — broad structural class (değişmez)
            *document_subtype — institution profile'a özgü domain tipi
            process_intent    — işlem amacı (değişmez)
            ...
        """

        text = str(
            text or ""
        ).strip()

        if not text:
            return self._empty_result(
                "Evrak metni boş."
            )

        priority = self.priority_agent.assess(text)

        # Aktif profile'dan allowed subtypes listesi.
        # Profile yoksa liste boş → subtype sınıflandırması atlanır.
        allowed_subtypes = self._get_allowed_subtypes(
            self.institution_profile
        )

        # ---------------------------------------------
        # 1. LLM classification (tek çağrı — subtype dahil)
        # ---------------------------------------------

        raw_result = (
            self._classify_with_llm(
                text,
                allowed_subtypes=allowed_subtypes,
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

        generated, was_overridden = self._validate_semantic_classification(
            text=text,
            generated=generated,
        )
        if was_overridden:
            classification_mode = "deterministic_validation"

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
        # 2b. Subtype validation
        # LLM'in döndürdüğü subtype allowlist ile kontrol edilir.
        # Allowlist dışındaki değerler → None.
        # Profile yoksa → None (broad type ile devam).
        # ---------------------------------------------

        raw_subtype = generated.get("document_subtype")
        document_subtype = self._validate_subtype(
            raw_subtype,
            allowed_subtypes,
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

        # Profile mevcutsa ama subtype belirlenemezse human review.
        # Profile yoksa (None) subtype beklenmediğinden flag kaldırılmaz.
        if allowed_subtypes and document_subtype is None:
            needs_human_review = True

        return {
            "document_type": (
                document_type
            ),

            # Yeni alan — canonical source: state.document["document_subtype"]
            # Profile yoksa ya da subtype belirlenemezse None.
            "document_subtype": (
                document_subtype
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

    # =====================================================
    # SUBTYPE HELPERS
    # =====================================================

    @staticmethod
    def _get_allowed_subtypes(
        profile: InstitutionProfile | None,
    ) -> list[str]:
        """
        Institution profile'ından izin verilen subtype id listesini döndürür.

        Profile yoksa veya evrak_turleri boşsa boş liste döner.
        Boş liste → subtype sınıflandırması atlanır.
        """
        if profile is None:
            return []
        subtypes = [
            str(e).strip()
            for e in (profile.evrak_turleri or [])
            if e
        ]
        return subtypes

    @staticmethod
    def _validate_subtype(
        subtype: Any,
        allowed_subtypes: list[str],
    ) -> str | None:
        """
        LLM'in döndürdüğü subtype değerini allowlist ile doğrular.

        Kurallar:
        - allowed_subtypes boşsa (profile yok) → None
        - subtype None / boş string / "null" → None
        - allowed_subtypes içindeyse → subtype
        - dışındaysa → None  (fuzzy match yok — güvenli taraf)
        """
        if not allowed_subtypes:
            return None
        if not subtype:
            return None
        candidate = str(subtype).strip().lower()
        if candidate in ("null", "none", ""):
            return None
        if candidate in allowed_subtypes:
            return candidate
        return None

    # =====================================================
    # LLM
    # =====================================================

    def _classify_with_llm(
        self,
        text: str,
        allowed_subtypes: list[str] | None = None,
    ) -> dict[str, Any]:

        # ── Subtype bölümü: yalnız profile mevcutsa eklenir ──────────────
        if allowed_subtypes:
            subtype_list = "\n".join(
                f"  {s}" for s in allowed_subtypes
            )
            subtype_section = f"""

DOCUMENT_SUBTYPE için SADECE aşağıdaki değerlerden birini seç
(bunlar aktif kurum profilinin kabul ettiği evrak türleridir):

{subtype_list}

Belge bu türlerden hiçbirine güvenilir biçimde uymuyorsa null döndür.
Tahmin etme. document_type ve process_intent ile semantik tutarlılığı gözet.
Eğer evrak bilgi talebi içermiyorsa bilgi_edinme seçme.
"""
            subtype_field_example = '"document_subtype": "bilgi_edinme",'
            subtype_evidence_comment = (
                '\n        {\n'
                '            "field": "document_subtype",\n'
                '            "text": "kaynak metindeki destekleyici ifade"\n'
                '        },'
            )
        else:
            subtype_section = ""
            subtype_field_example = '"document_subtype": null,'
            subtype_evidence_comment = ""
        # ─────────────────────────────────────────────────────────────────

        system_prompt = f"""
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
diger{subtype_section}

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

{{
    "document_type": "dilekce",
    {subtype_field_example}
    "process_intent": "bilgi_talebi",
    "evidence": [{subtype_evidence_comment}
        {{
            "field": "subject",
            "text": "kaynak metindeki ifade"
        }},
        {{
            "field": "request",
            "text": "kaynak metindeki ifade"
        }}
    ]
}}
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

            "document_subtype": (
                result.get("document_subtype")
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
            "â": "a",
            "î": "i",
            "û": "u",
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

    def _validate_semantic_classification(
        self,
        text: str,
        generated: dict[str, Any],
    ) -> tuple[dict[str, Any], bool]:
        """Override valid LLM labels only for explicit, high-confidence text."""

        result = dict(generated)
        normalized = self._normalize_label(text)
        official_signals = (
            normalized.startswith("t_c_") or "_t_c_" in normalized,
            "sayi_" in normalized,
            "konu_" in normalized,
            "ilgi_" in normalized,
            bool(re.search(r"(?:mudurlugune|baskanligina|kaymakamligina|ilgili_birimlere)", normalized)),
            bool(re.search(r"(?:geregini_rica_ederim|bilgilerinize_(?:arz|rica|sunulur))", normalized)),
        )
        official_document = (
            sum(official_signals) >= 3
            and official_signals[1]
            and (official_signals[4] or official_signals[5])
        )
        personal_action = bool(re.search(
            r"(?:talep_ediyorum|basvuruyorum|sikayetciyim|sikayet_ediyorum|"
            r"basvurumun_isleme_alinmasini|onarilmasini_arz_ederim|yapilmasini_arz_ederim)",
            normalized,
        ))
        petition_document = personal_action and not official_document

        document_type = str(result.get("document_type") or "diger")
        process_intent = str(result.get("process_intent") or "diger")
        if official_document:
            document_type = "resmi_yazi"
        elif petition_document and document_type != "form":
            document_type = "dilekce"

        if re.search(r"(?:bilgi_edinme_kapsaminda|bilgi_edinme_hakki|bilgi_talep_ediyorum)", normalized):
            process_intent = "bilgi_talebi"
        elif re.search(r"(?:sikayetciyim|sikayet_ediyorum|hususu_sikayet)", normalized):
            process_intent = "sikayet"
        elif re.search(r"(?:basvurunuza_cevaben|ilgi_yaziniza_cevaben|cevap_olarak)", normalized) or (
            "basvurunuz_incelenmis" in normalized and "bilgilerinize_sunulur" in normalized
        ):
            process_intent = "cevap"
        elif re.search(r"(?:ekte_gonderilmistir|geregi_icin_gonderilmistir|ilgili_birime_iletilmesi)", normalized) or (
            "gonderilmesi_hususunda" in normalized and "rica_ederim" in normalized
        ):
            process_intent = "iletim"
        elif re.search(r"(?:basvuruyorum|ruhsat_basvurusu|basvurumun_isleme_alinmasini)", normalized) or (
            petition_document and re.search(r"(?:onarilmasini|yapilmasini)_arz_ederim", normalized)
        ):
            process_intent = "basvuru"

        overridden = (
            document_type != result.get("document_type")
            or process_intent != result.get("process_intent")
        )
        result["document_type"] = document_type
        result["process_intent"] = process_intent
        return result, overridden
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
            "document_subtype",
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
            "document_subtype": None,
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
