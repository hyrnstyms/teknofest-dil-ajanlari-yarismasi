import pytest
from unittest.mock import MagicMock
from backend.app.graph.workflow import KamuaiWorkflow
from backend.app.graph.state import DocumentState
from backend.app.llm.base import LLMClient

@pytest.fixture
def mock_workflow(monkeypatch):
    class FakeRetriever:
        def search_legal(self, *args, **kwargs):
            return []

    monkeypatch.setattr(
        "backend.app.agents.legal_agent.Retriever",
        FakeRetriever,
    )
    monkeypatch.setattr(
        "backend.app.agents.writing_agent.Retriever",
        FakeRetriever,
    )

    fast_llm = MagicMock(spec=LLMClient)
    fast_llm.chat.return_value = "{}"
    fast_llm.get_provider_name.return_value = "evren"
    fast_llm.get_model_name.return_value = "llm-fast"

    legal_llm = MagicMock(spec=LLMClient)
    legal_llm.chat.return_value = '{"items":[]}'
    legal_llm.get_provider_name.return_value = "evren"
    legal_llm.get_model_name.return_value = "llm-large"

    calls = []

    def fake_create_llm_client(agent_name):
        calls.append(agent_name)
        if agent_name == "legal_agent":
            return legal_llm
        return fast_llm

    monkeypatch.setattr(
        "backend.app.graph.workflow.create_llm_client",
        fake_create_llm_client,
    )
    wf = KamuaiWorkflow()
    wf._test_llm_factory_calls = calls
    wf._test_fast_llm = fast_llm
    wf._test_legal_llm = legal_llm
    return wf

def test_workflow_initialization(mock_workflow):
    assert mock_workflow.graph is not None


def test_workflow_assigns_fast_and_large_evren_clients(mock_workflow):
    assert mock_workflow._test_llm_factory_calls == [
        "document_agent",
        "legal_agent",
    ]
    assert mock_workflow.doc_agent.llm is mock_workflow._test_fast_llm
    assert mock_workflow.extract_agent.llm is mock_workflow._test_fast_llm
    assert mock_workflow.summary_agent.llm is mock_workflow._test_fast_llm
    assert mock_workflow.writing_agent.llm is mock_workflow._test_fast_llm
    assert mock_workflow.legal_agent.llm is mock_workflow._test_legal_llm
    assert not hasattr(mock_workflow.quality_agent, "llm")

def test_workflow_end_to_end_empty_text(mock_workflow):
    # This will test the error isolation and degradation
    res = mock_workflow.run("")
    assert "node_timings" in res
    assert "document_agent" in res["node_timings"]
    assert "extraction_agent" in res["node_timings"]
    assert res["quality"]["status"] in ["warning", "fail"]
    assert res["human_review"]["required"] is True

def test_workflow_mehmet_kaya_end_to_end(mock_workflow):
    text = """
    T.C. ÖRNEK KAMU KURUMU Bilgi Edinme Birimine
    Konu: Proje Harcamaları Hakkında Bilgi Talebi
    Başvuru Sahibi: Mehmet Kaya
    T.C. Kimlik No: 10000000146
    Telefon: 0532 111 22 33
    E-posta: mehmet.kaya@example.com
    Kurumunuz tarafından yürütülen Akıllı Şehir Projesi hakkında bilgi edinmek istiyorum.
    """
    res = mock_workflow.run(text)
    
    assert "node_timings" in res
    assert "document" in res
    assert "extraction" in res
    
    # Check timings
    assert "document_agent" in res["node_timings"]
    assert "quality_agent" in res["node_timings"]
    
    # Final state schema
    assert "raw_text" in res
    assert "quality" in res
    assert "human_review" in res


def test_node_writing_uses_applicant_and_verified_legal_context():
    captured = {}

    class CapturingWritingAgent:
        def draft(self, **kwargs):
            captured.update(kwargs)
            return {"draft": {"body": "İnceleme değerlendirilecektir."}}

    workflow = KamuaiWorkflow.__new__(KamuaiWorkflow)
    workflow.writing_agent = CapturingWritingAgent()
    result = workflow.node_writing(DocumentState(
        document={"process_intent": "cevap"},
        extraction={"fields": {
            "person_name": {"value": "Polat Madencilik adına Pelin Sönmez"},
            "recipient": {"value": "Örenli İlçe Kaymakamlığı"},
        }},
        legal_analysis={
            "evidence": [{"evidence": "İhale işlemleri bu Kanuna tabidir.", "source": "K1"}],
            "sources": [{"law_number": "4734", "madde_no": "2", "title": "Kamu İhale Kanunu"}],
        },
        missing_fields={"missing_fields": []},
        summary={"short_summary": "Akaryakıt ihalesine ilişkin itiraz."},
        routing={"recommended_unit": "Yazı İşleri Müdürlüğü"},
    ))

    assert result["node_timings"]["writing_agent"]["status"] == "completed"
    assert captured["recipient"] == "Polat Madencilik adına Pelin Sönmez"
    assert "4734 sayılı Kanun" in captured["legal_context"]
    assert captured["state"]["legal_analysis"]["evidence"]
    assert "4734 sayılı Kanun" in captured["state"]["legal_context"]

def test_node_legal_keeps_explicit_document_law_reference():
    captured = {}

    class CapturingLegalAgent:
        def analyze(self, **kwargs):
            captured.update(kwargs)
            return {"evidence": [], "sources": []}

    workflow = KamuaiWorkflow.__new__(KamuaiWorkflow)
    workflow.legal_agent = CapturingLegalAgent()
    result = workflow.node_legal(DocumentState(
        raw_text="4734 sayılı Kamu İhale Kanunu uyarınca inceleme talep ediyorum.",
        document={
            "process_intent": "basvuru",
            "subject_excerpt": "Akaryakıt ihalesi itirazı",
            "request_excerpt": "İnceleme talep ediyorum",
        },
    ))

    assert result["node_timings"]["legal_agent"]["status"] == "completed"
    assert "4734 sayılı Kanun" in captured["query"]
    assert captured["strict_explicit_law"] is True
