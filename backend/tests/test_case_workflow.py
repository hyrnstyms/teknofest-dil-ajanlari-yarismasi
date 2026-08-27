"""Acceptance tests for the frozen Case workflow contract."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.app.auth.tokens import issue_token
from backend.app.cases.runtime import get_case_engine
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
    assert event_types[-2:] == ["ROUTING_CONFIRMED", "CASE_ROUTED"]

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
