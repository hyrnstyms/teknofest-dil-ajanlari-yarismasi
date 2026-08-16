import pytest
from unittest.mock import MagicMock
from backend.app.agents.summary_agent import SummaryAgent
from backend.app.llm.base import LLMClient

@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=LLMClient)
    llm.get_provider_name.return_value = "mock"
    llm.get_model_name.return_value = "mock"
    # Varsayılan olarak geçerli bir JSON döndürsün
    llm.chat.return_value = '{"short_summary": "LLM tarafından üretilen kısa özet."}'
    return llm

@pytest.fixture
def agent(mock_llm):
    return SummaryAgent(llm=mock_llm)

def test_summary_normal_dilekce(agent):
    # 1. normal dilekçe + applicant + subject + request (deterministic summary generated)
    extracted = {
        "person_name": {"value": "Ahmet Yılmaz"},
        "subject": {"value": "Bilgi talebi"},
        "request": {"value": "belgelerin onaylı örneğini talep ediyorum"}
    }
    res = agent.summarize("Ham metin...", {}, extracted)
    assert res["structured_summary"]["applicant"] == "Ahmet Yılmaz"
    assert res["structured_summary"]["subject"] == "Bilgi talebi"
    assert "Ahmet Yılmaz" in res["short_summary"]
    assert "belgelerin onaylı örneğini talep ediyorum" in res["short_summary"]
    # Deterministic succeeded, LLM should not be called
    agent.llm.chat.assert_not_called()

def test_summary_empty_input(agent):
    # 3. empty input
    res = agent.summarize("", {}, {})
    assert res["short_summary"] is None
    assert any("yeterli bilgi bulunamadı" in w for w in res["warnings"])
    
def test_summary_llm_offline_fallback():
    # 4. LLM offline fallback
    agent = SummaryAgent(llm=None)
    res = agent.summarize("Sadece ham metin var, çıkarılmış alan yok.", {}, {})
    assert res["short_summary"] is None
    assert any("yeterli bilgi bulunamadı" in w for w in res["warnings"])

def test_summary_llm_semantic_fallback(agent):
    # If deterministic fails but text is present, LLM should be called
    res = agent.summarize("Benim adım Mehmet. Bu bir bilgi edinme talebidir.", {}, {})
    assert res["short_summary"] == "LLM tarafından üretilen kısa özet."
    agent.llm.chat.assert_called_once()
