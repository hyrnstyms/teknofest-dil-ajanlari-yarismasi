from datetime import date

from backend.app.agents.priority_agent import PriorityAgent


AS_OF = date(2026, 8, 23)


def test_near_and_overdue_deadlines_are_high_priority():
    agent = PriorityAgent()
    near = agent.assess("Son tarih: 25.08.2026", reference_date=AS_OF)
    overdue = agent.assess("20.08.2026 tarihine kadar başvurulmalıdır.", reference_date=AS_OF)
    assert (near["priority"], near["priority_rule"]) == ("HIGH", "deadline_near")
    assert (overdue["priority"], overdue["priority_rule"]) == ("HIGH", "deadline_overdue")


def test_future_normal_deadline_is_medium_priority():
    result = PriorityAgent().assess("Son başvuru tarihi: 15.09.2026", reference_date=AS_OF)
    assert result["priority"] == "MEDIUM"
    assert result["days_remaining"] == 23


def test_no_deadline_or_urgency_is_low_priority():
    result = PriorityAgent().assess("Süreç hakkında bilgi verilmesini talep ederim.", reference_date=AS_OF)
    assert (result["priority"], result["priority_rule"]) == (
        "LOW", "no_urgency_or_deadline"
    )


def test_missing_or_malformed_date_is_safe():
    agent = PriorityAgent()
    missing = agent.assess(None, reference_date=AS_OF)
    malformed = agent.assess("Son tarih: yarın öğleden sonra", reference_date=AS_OF)
    assert missing["priority"] == "LOW"
    assert (malformed["priority"], malformed["priority_rule"]) == (
        "LOW", "invalid_deadline"
    )


def test_same_input_and_reference_date_produce_same_output():
    agent = PriorityAgent()
    first = agent.assess("İvedi işlem; son tarih: 01.09.2026", reference_date=AS_OF)
    second = agent.assess("İvedi işlem; son tarih: 01.09.2026", reference_date=AS_OF)
    assert first == second
    assert first["decision_source"] == "rule_based"
