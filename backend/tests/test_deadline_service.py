from backend.app.intelligence.deadline import LegalDeadlineService


service = LegalDeadlineService()


def _verified_analysis(text="Başvurunun sonucu 30 takvim günü içinde bildirilir."):
    return {
        "evidence": [{"evidence": text, "source": "K1"}],
        "sources": [
            {
                "law_number": "3071",
                "madde_no": "7",
                "title": "Dilekçe Hakkının Kullanılmasına Dair Kanun",
            }
        ],
    }


def test_calendar_deadline_uses_python_date_arithmetic():
    result = service.evaluate(
        received_at="2026-08-27T09:30:00+03:00",
        as_of="2026-09-14T09:30:00+03:00",
        legal_analysis=_verified_analysis(),
    )

    assert result["applicable"] is True
    assert result["deadline_days"] == 30
    assert result["deadline_type"] == "CALENDAR_DAY"
    assert result["due_at"] == "2026-09-26T09:30:00+03:00"
    assert result["remaining_days"] == 12
    assert result["risk_level"] == "NORMAL"
    assert result["legal_basis"]["verified"] is True
    assert result["legal_basis"]["citation"] == "3071 sayılı Kanun, Madde 7"


def test_structured_verified_duration_is_preferred():
    result = service.evaluate(
        received_at="2026-08-27T09:30:00+03:00",
        as_of="2026-08-27T09:30:00+03:00",
        verified_legal_evidence={
            "verified": True,
            "deadline_days": 15,
            "deadline_type": "CALENDAR_DAY",
            "legal_basis": {
                "law_number": "4982",
                "article": "11",
                "citation": "4982 sayılı Kanun, Madde 11",
            },
            "text": "Metindeki serbest ifade farklı olsa bile yapılandırılmış süre kullanılır.",
        },
    )

    assert result["deadline_days"] == 15
    assert result["due_at"] == "2026-09-11T09:30:00+03:00"


def test_structured_duration_wins_over_earlier_verified_text():
    result = service.evaluate(
        received_at="2026-08-27T09:30:00+03:00",
        as_of="2026-08-27T09:30:00+03:00",
        legal_analysis={
            "evidence": [
                {"text": "Genel metinde 30 gün ifadesi vardır.", "source": "K1"},
                {
                    "deadline_days": 15,
                    "deadline_type": "CALENDAR_DAY",
                    "source": "K1",
                },
            ],
            "sources": [{"law_number": "4982", "madde_no": "11"}],
        },
    )

    assert result["deadline_days"] == 15
    assert result["due_at"] == "2026-09-11T09:30:00+03:00"


def test_invalid_structured_duration_fails_safe():
    result = service.evaluate(
        received_at="2026-08-27T09:30:00+03:00",
        verified_legal_evidence={
            "verified": True,
            "deadline_days": 100_000,
            "deadline_type": "CALENDAR_DAY",
        },
    )

    assert result["deadline_days"] is None
    assert result["due_at"] is None
    assert result["risk_level"] == "UNKNOWN"


def test_unverified_and_retrieved_only_text_cannot_create_deadline():
    for legal_analysis in (
        {"evidence": ["30 gün içinde"]},
        {"retrieved_sources": [{"text": "30 gün içinde", "law_number": "3071"}]},
        {
            "evidence": [{"text": "30 gün içinde", "source": "K9"}],
            "sources": [{"law_number": "3071"}],
        },
        {
            "evidence": [{"text": "30 gün içinde", "source": "K1", "verified": False}],
            "sources": [{"law_number": "3071"}],
        },
    ):
        result = service.evaluate(
            received_at="2026-08-27T09:30:00+03:00",
            legal_analysis=legal_analysis,
        )
        assert result["deadline_days"] is None
        assert result["due_at"] is None
        assert result["risk_level"] == "UNKNOWN"


def test_created_at_never_substitutes_for_received_at():
    result = service.evaluate(
        received_at=None,
        created_at="2026-08-27T09:30:00+03:00",
        legal_analysis=_verified_analysis(),
    )

    assert result["deadline_days"] == 30
    assert result["received_at"] is None
    assert result["due_at"] is None
    assert result["risk_level"] == "UNKNOWN"


def test_naive_received_at_is_not_treated_as_reliable():
    result = service.evaluate(
        received_at="2026-08-27T09:30:00",
        legal_analysis=_verified_analysis(),
    )

    assert result["due_at"] is None
    assert result["risk_level"] == "UNKNOWN"


def test_business_day_duration_has_no_invented_calendar_math():
    result = service.evaluate(
        received_at="2026-08-27T09:30:00+03:00",
        legal_analysis=_verified_analysis("Bilgiye erişim 15 iş günü içinde sağlanır."),
    )

    assert result["applicable"] is True
    assert result["deadline_days"] == 15
    assert result["deadline_type"] == "BUSINESS_DAY"
    assert result["due_at"] is None
    assert result["remaining_days"] is None
    assert result["risk_level"] == "UNKNOWN"
