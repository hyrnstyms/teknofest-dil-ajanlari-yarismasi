import pytest
from backend.app.agents.quality_agent import QualityAgent

@pytest.fixture
def agent():
    return QualityAgent()

def test_quality_pass(agent):
    res = agent.check_quality(
        document={"document_type": "dilekce"},
        extraction={"fields": {"name": "test"}},
        legal_analysis={"sources": [{"law_number": "123"}]},
        missing_fields={"needs_human_review": False},
        summary={"short_summary": "test"},
        routing={"recommended_unit": "Bilgi Edinme Birimi", "needs_human_review": False},
        draft={"draft_text": "hello"},
        human_review={"required": False}
    )
    assert res["status"] == "pass"

def test_quality_missing_document(agent):
    res = agent.check_quality(
        document={},
        extraction={"fields": {"name": "test"}},
        legal_analysis={"sources": [{"law_number": "123"}]},
        missing_fields={"needs_human_review": False},
        summary={"short_summary": "test"},
        routing={"recommended_unit": "Bilgi Edinme Birimi", "needs_human_review": False},
        draft={"draft_text": "hello"},
        human_review={"required": False}
    )
    assert res["status"] == "fail"
    assert res["checks"]["document_classification"]["status"] == "fail"

def test_quality_invalid_legal_evidence(agent):
    res = agent.check_quality(
        document={"document_type": "dilekce"},
        extraction={"fields": {"name": "test"}},
        legal_analysis={"sources": []},  # empty sources
        missing_fields={"needs_human_review": False},
        summary={"short_summary": "test"},
        routing={"recommended_unit": "Bilgi Edinme Birimi", "needs_human_review": False},
        draft={"draft_text": "hello"},
        human_review={"required": False}
    )
    # WARNING, not fail for legal
    assert res["status"] == "warning"
    assert res["checks"]["legal_evidence"]["status"] == "warning"

def test_quality_routing_unit_not_in_registry(agent):
    res = agent.check_quality(
        document={"document_type": "dilekce"},
        extraction={"fields": {"name": "test"}},
        legal_analysis={"sources": [{"law_number": "123"}]},
        missing_fields={"needs_human_review": False},
        summary={"short_summary": "test"},
        routing={"recommended_unit": "Uydurma Birim", "needs_human_review": False},
        draft={"draft_text": "hello"},
        human_review={"required": False}
    )
    assert res["status"] == "fail"
    assert "bulunamadı" in res["issues"][0]
