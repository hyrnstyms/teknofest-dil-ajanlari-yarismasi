import pytest
from backend.app.agents.missing_field_agent import MissingFieldAgent

from backend.app.institutions.profile_loader import InstitutionProfile

@pytest.fixture
def agent():
    return MissingFieldAgent()

@pytest.fixture
def mock_profile():
    return InstitutionProfile(
        kurum_adi="Test Kurum",
        kurum_turu="test",
        evrak_turleri=[
            {
                "id": "bilgi_edinme",
                "required_fields": ["person_name", "request"]
            }
        ]
    )

def test_missing_fields_happy_path(agent):
    # 1. bilgi edinme + adres mevcut
    extracted = {
        "person_name": {"value": "Mehmet Kaya"},
        "address": {"value": "Örnek Mah."},
        "signature_present": {"value": True, "status": "present"},
        "subject": {"value": "Bilgi talebi"},
        "request": {"value": "Başvuru hakkında bilgi verilmesini istiyorum."}
    }
    res = agent.check_missing_fields("dilekce", "bilgi_talebi", extracted)
    assert res["required_fields"] == [
        "person_name",
        "address",
        "signature_present",
        "subject",
        "request",
    ]
    assert "person_name" in res["present_fields"]
    assert "address" in res["present_fields"]
    assert "signature_present" in res["present_fields"]
    assert len(res["missing_fields"]) == 0
    assert len(res["uncertain_fields"]) == 0
    assert res["needs_human_review"] is False
    assert res["field_results"]["signature_present"]["status"] == "present"

def test_missing_fields_profile_driven(agent, mock_profile):
    extracted = {
        "person_name": {"value": "Mehmet Kaya"}
    }
    # For bilgi_edinme in mock_profile, required are person_name, request
    res = agent.check_missing_fields("dilekce", "bilgi_talebi", extracted, document_subtype="bilgi_edinme", institution_profile=mock_profile)
    assert res["requirement_source"] == "profile"
    assert res["required_fields"] == ["person_name", "request"]
    assert "request" in res["missing_fields"]
    
def test_missing_fields_profile_driven_fallback(agent, mock_profile):
    extracted = {}
    # sikayet not in mock_profile, so it should fallback to legacy dilekce + process_intent rules
    res = agent.check_missing_fields("dilekce", "sikayet", extracted, document_subtype="sikayet", institution_profile=mock_profile)
    assert res["requirement_source"] == "legacy_fallback"
    assert "signature_present" in res["required_fields"]

def test_missing_fields_address_missing(agent):
    # 2. bilgi edinme + adres eksik
    extracted = {
        "person_name": {"value": "Mehmet Kaya"},
        "signature_present": {"value": True, "status": "present"}
    }
    res = agent.check_missing_fields("dilekce", "bilgi_talebi", extracted)
    assert "address" in res["missing_fields"]
    assert len(res["uncertain_fields"]) == 0
    assert res["needs_human_review"] is False
    assert res["field_results"]["address"]["status"] == "missing"

def test_missing_fields_signature_unknown(agent):
    # 3. signature unknown
    extracted = {
        "person_name": {"value": "Mehmet Kaya"},
        "address": {"value": "Örnek Mah."},
        "signature_present": {"value": None, "status": "unknown"}
    }
    res = agent.check_missing_fields("dilekce", "bilgi_talebi", extracted)
    assert "signature_present" in res["uncertain_fields"]
    assert "signature_present" not in res["missing_fields"]
    assert res["needs_human_review"] is True
    assert res["warnings"] == []
    assert res["field_results"]["signature_present"]["status"] == "uncertain"
    assert res["field_results"]["signature_present"]["reason"] == "Status is unknown."

def test_missing_fields_signature_explicit_false(agent):
    # 4. signature explicitly false -> missing
    extracted = {
        "person_name": {"value": "Mehmet Kaya"},
        "address": {"value": "Örnek Mah."},
        "signature_present": {"value": False, "status": "missing"}
    }
    res = agent.check_missing_fields("dilekce", "bilgi_talebi", extracted)
    assert "signature_present" in res["missing_fields"]
    assert "signature_present" not in res["uncertain_fields"]
    assert res["needs_human_review"] is False
    assert res["field_results"]["signature_present"]["status"] == "missing"

def test_missing_fields_empty_extraction(agent):
    # 5. empty extraction
    extracted = {}
    res = agent.check_missing_fields("dilekce", "bilgi_talebi", extracted)
    assert "person_name" in res["missing_fields"]
    assert "address" in res["missing_fields"]
    assert "signature_present" in res["uncertain_fields"]
    assert res["needs_human_review"] is True

def test_missing_fields_legal_evidence_present(agent):
    # 6. doğrulanmış legal evidence
    extracted = {"person_name": {"value": "Mehmet Kaya"}, "address": {"value": "Örnek Mah."}, "signature_present": {"value": True, "status": "present"}}
    legal_analysis = {
        "evidence": ["Başvuru sahibinin adı ve adresi zorunludur."],
        "sources": [{"law_number": "4982", "article": "6", "text": "Başvuru sahibinin adı ve adresi zorunludur."}]
    }
    res = agent.check_missing_fields("dilekce", "bilgi_talebi", extracted, legal_analysis)
    assert len(res["legal_basis"]) == 1
    assert res["legal_basis"][0]["evidence"] == "Başvuru sahibinin adı ve adresi zorunludur."
    assert res["legal_basis"][0]["validated"] is True
    assert not any("Zorunlu alanlara" in w for w in res["warnings"])

def test_missing_fields_legal_evidence_sources_only(agent):
    # 7. sources var evidence yok -> 4982/Madde6 UYDURULMUYOR
    extracted = {"person_name": {"value": "Mehmet Kaya"}, "address": {"value": "Örnek Mah."}, "signature_present": {"value": True, "status": "present"}}
    legal_analysis = {
        "evidence": [],
        "sources": [{"law_number": "4982", "article": "6", "text": "Başvuru sahibinin adı ve adresi zorunludur."}]
    }
    res = agent.check_missing_fields("dilekce", "bilgi_talebi", extracted, legal_analysis)
    assert len(res["legal_basis"]) == 0
    assert res["warnings"] == []

def test_missing_fields_legal_evidence_missing(agent):
    # 8. legal evidence yok
    extracted = {"person_name": {"value": "Mehmet Kaya"}, "address": {"value": "Örnek Mah."}, "signature_present": {"value": True, "status": "present"}}
    res = agent.check_missing_fields("dilekce", "bilgi_talebi", extracted)
    assert len(res["legal_basis"]) == 0
    assert res["warnings"] == []

def test_missing_fields_unknown_intent(agent):
    # 9. unknown rule combination
    extracted = {"person_name": {"value": "Mehmet Kaya"}}
    res = agent.check_missing_fields("diger", "bilinmeyen_islem", extracted)
    assert res["required_fields"] == [
        "person_name",
        "signature_present",
        "subject",
        "request",
    ]
    assert res["present_fields"] == ["person_name"]
    assert res["missing_fields"] == ["subject", "request"]
    assert res["uncertain_fields"] == ["signature_present"]
    assert res["needs_human_review"] is True
    assert res["warnings"] == []
