"""Focused behavior tests for the public ClarificationAgent wrapper."""

from copy import deepcopy

from backend.app.agents.clarification_agent import ClarificationAgent


def test_clarification_returns_no_question_without_missing_fields():
    result = ClarificationAgent().preview(missing_fields={})

    assert result["needs_clarification"] is False
    assert result["blocking"] is False
    assert result["requested_fields"] == []
    assert result["question"] == ""


def test_clarification_asks_for_first_blocking_field():
    result = ClarificationAgent().preview(
        missing_fields={
            "blocking_fields": ["location", "phone"],
            "missing_field_details": [
                {"field": "location", "blocking": True, "label": "Konum"},
                {"field": "phone", "blocking": True, "label": "Telefon"},
            ],
        }
    )

    assert result["needs_clarification"] is True
    assert result["blocking"] is True
    assert result["requested_fields"] == ["location"]
    assert result["question_type"] == "free_text"
    assert "Konum" in result["question"]


def test_clarification_ignores_nonblocking_detail():
    result = ClarificationAgent().preview(
        missing_fields={
            "blocking_fields": [],
            "missing_field_details": [
                {"field": "phone", "blocking": False, "label": "Telefon"}
            ],
        }
    )

    assert result["needs_clarification"] is False
    assert result["blocking"] is False


def test_clarification_permit_ambiguity_uses_choice_question():
    result = ClarificationAgent().preview(
        missing_fields={
            "permit_ambiguity": {
                "field": "permit_type",
                "question": "Hangi ruhsat türü?",
                "options": ["YAPI_RUHSATI", "ISYERI_ACMA_RUHSATI"],
            }
        }
    )

    assert result["requested_fields"] == ["permit_type"]
    assert result["question_type"] == "choice"
    assert result["options"] == ["YAPI_RUHSATI", "ISYERI_ACMA_RUHSATI"]
    assert result["resume_target"] == "routing"


def test_clarification_prioritizes_permit_ambiguity_over_other_missing_data():
    result = ClarificationAgent().preview(
        missing_fields={
            "permit_ambiguity": {
                "field": "permit_type",
                "question": "Ruhsat türünü seçiniz.",
                "options": ["YAPI_RUHSATI", "ISYERI_ACMA_RUHSATI"],
            },
            "blocking_fields": ["location"],
        }
    )

    assert result["requested_fields"] == ["permit_type"]
    assert result["resume_target"] == "routing"


def test_clarification_does_not_mutate_input():
    missing = {
        "blocking_fields": ["location"],
        "missing_field_details": [
            {"field": "location", "blocking": True, "label": "Konum"}
        ],
    }
    original = deepcopy(missing)

    ClarificationAgent().preview(missing_fields=missing)

    assert missing == original
