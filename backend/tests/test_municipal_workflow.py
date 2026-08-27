"""Focused evidence for the deterministic municipal task workflow."""

from __future__ import annotations

from sqlalchemy import create_engine

from backend.app.auth.dependencies import CurrentUser
from backend.app.auth.principals import DEMO_USERS
from backend.app.cases.engine import CaseEngine
from backend.app.db.models import Base
from backend.app.db.repository import AnalysisRepository
from backend.app.cases.intelligence_bridge import persist_initial_intelligence
from backend.app.intelligence.clarification import ClarificationAgent
from backend.app.intelligence.contracts import CaseIntelligenceContext
from backend.app.intelligence.orchestration import CaseAwareOrchestrator
from backend.app.intelligence.case_writing import CaseWritingService


def _context(text: str, intent: str = "sikayet", *, include_address: bool = True) -> CaseIntelligenceContext:
    fields = {
        "person_name": {"value": "Ayşe Yılmaz"},
        "subject": {"value": text},
        "request": {"value": text},
    }
    if include_address:
        fields["address"] = {"value": "Atatürk Mahallesi 10. Sokak"}
    return CaseIntelligenceContext(
        institution_id="belediye",
        raw_text=text,
        originator={"originator_type": "VATANDAS", "originator_name": "Ayşe Yılmaz"},
        document={"document_type": "dilekce", "process_intent": intent, "subject_excerpt": text},
        extraction={"fields": fields},
    )


def test_municipal_profiles_route_to_department_team_and_role():
    workflow = CaseAwareOrchestrator("belediye")
    expected = [
        ("Yolda çukur ve asfalt bozulması var.", "sikayet", "fen_isleri", "saha_bakim_ekibi", True),
        ("Mahallede çöp toplanmıyor.", "sikayet", "temizlik_isleri", "temizlik_saha_ekibi", True),
        ("İş yerinden gece gürültü geliyor.", "sikayet", "zabita", "denetim_ekibi", True),
        ("İşyeri açma ruhsat başvurusu.", "basvuru", "zabita", "ruhsat_inceleme", False),
    ]
    for text, intent, department, team, field_visit in expected:
        result = workflow.evaluate_first_stage(_context(text, intent))
        assert result["routing"]["recommended_department_code"] == department
        assert result["ai_operation"]["department_code"] == department
        assert result["ai_operation"]["team_code"] == team
        assert result["ai_operation"]["requires_field_visit"] is field_visit

    missing_location = workflow.evaluate_first_stage(
        _context("Kaldırım çöktü.", include_address=False)
    )
    assert missing_location["blocking_missing"] is True
    assert missing_location["clarification"]["missing_field"] == "location"
    assert missing_location["clarification"]["target_type"] == "VATANDAS"


def test_information_request_has_no_generic_address_requirement_and_internal_target():
    result = CaseAwareOrchestrator("belediye").evaluate_first_stage(
        CaseIntelligenceContext(
            institution_id="belediye",
            raw_text="4982 kapsamında bilgi edinme talebidir.",
            originator={"originator_type": "VATANDAS", "originator_name": "Ayşe Yılmaz"},
            document={"document_type": "bilgi_edinme", "process_intent": "bilgi_talebi"},
            extraction={"fields": {
                "person_name": {"value": "Ayşe Yılmaz"},
                "subject": {"value": "Bilgi edinme"},
                "request": {"value": "Bilgi talep ediyorum"},
            }},
        )
    )
    assert result["blocking_missing"] is False
    assert result["missing_fields"]["requirement_source"] == "process_profile:bilgi_edinme_basvurusu"
    assert "address" not in result["missing_fields"]["required_fields"]
    assert result["ai_operation"]["department_code"] == "yazi_isleri"

    target = ClarificationAgent().preview(
        missing_fields={"blocking_fields": ["sender_unit"], "missing_field_details": [{"field": "sender_unit", "blocking": True}]},
        originator={"originator_type": "KURUM_ICI", "originator_name": "Yazı İşleri"},
        document={"source_department_code": "yazi_isleri"},
    )
    assert target["target_type"] == "INTERNAL_DEPARTMENT"
    assert target["target_department"] == "yazi_isleri"
    assert target["recommended_action"] == "INTERNAL_INFORMATION_REQUESTED"


def _principal(user_key: str) -> CurrentUser:
    user = DEMO_USERS[user_key]
    return CurrentUser(
        id=user.id, name=user.name, role=user.role,
        institution_id=user.institution_id, department_code=user.department_code,
        user_key=user.user_key,
    )


