from backend.app.agents.missing_field_agent import MissingFieldAgent


def test_track2_address_none_is_missing():
    agent = MissingFieldAgent()
    extracted_A = {
        "person_name": {"value": "Mehmet Kaya"},
        "address": None,
        "signature_present": {"value": True},
        "request": {"value": "Bilgi istiyorum."}
    }
    res_A = agent.check_missing_fields("bilgi_edinme", "bilgi_talebi", extracted_A)
    assert "address" in res_A["missing_fields"], f"Test A Failed: address should be missing. Got: {res_A['missing_fields']}"


def test_track2_nested_person_name_is_present():
    agent = MissingFieldAgent()
    extracted_A = {
        "person_name": {"value": "Mehmet Kaya"},
        "address": None,
        "signature_present": {"value": True},
        "request": {"value": "Bilgi istiyorum."}
    }
    res_A = agent.check_missing_fields("bilgi_edinme", "bilgi_talebi", extracted_A)
    assert "person_name" in res_A["present_fields"], "Test A Failed: person_name should be present."


def test_track2_null_person_name_is_missing():
    agent = MissingFieldAgent()
    extracted_C = {
        "person_name": {"value": None},
        "address": {"value": "Ankara"},
        "signature_present": {"value": True},
        "request": {"value": "Test"}
    }
    res_C = agent.check_missing_fields("bilgi_edinme", "bilgi_talebi", extracted_C)
    assert "person_name" in res_C["missing_fields"], "Test C Failed: person_name should be missing."


def test_track2_empty_person_name_is_missing():
    agent = MissingFieldAgent()
    extracted_D = {
        "person_name": {"value": ""},
        "address": {"value": "Ankara"},
        "signature_present": {"value": True},
        "request": {"value": "Test"}
    }
    res_D = agent.check_missing_fields("bilgi_edinme", "bilgi_talebi", extracted_D)
    assert "person_name" in res_D["missing_fields"], "Test D Failed: empty string should be missing."


def test_track2_unknown_signature_is_uncertain():
    agent = MissingFieldAgent()
    extracted_E = {
        "person_name": {"value": "Ahmet"},
        "address": {"value": "Ankara"},
        "signature_present": {"status": "unknown"},
        "request": {"value": "Test"}
    }
    res_E = agent.check_missing_fields("bilgi_edinme", "bilgi_talebi", extracted_E)
    assert "signature_present" in res_E["uncertain_fields"], "Test E Failed: signature should be uncertain."
    assert "signature_present" not in res_E["missing_fields"], "Test E Failed: signature should not be missing."
    assert res_E["needs_human_review"] is True, "Test E Failed: should need human review."


def test_track2_human_review_can_be_required_without_missing_fields():
    agent = MissingFieldAgent()
    extracted_E = {
        "person_name": {"value": "Ahmet"},
        "address": {"value": "Ankara"},
        "signature_present": {"status": "unknown"},
        "request": {"value": "Test"}
    }
    res_E = agent.check_missing_fields("bilgi_edinme", "bilgi_talebi", extracted_E)
    assert len(res_E["missing_fields"]) == 0, "Test F Failed: missing fields should be empty."


def test_track2_missing_text_field_does_not_require_human_review():
    agent = MissingFieldAgent()
    extracted_A = {
        "person_name": {"value": "Mehmet Kaya"},
        "address": None,
        "signature_present": {"value": True},
        "request": {"value": "Bilgi istiyorum."}
    }
    res_G = agent.check_missing_fields("bilgi_edinme", "bilgi_talebi", extracted_A)
    assert "address" in res_G["missing_fields"], "Test G Failed: address should be missing."
    assert res_G["needs_human_review"] is False, "Test G Failed: should not need human review for a missing textual field."
