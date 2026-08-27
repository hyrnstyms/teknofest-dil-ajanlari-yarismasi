import pytest
from backend.app.intelligence.orchestration import CaseAwareOrchestrator
from backend.app.intelligence.contracts import CaseIntelligenceContext

@pytest.fixture
def orchestrator():
    return CaseAwareOrchestrator(institution="belediye")

def test_orchestration_complete_belediye_request(orchestrator, monkeypatch):
    # Mocking agents to avoid real LLM calls
    monkeypatch.setattr(orchestrator.missing_field_agent, "check_missing_fields", lambda **kwargs: {"missing_fields": [], "has_blocking_missing": False})
    monkeypatch.setattr(orchestrator.clarification_agent, "preview", lambda **kwargs: {"needs_clarification": False, "blocking": False})
    monkeypatch.setattr(orchestrator.routing_agent, "route", lambda *args, **kwargs: {"recommended_unit": "Fen İşleri Müdürlüğü", "recommended_department_code": "fen_isleri", "score": 0.82})
    monkeypatch.setattr(orchestrator.writing, "draft_for_intake", lambda **kwargs: {"draft_type": "INTERIM_INFORMATION"})
    monkeypatch.setattr(orchestrator.deadline_service, "evaluate", lambda **kwargs: {"applicable": False})
    monkeypatch.setattr(orchestrator.priority_agent, "assess", lambda *args, **kwargs: {"level": "normal"})

    ctx = CaseIntelligenceContext(
        institution_id="belediye",
        raw_text="Yol bakımı istiyorum.",
        document={"document_type": "dilekce", "process_intent": "talep"},
        summary={"short_summary": "Yol bakım talebi"}
    )
    
    result = orchestrator.evaluate_first_stage(ctx)
    
    assert result["wait_for"] == "WAIT_FOR_HUMAN_ROUTING_CONFIRMATION"
    assert result["recommended_workflow_status"] == "WAITING_INITIAL_REVIEW"
    assert result["blocking_missing"] is False
    assert result["routing"]["recommended_department_code"] == "fen_isleri"
    assert result["routing"]["score"] == 0.82
    assert result["routing"]["assigned"] is False
    assert "accuracy" not in result["routing"]
    assert "accuracy_percentage" not in result["routing"]
    assert result["official_response"] is None

def test_orchestration_blocking_missing_location(orchestrator, monkeypatch):
    missing_response = {"missing_fields": ["location"], "has_blocking_missing": True}
    clarification_response = {"needs_clarification": True, "blocking": True, "question": "Nerede?"}
    
    monkeypatch.setattr(orchestrator.missing_field_agent, "check_missing_fields", lambda **kwargs: missing_response)
    monkeypatch.setattr(orchestrator.clarification_agent, "preview", lambda **kwargs: clarification_response)
    monkeypatch.setattr(orchestrator.writing, "draft_for_intake", lambda **kwargs: {"draft_type": "MISSING_INFORMATION_REQUEST"})
    monkeypatch.setattr(orchestrator.deadline_service, "evaluate", lambda **kwargs: {"applicable": False})
    monkeypatch.setattr(orchestrator.priority_agent, "assess", lambda *args, **kwargs: {"level": "normal"})

    ctx = CaseIntelligenceContext(
        institution_id="belediye",
        raw_text="Bakım istiyorum.",
        document={"document_type": "dilekce", "process_intent": "talep"}
    )
    
    result = orchestrator.evaluate_first_stage(ctx)
    
    assert result["wait_for"] == "WAIT_FOR_HUMAN_CITIZEN_INFO"
    assert result["recommended_workflow_status"] == "WAITING_CITIZEN_INFO"
    assert result["blocking_missing"] is True
    assert result["clarification"]["question"] == "Nerede?"
    assert result["routing"] is None
    assert result["official_response"] is None

def test_orchestration_institution_isolation(orchestrator):
    assert orchestrator.institution == "belediye"
    # Ensure profile loaded correctly
    assert orchestrator.institution_profile is not None
