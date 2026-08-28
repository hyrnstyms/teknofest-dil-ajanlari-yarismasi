import json
import re
from typing import Any, TypedDict, List, Optional, Dict

from backend.app.llm.base import LLMClient
from backend.app.llm.factory import create_llm_client
from backend.app.rag.retriever import Retriever

# Official writing format renderer — opsiyonel entegrasyon
# Eksik context varsa fallback olarak mevcut _render_draft kullanılır.
try:
    from backend.app.official_writing.template_renderer import (
        render_ust_yazi,
        render_cevap_yazisi,
        render_eksik_bilgi_talebi,
    )
    from backend.app.official_writing.context_adapter import build_official_writing_context
    _OFFICIAL_RENDERER_AVAILABLE = True
except Exception:  # pragma: no cover
    _OFFICIAL_RENDERER_AVAILABLE = False


ALLOWED_DRAFT_TYPES = {
    "ust_yazi",
    "cevap_yazisi",
    "bilgilendirme_metni",
    "eksik_bilgi_talebi",
    "diger",
}

class WritingContext(TypedDict, total=False):
    institution_id: str
    document_type: str
    document_subtype: Optional[str]
    process_intent: str
    document_summary: str
    requested_action: Optional[str]

    extracted_fields: Dict[str, Any]

    verified_facts: List[str]

    missing_fields: List[str]
    uncertain_fields: List[str]

    legal_evidence: List[Dict[str, Any]]
    legal_context: str
    document_legal_references: List[str]

    routing: Dict[str, Any]

    sender_unit: Optional[str]
    recipient: Optional[str]

    institution_profile: Any


