from unittest.mock import MagicMock

import pytest

from backend.app.agents.summary_agent import SummaryAgent
from backend.app.graph.state import DocumentState
from backend.app.graph.workflow import KamuaiWorkflow
from backend.app.llm.base import LLMClient


@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=LLMClient)
    llm.get_provider_name.return_value = "mock"
    llm.get_model_name.return_value = "mock-model"
    return llm


def test_normal_dilekce_uses_deterministic_summary(mock_llm):
    agent = SummaryAgent(llm=mock_llm)
    extracted = {
        "person_name": {"value": "Ahmet Yılmaz"},
        "subject": {"value": "Bilgi talebi"},
        "request": {"value": "belgelerin onaylı örneğini talep ediyorum"},
    }

    workflow = KamuaiWorkflow.__new__(KamuaiWorkflow)
    workflow.summary_agent = agent
    node_result = workflow.node_summary(DocumentState(
        raw_text="Ham dilekçe metni",
        document={},
        extraction={"fields": extracted},
    ))
    result = node_result["summary"]

    assert node_result["node_timings"]["summary_agent"]["status"] == "completed"
    assert result["short_summary"] == (
        "Ahmet Yılmaz tarafından Bilgi talebi konusunda başvuru yapılmıştır. "
        "Başvuruda belgelerin onaylı örneğini talep ediyorum talep edilmektedir."
    )
    assert result["warnings"] == []
    assert result["needs_human_review"] is False
    assert result["llm"] == {
        "provider": "mock",
        "model": "mock-model",
        "attempted": False,
        "status": "not_required",
        "error": None,
    }
    mock_llm.chat.assert_not_called()


def test_long_official_document_accepts_code_fenced_json(mock_llm):
    mock_llm.chat.return_value = (
        "```json\n"
        '{"short_summary": "Kurum, raporun incelenerek görüş bildirilmesini istemektedir."}'
        "\n```"
    )
    agent = SummaryAgent(llm=mock_llm)
    raw_text = (
        "T.C. ÖRENLİ İLÇE KAYMAKAMLIĞI\n"
        "Konu: Faaliyet Raporu\n"
        "Ekli faaliyet raporunun incelenerek görüş bildirilmesi hususunda "
        "gereğini arz ederim. " * 20
    )

    result = agent.summarize(raw_text, {"document_type": "resmi_yazi"}, {})

    assert result["short_summary"] == (
        "Kurum, raporun incelenerek görüş bildirilmesini istemektedir."
    )
    assert result["summary_mode"] == "llm_grounded"
    assert result["needs_human_review"] is True
    assert result["llm"]["status"] == "success"
    assert result["llm"]["attempted"] is True
    call_kwargs = mock_llm.chat.call_args.kwargs
    assert set(call_kwargs) == {
        "system_prompt",
        "user_prompt",
        "temperature",
        "max_tokens",
        "json_mode",
    }
    assert call_kwargs["json_mode"] is True


def test_short_text_empty_llm_response_requires_review(mock_llm):
    mock_llm.chat.return_value = ""
    agent = SummaryAgent(llm=mock_llm)

    result = agent.summarize("Kısa bildirim.", {}, {})

    assert result["short_summary"] is None
    assert result["summary_mode"] == "unavailable"
    assert any("boş yanıt" in warning for warning in result["warnings"])
    assert result["needs_human_review"] is True
    assert result["llm"]["status"] == "empty_response"
    assert result["llm"]["error"] == "LLM boş yanıt döndürdü."


def test_invalid_json_is_reported(mock_llm):
    mock_llm.chat.return_value = "Özet üretildi ancak JSON formatında değil."
    agent = SummaryAgent(llm=mock_llm)

    result = agent.summarize("Başvuru metni", {}, {})

    assert result["short_summary"] is None
    assert any("geçerli JSON" in warning for warning in result["warnings"])
    assert result["needs_human_review"] is True
    assert result["llm"]["status"] == "invalid_json"
    assert result["llm"]["attempted"] is True


def test_llm_exception_is_reported_without_crashing(mock_llm):
    mock_llm.chat.side_effect = ConnectionError("Ollama bağlantısı kurulamadı")
    agent = SummaryAgent(llm=mock_llm)

    result = agent.summarize("Yalnız ham metin mevcut.", {}, {})

    assert result["short_summary"] is None
    assert any("Ollama bağlantısı kurulamadı" in warning for warning in result["warnings"])
    assert result["needs_human_review"] is True
    assert result["llm"]["status"] == "error"
    assert "ConnectionError" in result["llm"]["error"]
