import pytest
from backend.app.agents.quality_agent import QualityAgent
from backend.app.official_writing.context_adapter import build_official_writing_context

# Kaymakamlık YAML profilindeki gerçek birim adı (source-of-truth)
_VALID_UNIT = "Yazı İşleri Müdürlüğü"

@pytest.fixture
def agent():
    return QualityAgent()

def test_quality_pass(agent):
    res = agent.check_quality(
        document={"document_type": "dilekce", "process_intent": "basvuru"},
        extraction={"fields": {"name": {"value": "test", "evidence": "text"}}},
        legal_analysis={"evidence": ["valid evidence"]},
        missing_fields={"present_fields": ["name"], "missing_fields": [], "uncertain_fields": [], "needs_human_review": False},
        summary={"short_summary": "test"},
        routing={"recommended_unit": _VALID_UNIT, "needs_human_review": False},
        draft={"draft_generation_mode": "normal"},
        human_review={"required": False}
    )
    assert res["status"] == "pass"
    assert res["decision"] == "continue"

def test_quality_sources_only_warning(agent):
    res = agent.check_quality(
        document={"document_type": "dilekce", "process_intent": "basvuru"},
        extraction={"fields": {"name": {"value": "test", "evidence": "text"}}},
        legal_analysis={"evidence": [], "sources": [{"law_number": "123"}]},
        missing_fields={"present_fields": ["name"], "missing_fields": [], "uncertain_fields": [], "needs_human_review": False},
        summary={"short_summary": "test"},
        routing={"recommended_unit": _VALID_UNIT, "needs_human_review": False},
        draft={"draft_generation_mode": "normal"},
        human_review={"required": False}
    )
    assert res["status"] == "warning"
    assert res["checks"]["legal_evidence"]["status"] == "warning"
    assert res["decision"] == "human_review"


def test_quality_flags_unverified_outcome_claim_for_human_review(agent):
    res = agent.check_quality(
        document={"document_type": "dilekce", "process_intent": "basvuru"},
        extraction={"fields": {"name": {"value": "test", "evidence": "text"}}},
        legal_analysis={"evidence": ["valid evidence"]},
        missing_fields={"present_fields": ["name"], "missing_fields": [], "uncertain_fields": [], "needs_human_review": False},
        summary={"short_summary": "test"},
        routing={"recommended_unit": _VALID_UNIT, "needs_human_review": False},
        draft={
            "draft_generation_mode": "normal",
            "draft": {"body": "Başvurunuz işleme alınmıştır."},
        },
        human_review={"required": False},
    )

    assert res["checks"]["unverified_outcome_claim"]["status"] == "fail"
    assert res["requires_human_review"] is True
    assert res["decision"] == "block"


def test_quality_flags_fake_reference_when_source_fields_are_missing(agent):
    res = agent.check_quality(
        document={"document_type": "dilekce", "process_intent": "basvuru"},
        extraction={"fields": {"name": {"value": "test", "evidence": "text"}}},
        legal_analysis={"evidence": ["valid evidence"]},
        missing_fields={"present_fields": ["name"], "missing_fields": [], "uncertain_fields": [], "needs_human_review": False},
        summary={"short_summary": "test"},
        routing={"recommended_unit": _VALID_UNIT, "needs_human_review": False},
        draft={"draft_generation_mode": "normal", "draft": {"body": "00.00.0000 tarihli ve 00000000-000.00-000000 sayılı başvurunuz incelenmiştir."}},
    )

    assert res["checks"]["unverified_reference_claim"]["status"] == "warning"
    assert res["requires_human_review"] is True

