import json
from typing import Any

from backend.app.llm.base import LLMClient
from backend.app.llm.factory import create_llm_client
from backend.app.rag.retriever import Retriever


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
            or create_llm_client()
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

        retrieved_sources = (
            self.retriever.search_legal(
                query=query,
                limit=top_k,
                law_number=law_number,
            )
        )

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
