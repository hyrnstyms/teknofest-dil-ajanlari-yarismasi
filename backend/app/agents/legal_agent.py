import json
import re
import unicodedata
from typing import Any

from backend.app.llm.base import LLMClient
from backend.app.llm.factory import create_llm_client
from backend.app.rag.retriever import Retriever


LEGAL_TOKEN_RE = re.compile(r"[a-z\u00e7\u011f\u0131i\u00f6\u015f\u00fc0-9]+")
QUERY_STOPWORDS = {
    "acaba", "bir", "bu", "da", "de", "hangi", "hangisi", "hangisidir",
    "ile", "icin", "i\u00e7in", "kac", "ka\u00e7", "kadar",
    "mi", "m\u0131", "mu", "m\u00fc", "ne", "nedir", "nelerdir",
    "nas\u0131l", "soru", "ve", "veya",
}
EXPLICIT_LAW_RE = re.compile(r"\b(\d{3,6})\s+sayili\b")
ARTICLE_AFTER_RE = re.compile(
    r"\bmadde(?:si)?\s*[:.]?\s*(\d+(?:/[a-z])?)\b"
)
ARTICLE_BEFORE_RE = re.compile(
    r"\b(\d+(?:/[a-z])?)\s+(?:inci|uncu|nci|ncu)\s+madde(?:si)?\b"
)


