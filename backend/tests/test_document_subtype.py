import pytest
from unittest.mock import MagicMock
from backend.app.agents.document_agent import DocumentAgent
from backend.app.institutions.profile_loader import InstitutionProfile

class MockLLM:
    def __init__(self, response_json: str, *args, **kwargs):
        self.response_json = response_json

    def chat(self, *args, **kwargs):
        return self.response_json

    def get_provider_name(self):
        return "mock"

    def get_model_name(self):
        return "mock"

@pytest.fixture
def mock_kaymakamlik_profile():
    return InstitutionProfile(
        kurum_adi="Test Kaymakamlık",
        kurum_turu="kaymakamlik",
        evrak_turleri=["dilekce", "bilgi_edinme", "sosyal_yardim_basvuru", "ihale_itirazi"],
        birimler=[]
    )

@pytest.fixture
def mock_belediye_profile():
    return InstitutionProfile(
        kurum_adi="Test Belediye",
        kurum_turu="belediye",
        evrak_turleri=["dilekce", "ruhsat_basvurusu", "imar_talebi", "sikayet"],
        birimler=[]
    )

# 1. Kaymakamlık bilgi edinme
def test_kaymakamlik_bilgi_edinme(mock_kaymakamlik_profile):
    llm = MockLLM('{"document_type": "dilekce", "document_subtype": "bilgi_edinme", "process_intent": "bilgi_talebi"}')
    agent = DocumentAgent(llm=llm, institution_profile=mock_kaymakamlik_profile)
    res = agent.analyze("Tarafıma bilgi verilmesini arz ederim.")
    assert res["document_type"] == "dilekce"
    assert res["document_subtype"] == "bilgi_edinme"
    assert res["process_intent"] == "bilgi_talebi"

# 2. Kaymakamlık sosyal yardım
def test_kaymakamlik_sosyal_yardim(mock_kaymakamlik_profile):
    llm = MockLLM('{"document_type": "form", "document_subtype": "sosyal_yardim_basvuru", "process_intent": "basvuru"}')
    agent = DocumentAgent(llm=llm, institution_profile=mock_kaymakamlik_profile)
    res = agent.analyze("Yardım talep ediyorum.")
    assert res["document_type"] == "form"
    assert res["document_subtype"] == "sosyal_yardim_basvuru"
    assert res["process_intent"] == "basvuru"

# 3. Kaymakamlık ihale itirazı
def test_kaymakamlik_ihale_itirazi(mock_kaymakamlik_profile):
    llm = MockLLM('{"document_type": "dilekce", "document_subtype": "ihale_itirazi", "process_intent": "itiraz"}')
    agent = DocumentAgent(llm=llm, institution_profile=mock_kaymakamlik_profile)
    res = agent.analyze("İhaleye itiraz ediyorum.")
    assert res["document_type"] == "dilekce"
    assert res["document_subtype"] == "ihale_itirazi"
    assert res["process_intent"] == "itiraz"

# 4. Belediye ruhsat başvurusu
def test_belediye_ruhsat_basvurusu(mock_belediye_profile):
    llm = MockLLM('{"document_type": "form", "document_subtype": "ruhsat_basvurusu", "process_intent": "basvuru"}')
    agent = DocumentAgent(llm=llm, institution_profile=mock_belediye_profile)
    res = agent.analyze("Ruhsat başvurusu.")
    assert res["document_type"] == "form"
    assert res["document_subtype"] == "ruhsat_basvurusu"
    assert res["process_intent"] == "basvuru"

# 5. Belediye imar talebi
def test_belediye_imar_talebi(mock_belediye_profile):
    llm = MockLLM('{"document_type": "dilekce", "document_subtype": "imar_talebi", "process_intent": "basvuru"}')
    agent = DocumentAgent(llm=llm, institution_profile=mock_belediye_profile)
    res = agent.analyze("İmar durumu.")
    assert res["document_type"] == "dilekce"
    assert res["document_subtype"] == "imar_talebi"

# 6. Belediye şikâyet
def test_belediye_sikayet(mock_belediye_profile):
    llm = MockLLM('{"document_type": "dilekce", "document_subtype": "sikayet", "process_intent": "sikayet"}')
    agent = DocumentAgent(llm=llm, institution_profile=mock_belediye_profile)
    res = agent.analyze("Şikayetçiyim.")
    assert res["document_type"] == "dilekce"
    assert res["document_subtype"] == "sikayet"

# 7. Belge hiçbir profile subtype'a uymuyor
def test_no_matching_subtype(mock_belediye_profile):
    llm = MockLLM('{"document_type": "dilekce", "document_subtype": null, "process_intent": "diger"}')
    agent = DocumentAgent(llm=llm, institution_profile=mock_belediye_profile)
    res = agent.analyze("Bilinmeyen konu.")
    assert res["document_subtype"] is None
    assert res["needs_human_review"] is True

# 8. LLM profile dışı subtype döndürüyor
def test_llm_out_of_profile_subtype(mock_belediye_profile):
    # 'bilgi_edinme' is NOT in belediye profile
    llm = MockLLM('{"document_type": "dilekce", "document_subtype": "bilgi_edinme", "process_intent": "bilgi_talebi"}')
    agent = DocumentAgent(llm=llm, institution_profile=mock_belediye_profile)
    res = agent.analyze("Bana bilgi verin.")
    assert res["document_subtype"] is None
    assert res["needs_human_review"] is True
    # Ensure it doesn't crash and normalizes to None

# 9. Institution profile None
def test_profile_none():
    llm = MockLLM('{"document_type": "dilekce", "document_subtype": "bilgi_edinme", "process_intent": "bilgi_talebi"}')
    agent = DocumentAgent(llm=llm, institution_profile=None)
    res = agent.analyze("Bana bilgi verin.")
    assert res["document_subtype"] is None
    assert res["document_type"] == "dilekce"
    # Document type is dilekce, process intent is bilgi_talebi (not diger), so needs_human_review should be False here.
    # Note: needs_human_review logic for subtype applies only if profile exists and subtype is None.
    # But if profile is None, it defaults to original logic (False for dilekce/bilgi_talebi).
    assert res["needs_human_review"] is False

# 10. Empty document
def test_empty_document(mock_belediye_profile):
    agent = DocumentAgent(llm=MockLLM('{}'), institution_profile=mock_belediye_profile)
    res = agent.analyze("")
    assert res["document_subtype"] is None
    assert res["document_type"] == "diger"

# 11. MissingFieldAgent subtype precedence
from backend.app.agents.missing_field_agent import MissingFieldAgent

def test_missing_field_subtype_precedence():
    agent = MissingFieldAgent()
    # document_type="dilekce" normally requires 5 fields.
    # If subtype is "sosyal_yardim_basvuru", it requires ["person_name", "address", "signature_present", "phone"] (4 fields).
    ext = {}
    res = agent.check_missing_fields(
        document_type="dilekce",
        process_intent="basvuru",
        extracted_fields=ext,
        document_subtype="sosyal_yardim_basvuru"
    )
    assert "phone" in res["required_fields"]
    assert "subject" not in res["required_fields"] # subject is in dilekce but not in sosyal yardim
    assert "request" not in res["required_fields"] # request is in dilekce but not in sosyal yardim

# 12. Existing callers backward compatibility
def test_missing_field_backward_compatibility():
    agent = MissingFieldAgent()
    # Call without document_subtype
    ext = {}
    res = agent.check_missing_fields(
        document_type="dilekce",
        process_intent="basvuru",
        extracted_fields=ext
    )
    assert "subject" in res["required_fields"]
    assert "request" in res["required_fields"]
    assert "phone" not in res["required_fields"]
