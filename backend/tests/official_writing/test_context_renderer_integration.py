import json

from backend.app.agents.quality_agent import QualityAgent
from backend.app.agents.writing_agent import WritingAgent
from backend.app.graph.state import DocumentState
from backend.app.graph.workflow import KamuaiWorkflow


_UNIT = "Yazı İşleri Müdürlüğü"


class _StubLLM:
    def __init__(self, subject: str, body: str):
        self.subject = subject
        self.body = body

    def chat(self, **kwargs) -> str:
        return json.dumps({"subject": self.subject, "body": self.body})

    def get_provider_name(self) -> str:
        return "stub"

    def get_model_name(self) -> str:
        return "stub"


class _OfficialWritingRetriever:
    def search_official_writing(self, query: str, limit: int = 5) -> list[dict]:
        return [{
            "chunk_id": "official-writing-test",
            "source": "resmi_yazisma_yonetmeligi (checklist uzerinden)",
            "title": "Resmî Yazışma Yönetmeliği",
            "score": 0.9,
            "rag_domain": "official_writing",
            "law_number": "resmi_yazisma_yonetmeligi",
            "madde_no": "16",
            "trusted_source": True,
            "text": "Üst makama arz ederim; alt makama rica ederim.",
        }]


def _field(value):
    return {
        "value": value,
        "evidence": str(value),
        "source": "document",
        "method": "deterministic",
        "validated": True,
    }


def _state(extraction: dict, routing: dict | None = None) -> dict:
    return {
        "extraction": extraction,
        "routing": routing or {
            "recommended_unit": _UNIT,
            "needs_human_review": False,
        },
        "kurum_profili_id": "kaymakamlik_v1",
    }


def _quality(extraction: dict, routing: dict, draft: dict) -> dict:
    return QualityAgent().check_quality(
        document={"document_type": "dilekce", "process_intent": "basvuru"},
        extraction=extraction,
        legal_analysis={"evidence": ["Doğrulanmış test kanıtı"]},
        missing_fields={
            "present_fields": list(extraction.get("fields", {})),
            "missing_fields": [],
            "uncertain_fields": [],
            "needs_human_review": False,
        },
        summary={"short_summary": "Test özeti"},
        routing=routing,
        draft=draft,
    )


def _draft_via_workflow_node(
    agent: WritingAgent,
    extraction: dict,
    routing: dict,
    summary: str,
    requested_action: str,
    process_intent: str = None,
) -> dict:
    workflow = KamuaiWorkflow.__new__(KamuaiWorkflow)
    workflow.writing_agent = agent
    result = workflow.node_writing(DocumentState(
        document={"process_intent": process_intent or requested_action},
        extraction=extraction,
        missing_fields={"missing_fields": []},
        summary={"short_summary": summary},
        routing=routing,
        kurum_profili_id="kaymakamlik_v1",
    ))
    assert result["node_timings"]["writing_agent"]["status"] == "completed"
    return result["draft"]


def test_normal_cevap_yazisi_full_chain():
    extraction = {
        "fields": {
            "person_name": _field("Mehmet Kaya"),
            "subject": _field("Bilgi Edinme Başvurusu"),
            "document_date": _field("2026-08-16"),
            "document_number": _field("2026/145"),
            "address": _field("Örenli"),
        }
    }
    state = _state(extraction)
    agent = WritingAgent(
        llm=_StubLLM(
            "Bilgi Edinme Başvurusu",
            "Başvurunuz incelenmiş ve talep edilen bilgi hazırlanmıştır.",
        ),
        retriever=_OfficialWritingRetriever(),
    )

    draft = _draft_via_workflow_node(
        agent=agent,
        extraction=extraction,
        routing=state["routing"],
        summary="Mehmet Kaya bilgi edinme başvurusunda bulunmuştur.",
        requested_action="Başvuru sahibine cevap verilmesi",
        process_intent="basvuru",
    )
    quality = _quality(extraction, state["routing"], draft)

    assert draft["draft_type"] == "cevap_yazisi"
    assert draft["official_render"]["success"] is True
    assert "16.08.2026 tarihli ve 2026/145 sayılı" in draft["official_rendered_text"]
    assert "Saygılarımla." in draft["official_rendered_text"]
    assert quality["checks"]["official_format"]["status"] == "warning"
    assert quality["requires_human_review"] is True


def test_missing_official_metadata_still_renders_preview():
    extraction = {"fields": {"subject": _field("Süreç Bilgilendirmesi")}}
    state = _state(extraction)
    agent = WritingAgent(
        llm=_StubLLM(
            "Süreç Bilgilendirmesi",
            "İnceleme süreci devam etmektedir.",
        ),
        retriever=_OfficialWritingRetriever(),
    )

    draft = _draft_via_workflow_node(
        agent=agent,
        extraction=extraction,
        routing=state["routing"],
        summary="İnceleme süreci hakkında genel bilgi verilecektir.",
        requested_action="Bilgilendirme yapılması",
        process_intent="bildirim",
    )
    quality = _quality(extraction, state["routing"], draft)

    assert draft["draft_type"] == "bilgilendirme_metni"
    assert draft["official_render"]["success"] is True
    assert {"sayi", "tarih", "muhatap", "imza.ad_soyad", "imza.unvan"}.issubset(
        set(draft["official_render"]["missing_fields"])
    )
    assert "[SAYI]" in draft["official_rendered_text"]
    assert "[MUHATAP]" in draft["official_rendered_text"]
    assert "[AD SOYAD]" in draft["official_rendered_text"]
    assert quality["checks"]["official_writing_format"]["status"] == "warning"
    assert quality["requires_human_review"] is True


def test_ust_yazi_uses_nested_recipient_and_routing_profile():
    extraction = {
        "fields": {
            "recipient": _field("İlçe Sağlık Müdürlüğüne"),
            "subject": _field("Sağlık Raporunun İletilmesi"),
        }
    }
    state = _state(extraction)
    agent = WritingAgent(
        llm=_StubLLM(
            "Sağlık Raporunun İletilmesi",
            "Ekli sağlık raporu gereği için gönderilmektedir.",
        ),
        retriever=_OfficialWritingRetriever(),
    )

    draft = _draft_via_workflow_node(
        agent=agent,
        extraction=extraction,
        routing=state["routing"],
        summary="Ekli sağlık raporu ilgili kuruma iletilecektir.",
        requested_action="Ekli olarak ilgili kuruma iletilmesi",
        process_intent="sevk",
    )
    quality = _quality(extraction, state["routing"], draft)

    assert draft["draft_type"] == "ust_yazi"
    assert draft["official_render"]["success"] is True
    assert "İLÇE SAĞLIK MÜDÜRLÜĞÜNE" in draft["official_rendered_text"]
    assert draft["official_render"]["context"]["tc_baslik"]["birim_adi"] == _UNIT
    assert "routing.recommended_unit" in (
        draft["official_render"]["source_map"]["tc_baslik.birim_adi"]
    )
    assert quality["status"] == "warning"