def test_case_task_is_pending_until_department_confirms_assignment_and_has_timeline():
    db = create_engine("sqlite://")
    from backend.app.db import case_models  # noqa: F401 - register Case metadata

    Base.metadata.create_all(db)
    engine = CaseEngine(db)
    engine.bootstrap()
    registry = _principal("ayse_kaya")
    fen = _principal("mehmet_demir")
    case = engine.create_case(registry, {
        "source_type": "VATANDAS", "source_channel": "WEB_FORM",
        "originator_type": "VATANDAS", "originator_name": "Ayşe Yılmaz", "confirmed": True,
    })
    case = engine.mark_analysis_started(case["id"], registry, expected_version=case["version"], confirmed=True)
    case = engine.mark_analysis_completed(case["id"], registry, expected_version=case["version"], confirmed=True)
    case = engine.accept_review(registry, case["id"], case["version"], True)
    routed = engine.route_case(
        registry, case["id"], department_code="fen_isleri", expected_version=case["version"], confirmed=True,
        reason="Yol bakımı", routing_snapshot={"ai_operation": {
            "task_type": "YOL_BAKIM_INCELEME", "department_code": "fen_isleri",
            "team_code": "saha_bakim_ekibi", "recommended_role": "SAHA_EKIBI",
        }},
    )
    task = routed["task"]
    assert task["status"] == "ASSIGNMENT_PENDING"
    assert task["assigned_user_id"] is None
    assigned = engine.assign_task(
        fen, case["id"], task["id"], assigned_user_id=fen.id,
        expected_version=routed["version"], confirmed=True,
    )
    assert assigned["task"]["status"] == "ASSIGNED"
    progressed = engine.update_task_status(
        fen, case["id"], task["id"], status="IN_PROGRESS",
        expected_version=assigned["case"]["version"], confirmed=True,
    )
    done = engine.update_task_status(
        fen, case["id"], task["id"], status="DONE",
        expected_version=progressed["case"]["version"], confirmed=True,
    )
    aggregate = engine.get_case_aggregate(fen, case["id"])
    assert aggregate["tasks"][0]["status"] == "DONE"
    assert any(event["event_type"] == "CASE_ROUTED" for event in aggregate["timeline"])
    assert any(event["event_type"] == "TASK_ASSIGNED" for event in aggregate["timeline"])
    assert all(item["id"] != case["id"] for item in engine.list_inbox(registry)["items"])
    assert any(item["id"] == case["id"] for item in engine.list_inbox(fen)["items"])


def test_internal_information_request_is_recorded_on_case():
    db = create_engine("sqlite://")
    from backend.app.db import case_models  # noqa: F401

    Base.metadata.create_all(db)
    engine = CaseEngine(db)
    engine.bootstrap()
    registry = _principal("ayse_kaya")
    case = engine.create_case(registry, {
        "source_type": "KURUM_ICI", "source_channel": "KURUM_ICI",
        "originator_type": "KURUM_ICI", "originator_name": "Yazı İşleri", "confirmed": True,
    })
    created = engine.create_information_request(
        registry, case["id"], requested_fields=["attachment"], reason="Ek bulunamadı.",
        expected_version=case["version"], confirmed=True, target_department="yazi_isleri",
    )
    assert created["information_request"]["target_type"] == "INTERNAL_DEPARTMENT"
    assert created["information_request"]["target_department"] == "yazi_isleri"
    aggregate = engine.get_case_aggregate(registry, case["id"])
    assert aggregate["information_requests"][0]["recommended_action"] == "INTERNAL_INFORMATION_REQUESTED"
    assert any(event["event_type"] == "INTERNAL_INFORMATION_REQUESTED" for event in aggregate["timeline"])


def test_intake_draft_exposes_recipient_kind_before_generation():
    service = CaseWritingService()
    assert service.draft_for_intake(originator={"originator_type": "VATANDAS"})["recipient_kind"] == "VATANDAS"
    assert service.draft_for_intake(originator={"originator_type": "DIS_KURUM"})["recipient_kind"] == "KURUM"
    assert service.draft_for_intake(originator={"originator_type": "KURUM_ICI"})["recipient_kind"] == "INTERNAL_UNIT"


def test_case_aggregate_exposes_ai_operation_priority_and_deadline_risk():
    db = create_engine("sqlite://")
    from backend.app.db import case_models  # noqa: F401

    Base.metadata.create_all(db)
    engine = CaseEngine(db)
    engine.bootstrap()
    registry = _principal("ayse_kaya")
    analysis_id = "municipal-priority-analysis"
    state = {
        "analysis_id": analysis_id,
        "institution_id": "belediye",
        "raw_text": "Acil olarak yoldaki çukurun onarılmasını istiyorum.",
        "document": {"document_type": "dilekce", "process_intent": "sikayet", "subject_excerpt": "Yol çukuru"},
        "extraction": {"fields": {
            "person_name": {"value": "Ayşe Yılmaz"}, "subject": {"value": "Yol çukuru"},
            "request": {"value": "Acil onarım"}, "address": {"value": "Atatürk Mahallesi"},
        }},
        "legal_analysis": {}, "missing_fields": {}, "summary": {}, "routing": {},
    }
    AnalysisRepository(engine=db).save_analysis(analysis_id, state)
    case = engine.create_case(registry, {
        "source_type": "VATANDAS", "source_channel": "WEB_FORM", "originator_type": "VATANDAS",
        "originator_name": "Ayşe Yılmaz", "analysis_id": analysis_id, "confirmed": True,
    })
    persist_initial_intelligence(engine=engine, user=registry, case=case, analysis_id=analysis_id, state=state)
    aggregate = engine.get_case_aggregate(registry, case["id"])
    assert aggregate["ai_operation"]["department_code"] == "fen_isleri"
    assert aggregate["priority_assessment"]["priority"] == "HIGH"
    assert aggregate["priority_assessment"]["priority_reason"]
    assert aggregate["case"]["priority"] == "HIGH"
    assert aggregate["deadline"]["risk_level"] in {"UNKNOWN", "NORMAL"}