class LegalAgent:
    """
    Mevzuat tabanlı analiz agent'ı.

    Akış:
        Soru / evrak
            ↓
        BGE-M3 + Qdrant retrieval
            ↓
        En ilgili mevzuat kaynaklarını seç
            ↓
        LLM kaynak içinden evidence çıkarır
            ↓
        Python evidence doğrulaması
            ↓
        Kaynak-temelli cevap
    """

    def __init__(
        self,
        llm: LLMClient | None = None,
        retriever: Retriever | None = None,
    ):
        self.llm = (
            llm
            or create_llm_client(
                "legal_agent"
            )
        )

        self.retriever = (
            retriever
            or Retriever()
        )

    def analyze(
        self,
        query: str,
        law_number: str | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """
        Kullanıcı sorgusunu mevzuat açısından analiz eder.
        """

        explicit_law, explicit_article = (
            self._extract_explicit_reference(query)
        )
        effective_law = law_number or explicit_law
        retrieval_limit = (
            max(top_k, 20)
            if explicit_law and explicit_article
            else top_k
        )

        retrieved_sources = (
            self.retriever.search_legal(
                query=query,
                limit=retrieval_limit,
                law_number=effective_law,
            )
        )

        # An explicit query-derived law number is a preference, not a hard
        # failure mode. If that law is absent, preserve semantic retrieval.
        if explicit_law and law_number is None and not retrieved_sources:
            retrieved_sources = self.retriever.search_legal(
                query=query,
                limit=top_k,
                law_number=None,
            )

        if explicit_law and explicit_article:
            retrieved_sources = self._prioritize_explicit_article(
                retrieved_sources,
                law_number=explicit_law,
                article=explicit_article,
            )

        retrieved_sources = retrieved_sources[:top_k]

        if not retrieved_sources:
            return self._empty_result(
                message=(
                    "İlgili mevzuat kaynağı "
                    "bulunamadı."
                )
            )

        # LLM'e bütün Top-K sonuçlarını göndermiyoruz.
        # En alakalı kaynakları seçiyoruz.
        selected_sources = (
            self._select_sources(
                retrieved_sources
            )
        )

        answer, evidence = (
            self._generate_grounded_answer(
                query=query,
                sources=selected_sources,
            )
        )

        retrieval_score = (
            self._calculate_retrieval_score(
                retrieved_sources
            )
        )

        return {
            "answer": answer,

            # Gerçekten doğrulanan evidence parçaları
            "evidence": evidence,

            # LLM'e verilen kaynaklar
            "sources": selected_sources,

            # Retriever'ın ilk Top-K sonuçları
            "retrieved_sources": (
                retrieved_sources
            ),

            # Hukuki doğruluk skoru DEĞİLDİR.
            "retrieval_score": retrieval_score,

            "confidence_type": (
                "retrieval_score"
            ),

            "llm": {
                "provider": (
                    self.llm
                    .get_provider_name()
                ),
                "model": (
                    self.llm
                    .get_model_name()
                ),
            },
        }

    def _generate_grounded_answer(
        self,
        query: str,
        sources: list[dict[str, Any]],
    ) -> tuple[
        str,
        list[dict[str, str]],
    ]:
        """
        LLM'den yalnızca kaynakta bulunan ifadeleri
        çıkarmasını ister.

        Ardından Python tarafında bu ifadelerin
        gerçekten kaynakta bulunup bulunmadığını kontrol eder.
        """

        context = self._build_context(
            sources
        )

        system_prompt = """
Sen kaynak-temelli bir Türkçe mevzuat bilgi çıkarım sistemisin.

KURALLAR:
1. Yalnızca verilen kaynakları kullan.
2. Kaynaklarda bulunmayan hukuki yorum, bilgi veya sonuç üretme.
3. Evidence kısa olmalı ve ilgili kaynak metninde birebir doğrulanabilmelidir.
4. Kaynaklar soruyu doğrudan cevaplamıyorsa tahmin etme ve {"items":[]} döndür.
5. Yalnızca şu JSON şemasını döndür; JSON dışında açıklama yazma:
   {"items":[{"evidence":"kaynakta geçen kısa ifade","source":"K1"}]}

ÖRNEK 1 — kaynak cevaplıyor:
Soru: Başvuru kaç gün içinde cevaplanır?
K1 Metin: Başvurunun sonucu en geç otuz gün içinde bildirilir.
Çıktı: {"items":[{"evidence":"Başvurunun sonucu en geç otuz gün içinde bildirilir.","source":"K1"}]}

ÖRNEK 2 — kaynak cevaplamıyor:
Soru: Başvuru ücreti ne kadardır?
K1 Metin: Başvurunun sonucu yazılı olarak bildirilir.
Çıktı: {"items":[]}
"""

        user_prompt = f"""
SORU:
{query}

MEVZUAT KAYNAKLARI:
{context}

Soruyu doğrudan cevaplayan kısa kaynak ifadelerini JSON şemasında çıkar.
"""

        raw_response = self.llm.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=450,
            json_mode=True,
        )

        try:
            parsed = json.loads(
                raw_response
            )
        except json.JSONDecodeError:
            return (
                "Model yapılandırılmış mevzuat "
                "çıktısı üretemedi.",
                [],
            )

        items = parsed.get(
            "items",
            []
        )

        if not isinstance(
            items,
            list,
        ):
            return (
                "Model geçerli bir mevzuat "
                "kanıt listesi üretemedi.",
                [],
            )

        validated_items = (
            self._validate_evidence_items(
                items=items,
                sources=sources,
                query=query,
            )
        )

        if not validated_items:
            return (
                "Sağlanan kaynaklarda soruya ilişkin "
                "doğrulanabilir bir bilgi çıkarılamadı.",
                [],
            )

        answer = (
            self._render_evidence_answer(
                validated_items,
                sources,
            )
        )

        return (
            answer,
            validated_items,
        )

    @staticmethod
    def _select_sources(
        sources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        LLM'e gönderilecek kaynakları seçer.

        Belirgin bir Top-1 sonucu varsa yalnızca
        onu gönderir.

        Böylece alakasız maddelerin modele karışması
        azaltılır.
        """

        if not sources:
            return []

        if len(sources) == 1:
            return sources

        top_score = float(
            sources[0].get(
                "score",
                0.0,
            )
        )

        second_score = float(
            sources[1].get(
                "score",
                0.0,
            )
        )

        score_gap = (
            top_score
            - second_score
        )

        # Güçlü ve belirgin Top-1.
        if (
            top_score >= 0.72
            and score_gap >= 0.03
        ):
            return [
                sources[0]
            ]

        # Aksi halde Top-3 arasından
        # en iyi sonuca yakın olanları seç.
        selected = []

        for source in sources[:3]:
            score = float(
                source.get(
                    "score",
                    0.0,
                )
            )

            if score >= (
                top_score - 0.08
            ):
                selected.append(
                    source
                )

        if not selected:
            return [
                sources[0]
            ]

        return selected

    @staticmethod
    def _build_context(
        sources: list[dict[str, Any]],
    ) -> str:
        """
        Retriever sonuçlarını LLM context'ine dönüştürür.
        """

        context_parts = []

        for index, source in enumerate(
            sources,
            start=1,
        ):
            source_id = f"K{index}"

            title = source.get("title") or source.get("source")
            source_type = source.get("source_type")
            law_number = source.get("law_number")
            article = source.get("madde_no") or source.get("article")

            text = (
                source.get("text")
                or ""
            )

            metadata_lines = [f"[{source_id}]"]
            if title:
                metadata_lines.append(f"Kaynak Adı: {title}")
            if source_type:
                metadata_lines.append(f"Kaynak Türü: {source_type}")
            if law_number:
                metadata_lines.append(f"Kanun/Yönetmelik No: {law_number}")
            if article:
                metadata_lines.append(f"Madde: {article}")
            metadata_lines.extend(("Metin:", str(text)))
            context_parts.append("\n".join(metadata_lines))

        return "\n\n---\n\n".join(
            context_parts
        )

    def _validate_evidence_items(
        self,
        items: list[dict[str, Any]],
        sources: list[dict[str, Any]],
        query: str = "",
    ) -> list[dict[str, str]]:
        """
        LLM tarafından çıkarılan evidence gerçekten
        belirtilen kaynak içinde geçiyor mu kontrol eder.

        Kaynakta olmayan ifadeler otomatik olarak elenir.
        """

        source_map: dict[
            str,
            str,
        ] = {}

        for index, source in enumerate(
            sources,
            start=1,
        ):
            source_id = f"K{index}"

            source_map[source_id] = str(
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

            if not normalized_evidence:
                continue

            # Kritik güvenlik kontrolü:
            # Evidence kaynakta birebir bulunmuyorsa
            # cevaba alınmaz.
            if (
                normalized_evidence
                not in normalized_source
            ):
                continue

            # A verbatim sentence may still be irrelevant to the question.
            # Require a deterministic lexical link without another model call.
            if query and not self._is_query_relevant(
                query=query,
                source_text=source_map[source_id],
            ):
                continue

            dedup_key = (
                source_id,
                normalized_evidence,
            )

            if dedup_key in seen:
                continue

            seen.add(
                dedup_key
            )

            validated.append(
                {
                    "evidence": evidence,
                    "source": source_id,
                }
            )

        return validated

    @classmethod
    def _is_query_relevant(
        cls,
        query: str,
        source_text: str,
    ) -> bool:
        query_tokens = cls._informative_tokens(query)
        if not query_tokens:
            return False

        source_tokens = cls._informative_tokens(source_text)
        shared_count = len(query_tokens & source_tokens)

        # One concept is sufficient for a terse query. Multi-concept queries
        # require two anchors so an incidental single word cannot pass.
        required_shared = 1 if len(query_tokens) <= 2 else 2
        return shared_count >= required_shared

    @staticmethod
    def _informative_tokens(text: str) -> set[str]:
        normalized = unicodedata.normalize("NFKC", str(text)).casefold()
        normalized = normalized.replace("i\u0307", "i")
        normalized = normalized.translate(str.maketrans({
            "\u00e2": "a", "\u00ee": "i", "\u00fb": "u",
        }))
        return {
            token
            for token in LEGAL_TOKEN_RE.findall(normalized)
            if len(token) > 1 and token not in QUERY_STOPWORDS
        }

    @classmethod
    def _extract_explicit_reference(
        cls,
        query: str,
    ) -> tuple[str | None, str | None]:
        normalized = cls._reference_text(query)
        law_match = EXPLICIT_LAW_RE.search(normalized)
        if not law_match:
            return None, None

        article = None
        for pattern in (ARTICLE_AFTER_RE, ARTICLE_BEFORE_RE):
            match = pattern.search(normalized)
            if not match:
                continue
            if normalized[max(0, match.start() - 8):match.start()].endswith(
                "gecici "
            ):
                continue
            article = match.group(1)
            break

        return law_match.group(1), article

    @staticmethod
    def _reference_text(text: str) -> str:
        normalized = unicodedata.normalize("NFKC", str(text)).casefold()
        normalized = normalized.replace("i\u0307", "i")
        return normalized.translate(str.maketrans({
            "\u00e7": "c", "\u011f": "g", "\u0131": "i",
            "\u00f6": "o", "\u015f": "s", "\u00fc": "u",
            "\u00e2": "a", "\u00ee": "i", "\u00fb": "u",
        }))

    @staticmethod
    def _prioritize_explicit_article(
        sources: list[dict[str, Any]],
        law_number: str,
        article: str,
    ) -> list[dict[str, Any]]:
        def is_exact(source: dict[str, Any]) -> bool:
            source_law = str(source.get("law_number") or "").strip()
            source_article = str(
                source.get("madde_no") or source.get("article") or ""
            ).strip().casefold()
            return source_law == law_number and source_article == article

        return sorted(sources, key=lambda source: not is_exact(source))

    @staticmethod
    def _normalize_text(
        text: str,
    ) -> str:
        """
        Basit whitespace/case normalizasyonu.

        Evidence doğrulaması için kullanılır.
        """

        return " ".join(
            str(text)
            .lower()
            .split()
        )

    @staticmethod
    def _render_evidence_answer(
        items: list[dict[str, str]],
        sources: list[dict[str, Any]],
    ) -> str:
        """
        Doğrulanmış evidence parçalarından
        kullanıcıya gösterilecek cevabı oluşturur.
        """

        lines = [
            (
                "Mevzuat kaynağında soruyla ilgili "
                "şu bilgiler yer almaktadır:"
            ),
            "",
        ]

        source_map = {
            f"K{index}": source
            for index, source in enumerate(sources, start=1)
        }

        for item in items:
            source_id = item["source"]
            source = source_map.get(source_id, {})
            citation_parts = []
            title = source.get("title") or source.get("source")
            law_number = source.get("law_number")
            article = source.get("madde_no") or source.get("article")
            if title:
                citation_parts.append(str(title))
            if law_number:
                citation_parts.append(str(law_number))
            if article:
                citation_parts.append(f"Madde {article}")
            citation = ", ".join(citation_parts) or source_id
            lines.append(
                f"- {item['evidence']} "
                f"[{citation}]"
            )

        return "\n".join(
            lines
        )

    @staticmethod
    def _calculate_retrieval_score(
        sources: list[dict[str, Any]],
    ) -> float:
        """
        BGE-M3/Qdrant retrieval skorunu döndürür.

        Bu değer hukuki doğruluk olasılığı değildir.
        """

        if not sources:
            return 0.0

        top_score = float(
            sources[0].get(
                "score",
                0.0,
            )
        )

        return round(
            min(
                max(
                    top_score,
                    0.0,
                ),
                1.0,
            ),
            4,
        )

    def _empty_result(
        self,
        message: str,
    ) -> dict[str, Any]:
        return {
            "answer": message,
            "evidence": [],
            "sources": [],
            "retrieved_sources": [],
            "retrieval_score": 0.0,
            "confidence_type": (
                "retrieval_score"
            ),
            "llm": {
                "provider": (
                    self.llm
                    .get_provider_name()
                ),
                "model": (
                    self.llm
                    .get_model_name()
                ),
            },
        }
