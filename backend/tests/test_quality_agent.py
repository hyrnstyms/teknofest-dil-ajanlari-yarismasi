import pytest
from backend.app.agents.quality_agent import QualityAgent

@pytest.fixture
def agent():
    return QualityAgent()

def test_quality_pass(agent):
    res = agent.check_quality(
        document={"document_type": "dilekce"},
        extraction={"fields": {"name": {"value": "test", "evidence": "text"}}},
        legal_analysis={"evidence": ["valid evidence"]},
        missing_fields={"needs_human_review": False},
        summary={"short_summary": "test"},
        routing={"recommended_unit": "Bilgi Edinme Birimi", "needs_human_review": False},
        draft={"draft_generation_mode": "normal"},
        human_review={"required": False}
    )
    assert res["status"] == "pass"

def test_quality_sources_only_warning(agent):
    res = agent.check_quality(
        document={"document_type": "dilekce"},
        extraction={"fields": {"name": {"value": "test", "evidence": "text"}}},
        legal_analysis={"evidence": [], "sources": [{"law_number": "123"}]},
        missing_fields={"needs_human_review": False},
        summary={"short_summary": "test"},
        routing={"recommended_unit": "Bilgi Edinme Birimi", "needs_human_review": False},
        draft={"draft_generation_mode": "normal"},
        human_review={"required": False}
    )
    assert res["status"] == "warning"
    assert res["checks"]["legal_evidence"]["status"] == "warning"

def test_quality_contradictory_missing_statuses(agent):
    res = agent.check_quality(
        document={"document_type": "dilekce"},
        extraction={"fields": {"name": {"value": "test", "evidence": "text"}}},
        legal_analysis={"evidence": ["valid evidence"]},
        missing_fields={
            "present_fields": ["person_name"],
            "missing_fields": ["person_name"],
            "uncertain_fields": [],
            "needs_human_review": False
        },
        summary={"short_summary": "test"},
        routing={"recommended_unit": "Bilgi Edinme Birimi", "needs_human_review": False},
        draft={"draft_generation_mode": "normal"},
        human_review={"required": False}
    )
    assert res["status"] == "fail"
    assert res["checks"]["missing_fields_consistency"]["status"] == "fail"

def test_quality_ambiguous_routing(agent):
    res = agent.check_quality(
        document={"document_type": "dilekce"},
        extraction={"fields": {"name": {"value": "test", "evidence": "text"}}},
        legal_analysis={"evidence": ["valid evidence"]},
        missing_fields={"needs_human_review": False},
        summary={"short_summary": "test"},
        routing={
            "recommended_unit": "Bilgi Edinme Birimi", 
            "needs_human_review": True,
            "ambiguity_reason": "low_margin"
        },
        draft={"draft_generation_mode": "normal"},
        human_review={"required": False}
    )
    assert res["status"] == "warning"
    assert res["checks"]["routing"]["status"] == "warning"
    assert res["requires_human_review"] is True

def test_quality_summary_inconsistency(agent):
    res = agent.check_quality(
        document={"document_type": "dilekce"},
        extraction={"fields": {"person_name": {"value": "Ahmet", "evidence": "text"}}},
        legal_analysis={"evidence": ["valid evidence"]},
        missing_fields={"needs_human_review": False},
        summary={"structured_summary": {"applicant": "Mehmet"}},
        routing={"recommended_unit": "Bilgi Edinme Birimi", "needs_human_review": False},
        draft={"draft_generation_mode": "normal"},
        human_review={"required": False}
    )
    assert res["status"] == "warning"
    assert res["checks"]["summary_consistency"]["status"] == "warning"

def test_quality_blocked_draft(agent):
    res = agent.check_quality(
        document={"document_type": "dilekce"},
        extraction={"fields": {"name": {"value": "test", "evidence": "text"}}},
        legal_analysis={"evidence": ["valid evidence"]},
        missing_fields={"needs_human_review": False},
        summary={"short_summary": "test"},
        routing={"recommended_unit": "Bilgi Edinme Birimi", "needs_human_review": False},
        draft={"draft_generation_mode": "blocked_insufficient_context"},
        human_review={"required": False}
    )
    assert res["status"] == "warning"
    assert res["checks"]["draft"]["status"] == "warning"
    assert res["requires_human_review"] is True

def test_quality_official_render_missing(agent):
    res = agent.check_quality(
        document={"document_type": "dilekce"},
        extraction={"fields": {"name": {"value": "test", "evidence": "text"}}},
        legal_analysis={"evidence": ["valid evidence"]},
        missing_fields={"needs_human_review": False},
        summary={"short_summary": "test"},
        routing={"recommended_unit": "Bilgi Edinme Birimi", "needs_human_review": False},
        draft={
            "draft_generation_mode": "normal",
            "official_render": {"success": False, "attempted": False}
        },
        human_review={"required": False}
    )
    assert res["status"] == "warning"
    assert res["checks"]["official_format"]["status"] == "warning"
    assert res["requires_human_review"] is True