class WritingAgent:
    """
    Görev 2:
    - hazırlanacak resmî yazı türünü belirler
    - Resmî Yazışma Kılavuzu'ndan RAG yapar
    - taslak üretir
    - kullanılan yazışma kurallarını doğrular
    - boş/hatalı LLM çıktısında güvenli fallback uygular
    """

    def __init__(
        self,
        llm: LLMClient | None = None,
        retriever: Retriever | None = None,
    ):
        self.llm = (
            llm
            or create_llm_client(
                "writing_agent"
            )
        )

        self.retriever = (
            retriever
            or Retriever()
        )

    def draft(
        self,
        context: WritingContext = None,
        # backward compatibility:
        document_summary: str = "",
        requested_action: str | None = None,
        missing_fields: list[str] | None = None,
        verified_facts: list[str] | None = None,
        legal_context: str | None = None,
        document_legal_references: list[str] | None = None,
        recipient: str | None = None,
        sender_unit: str | None = None,
        top_k: int = 5,
        state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        if context is None:
            context = {
                "document_summary": document_summary,
                "requested_action": requested_action,
                "missing_fields": missing_fields or [],
                "uncertain_fields": [],
                "verified_facts": verified_facts or [],
                "legal_context": legal_context or "",
                "document_legal_references": document_legal_references or [],
                "recipient": recipient,
                "sender_unit": sender_unit,
                "process_intent": "",
                "document_subtype": None,
                "routing": {},
            }
        
        c_document_summary = context.get("document_summary", "")
        c_requested_action = context.get("requested_action")
        c_missing_fields = context.get("missing_fields") or []
        c_uncertain_fields = context.get("uncertain_fields") or []
        c_verified_facts = [
            str(fact).strip()
            for fact in (context.get("verified_facts") or [])
            if str(fact).strip()
        ]
        c_legal_context = str(context.get("legal_context") or "").strip()
        c_document_legal_references = [
            str(reference).strip()
            for reference in (context.get("document_legal_references") or [])
            if str(reference).strip()
        ]
        c_recipient = context.get("recipient")
        c_sender_unit = context.get("sender_unit")

        # QualityAgent aynı invariantı çıktıdan sonra da doğrular. Burada ise
        # modele gitmeden önce extraction kaynaklı muhatabı deterministik
        # biçimde geri kazanır ve yanlış context değerinin taslağa kilitlenmesini
        # engelleriz. Çağıranın context sözlüğü yerinde değiştirilmez.
        extracted_recipient = self._recipient_from_extraction(
            context.get("extracted_fields") or {}
        )
        if extracted_recipient and self._different_recipient(
            c_recipient, extracted_recipient
        ):
            c_recipient = extracted_recipient
            context = dict(context)
            context["recipient"] = c_recipient

        # -------------------------------------------------
        # 1. Hangi resmî yazı hazırlanmalı?
        # -------------------------------------------------

        type_result = self._decide_draft_type(context)

        draft_type = type_result.get("draft_type", "diger")
        mode = type_result.get("mode", "")
        
        if draft_type == "blocked" or mode.startswith("blocked"):
            return {
                "draft_type": "diger" if draft_type == "blocked" else draft_type,
                "draft_type_reason": type_result.get("reason"),
                "draft_generation_mode": mode or "blocked",
                "draft": None,
                "rendered_text": None,
                "process_explanation": type_result.get("reason"),
                "applied_rules": [],
                "supporting_rules": [],
                "rule_validation": {"proposed": 0, "validated": 0},
                "sources": [],
                "retrieval_score": 0.0,
                "llm": self._llm_info(),
                "verified_facts_used": c_verified_facts,
                "requires_human_approval": True,
                "needs_additional_context": True,
                "warning": type_result.get("reason"),
            }

        # -------------------------------------------------
        # 2. Resmî Yazışma Kılavuzu retrieval
        # -------------------------------------------------

        retrieval_query = (
            self._build_retrieval_query(
                draft_type=draft_type,
                document_summary=(
                    c_document_summary
                ),
            )
        )

        sources = (
            self.retriever
            .search_official_writing(
                query=retrieval_query,
                limit=top_k,
            )
        )

        if not sources:
            return {
                "draft_type": draft_type,

                "draft_type_reason": (
                    type_result.get(
                        "reason"
                    )
                ),

                "draft": None,

                "rendered_text": None,

                "process_explanation": (
                    self._build_process_explanation(
                        draft_type=(
                            draft_type
                        ),
                        missing_fields=(
                            c_missing_fields
                        ),
                    )
                ),

                "applied_rules": [],

                "supporting_rules": [],

                "sources": [],

                "retrieval_score": 0.0,

                "llm": (
                    self._llm_info()
                ),

                "requires_human_approval": True,

                "error": (
                    "Resmî Yazışma Kılavuzu "
                    "kaynağı bulunamadı."
                ),
            }

        # -------------------------------------------------
        # 3. RAG context
        # -------------------------------------------------

        context = (
            self._build_context(
                sources
            )
        )

        # -------------------------------------------------
        # 4. LLM taslak üretimi
        # -------------------------------------------------

        generated = (
            self._generate_draft(
                document_summary=(
                    c_document_summary
                ),
                requested_action=(
                    c_requested_action
                ),
                missing_fields=(
                    c_missing_fields
                ),
                verified_facts=(
                    c_verified_facts
                ),
                legal_context=c_legal_context,
                document_legal_references=c_document_legal_references,
                recipient=c_recipient,
                sender_unit=c_sender_unit,
                draft_type=draft_type,
                context=context,
            )
        )

        generation_mode = "llm"

        # -------------------------------------------------
        # 5. LLM boş/geçersiz taslak verdiyse fallback
        # -------------------------------------------------

        if not self._is_draft_complete(
            generated
        ):

            if draft_type == "eksik_bilgi_talebi":
                generated = self._build_missing_info_fallback(
                    missing_fields=c_missing_fields
                )
                generation_mode = "deterministic_fallback"
            else:
                generated = self._repair_draft(
                    generated=generated,
                    document_summary=c_document_summary,
                    requested_action=c_requested_action,
                    verified_facts=c_verified_facts,
                    legal_context=c_legal_context,
                    document_legal_references=c_document_legal_references,
                    recipient=c_recipient,
                    sender_unit=c_sender_unit,
                    draft_type=draft_type,
                    context=context,
                )
                generation_mode = "llm_repair"

        # -------------------------------------------------
        # 6. Son kontrol
        # -------------------------------------------------

        if not self._is_draft_complete(
            generated
        ):
            if c_verified_facts and draft_type in {"cevap_yazisi", "bilgilendirme_metni"}:
                generated = self._build_verified_facts_fallback(
                    draft_type=draft_type,
                    verified_facts=c_verified_facts,
                )

                generation_mode = (
                    "deterministic_verified_facts_fallback"
                )

        if not self._is_draft_complete(
            generated
        ):
            supporting_rules = (
                self._extract_supporting_rules(
                    sources=sources,
                    draft_type=draft_type,
                )
            )

            return {
                "draft_type": draft_type,

                "draft_type_reason": (
                    type_result.get(
                        "reason"
                    )
                ),

                "draft_generation_mode": (
                    "blocked_insufficient_context"
                ),

                "draft": None,

                "rendered_text": None,

                "process_explanation": (
                    "Hazırlanması gereken yazı türü "
                    "belirlendi ancak güvenilir bir "
                    "taslak oluşturmak için yeterli "
                    "somut işlem bilgisi bulunamadı. "
                    "Sistem bilgi uydurmak yerine "
                    "yetkili personelden ek bilgi "
                    "istemektedir."
                ),

                "applied_rules": [],

                "supporting_rules": (
                    supporting_rules
                ),

                "rule_validation": {
                    "proposed": 0,
                    "validated": 0,
                },

                "sources": sources,

                "retrieval_score": (
                    self._calculate_retrieval_score(
                        sources
                    )
                ),

                "llm": (
                    self._llm_info()
                ),

                "verified_facts_used": (
                    c_verified_facts
                ),

                "requires_human_approval": True,

                "needs_additional_context": True,

                "required_input": [
                    (
                        "Taslakta kullanıcıya "
                        "bildirilecek somut işlem "
                        "durumu veya sonuç"
                    )
                ],

                "warning": (
                    "Yetersiz bilgi nedeniyle "
                    "resmî yazı taslağı otomatik "
                    "olarak oluşturulmadı."
                ),
            }

        generated = self._ensure_document_legal_references(
            generated,
            c_document_legal_references,
        )

        # -------------------------------------------------
        # 7. LLM'in iddia ettiği kuralları doğrula
        # -------------------------------------------------

        validated_rules = (
            self._validate_rules(
                items=generated.get(
                    "applied_rules",
                    [],
                ),
                sources=sources,
            )
        )

        # -------------------------------------------------
        # 8. Kılavuzdan deterministik destekleyici
        #    kural parçaları çıkar.
        # -------------------------------------------------

        supporting_rules = (
            self._extract_supporting_rules(
                sources=sources,
                draft_type=draft_type,
            )
        )

        # -------------------------------------------------
        # 9. Muhatap/gönderen bilgisini güvene al.
        # -------------------------------------------------

        draft = self._sanitize_draft(
            generated=generated,
            recipient=c_recipient,
            sender_unit=c_sender_unit,
        )

        process_explanation = self._build_process_explanation(
            draft_type=draft_type,
            missing_fields=c_missing_fields,
        )

        retrieval_score = (
            self._calculate_retrieval_score(
                sources
            )
        )

        proposed_rule_count = len(
            generated.get(
                "applied_rules",
                [],
            )
        )

        validated_rule_count = len(
            validated_rules
        )

        render_state = dict(state or {})
        render_state.setdefault(
            "missing_fields",
            {"missing_fields": list(c_missing_fields)},
        )

        return {
            "draft_type": (
                draft_type
            ),

            "draft_type_reason": (
                type_result.get(
                    "reason"
                )
            ),

            "draft_generation_mode": (
                generation_mode
            ),

            "draft": draft,

            "rendered_text": (
                self._render_draft(
                    draft
                )
            ),

            # Official Writing format renderer denemesi.
            # Başarılı olursa ek alan olarak eklenir; mevcut rendered_text
            # fallback olarak korunur ve API contract bozulmaz.
            **self._try_official_render(draft, draft_type, render_state),

            "process_explanation": (
                process_explanation
            ),

            "applied_rules": (
                validated_rules
            ),

            # Bunlar doğrudan RAG kaynağından
            # deterministik olarak alınır.
            "supporting_rules": (
                supporting_rules
            ),

            "rule_validation": {
                "proposed": (
                    proposed_rule_count
                ),
                "validated": (
                    validated_rule_count
                ),
            },

            "sources": sources,

            "retrieval_score": (
                retrieval_score
            ),

            "llm": (
                self._llm_info()
            ),

            "verified_facts_used": (
                c_verified_facts
            ),

            # Kamu personeli onayı zorunlu.
            "requires_human_approval": True,

            "needs_additional_context": False,

            "warning": None,
        }

    # =====================================================
    # YAZI TÜRÜ KARARI
    # =====================================================

    @staticmethod
    def _extracted_text(fields: dict[str, Any], field_name: str) -> str | None:
        value = fields.get(field_name)
        if isinstance(value, dict):
            if value.get("validated") is False:
                return None
            value = value.get("value")
        if value is None:
            return None
        normalized = " ".join(str(value).split()).strip()
        return normalized or None

    @classmethod
    def _recipient_from_extraction(cls, fields: dict[str, Any]) -> str | None:
        """Resolve only evidence-backed recipient candidates.

        A named person is the strongest addressee signal. Institutional input
        without a person falls back to its extracted sender unit. Explicitly
        unvalidated fields are never promoted into an official draft.
        """
        if not isinstance(fields, dict):
            return None
        return cls._extracted_text(fields, "person_name") or cls._extracted_text(
            fields, "sender_unit"
        )

    @staticmethod
    def _different_recipient(current: Any, expected: str) -> bool:
        if current is None:
            return True
        normalized_current = " ".join(str(current).split()).strip().casefold()
        return normalized_current != expected.casefold()

    def _decide_draft_type(
        self,
        context: WritingContext,
    ) -> dict[str, str]:
        """
        Tamamen deterministik kurallarla yazı türüne karar verir.
        LLM çağrısı yapılmaz.
        """
        uncertain_fields = context.get("uncertain_fields") or []
        missing_fields = context.get("missing_fields") or []
        process_intent = context.get("process_intent") or ""
        routing = context.get("routing") or {}
        recipient = context.get("recipient")

        # 1) CONTENT-CRITICAL UNCERTAINTY blokajı.
        critical_uncertain = [
            f for f in uncertain_fields 
            if f not in ["signature_present", "authority_document_present"]
        ]
        
        # Eğer muhatap belli değilse cevap yazısı / üst yazı tehlikeli
        # NOT: Artık person_name her zaman zorunlu olmadığı için, muhatabın belli olmaması
        # taslağı tamamen bloke etmemelidir. Bunun yerine [MUHATAP] placeholder'ı kullanılacaktır.
        if not recipient and process_intent in ["basvuru", "sikayet", "itiraz", "bilgi_talebi"]:
            if "recipient" not in missing_fields and "recipient" not in critical_uncertain:
                pass # critical_uncertain.append("recipient") iptal edildi.
                
        if critical_uncertain:
            return {
                "draft_type": "blocked",
                "mode": "blocked_uncertain_fields",
                "reason": (
                    f"Kritik alanlarda belirsizlik ({', '.join(critical_uncertain)}) "
                    "olduğu için otomatik taslak üretimi durduruldu."
                ),
            }

        # 2) Eksik kritik alan
        if missing_fields:
            return {
                "draft_type": "eksik_bilgi_talebi",
                "reason": "Evrakta zorunlu eksik bilgiler bulunduğu için eksik bilgi talebi seçildi."
            }

        # 3) process_intent üzerinden karar
        intent_map = {
            "basvuru": "cevap_yazisi",
            "belge_talebi": "cevap_yazisi",
            "sikayet": "cevap_yazisi",
            "itiraz": "cevap_yazisi",
            "bilgi_talebi": "cevap_yazisi",
            "sevk": "ust_yazi",
            "ihbar": "ust_yazi",
            "iletisim": "ust_yazi",
            "bildirim": "bilgilendirme_metni",
        }
        
        if process_intent in intent_map:
            return {
                "draft_type": intent_map[process_intent],
                "reason": f"İşlem amacı ({process_intent}) kurallarına göre {intent_map[process_intent]} seçildi."
            }

        # 4) Routing hedefi var mı?
        if routing.get("recommended_unit") and not recipient:
            # Internal forwarding
            return {
                "draft_type": "ust_yazi",
                "reason": "Evrakın iç birime sevk edileceği anlaşıldığı için üst yazı seçildi."
            }

        # 5) Ambiguous / Belirsiz
        return {
            "draft_type": "diger",
            "mode": "blocked_ambiguous_draft_type",
            "reason": "İşlem amacı ve bağlamından resmî yazı türü kesin olarak belirlenemedi."
        }

    # =====================================================
    # RETRIEVAL
    # =====================================================

    @staticmethod
    def _build_retrieval_query(
        draft_type: str,
        document_summary: str,
    ) -> str:

        type_queries = {

            "ust_yazi": (
                "Resmî yazıda başlık muhatap konu "
                "metin ek ilgi arz rica kuralları"
            ),

            "cevap_yazisi": (
                "Resmî cevap yazısında muhatap konu "
                "metin ilgi arz rica kuralları"
            ),

            "bilgilendirme_metni": (
                "Resmî yazıda konu muhatap metin "
                "içeriği ve yazım kuralları"
            ),

            "eksik_bilgi_talebi": (
                "Resmî yazıda konu muhatap metin "
                "talep ve arz rica kuralları"
            ),

            "diger": (
                "Resmî yazıda başlık konu muhatap "
                "metin arz rica kuralları"
            ),
        }

        base_query = (
            type_queries.get(
                draft_type,
                type_queries["diger"],
            )
        )

        return (
            f"{base_query}. "
            f"Evrak konusu: "
            f"{document_summary[:400]}"
        )

    @staticmethod
    def _build_context(
        sources: list[dict[str, Any]],
    ) -> str:

        parts = []

        for index, source in enumerate(
            sources,
            start=1,
        ):

            source_id = f"K{index}"

            text = str(
                source.get(
                    "text",
                    "",
                )
                or ""
            )

            parts.append(
                f"""
[{source_id}]
Kaynak: Resmî Yazışma Kılavuzu

{text}
""".strip()
            )

        return "\n\n---\n\n".join(
            parts
        )

    # =====================================================
    # TASLAK ÜRETİMİ
    # =====================================================

    def _generate_draft(
        self,
        document_summary: str,
        requested_action: str | None,
        missing_fields: list[str],
        verified_facts: list[str],
        legal_context: str,
        document_legal_references: list[str],
        recipient: str | None,
        sender_unit: str | None,
        draft_type: str,
        context: str,
    ) -> dict[str, Any]:
        """
        LLM yalnızca taslağın içerik alanlarını üretir.

        Kılavuz evidence çıkarımı bu çağrıdan ayrılmıştır.
        Böylece küçük modelden aynı anda hem yazı üretmesi
        hem de exact kaynak alıntısı yapması istenmez.
        """

        action_text = (
            requested_action
            or "Belirtilmedi"
        )

        missing_text = (
            ", ".join(missing_fields)
            if missing_fields
            else "Yok"
        )

        facts_text = (
            "\n".join(
                f"- {fact}"
                for fact in verified_facts
            )
            if verified_facts
            else "Yok"
        )

        system_prompt = """
Sen Türkiye'deki kamu kurumları için resmî yazı
taslağı hazırlayan bir asistansın.

KESİN KURALLAR:

1. subject ve body alanları boş olamaz.

2. Öncelikli gerçek kaynağı DOĞRULANMIŞ İŞLEM
   BİLGİLERİ (VERIFIED FACTS) bölümüdür.

3. DOĞRULANMIŞ İŞLEM BİLGİLERİ verilmişse cevap
   metnindeki işlem durumu veya sonuç yalnızca bu
   bilgilerden oluşturulmalıdır.

4. Verilmeyen kurum, kişi, tarih, belge sayısı,
   dosya numarası, süre, kanun, yönetmelik, sonuç, 
   gönderici (sender) veya muhatap (recipient) KESİNLİKLE UYDURMA.
   Unknown / bilinmeyen bir alanı biliniyormuş gibi yazma.

5. Evrakın anlamını değiştirme.

6. Resmî, kısa ve profesyonel Türkçe kullan.

7. Cevap yazısında yalnızca verilen işlem durumunu
   veya sonucu bildir.

8. Eksik bilgi talebi ise yalnızca verilen eksik
   alanların tamamlanmasını iste.

9. Kılavuzda bulunan örnek olayları taslağa taşıma.

10. JSON dışında hiçbir şey döndürme.

11. DOĞRULANMIŞ İŞLEM BİLGİLERİ işlem sonucunu açıkça doğrulamıyorsa
    "başvurunuz işleme alınmıştır", "kabul edilmiştir", "onaylanmıştır",
    "verilmiştir", "uygun görülmüştür", "sonuçlandırılmıştır" veya "tamamlanmıştır"
    gibi kesin sonuç/başvuru durumu söyleme. 
    Yalnızca "incelenmektedir" veya "değerlendirilecektir" gibi
    sonuca dair olmayan süreç ifadelerini kullan.

12. KILAVUZ KAYNAKLARI (Official Writing Rules) YALNIZCA resmî yazışmanın nasıl düzenleneceğini (biçim/şekil kurallarını) belirler. Başvuruya ilişkin kişi, olay, tarih, sayı, karar veya işlem sonucu bu kaynaklardan TÜRETİLEMEZ.

13. Başvurunun tarihi veya sayısı doğrulanmış verilerde YOKSA bu bilgiye
    hiç değinme. 00.00.0000, 00000000-..., köşeli placeholder ya da
    tahmini/sahte tarih ve referans numarası üretme.

14. Çıktıya asla (basvuru, dilekce, ust_yazi, process_intent, signature_present vb.) geliştirici değişken / enum key sızdırma. Türkçe metin ("başvuru", "dilekçe", "üst yazı") kullan.

Hiyerarşi (Önem sırası):
1. VERIFIED FACTS (Doğrulanmış Olgular)
2. EXTRACTED/VALIDATED CONTEXT (Evrak Özeti, Eksik Alanlar)
3. ROUTING/INSTITUTION CONTEXT (Muhatap, Gönderen)
4. VALIDATED LEGAL EVIDENCE (Hukuki Bağlam)
5. OFFICIAL WRITING RULES (Kılavuz Biçim Kuralları)

SADECE ŞU JSON FORMATINI DÖNDÜR:

{
    "subject": "kısa ve açık konu",
    "body": "resmî yazının ana metni"
}
"""

        user_prompt = f"""
YAZI TÜRÜ:
{draft_type}

EVRAK ÖZETİ:
{document_summary}

ÖNERİLEN İŞLEM:
{action_text}

EKSİK ALANLAR:
{missing_text}

DOĞRULANMIŞ İŞLEM BİLGİLERİ:
{facts_text}

HUKUKİ BAĞLAM (yalnızca doğrulanmış kanıt):
{legal_context or "Yok"}

EVRAKTA AÇIKÇA GEÇEN MEVZUAT ATIFLARI:
{', '.join(document_legal_references) if document_legal_references else "Yok"}
Bu atıflar başvuru sahibinin beyanıdır; bunlardan hukuki sonuç çıkarma.

MUHATAP:
{recipient or "BELİRTİLMEDİ"}

GÖNDEREN:
{sender_unit or "BELİRTİLMEDİ"}

KILAVUZ KAYNAKLARI:
{context}

Sadece verilen gerçeklere dayanarak subject ve body üret.
"""

        raw = self.llm.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=350,
            json_mode=True,
        )

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            return {}

        if not isinstance(
            result,
            dict,
        ):
            return {}

        return {
            "subject": str(
                result.get(
                    "subject",
                    "",
                )
                or ""
            ).strip(),

            "body": str(
                result.get(
                    "body",
                    "",
                )
                or ""
            ).strip(),

            # Kapanışı henüz modele bırakmıyoruz.
            # Routing/Quality aşamasında muhatap türüne göre
            # kılavuz temelli üretilecek.
            "closing": None,

            "applied_rules": [],
        }

    def _repair_draft(
        self,
        generated: dict[str, Any],
        document_summary: str,
        requested_action: str | None,
        verified_facts: list[str],
        legal_context: str,
        document_legal_references: list[str],
        recipient: str | None,
        sender_unit: str | None,
        draft_type: str,
        context: str,
    ) -> dict[str, Any]:

        facts_text = (
            "\n".join(
                f"- {fact}"
                for fact in verified_facts
            )
            if verified_facts
            else "Yok"
        )

        system_prompt = """
Önceki resmî yazı taslağında subject veya body alanı
eksik bırakıldı veya geçersiz bir sonuç üretildi.

Yalnızca verilen olguları kullan.
Yeni kurum, tarih, sayı, süre, mevzuat, sonuç, gönderen veya muhatap uydurma.
Başvurunun tarihi veya sayısı doğrulanmış verilerde yoksa bu bilgiye hiç
değinme; sahte tarih, referans numarası veya placeholder üretme.
Doğrulanmış işlem sonucu yoksa başvurunun işleme alındığını, kabul
edildiğini, onaylandığını, uygun görüldüğünü, tamamlandığını veya sonuçlandığını KESİNLİKLE söyleme.
Yalnızca süreç belirten ve sonucu kesinleştirmeyen ifade kullan.
Yazı türü ("basvuru", "dilekce", "ust_yazi" gibi) developer key'lerini çıktıya SIZDIRMA (Türkçe: başvuru, dilekçe, üst yazı kullan).

JSON dışında hiçbir şey döndürme.

{
    "subject": "boş olmayan kısa konu",
    "body": "boş olmayan resmî metin"
}
"""

        user_prompt = f"""
YAZI TÜRÜ:
{draft_type}

EVRAK ÖZETİ:
{document_summary}

ÖNERİLEN İŞLEM:
{requested_action or "Belirtilmedi"}

DOĞRULANMIŞ İŞLEM BİLGİLERİ:
{facts_text}

HUKUKİ BAĞLAM (yalnızca doğrulanmış kanıt):
{legal_context or "Yok"}

EVRAKTA AÇIKÇA GEÇEN MEVZUAT ATIFLARI:
{', '.join(document_legal_references) if document_legal_references else "Yok"}
Bu atıflar başvuru sahibinin beyanıdır; bunlardan hukuki sonuç çıkarma.

MUHATAP:
{recipient or "BELİRTİLMEDİ"}

GÖNDEREN:
{sender_unit or "BELİRTİLMEDİ"}

ÖNCEKİ EKSİK ÇIKTI:
{json.dumps(generated, ensure_ascii=False)}

KILAVUZ:
{context}

subject ve body alanlarını eksiksiz üret.
"""

        raw = self.llm.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=300,
            json_mode=True,
        )

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            return {}

        if not isinstance(
            result,
            dict,
        ):
            return {}

        return {
            "subject": str(
                result.get(
                    "subject",
                    "",
                )
                or ""
            ).strip(),

            "body": str(
                result.get(
                    "body",
                    "",
                )
                or ""
            ).strip(),

            "closing": None,
            "applied_rules": [],
        }

    # =====================================================
    # DETERMINISTIC FALLBACK
    # =====================================================

    @staticmethod
    def _build_verified_facts_fallback(
        draft_type: str,
        verified_facts: list[str],
    ) -> dict[str, Any]:
        """
        LLM geçerli taslak üretemezse yalnızca önceki
        agentlar tarafından doğrulanmış işlem bilgilerini
        kullanarak güvenli taslak oluşturur.

        Yeni olgu üretmez.
        """

        cleaned_facts = [
            str(fact).strip()
            for fact in verified_facts
            if str(fact).strip()
        ]

        if not cleaned_facts:
            return {}

        if draft_type == "cevap_yazisi":
            subject = "Başvurunun İşlem Durumu"
        else:
            subject = "Bilgilendirme"

        body = " ".join(
            fact.rstrip(".") + "."
            for fact in cleaned_facts
        )

        return {
            "sender_unit": None,
            "recipient": None,
            "subject": subject,
            "body": body,
            "closing": None,
            "applied_rules": [],
        }

    @staticmethod
    def _build_missing_info_fallback(
        missing_fields: list[str],
    ) -> dict[str, Any]:
        """
        Eksik bilgi talebi gibi basit ve kesin
        işlemlerde LLM boş cevap verirse Python
        güvenli bir taslak oluşturur.
        """

        readable_fields = ", ".join(
            missing_fields
        )

        if len(missing_fields) == 1:

            subject = (
                "Eksik Bilginin Tamamlanması"
            )

            body = (
                "Başvurunun değerlendirilmesine "
                "devam edilebilmesi için eksik "
                f"olduğu tespit edilen "
                f"{readable_fields} bilgisinin "
                "tamamlanması talep edilmektedir."
            )

        else:

            subject = (
                "Eksik Bilgilerin Tamamlanması"
            )

            body = (
                "Başvurunun değerlendirilmesine "
                "devam edilebilmesi için eksik "
                "olduğu tespit edilen aşağıdaki "
                "bilgilerin tamamlanması talep "
                f"edilmektedir: {readable_fields}."
            )

        return {
            "sender_unit": None,
            "recipient": None,
            "subject": subject,
            "body": body,

            # Arz/rica gibi ifadeleri burada
            # kafadan üretmiyoruz.
            "closing": None,

            "applied_rules": [],
        }

    # =====================================================
    # TASLAK KONTROLÜ
    # =====================================================

    @staticmethod
    def _is_draft_complete(
        generated: dict[str, Any],
    ) -> bool:

        if not isinstance(
            generated,
            dict,
        ):
            return False

        subject = str(
            generated.get(
                "subject",
                "",
            )
            or ""
        ).strip()

        body = str(
            generated.get(
                "body",
                "",
            )
            or ""
        ).strip()

        return bool(
            subject
            and body
        )

    # =====================================================
    # KILAVUZ KURALI DOĞRULAMA
    # =====================================================

    def _validate_rules(
        self,
        items: list[dict[str, Any]],
        sources: list[dict[str, Any]],
    ) -> list[dict[str, str]]:

        source_map = {}

        for index, source in enumerate(
            sources,
            start=1,
        ):

            source_map[
                f"K{index}"
            ] = str(
                source.get(
                    "text",
                    "",
                )
                or ""
            )

        validated = []

        seen = set()

        for item in items:

            if not isinstance(
                item,
                dict,
            ):
                continue

            evidence = str(
                item.get(
                    "evidence",
                    "",
                )
            ).strip()

            source_id = str(
                item.get(
                    "source",
                    "",
                )
            ).strip()

            if not evidence:
                continue

            if source_id not in source_map:
                continue

            normalized_evidence = (
                self._normalize_text(
                    evidence
                )
            )

            normalized_source = (
                self._normalize_text(
                    source_map[
                        source_id
                    ]
                )
            )

            if (
                normalized_evidence
                not in normalized_source
            ):
                continue

            key = (
                source_id,
                normalized_evidence,
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            validated.append(
                {
                    "evidence": evidence,
                    "source": source_id,
                }
            )

        return validated

    # =====================================================
    # KILAVUZDAN DOĞRUDAN DESTEKLEYİCİ KURAL ÇIKAR
    # =====================================================

    def _extract_supporting_rules(
        self,
        sources: list[dict[str, Any]],
        draft_type: str,
    ) -> list[dict[str, str]]:
        """
        Resmî Yazışma Kılavuzu kaynaklarından yalnızca
        açıklayıcı/normatif kural niteliğindeki cümleleri
        seçer.
    
        Örnek yazılar, örnek kapanış ifadeleri ve belge
        içerikleri destekleyici kural olarak gösterilmez.
        """
    
        # Yazışma kuralıyla ilgili olabilecek kavramlar.
        topic_keywords = [
            "konu",
            "muhatap",
            "metin",
            "başlık",
            "ilgi",
            "ek",
            "arz",
            "rica",
        ]
    
        # Bir cümlenin sadece kavramı içermesi yetmez.
        # Kural anlatıyor olması için normatif/açıklayıcı
        # ifadelerden en az birini de içermesini istiyoruz.
        rule_markers = [
            "yazılır",
            "yazılmalıdır",
            "belirtilir",
            "belirtilmelidir",
            "kullanılır",
            "kullanılmalıdır",
            "yer verilir",
            "yer alır",
            "oluşur",
            "hazırlanır",
            "düzenlenir",
            "gösterilir",
            "bulunur",
            "başlar",
            "bitirilir",
            "ifade edilir",
            "yapılır",
            "yapılmalıdır",
            "uygulanır",
            "uyulmalıdır",
        ]
    
        # Kılavuz içindeki örnek belge/metin parçalarını
        # kural diye göstermemek için.
        excluded_markers = [
            "örnek:",
            "örnek ",
            "örneğin",
            "ilgi (a)",
            "ilgi (b)",
            "kurumumuza",
            "bilgilerini ve gereğini",
            "arz ederim",
            "rica ederim",
            "arz/rica ederim",
        ]
    
        results = []
        seen = set()
    
        for source_index, source in enumerate(
            sources,
            start=1,
        ):
            source_id = f"K{source_index}"
    
            text = str(
                source.get(
                    "text",
                    "",
                )
                or ""
            )
    
            pieces = re.split(
                r"(?<=[.!?])\s+|\n+",
                text,
            )
    
            for piece in pieces:
    
                clean = " ".join(
                    piece.split()
                ).strip()
    
                # Çok kısa parçalar genellikle başlık
                # veya örnek ifade oluyor.
                if len(clean) < 50:
                    continue
    
                lowered = clean.lower()
    
                # Örnek içerikleri ele.
                if any(
                    marker in lowered
                    for marker in excluded_markers
                ):
                    continue
    
                # Resmî yazışmayla ilgili bir kavram geçmeli.
                has_topic = any(
                    keyword in lowered
                    for keyword in topic_keywords
                )
    
                if not has_topic:
                    continue
    
                # Ve cümlenin gerçekten kural/açıklama
                # niteliğinde olması gerekiyor.
                has_rule_marker = any(
                    marker in lowered
                    for marker in rule_markers
                )
    
                if not has_rule_marker:
                    continue
    
                normalized = (
                    self._normalize_text(
                        clean
                    )
                )
    
                if normalized in seen:
                    continue
    
                seen.add(
                    normalized
                )
    
                results.append(
                    {
                        "evidence": clean,
                        "source": source_id,
                    }
                )
    
                if len(results) >= 3:
                    return results
    
        return results
    
    # =====================================================
    # SANITIZE
    # =====================================================

    @staticmethod
    def _ensure_document_legal_references(
        generated: dict[str, Any],
        references: list[str],
    ) -> dict[str, Any]:
        """Preserve statute references explicitly asserted by the applicant.

        This records a document fact only; it does not treat the reference as
        a verified legal conclusion.
        """

        if not generated or not references:
            return generated
        body = str(generated.get("body") or "").strip()
        combined = f"{generated.get('subject') or ''} {body}".casefold()
        missing = [
            reference
            for reference in references
            if reference.casefold() not in combined
        ]
        if missing:
            suffix = "Başvuruda " + ", ".join(missing) + " atfı yapılmıştır."
            generated = dict(generated)
            generated["body"] = f"{body} {suffix}".strip()
        return generated

    @staticmethod
    def _sanitize_draft(
        generated: dict[str, Any],
        recipient: str | None,
        sender_unit: str | None,
    ) -> dict[str, Any]:

        subject = str(
            generated.get(
                "subject",
                "",
            )
            or ""
        ).strip()

        body = str(
            generated.get(
                "body",
                "",
            )
            or ""
        ).strip()

        closing_raw = (
            generated.get(
                "closing"
            )
        )

        closing = None

        if closing_raw:
            closing = str(
                closing_raw
            ).strip()

        return {
            # Model bunları değiştiremez.
            "sender_unit": (
                sender_unit
                if sender_unit
                else None
            ),

            "recipient": (
                recipient
                if recipient
                else None
            ),

            "subject": (
                subject
            ),

            "body": (
                body
            ),

            "closing": (
                closing
            ),
        }

    # =====================================================
    # OFFICIAL WRITING FORMAT RENDER (Adapter)
    # =====================================================

    @staticmethod
    def _try_official_render(
        draft: dict[str, Any],
        draft_type: str,
        state: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Writing Agent'ın structured draft çıktısını, Official Writing
        format motoru (template_renderer) üzerinden render etmeye çalışır.
        
        Returns:
            dict: API response içine doğrudan merge edilecek telemetry objesi.
                  Eğer render başarılıysa 'official_rendered_text' içerir.
        """
        result = {
            "official_render": {
                "attempted": False,
                "success": False,
                "template": None,
                "missing_fields": [],
                "warnings": [],
                "source_map": {},
                "fallback_policies": {}
            }
        }

        if not _OFFICIAL_RENDERER_AVAILABLE:
            result["official_render_warning"] = "Official renderer modülü yüklenemedi."
            return result

        if draft_type == "diger":
            # Bu türler için template motoru kullanılmaz.
            return result

        result["official_render"]["attempted"] = True
        state = state or {}

        # Context Adapter'ı çağır
        try:
            adapter_res = build_official_writing_context(draft, state, draft_type)
        except Exception as exc:
            result["official_render_warning"] = f"Context adapter hatası: {exc}"
            return result

        result["official_render"]["missing_fields"] = adapter_res.get("missing_required_fields", [])
        result["official_render"]["warnings"] = adapter_res.get("warnings", [])
        result["official_render"]["source_map"] = adapter_res.get("source_map", {})
        result["official_render"]["fallback_policies"] = adapter_res.get("fallback_policies", {})

        context = adapter_res.get("context", {})
        result["official_render"]["context"] = context
        
        try:
            rendered = None
            if draft_type in ("ust_yazi", "bilgilendirme_metni"):
                rendered = render_ust_yazi(context)
                result["official_render"]["template"] = "ust_yazi.jinja2"
            elif draft_type == "cevap_yazisi":
                rendered = render_cevap_yazisi(context)
                result["official_render"]["template"] = "cevap_yazisi.jinja2"
            elif draft_type == "eksik_bilgi_talebi":
                rendered = render_eksik_bilgi_talebi(context)
                result["official_render"]["template"] = "eksik_bilgi_talebi.jinja2"

            if rendered:
                result["official_rendered_text"] = rendered
                result["official_render"]["success"] = True

        except Exception as exc:
            result["official_render_warning"] = f"Official template render hatası: {exc}"

        return result

    # =====================================================
    # RENDER (Mevcut)
    # =====================================================

    @staticmethod
    def _render_draft(
        draft: dict[str, Any],
    ) -> str:

        lines = []

        sender = draft.get(
            "sender_unit"
        )

        recipient = draft.get(
            "recipient"
        )

        subject = draft.get(
            "subject"
        )

        body = draft.get(
            "body"
        )

        closing = draft.get(
            "closing"
        )

        if sender:
            lines.append(
                str(sender)
            )
            lines.append("")

        if recipient:
            lines.append(
                str(recipient)
            )
            lines.append("")

        if subject:
            lines.append(
                f"Konu: {subject}"
            )
            lines.append("")

        if body:
            lines.append(
                str(body)
            )

        if closing:
            lines.append("")
            lines.append(
                str(closing)
            )

        return "\n".join(
            lines
        ).strip()

    # =====================================================
    # SÜREÇ AÇIKLAMASI
    # =====================================================

    @staticmethod
    def _build_process_explanation(
        draft_type: str,
        missing_fields: list[str],
    ) -> str:

        if (
            draft_type
            == "eksik_bilgi_talebi"
        ):

            fields = ", ".join(
                missing_fields
            )

            return (
                "Sistem evrakta eksik bilgi "
                f"tespit ettiği için ({fields}) "
                "eksik bilgi talebi taslağı "
                "oluşturdu. Taslak yetkili "
                "personelin onayına sunulmalıdır."
            )

        type_names = {

            "ust_yazi": (
                "üst yazı"
            ),

            "cevap_yazisi": (
                "cevap yazısı"
            ),

            "bilgilendirme_metni": (
                "bilgilendirme metni"
            ),

            "diger": (
                "alternatif resmî yazı"
            ),
        }

        readable_type = (
            type_names.get(
                draft_type,
                draft_type,
            )
        )

        return (
            "Sistem evrakın içeriğine göre "
            f"{readable_type} hazırlanmasını "
            "önerdi. Oluşturulan taslak nihai "
            "işlemden önce yetkili personelin "
            "onayına sunulmalıdır."
        )

    # =====================================================
    # HELPERS
    # =====================================================

    @staticmethod
    def _normalize_text(
        text: str,
    ) -> str:

        return " ".join(
            str(text)
            .lower()
            .split()
        )

    @staticmethod
    def _calculate_retrieval_score(
        sources: list[dict[str, Any]],
    ) -> float:

        if not sources:
            return 0.0

        score = float(
            sources[0].get(
                "score",
                0.0,
            )
        )

        return round(
            min(
                max(
                    score,
                    0.0,
                ),
                1.0,
            ),
            4,
        )

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

    def draft_case_aware(
        self,
        *,
        stage: str,
        clarification: dict[str, Any] | None = None,
        missing_fields: dict[str, Any] | None = None,
        routing: dict[str, Any] | None = None,
        originator=None,
        extraction: dict[str, Any] | None = None,
        department_action=None,
        summary: dict[str, Any] | None = None,
        legal_analysis: dict[str, Any] | None = None,
        document: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Case-lifecycle drafts. Legacy ``draft()`` is unchanged."""
        from backend.app.intelligence.case_writing import CaseWritingService

        service = CaseWritingService()
        if stage in {"intake", "first_stage", "MISSING_INFORMATION_REQUEST", "INTERIM_INFORMATION"}:
            return service.draft_for_intake(
                clarification=clarification,
                missing_fields=missing_fields,
                routing=routing,
                originator=originator,
                extraction=extraction,
            )
        if stage in {"OFFICIAL_RESPONSE", "official_response"}:
            return service.draft_official_response(
                department_action=department_action,
                originator=originator,
                extraction=extraction,
                routing=routing,
                summary=summary,
                legal_analysis=legal_analysis,
                document=document,
            )
        return service.draft_internal(
            stage,  # type: ignore[arg-type]
            body="",
            subject="",
            originator=originator,
            extraction=extraction,
            department_action=department_action,
        )
