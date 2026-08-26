import pytest
from unittest.mock import MagicMock
from backend.app.agents.extraction_agent import ExtractionAgent
from backend.app.llm.base import LLMClient

@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=LLMClient)
    llm.get_provider_name.return_value = "mock_provider"
    llm.get_model_name.return_value = "mock_model"
    # Varsayılan olarak geçerli bir boş JSON döndür
    llm.chat.return_value = "{}"
    return llm

@pytest.fixture
def agent(mock_llm):
    return ExtractionAgent(llm=mock_llm)

def test_empty_text(agent):
    res = agent.extract("")
    assert res["warnings"] == ["Metin boş."]
    assert res["needs_human_review"] is True
    assert res["fields"] == {}

def test_valid_tc(agent):
    # TC Validation (algoritmik): 10000000146 valid bir TC örneğidir. (1+0+0+0+1)*7 - (0+0+0+0) = 14 % 10 = 4. Wait, let me use a known valid TC or I can just check the method itself.
    # 10000000146 sum_odd=2, sum_even=0, check1=14%10=4. digits[9]=4. check2 = (2+0+4)%10 = 6. So 10000000146 is VALID.
    text = "TC: 10000000146"
    res = agent.extract(text)
    assert "national_id" in res["fields"]
    assert res["fields"]["national_id"]["value"] == "10000000146"
    assert "invalid_national_id_candidate" not in res["warnings"]

def test_invalid_tc(agent):
    # 11 haneli ama checksum tutmayan
    text = "TC: 12345678901"
    res = agent.extract(text)
    assert "national_id" not in res["fields"]
    assert "invalid_national_id_candidate" in res["warnings"]
    assert res["needs_human_review"] is True

def test_email_extraction(agent):
    text = "Lütfen ornek@example.com adresine yazın."
    res = agent.extract(text)
    assert res["fields"]["email"]["value"] == "ornek@example.com"
    assert res["fields"]["email"]["method"] == "regex"

def test_phone_extraction_and_normalization(agent):
    text = "Tel: +90 532 111 22 33"
    res = agent.extract(text)
    assert res["fields"]["phone"]["value"] == "05321112233"
    assert res["fields"]["phone"]["evidence"] == "+90 532 111 22 33"

def test_document_date_extraction(agent):
    text = "Tarih: 16.08.2026\nKonu: Bilgi talebi"
    res = agent.extract(text)
    assert res["fields"]["document_date"]["value"] == "2026-08-16"
    assert res["fields"]["document_date"]["evidence"] == "Tarih: 16.08.2026"

def test_document_number_extraction(agent):
    text = "Sayı: 2026/145\nTarih: 16.08.2026"
    res = agent.extract(text)
    assert res["fields"]["document_number"]["value"] == "2026/145"
    assert res["fields"]["document_number"]["evidence"] == "Sayı: 2026/145"

def test_document_context_reuse(agent):
    ctx = {
        "subject_excerpt": "Proje Harcamaları",
        "request_excerpt": "Belgelerin verilmesini arz ederim."
    }
    res = agent.extract("Metin", document_context=ctx)
    assert res["fields"]["subject"]["value"] == "Proje Harcamaları"
    assert res["fields"]["request"]["value"] == "Belgelerin verilmesini arz ederim."
    assert res["fields"]["subject"]["method"] == "document_agent"

def test_attachment_extraction(agent):
    text = "Ekler: 1. Başvuru Formu\nEk 2: Kimlik Fotokopisi\nEk yoktur."
    res = agent.extract(text)
    # "Ek yoktur" satırı filtrelenmeli
    attachments = res["fields"]["attachments"]["value"]
    assert len(attachments) == 2
    assert attachments[0]["name"] == "1. Başvuru Formu"

def test_signature_unknown(agent):
    text = "Sıradan bir metin, elektronik ibare bulunmuyor."
    res = agent.extract(text)
    assert res["fields"]["signature_present"]["status"] == "unknown"

def test_electronic_signature(agent):
    text = "Bu belge güvenli elektronik imza ile imzalanmıştır."
    res = agent.extract(text)
    assert res["fields"]["signature_present"]["value"] is True
    assert res["fields"]["signature_present"]["status"] == "present"


def test_turkish_dotted_capital_i_signature_is_detected(agent):
    res = agent.extract("İmza: Polat Madencilik adına Pelin Sönmez")

    assert res["fields"]["signature_present"]["value"] is True
    assert res["fields"]["signature_present"]["status"] == "present"
    assert res["fields"]["signature_present"]["evidence"] == "İmza"

