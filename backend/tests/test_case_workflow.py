"""Acceptance tests for the frozen Case workflow contract."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.auth.tokens import issue_token
from backend.app.cases.runtime import get_case_engine
from backend.app.db.repository import AnalysisRepository
from backend.app.db.case_models import CaseUser
from backend.app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_case_domain():
    engine = get_case_engine()
    engine.clear_domain()
    yield
    engine.clear_domain()


def _login(user_key: str) -> dict[str, str]:
    response = client.post("/api/auth/demo-login", json={"user_key": user_key})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _custom_user_headers(
    *,
    institution_id: str,
    department_code: str,
    role: str = "BIRIM_PERSONELI",
) -> dict[str, str]:
    user_id = str(uuid.uuid4())
    user_key = f"test_{uuid.uuid4().hex}"
    engine = get_case_engine()
    with engine.session_factory.begin() as session:
        session.add(
            CaseUser(
                id=user_id,
                user_key=user_key,
                name="Test Personeli",
                role=role,
                institution_id=institution_id,
                department_code=department_code,
                is_active=True,
            )
        )
    return {"Authorization": f"Bearer {issue_token(user_id, user_key)}"}


def _create_case(headers: dict[str, str], *, name: str = "Ali Yılmaz") -> dict:
    response = client.post(
        "/api/cases",
        headers=headers,
        json={
            "source_type": "VATANDAS",
            "source_channel": "WEB_FORM",
            "originator_type": "VATANDAS",
            "originator_name": name,
            "originator_email": "ali@example.test",
            "originator_phone": "+905550000000",
            "confirmed": True,
            # These fields are deliberately ignored; authority comes from token.
            "role": "BIRIM_PERSONELI",
            "institution_id": "kaymakamlik",
            "department_code": "fen_isleri",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _advance_to_ready(case: dict, ayse: dict[str, str]) -> dict:
    response = client.post(
        f"/api/cases/{case['id']}/analysis/start",
        headers=ayse,
        json={"expected_version": case["version"], "confirmed": True},
    )
    assert response.status_code == 200, response.text
    response = client.post(
        f"/api/cases/{case['id']}/analysis/complete",
        headers=ayse,
        json={"expected_version": response.json()["version"], "confirmed": True},
    )
    assert response.status_code == 200, response.text
    response = client.post(
        f"/api/cases/{case['id']}/accept-review",
        headers=ayse,
        json={"expected_version": response.json()["version"], "confirmed": True},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _route_to_fen(case: dict, ayse: dict[str, str]) -> dict:
    response = client.post(
        f"/api/cases/{case['id']}/route",
        headers=ayse,
        json={
            "target_department_code": "fen_isleri",
            "expected_version": case["version"],
            "confirmed": True,
            "reason": "Yol bakım talebi",
            "routing_snapshot": {"recommended_department_code": "fen_isleri"},
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_related_documents_receive_same_zincir_id():
    ayse = _login("ayse_kaya")
    engine = get_case_engine()
    repository = AnalysisRepository(engine=engine.engine)
    received_at = datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)

    def create_with_subject(analysis_id: str, subject: str, received: datetime) -> dict:
        repository.save_analysis(
            analysis_id,
            {
                "analysis_id": analysis_id,
                "institution_id": "belediye",
                "document": {"subject_excerpt": subject},
                "extraction": {"fields": {"subject": {"value": subject}}},
            },
        )
        response = client.post(
            "/api/cases",
            headers=ayse,
            json={
                "source_type": "VATANDAS",
                "source_channel": "WEB_FORM",
                "originator_type": "VATANDAS",
                "originator_name": "Ali Yilmaz",
                "analysis_id": analysis_id,
                "received_at": received.isoformat(),
                "confirmed": True,
            },
        )
        assert response.status_code == 200, response.text
        return response.json()

    first = create_with_subject(
        "chain-analysis-1", "Cinar Mahallesi yol bakim talebi", received_at
    )
    second = create_with_subject(
        "chain-analysis-2",
        "Cinar Mahallesi icin yol bakim basvurusu",
        received_at + timedelta(days=20),
    )

    refreshed_first = client.get(f"/api/cases/{first['id']}", headers=ayse).json()["case"]
    assert second["zincir_id"]
    assert refreshed_first["zincir_id"] == second["zincir_id"]

def test_demo_auth_resolves_backend_current_user():
    ayse = _login("ayse_kaya")

    response = client.get("/api/auth/me", headers=ayse)

    assert response.status_code == 200
    assert response.json() == {
        "id": "a1e0a1e0-1111-4111-8111-000000000001",
        "name": "Ayşe Kaya",
        "role": "EVRAK_KAYIT",
        "institution_id": "belediye",
        "department_code": "yazi_isleri",
    }
    assert client.get("/api/auth/me").status_code == 401
    assert client.get(
        "/api/auth/me", headers={"Authorization": "Bearer forged"}
    ).json()["detail"]["code"] == "invalid_token"


def test_role_scoped_inboxes_and_department_isolation():
    ayse = _login("ayse_kaya")
    mehmet = _login("mehmet_demir")
    imar = _custom_user_headers(
        institution_id="belediye", department_code="imar_sehircilik"
    )
    other_institution = _custom_user_headers(
        institution_id="kaymakamlik", department_code="yazi_isleri"
    )
    case = _create_case(ayse)

    registry = client.get("/api/cases/inbox", headers=ayse)
    assert [item["id"] for item in registry.json()["items"]] == [case["id"]]
    assert registry.json()["items"][0]["current_department_code"] == "yazi_isleri"
    assert "originator_email" not in registry.json()["items"][0]
    assert client.get("/api/cases/inbox", headers=mehmet).json()["items"] == []

    routed = _route_to_fen(_advance_to_ready(case, ayse), ayse)
    department = client.get("/api/cases/inbox", headers=mehmet)
    assert [item["id"] for item in department.json()["items"]] == [case["id"]]
    assert client.get("/api/cases/inbox", headers=imar).json()["items"] == []
    assert client.get(f"/api/cases/{case['id']}", headers=imar).status_code == 403
    hidden = client.get(f"/api/cases/{case['id']}", headers=other_institution)
    assert hidden.status_code == 404
    assert hidden.json()["detail"]["code"] == "case_not_found"
    assert routed["current_department_code"] == "fen_isleri"


def test_route_requires_confirmation_and_is_atomic():
    ayse = _login("ayse_kaya")
    mehmet = _login("mehmet_demir")
    case = _advance_to_ready(_create_case(ayse), ayse)

    rejected = client.post(
        f"/api/cases/{case['id']}/route",
        headers=ayse,
        json={
            "department_code": "fen_isleri",
            "expected_version": case["version"],
            "confirmed": False,
        },
    )
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "confirmation_required"

    invalid = client.post(
        f"/api/cases/{case['id']}/route",
        headers=ayse,
        json={
            "department_code": "uydurma_birim",
            "expected_version": case["version"],
            "confirmed": True,
        },
    )
    assert invalid.status_code == 400
    assert invalid.json()["detail"]["code"] == "invalid_department"

    routed = _route_to_fen(case, ayse)
    aggregate = client.get(f"/api/cases/{case['id']}", headers=mehmet).json()
    assert routed["workflow_status"] == "IN_DEPARTMENT"
    assert len(aggregate["assignments"]) == 1
    assert aggregate["assignments"][0]["ended_at"] is None
    event_types = [event["event_type"] for event in aggregate["events"]]
    assert event_types[-4:] == [
        "ROUTING_CONFIRMED",
        "TASK_CREATED",
        "CASE_ROUTED",
        "DRAFT_SAVED",
    ]
    routing_event = next(
        event for event in aggregate["events"] if event["event_type"] == "CASE_ROUTED"
    )
    assert routing_event["before_value"]["department_code"] == "yazi_isleri"
    assert routing_event["after_value"]["department_code"] == "fen_isleri"

    forwarding = aggregate["drafts"][0]
    assert forwarding["draft_type"] == "FORWARDING_COVER_LETTER"
    assert forwarding["content"]["recipient"] == aggregate["case"]["current_department_name"]
    assert forwarding["content"]["recipient_kind"] == "INTERNAL_DEPARTMENT"

    invalid_state = client.post(
        f"/api/cases/{case['id']}/route",
        headers=ayse,
        json={
            "department_code": "fen_isleri",
            "expected_version": routed["version"],
            "confirmed": True,
        },
    )
    assert invalid_state.status_code == 409
    assert invalid_state.json()["detail"]["code"] == "invalid_case_transition"


def test_department_start_and_action_are_human_authorized():
    ayse = _login("ayse_kaya")
    mehmet = _login("mehmet_demir")
    case = _route_to_fen(_advance_to_ready(_create_case(ayse), ayse), ayse)

    forbidden = client.post(
        f"/api/cases/{case['id']}/department-action",
        headers=ayse,
        json={
            "action_type": "SAHA_INCELEMESI",
            "result": "Sonuç",
            "decision": "Karar",
            "expected_version": case["version"],
            "confirmed": True,
        },
    )
    assert forbidden.status_code == 403

    started = client.post(
        f"/api/cases/{case['id']}/start",
        headers=mehmet,
        json={"expected_version": case["version"], "confirmed": True},
    )
    assert started.status_code == 200
    assert started.json()["workflow_status"] == "IN_PROGRESS"
    invalid_state = client.post(
        f"/api/cases/{case['id']}/start",
        headers=mehmet,
        json={
            "expected_version": started.json()["version"],
            "confirmed": True,
        },
    )
    assert invalid_state.status_code == 409
    assert invalid_state.json()["detail"]["code"] == "invalid_case_transition"
    action = client.post(
        f"/api/cases/{case['id']}/department-action",
        headers=mehmet,
        json={
            "action_type": "SAHA_INCELEMESI",
            "result": "Yol deformasyonu tespit edildi.",
            "decision": "Bakım programına alındı.",
            "expected_version": started.json()["version"],
            "confirmed": True,
        },
    )
    assert action.status_code == 200
    assert action.json()["verified"] is True
    assert action.json()["recorded_by_user_id"].startswith("b2e0b2e0")
    aggregate = client.get(f"/api/cases/{case['id']}", headers=mehmet).json()
    assert len(aggregate["drafts"]) == 2
    official = aggregate["drafts"][-1]
    assert official["draft_type"] == "OFFICIAL_RESPONSE"
    assert official["content"]["recipient"] == aggregate["case"]["originator_name"]
    edited = client.post(
        f"/api/cases/{case['id']}/drafts", headers=mehmet,
        json={"draft_type": "OFFICIAL_RESPONSE", "content": {**official["content"], "subject": "Personel DÃ¼zeltmesi"}, "grounded_action_id": official["grounded_action_id"], "expected_version": aggregate["case"]["version"], "confirmed": True},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["draft"]["status"] == "EDITED"
    assert edited.json()["draft"]["revision"] == 2
    approved = client.post(
        f"/api/cases/{case['id']}/drafts/{edited.json()['draft']['id']}/approve",
        headers=mehmet,
        json={"expected_version": edited.json()["case"]["version"], "confirmed": True},
    )
    assert approved.status_code == 200, approved.text
    approved_aggregate = client.get(f"/api/cases/{case['id']}", headers=mehmet).json()
    approval_event = next(
        event
        for event in reversed(approved_aggregate["events"])
        if event["event_type"] == "DRAFT_APPROVED"
    )
    assert approval_event["before_value"]["status"] == "EDITED"
    assert approval_event["after_value"]["status"] == "APPROVED"
    assert approval_event["after_value"]["approved_by_user_id"]

    queue = client.get("/api/cases/official-writings", headers=mehmet)
    assert queue.status_code == 200
    assert {item["draft_type"] for item in queue.json()["items"]} == {"FORWARDING_COVER_LETTER", "OFFICIAL_RESPONSE"}


@pytest.mark.parametrize(
    ("registry_key", "department_headers", "department_code"),
    [
        ("ayse_kaya", None, "imar_sehircilik"),
        ("selin_aksoy", "murat_celik", "milli_egitim"),
    ],
)
def test_official_writing_is_generic_for_other_department_and_kaymakamlik(registry_key, department_headers, department_code):
    registry = _login(registry_key)
    worker = _login(department_headers) if department_headers else _custom_user_headers(institution_id="belediye", department_code=department_code)
    case = _advance_to_ready(_create_case(registry, name="Kurumsal BaÅŸvuru Sahibi"), registry)
    routed_response = client.post(f"/api/cases/{case['id']}/route", headers=registry, json={"department_code": department_code, "expected_version": case["version"], "confirmed": True})
    assert routed_response.status_code == 200, routed_response.text
    routed = routed_response.json()
    started = client.post(f"/api/cases/{case['id']}/start", headers=worker, json={"expected_version": routed["version"], "confirmed": True}).json()
    action = client.post(f"/api/cases/{case['id']}/department-action", headers=worker, json={"action_type": "INCELEME", "result": "BaÅŸvuru birim tarafÄ±ndan incelendi.", "decision": "Ä°ÅŸlem planÄ±na alÄ±ndÄ±.", "expected_version": started["version"], "confirmed": True})
    assert action.status_code == 200, action.text
    aggregate = client.get(f"/api/cases/{case['id']}", headers=worker).json()
    assert aggregate["case"]["institution_id"] == ("kaymakamlik" if registry_key == "selin_aksoy" else "belediye")
    assert aggregate["case"]["current_department_code"] == department_code
    assert [draft["draft_type"] for draft in aggregate["drafts"]] == ["FORWARDING_COVER_LETTER", "OFFICIAL_RESPONSE"]
    assert aggregate["drafts"][-1]["content"]["recipient"] == aggregate["case"]["originator_name"]


def test_citizen_token_isolation_allowlist_and_safe_projection():
    ayse = _login("ayse_kaya")
    first = _create_case(ayse, name="Birinci Vatandaş")
    second = _create_case(ayse, name="İkinci Vatandaş")
    started = client.post(
        f"/api/cases/{first['id']}/analysis/start",
        headers=ayse,
        json={"expected_version": first["version"], "confirmed": True},
    ).json()
    reviewed = client.post(
        f"/api/cases/{first['id']}/analysis/complete",
        headers=ayse,
        json={"expected_version": started["version"], "confirmed": True},
    ).json()
    requested = client.post(
        f"/api/cases/{first['id']}/citizen-requests",
        headers=ayse,
        json={
            "question": "Yolun açık adresi nedir?",
            "requested_fields": ["location"],
            "resume_target": "READY_TO_ROUTE",
            "expected_version": reviewed["version"],
            "confirmed": True,
        },
    )
    assert requested.status_code == 200

    path = f"/api/public/cases/{first['tracking_code']}"
    public = client.get(path, params={"token": first["citizen_access_token"]})
    assert public.status_code == 200
    assert set(public.json()) == {
        "tracking_code",
        "public_status",
        "received_at",
        "updated_at",
        "timeline",
        "clarification",
    }
    assert "Birinci Vatandaş" not in public.text
    assert client.get(
        path, params={"token": second["citizen_access_token"]}
    ).status_code == 404

    extra = client.post(
        f"{path}/complete-info",
        params={"token": first["citizen_access_token"]},
        json={"answers": {"location": "Çınar Sokak", "internal_note": "x"}},
    )
    assert extra.status_code == 400
    completed = client.post(
        f"{path}/complete-info",
        params={"token": first["citizen_access_token"]},
        json={"answers": {"location": "Çınar Sokak"}},
    )
    assert completed.status_code == 200
    aggregate = client.get(f"/api/cases/{first['id']}", headers=ayse).json()
    assert aggregate["case"]["workflow_status"] == "READY_TO_ROUTE"
    assert aggregate["citizen_requests"][0]["status"] == "COMPLETED"
    assert aggregate["events"][-1]["event_type"] == "CITIZEN_INFO_COMPLETED"


def test_official_draft_requires_verified_action_and_closed_is_terminal():
    ayse = _login("ayse_kaya")
    mehmet = _login("mehmet_demir")
    case = _route_to_fen(_advance_to_ready(_create_case(ayse), ayse), ayse)
    started = client.post(
        f"/api/cases/{case['id']}/start",
        headers=mehmet,
        json={"expected_version": case["version"], "confirmed": True},
    ).json()

    ungrounded = client.post(
        f"/api/cases/{case['id']}/drafts",
        headers=mehmet,
        json={
            "draft_type": "OFFICIAL_RESPONSE",
            "content": {"body": "Yanıt"},
            "expected_version": started["version"],
            "confirmed": True,
        },
    )
    assert ungrounded.status_code == 409
    assert ungrounded.json()["detail"]["code"] == "verified_department_action_required"

    action = client.post(
        f"/api/cases/{case['id']}/department-action",
        headers=mehmet,
        json={
            "action_type": "SAHA_INCELEMESI",
            "result": "Kontrol edildi.",
            "decision": "Onarım yapılacak.",
            "expected_version": started["version"],
            "confirmed": True,
        },
    ).json()
    saved = client.post(
        f"/api/cases/{case['id']}/drafts",
        headers=mehmet,
        json={
            "draft_type": "OFFICIAL_RESPONSE",
            "content": {"body": "Talebiniz programa alınmıştır."},
            "grounded_action_id": action["id"],
            "expected_version": action["case"]["version"],
            "confirmed": True,
        },
    ).json()
    approved = client.post(
        f"/api/cases/{case['id']}/drafts/{saved['draft']['id']}/approve",
        headers=mehmet,
        json={"expected_version": saved["case"]["version"], "confirmed": True},
    ).json()
    completed = client.post(
        f"/api/cases/{case['id']}/complete",
        headers=mehmet,
        json={
            "draft_id": saved["draft"]["id"],
            "expected_version": approved["case"]["version"],
            "confirmed": True,
        },
    )
    assert completed.status_code == 200
    assert completed.json()["recipient"]["originator_name"] == "Ali Yılmaz"
    assert completed.json()["case"]["workflow_status"] == "COMPLETED"

    closed = client.post(
        f"/api/cases/{case['id']}/close",
        headers=ayse,
        json={
            "expected_version": completed.json()["case"]["version"],
            "confirmed": True,
        },
    )
    assert closed.status_code == 200
    assert closed.json()["workflow_status"] == "CLOSED"
    terminal = client.post(
        f"/api/cases/{case['id']}/start",
        headers=mehmet,
        json={"expected_version": closed.json()["version"], "confirmed": True},
    )
    assert terminal.status_code == 409
    assert terminal.json()["detail"]["code"] == "invalid_case_transition"

    aggregate = client.get(f"/api/cases/{case['id']}", headers=mehmet).json()
    ordered = [
        (event["created_at"], event["id"]) for event in aggregate["events"]
    ]
    assert ordered == sorted(ordered)
    assert aggregate["events"][-2]["event_type"] == "CASE_COMPLETED"
    assert aggregate["events"][-1]["event_type"] == "CASE_CLOSED"
    assert all(
        note["delivery_status"] == "STORED_NOT_SENT"
        for note in aggregate["notifications"]
    )


def test_department_directory_comes_from_profile():
    ayse = _login("ayse_kaya")
    response = client.get(
        "/api/institutions/belediye/departments", headers=ayse
    )

    assert response.status_code == 200
    departments = {item["code"]: item for item in response.json()["departments"]}
    assert departments["fen_isleri"]["name"] == "Fen İşleri Müdürlüğü"
    assert departments["yazi_isleri"]["description"]


def test_analysis_api_remains_compatible_and_can_add_case_link(monkeypatch):
    class MockWorkflow:
        def run(self, text, document_id=None):
            return {
                "document": {"document_type": "dilekce"},
                "human_review": {"required": True, "status": "pending_review"},
                "routing": {
                    "recommended_unit": "Fen İşleri Müdürlüğü",
                    "recommended_department_code": "fen_isleri",
                },
            }

    monkeypatch.setattr(
        "backend.app.main.get_workflow", lambda institution=None: MockWorkflow()
    )
    unauthenticated = client.post(
        "/api/documents/analyze-text", json={"text": "Eski tüketici"}
    )
    assert unauthenticated.status_code == 200
    assert "analysis_id" in unauthenticated.json()
    assert "case_id" not in unauthenticated.json()

    ayse = _login("ayse_kaya")
    integrated = client.post(
        "/api/documents/analyze-text",
        headers=ayse,
        json={"text": "Yol onarım talebi", "institution": "belediye"},
    )
    assert integrated.status_code == 200
    assert {"analysis_id", "case_id", "tracking_code"} <= set(integrated.json())
    aggregate = client.get(
        f"/api/cases/{integrated.json()['case_id']}", headers=ayse
    )
    assert aggregate.status_code == 200
    assert aggregate.json()["case"]["analysis_id"] == integrated.json()["analysis_id"]
    assert aggregate.json()["analysis"]["analysis_id"] == integrated.json()["analysis_id"]


def test_yazi_isleri_to_fen_isleri_e2e():
    registry = _login("ayse_kaya")
    fen = _login("mehmet_demir")
    case = _advance_to_ready(_create_case(registry), registry)

    routed = _route_to_fen(case, registry)

    registry_inbox = client.get("/api/cases/inbox", headers=registry).json()["items"]
    fen_inbox = client.get("/api/cases/inbox", headers=fen).json()["items"]
    aggregate = client.get(f"/api/cases/{case['id']}", headers=fen).json()
    assert routed["current_department_code"] == "fen_isleri"
    assert all(item["id"] != case["id"] for item in registry_inbox)
    assert any(item["id"] == case["id"] for item in fen_inbox)
    assert aggregate["assignment"]["status"] == "ASSIGNMENT_PENDING"
    assert any(event["event_type"] == "CASE_ROUTED" for event in aggregate["timeline"])


def test_document_to_task():
    registry = _login("ayse_kaya")
    fen = _login("mehmet_demir")
    case = _advance_to_ready(_create_case(registry), registry)
    response = client.post(
        f"/api/cases/{case['id']}/route",
        headers=registry,
        json={
            "department_code": "fen_isleri",
            "expected_version": case["version"],
            "confirmed": True,
            "routing_snapshot": {
                "ai_operation": {
                    "task_type": "YOL_BAKIM_INCELEME",
                    "department_code": "fen_isleri",
                    "team_code": "saha_bakim_ekibi",
                    "recommended_role": "SAHA_EKIBI",
                    "requires_field_visit": True,
                }
            },
        },
    )
    assert response.status_code == 200, response.text
    aggregate = client.get(f"/api/cases/{case['id']}", headers=fen).json()
    assert aggregate["assignment"]["task_type"] == "YOL_BAKIM_INCELEME"
    assert aggregate["assignment"]["team_code"] == "saha_bakim_ekibi"
    assert aggregate["assignment"]["recommended_role"] == "SAHA_EKIBI"
    assert aggregate["assignment"]["assigned_user_id"] is None


def test_citizen_missing_info_target():
    registry = _login("ayse_kaya")
    case = _create_case(registry)
    response = client.post(
        f"/api/cases/{case['id']}/information-requests",
        headers=registry,
        json={
            "requested_fields": ["location"],
            "reason": "Saha incelemesi için konum gereklidir.",
            "target_type": "VATANDAS",
            "expected_version": case["version"],
            "confirmed": True,
        },
    )
    assert response.status_code == 200, response.text
    request = response.json()["information_request"]
    assert request["target_type"] == "VATANDAS"
    assert request["target_name"] == "Ali Yılmaz"
    assert request["recommended_action"] == "CITIZEN_INFORMATION_REQUESTED"


def test_internal_missing_info_target():
    registry = _login("ayse_kaya")
    created = client.post(
        "/api/cases",
        headers=registry,
        json={
            "source_type": "KURUM_ICI",
            "source_channel": "KURUM_ICI",
            "originator_type": "KURUM_ICI",
            "originator_name": "Yazı İşleri Müdürlüğü",
            "confirmed": True,
        },
    )
    assert created.status_code == 200, created.text
    case = created.json()
    response = client.post(
        f"/api/cases/{case['id']}/information-requests",
        headers=registry,
        json={
            "requested_fields": ["attachment"],
            "reason": "Eksik ek gönderici birimden tamamlanmalıdır.",
            "target_type": "KURUM_ICI",
            "target_department": "yazi_isleri",
            "expected_version": case["version"],
            "confirmed": True,
        },
    )
    assert response.status_code == 200, response.text
    request = response.json()["information_request"]
    assert request["target_type"] == "INTERNAL_DEPARTMENT"
    assert request["target_department"] == "yazi_isleri"
    assert request["recommended_action"] == "INTERNAL_INFORMATION_REQUESTED"


def test_role_specific_case_visibility():
    registry = _login("ayse_kaya")
    fen = _login("mehmet_demir")
    imar = _custom_user_headers(institution_id="belediye", department_code="imar_sehircilik")
    case = _advance_to_ready(_create_case(registry), registry)
    _route_to_fen(case, registry)
    assert client.get(f"/api/cases/{case['id']}", headers=fen).status_code == 200
    denied = client.get(f"/api/cases/{case['id']}", headers=imar)
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "action_forbidden"


def test_timeline_after_route():
    registry = _login("ayse_kaya")
    fen = _login("mehmet_demir")
    case = _advance_to_ready(_create_case(registry), registry)
    _route_to_fen(case, registry)
    timeline = client.get(f"/api/cases/{case['id']}", headers=fen).json()["timeline"]
    routed = next(event for event in timeline if event["event_type"] == "CASE_ROUTED")
    assert routed["payload"]["from_department"] == "yazi_isleri"
    assert routed["payload"]["to_department"] == "fen_isleri"
    assert any(event["event_type"] == "TASK_CREATED" for event in timeline)

def test_staff_issued_citizen_link_opens_only_the_scoped_case():
    ayse = _login("ayse_kaya")
    first = _create_case(ayse, name="Bağlantı Sahibi")
    second = _create_case(ayse, name="Diğer Vatandaş")

    issued = client.post(f"/api/cases/{first['id']}/citizen-access", headers=ayse)
    assert issued.status_code == 200
    payload = issued.json()
    assert payload["tracking_code"] == first["tracking_code"]
    assert "demo-token" not in payload["citizen_url"]
    token = payload["citizen_url"].split("token=", 1)[1]

    public = client.get(f"/api/public/cases/{first['tracking_code']}", params={"token": token})
    assert public.status_code == 200
    assert public.json()["tracking_code"] == first["tracking_code"]
    assert client.get(f"/api/public/cases/{second['tracking_code']}", params={"token": token}).status_code == 404
