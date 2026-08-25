from backend.app.agents.missing_field_agent import MissingFieldAgent

def run_tests():
    print("--- MISSING FIELD AGENT REGRESSION TESTS ---")
    agent = MissingFieldAgent()

    # Test A: required=["person_name", "address"], person_name present, address None -> address missing
    # We will simulate the rule by passing document_type="dilekce" (which requires person_name, address, signature_present, subject, request)
    # But wait, let's just use "bilgi_edinme" which requires person_name, address, signature_present, request
    extracted_A = {
        "person_name": {"value": "Mehmet Kaya"},
        "address": None,
        "signature_present": {"value": True},
        "request": {"value": "Bilgi istiyorum."}
    }
    res_A = agent.check_missing_fields("bilgi_edinme", "bilgi_talebi", extracted_A)
    assert "address" in res_A["missing_fields"], f"Test A Failed: address should be missing. Got: {res_A['missing_fields']}"
    assert "person_name" in res_A["present_fields"], "Test A Failed: person_name should be present."

    # Test B: nested {"value": "Mehmet Kaya"} -> present
    # Handled in Test A

    # Test C: {"value": null} -> missing
    extracted_C = {
        "person_name": {"value": None},
        "address": {"value": "Ankara"},
        "signature_present": {"value": True},
        "request": {"value": "Test"}
    }
    res_C = agent.check_missing_fields("bilgi_edinme", "bilgi_talebi", extracted_C)
    assert "person_name" in res_C["missing_fields"], "Test C Failed: person_name should be missing."

    # Test D: empty string -> missing
    extracted_D = {
        "person_name": {"value": ""},
        "address": {"value": "Ankara"},
        "signature_present": {"value": True},
        "request": {"value": "Test"}
    }
    res_D = agent.check_missing_fields("bilgi_edinme", "bilgi_talebi", extracted_D)
    assert "person_name" in res_D["missing_fields"], "Test D Failed: empty string should be missing."

    # Test E: signature unknown -> uncertain, doğrudan missing değil
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

    # Test F: needs_human_review true ama missing_fields=[]
    # Test E actually covers this. missing_fields is empty, but needs_human_review is True.
    assert len(res_E["missing_fields"]) == 0, "Test F Failed: missing fields should be empty."

    # Test G: missing_fields=["address"] ama needs_human_review false
    res_G = agent.check_missing_fields("bilgi_edinme", "bilgi_talebi", extracted_A)
    assert "address" in res_G["missing_fields"], "Test G Failed: address should be missing."
    assert res_G["needs_human_review"] is False, "Test G Failed: should not need human review for a missing textual field."
    
    print("All Regression Tests Passed!")

if __name__ == "__main__":
    run_tests()