def test_authority_document(agent):
    text = "Ekte yetki belgesi sunulmuştur."
    res = agent.extract(text)
    assert res["fields"]["authority_document_present"]["value"] is True

def test_llm_hallucination_reject(mock_llm):
    agent = ExtractionAgent(llm=mock_llm)
    # Metinde geçmeyen bir person_name döndürelim
    mock_llm.chat.return_value = '{"person_name": {"value": "Olmayan Kişi", "evidence": "Olmayan Kişi"}}'
    text = "Ahmet Yılmaz başvurdu."
    res = agent.extract(text)
    assert "person_name" not in res["fields"]
    assert "evidence_validation_failed_for_person_name" in res["warnings"]

def test_llm_invalid_json(mock_llm):
    agent = ExtractionAgent(llm=mock_llm)
    mock_llm.chat.return_value = "Ben json degilim"
    res = agent.extract("Test metni")
    assert "semantic_extraction_unavailable" in res["warnings"]
    assert res["needs_human_review"] is True

def test_llm_offline_fallback():
    # LLM None olsa bile (veya chat() hata verse bile), deterministik alanlar çalışmalı.
    # We will simulate LLM exception
    class BrokenLLM(LLMClient):
        def chat(self, *args, **kwargs):
            raise Exception("LLM is offline")
        def get_provider_name(self): return "broken"
        def get_model_name(self): return "broken"
        
    agent = ExtractionAgent(llm=BrokenLLM())
    try:
        agent.extract("Tel: 0532 111 22 33")
    except Exception:
        pytest.fail("Agent crashed when LLM is offline/raised exception")

def test_multi_line_address_marker_extraction(agent):
    text = "Adres: Örnek Mahallesi Çiçek Sokak No: 12\nKadıköy / İstanbul\n\n\nBaşka metinler"
    res = agent.extract(text)
    assert res["fields"]["address"]["method"] == "deterministic"
    assert "Kadıköy / İstanbul" in res["fields"]["address"]["value"]

def test_address_next_field_boundary(agent):
    text = "Adres: Örnek Mahallesi Çiçek Sokak No: 12\nKadıköy / İstanbul\nTelefon: 0532 111 22 33"
    res = agent.extract(text)
    address_val = res["fields"]["address"]["value"]
    assert "Kadıköy / İstanbul" in address_val
    assert "Telefon" not in address_val

def test_person_name_marker(agent):
    text = "Başvuru Sahibi: Mehmet Kaya\nAdres: ..."
    res = agent.extract(text)
    assert res["fields"]["person_name"]["method"] == "deterministic"
    assert res["fields"]["person_name"]["value"] == "Mehmet Kaya"

def test_deterministic_address_ignores_llm(mock_llm):
    agent = ExtractionAgent(llm=mock_llm)
    # LLM tamamen alakasız bir adres dönse bile:
    mock_llm.chat.return_value = '{"address": {"value": "LLM Adresi", "evidence": "LLM Adresi"}}'
    text = "Adres: Doğru Adres\nTelefon: 0532\nLLM Adresi metin içinde geçse bile."
    res = agent.extract(text)
    assert res["fields"]["address"]["method"] == "deterministic"
    assert res["fields"]["address"]["value"] == "Doğru Adres"

def test_address_semantic_fallback(mock_llm):
    agent = ExtractionAgent(llm=mock_llm)
    # Marker yok, bu yüzden LLM'e düşmeli
    mock_llm.chat.return_value = '{"address": {"value": "Örnek Mah.", "evidence": "Örnek Mah."}}'
    text = "Benim evim Örnek Mah. sınırlarında."
    res = agent.extract(text)
    assert res["fields"]["address"]["method"] == "llm"
    assert res["fields"]["address"]["value"] == "Örnek Mah."

def test_recipient_behavior(agent):
    text = "T.C.\nÖRNEK KAMU KURUMU\nBilgi Edinme Birimine"
    res = agent.extract(text)
    assert res["fields"]["recipient"]["method"] == "deterministic"
    assert res["fields"]["recipient"]["value"] == "Bilgi Edinme Birimine"
    # Subject shouldn't automatically be set to this just because it's a prominent header.
    # LLM might do it, but we deterministicly caught recipient.
    # We just check recipient logic works.