def test_quality_contradictory_missing_statuses(agent):
    res = agent.check_quality(
        document={"document_type": "dilekce", "process_intent": "basvuru"},
        extraction={"fields": {"name": {"value": "test", "evidence": "text"}}},
        legal_analysis={"evidence": ["valid evidence"]},
        missing_fields={
            "present_fields": ["person_name"],
            "missing_fields": ["person_name"],
            "uncertain_fields": [],
            "needs_human_review": False
        },
        summary={"short_summary": "test"},
        routing={"recommended_unit": _VALID_UNIT, "needs_human_review": False},
        draft={"draft_generation_mode": "normal"},
        human_review={"required": False}
    )
    assert res["status"] == "fail"
    assert res["checks"]["missing_fields_consistency"]["status"] == "fail"
    assert res["decision"] == "block"

def test_quality_ambiguous_routing(agent):
    res = agent.check_quality(
        document={"document_type": "dilekce", "process_intent": "basvuru"},
        extraction={"fields": {"name": {"value": "test", "evidence": "text"}}},
        legal_analysis={"evidence": ["valid evidence"]},
        missing_fields={"present_fields": ["name"], "missing_fields": [], "uncertain_fields": [], "needs_human_review": False},
        summary={"short_summary": "test"},
        routing={
            "recommended_unit": _VALID_UNIT,
            "needs_human_review": True,
            "ambiguity_reason": "low_margin"
        },
        draft={"draft_generation_mode": "normal"},
        human_review={"required": False}
    )
    assert res["status"] == "warning"
    assert res["checks"]["routing"]["status"] == "warning"
    assert res["requires_human_review"] is True
    assert res["decision"] == "human_review"

def test_quality_summary_inconsistency(agent):
    res = agent.check_quality(
        document={"document_type": "dilekce", "process_intent": "basvuru"},
        extraction={"fields": {"person_name": {"value": "Ahmet", "evidence": "text"}}},
        legal_analysis={"evidence": ["valid evidence"]},
        missing_fields={"present_fields": ["person_name"], "missing_fields": [], "uncertain_fields": [], "needs_human_review": False},
        summary={"structured_summary": {"applicant": "Mehmet"}},
        routing={"recommended_unit": _VALID_UNIT, "needs_human_review": False},
        draft={"draft_generation_mode": "normal"},
        human_review={"required": False}
    )
    assert res["status"] == "warning"
    assert res["checks"]["summary_consistency"]["status"] == "warning"

def test_quality_blocked_draft(agent):
    res = agent.check_quality(
        document={"document_type": "dilekce", "process_intent": "basvuru"},
        extraction={"fields": {"name": {"value": "test", "evidence": "text"}}},
        legal_analysis={"evidence": ["valid evidence"]},
        missing_fields={"present_fields": ["name"], "missing_fields": [], "uncertain_fields": [], "needs_human_review": False},
        summary={"short_summary": "test"},
        routing={"recommended_unit": _VALID_UNIT, "needs_human_review": False},
        draft={"draft_generation_mode": "blocked_insufficient_context"},
        human_review={"required": False}
    )
    assert res["status"] == "warning"
    assert res["checks"]["draft"]["status"] == "warning"
    assert res["requires_human_review"] is True

def test_quality_official_render_missing(agent):
    res = agent.check_quality(
        document={"document_type": "dilekce", "process_intent": "basvuru"},
        extraction={"fields": {"name": {"value": "test", "evidence": "text"}}},
        legal_analysis={"evidence": ["valid evidence"]},
        missing_fields={"present_fields": ["name"], "missing_fields": [], "uncertain_fields": [], "needs_human_review": False},
        summary={"short_summary": "test"},
        routing={"recommended_unit": _VALID_UNIT, "needs_human_review": False},
        draft={
            "draft_generation_mode": "normal",
            "official_render": {"success": False, "attempted": False}
        },
        human_review={"required": False}
    )
    assert res["status"] == "warning"
    assert res["checks"]["official_format"]["status"] == "warning"
    assert res["requires_human_review"] is True

