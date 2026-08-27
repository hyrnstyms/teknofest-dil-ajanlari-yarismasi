"""PII response masking and citizen-notification integration tests."""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from backend.app.cases.runtime import get_case_engine
from backend.app.db.repository import AnalysisRepository
from backend.app.main import app
from backend.app.utils.pii import mask_pii


client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_pii_notification_domain():
    engine = get_case_engine()
    repository = AnalysisRepository(engine=engine.engine)
    engine.clear_domain()
    repository.clear()
    yield
    engine.clear_domain()
    repository.clear()


def _login(user_key: str) -> dict[str, str]:
    response = client.post("/api/auth/demo-login", json={"user_key": user_key})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _workflow_with_pii():
    class MockWorkflow:
        def run(self, text: str, document_id: str | None = None) -> dict:
            return {
                "document": {"document_type": "dilekce"},
                "human_review": {"required": True, "status": "pending_review"},
                "extraction": {
                    "fields": {
                        "national_id": {
                            "value": "10000000146",
                            "evidence": ["TC: 10000000146"],
                        },
                        "phone": {
                            "value": "+90 555 123 45 67",
                            "evidence": ["Telefon: +90 555 123 45 67"],
                        },
                        "email": {
                            "value": "vatandas@example.test",
                            "evidence": ["E-posta: vatandas@example.test"],
                        },
                    }
                },
            }

    return MockWorkflow()


def test_mask_pii_masks_supported_values_without_mutating_input():
    raw = {"text": "TC 10000000146, +90 555 123 45 67, vatandas@example.test"}

    masked = mask_pii(raw)

    assert masked == {"text": "TC [TC_KIMLIK_NO], [TELEFON], [E_POSTA]"}
    assert raw["text"].endswith("vatandas@example.test")


def test_analysis_response_masks_pii_by_default_and_retains_raw_db_state(monkeypatch):
    monkeypatch.setattr("backend.app.main.get_workflow", lambda institution="kaymakamlik": _workflow_with_pii())

    response = client.post("/api/documents/analyze-text", json={"text": "örnek evrak"})

    assert response.status_code == 200
    analysis_id = response.json()["analysis_id"]
    masked_fields = response.json()["extraction"]["fields"]
    assert masked_fields["national_id"]["value"] == "[TC_KIMLIK_NO]"
    assert masked_fields["phone"]["value"] == "[TELEFON]"
    assert masked_fields["email"]["value"] == "[E_POSTA]"
    assert masked_fields["email"]["evidence"] == ["E-posta: [E_POSTA]"]

    stored = AnalysisRepository().get_analysis(analysis_id)
    assert stored is not None
    assert stored["extraction"]["fields"]["national_id"]["value"] == "10000000146"

    raw_response = client.get(f"/api/analysis/{analysis_id}?mask=false")
    assert raw_response.status_code == 200
    assert raw_response.json()["extraction"]["fields"]["phone"]["value"] == "+90 555 123 45 67"

    masked_response = client.get(f"/api/analysis/{analysis_id}")
    assert masked_response.json()["extraction"]["fields"]["phone"]["value"] == "[TELEFON]"


def test_rejected_linked_analysis_queues_portal_notification(monkeypatch, caplog):
    monkeypatch.setattr("backend.app.main.get_workflow", lambda institution="kaymakamlik": _workflow_with_pii())
    headers = _login("ayse_kaya")
    analysis = client.post(
        "/api/documents/analyze-text",
        headers=headers,
        json={"text": "örnek evrak", "institution": "belediye"},
    )
    assert analysis.status_code == 200
    case_id = analysis.json()["case_id"]

    with caplog.at_level(logging.INFO, logger="backend.app.cases.notifications"):
        rejected = client.post(
            f"/api/analysis/{analysis.json()['analysis_id']}/reject",
            json={"reason": "Eksik belge"},
        )

    assert rejected.status_code == 200
    aggregate = client.get(f"/api/cases/{case_id}", headers=headers)
    assert aggregate.status_code == 200
    notifications = aggregate.json()["notifications"]
    rejected_notification = next(
        item for item in notifications if item["template_key"] == "ANALYSIS_REJECTED"
    )
    assert rejected_notification["channel"] == "PORTAL"
    assert rejected_notification["delivery_status"] == "STORED_NOT_SENT"
    assert "Citizen notification queued" in caplog.text
