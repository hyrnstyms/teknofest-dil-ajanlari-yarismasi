import pytest
from backend.app.agents.missing_field_agent import MissingFieldAgent

@pytest.fixture
def agent():
    return MissingFieldAgent()

def test_missing_fields_happy_path(agent):
    # 1. bilgi edinme + adres mevcut
    extracted = {
        "person_name": {"value": "Mehmet Kaya"},
        "address": {"value": "Örnek Mah."},
        "signature_present": {"value": True, "status": "present"}
    }
    res = agent.check_missing_fields("dilekce", "bilgi_talebi", extracted)
    assert "person_name" in res["present_fields"]
    assert "address" in res["present_fields"]
    assert "signature_present" in res["present_fields"]
    assert len(res["missing_fields"]) == 0
    assert len(res["uncertain_fields"]) == 0
    assert res["needs_human_review"] is False

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
    assert "signature_present durumu yalnızca metin üzerinden doğrulanamadı." in res["warnings"]

def test_missing_fields_empty_extraction(agent):
    # 4. empty extraction
    extracted = {}
    res = agent.check_missing_fields("dilekce", "bilgi_talebi", extracted)
    assert "person_name" in res["missing_fields"]
    assert "address" in res["missing_fields"]
    assert "signature_present" in res["uncertain_fields"]
    assert res["needs_human_review"] is True

def test_missing_fields_legal_evidence_present(agent):
    # 5. legal evidence mevcut
    extracted = {"person_name": {"value": "Mehmet Kaya"}, "address": {"value": "Örnek Mah."}, "signature_present": {"value": True, "status": "present"}}
    legal_analysis = {
        "evidence": ["Some verified text"],
        "sources": [{"law_number": "4982", "article": "6", "text": "Başvuru sahibinin adı ve adresi zorunludur."}]
    }
    res = agent.check_missing_fields("dilekce", "bilgi_talebi", extracted, legal_analysis)
    assert len(res["legal_basis"]) == 1
    assert res["legal_basis"][0]["law_number"] == "4982"
    assert res["legal_basis"][0]["validated"] is True
    assert not any("Zorunlu alanlara" in w for w in res["warnings"])

def test_missing_fields_legal_evidence_missing(agent):
    # 6. legal evidence yok
    extracted = {"person_name": {"value": "Mehmet Kaya"}, "address": {"value": "Örnek Mah."}, "signature_present": {"value": True, "status": "present"}}
    res = agent.check_missing_fields("dilekce", "bilgi_talebi", extracted)
    assert len(res["legal_basis"]) == 0
    assert any("Zorunlu alanlara" in w for w in res["warnings"])

def test_missing_fields_unknown_intent(agent):
    # 7. bilinmeyen intent
    extracted = {"person_name": {"value": "Mehmet Kaya"}}
    res = agent.check_missing_fields("diger", "bilinmeyen_islem", extracted)
    assert len(res["required_fields"]) == 0
    assert any("bulunamadı" in w for w in res["warnings"])
