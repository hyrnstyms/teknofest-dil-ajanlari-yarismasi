"""Authorization and filtering tests for GET /api/cases?department_code=."""

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


def _worker(department_code: str) -> dict[str, str]:
    user_id = str(uuid.uuid4())
    user_key = f"queue_{uuid.uuid4().hex}"
    engine = get_case_engine()
    with engine.session_factory.begin() as session:
        session.add(
            CaseUser(
                id=user_id,
                user_key=user_key,
                name="Birim Test Personeli",
                role="BIRIM_PERSONELI",
                institution_id="belediye",
                department_code=department_code,
                is_active=True,
            )
        )
    return {"Authorization": f"Bearer {issue_token(user_id, user_key)}"}


def _create_ready_case(registry: dict[str, str], name: str) -> dict:
    response = client.post(
        "/api/cases",
        headers=registry,
        json={
            "source_type": "VATANDAS",
            "source_channel": "WEB_FORM",
            "originator_type": "VATANDAS",
            "originator_name": name,
            "confirmed": True,
        },
    )
    assert response.status_code == 200, response.text
    case = response.json()
    for path in ("analysis/start", "analysis/complete", "accept-review"):
        response = client.post(
            f"/api/cases/{case['id']}/{path}",
            headers=registry,
            json={"expected_version": case["version"], "confirmed": True},
        )
        assert response.status_code == 200, response.text
        case = response.json()
    return case


def _route(
    registry: dict[str, str], case: dict, department_code: str
) -> dict:
    response = client.post(
        f"/api/cases/{case['id']}/route",
        headers=registry,
        json={
            "department_code": department_code,
            "expected_version": case["version"],
            "confirmed": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_registry_filters_same_institution_cases_by_department():
    registry = _login("ayse_kaya")
    fen_case = _route(
        registry, _create_ready_case(registry, "Fen Başvurusu"), "fen_isleri"
    )
    imar_case = _route(
        registry,
        _create_ready_case(registry, "İmar Başvurusu"),
        "imar_sehircilik",
    )

    fen_queue = client.get(
        "/api/cases?department_code=fen_isleri", headers=registry
    )

    assert fen_queue.status_code == 200
    assert [item["id"] for item in fen_queue.json()["items"]] == [fen_case["id"]]
    assert imar_case["id"] not in {
        item["id"] for item in fen_queue.json()["items"]
    }


def test_department_worker_can_read_only_own_queue():
    registry = _login("ayse_kaya")
    worker = _login("mehmet_demir")
    fen_case = _route(
        registry, _create_ready_case(registry, "Fen Başvurusu"), "fen_isleri"
    )

    response = client.get(
        "/api/cases?department_code=fen_isleri", headers=worker
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [fen_case["id"]]
    assert "originator_email" not in response.json()["items"][0]


def test_department_worker_gets_403_for_another_department():
    worker = _login("mehmet_demir")

    response = client.get(
        "/api/cases?department_code=imar_sehircilik", headers=worker
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "action_forbidden"


def test_invalid_department_is_rejected():
    registry = _login("ayse_kaya")

    response = client.get(
        "/api/cases?department_code=uydurma_birim", headers=registry
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_department"


def test_department_queue_supports_status_and_pagination():
    registry = _login("ayse_kaya")
    worker = _worker("imar_sehircilik")
    first = _route(
        registry, _create_ready_case(registry, "Birinci İmar"), "imar_sehircilik"
    )
    second = _route(
        registry, _create_ready_case(registry, "İkinci İmar"), "imar_sehircilik"
    )

    first_page = client.get(
        "/api/cases?department_code=imar_sehircilik&status=IN_DEPARTMENT&limit=1",
        headers=worker,
    )
    assert first_page.status_code == 200
    assert len(first_page.json()["items"]) == 1
    assert first_page.json()["next_cursor"] == "1"

    second_page = client.get(
        "/api/cases?department_code=imar_sehircilik&status=IN_DEPARTMENT&limit=1&cursor=1",
        headers=worker,
    )
    assert second_page.status_code == 200
    assert len(second_page.json()["items"]) == 1
    assert {
        first_page.json()["items"][0]["id"],
        second_page.json()["items"][0]["id"],
    } == {first["id"], second["id"]}


def test_department_queue_rejects_invalid_status_and_cursor():
    registry = _login("ayse_kaya")

    invalid_status = client.get(
        "/api/cases?department_code=fen_isleri&status=ROUTED", headers=registry
    )
    invalid_cursor = client.get(
        "/api/cases?department_code=fen_isleri&cursor=-1", headers=registry
    )

    assert invalid_status.status_code == 400
    assert invalid_status.json()["detail"]["code"] == "validation_error"
    assert invalid_cursor.status_code == 400
    assert invalid_cursor.json()["detail"]["code"] == "validation_error"