def test_quality_invalid_unit_fails(agent):
    """Profile dışı birim routing check'i 'fail' vermelidir."""
    res = agent.check_quality(
        document={"document_type": "dilekce", "process_intent": "basvuru"},
        extraction={"fields": {"name": {"value": "test", "evidence": "text"}}},
        legal_analysis={"evidence": ["valid evidence"]},
        missing_fields={"present_fields": ["name"], "missing_fields": [], "uncertain_fields": [], "needs_human_review": False},
        summary={"short_summary": "test"},
        routing={"recommended_unit": "Hayali Birim 999", "needs_human_review": False},
        draft={"draft_generation_mode": "normal"},
        human_review={"required": False}
    )
    assert res["checks"]["routing"]["status"] == "fail"
    assert res["decision"] == "block"

def test_quality_critical_uncertain_is_human_review(agent):
    res = agent.check_quality(
        document={"document_type": "dilekce", "process_intent": "basvuru"},
        extraction={"fields": {"name": {"value": "test", "evidence": "text"}}},
        legal_analysis={"evidence": ["valid evidence"]},
        missing_fields={
            "present_fields": ["person_name"],
            "missing_fields": [],
            "uncertain_fields": ["signature_present"],
            "needs_human_review": False
        },
        summary={"short_summary": "test"},
        routing={"recommended_unit": _VALID_UNIT, "needs_human_review": False},
        draft={"draft_generation_mode": "normal"},
        human_review={"required": False}
    )
    assert res["checks"]["missing_fields"]["status"] == "warning"
    assert res["requires_human_review"] is True
    assert res["decision"] == "human_review"

def test_quality_belediye_isolation():
    belediye_agent = QualityAgent(institution="belediye")
    res = belediye_agent.check_quality(
        document={"document_type": "dilekce", "process_intent": "basvuru"},
        extraction={"fields": {"name": {"value": "test", "evidence": "text"}}},
        legal_analysis={"evidence": ["valid evidence"]},
        missing_fields={"present_fields": ["name"], "missing_fields": [], "uncertain_fields": [], "needs_human_review": False},
        summary={"short_summary": "test"},
        routing={"recommended_unit": "Zabıta Müdürlüğü", "needs_human_review": False},
        draft={"draft_generation_mode": "normal"},
        human_review={"required": False}
    )
    assert res["checks"]["routing"]["status"] == "pass"
    assert res["decision"] == "continue"


def test_quality_rendered_preview_with_placeholders_is_warning(agent):
    extraction = {
        "fields": {
            "subject": {
                "value": "Bilgi Talebi",
                "evidence": "Bilgi Talebi",
                "validated": True,
            },
            "person_name": {
                "value": "Mehmet Kaya",
                "evidence": "Mehmet Kaya",
                "validated": True,
            },
        }
    }
    routing = {"recommended_unit": _VALID_UNIT, "needs_human_review": False}
    adapter_result = build_official_writing_context(
        draft={
            "subject": "Bilgi Talebi",
            "body": "Başvurunuz incelenmiştir.",
            "recipient": "Mehmet Kaya",
            "sender_unit": _VALID_UNIT,
        },
        state={
            "extraction": extraction,
            "routing": routing,
            "kurum_profili_id": "kaymakamlik_v1",
        },
        draft_type="ust_yazi",
    )

    res = agent.check_quality(
        document={"document_type": "dilekce", "process_intent": "basvuru"},
        extraction=extraction,
        legal_analysis={"evidence": ["valid evidence"]},
        missing_fields={
            "present_fields": ["person_name"],
            "missing_fields": [],
            "uncertain_fields": [],
            "needs_human_review": False,
        },
        summary={"short_summary": "test"},
        routing=routing,
        draft={
            "draft_type": "ust_yazi",
            "draft_generation_mode": "llm",
            "requires_human_approval": True,
            "official_render": {
                "attempted": True,
                "success": True,
                "context": adapter_result["context"],
                "missing_fields": adapter_result["missing_required_fields"],
            },
        },
    )

    assert res["status"] == "warning"
    assert res["checks"]["official_format"]["status"] == "warning"
    assert res["checks"]["official_writing_format"]["status"] == "warning"
    assert res["requires_human_review"] is True
