"""
backend/tests/official_writing/test_context_adapter.py
"""

import pytest
from typing import Any
from unittest.mock import MagicMock, patch

from backend.app.official_writing.context_adapter import build_official_writing_context
from backend.app.institutions.profile_loader import InstitutionProfile


@pytest.fixture
def writing_agent():
    """WritingAgent'ı Qdrant/Ollama bağlantısı olmadan başlat."""
    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = []
    with patch("backend.app.agents.writing_agent.Retriever", return_value=mock_retriever):
        from backend.app.agents.writing_agent import WritingAgent
        return WritingAgent(retriever=mock_retriever)

def mock_state() -> dict[str, Any]:
    return {
        "extraction": {
            "fields": {},
            "subject": {"value": "Extraction Subject", "evidence": []},
            "document_number": {"value": "INCOMING-123", "evidence": []},
            "document_date": {"value": "15.08.2026", "evidence": []},
            "person_name": {"value": "Ahmet Yılmaz", "evidence": []},
            "institution": {"value": "Diğer Kurum", "evidence": []}
        }
    }

def mock_draft() -> dict[str, Any]:
    return {
        "subject": "Writing Generated Subject",
        "body": "Birinci paragraf.\nİkinci paragraf.",
        "recipient": "Açık Hedef Kurum",
        "sender_unit": "yazi_isleri",
        "verified_facts_used": {}
    }

def test_context_adapter_sayi_tarih_missing():
    # Kural 2: Outgoing sayi/tarih uydurulmaz, incoming kullanılmaz
    state = mock_state()
    draft = mock_draft()
    
    res = build_official_writing_context(draft, state, "ust_yazi")
    
    ctx = res["context"]
    missing = res["missing_required_fields"]
    
    assert ctx["sayi"] == ""
    assert ctx["tarih"] == ""
    assert "sayi" in missing
    assert "tarih" in missing

def test_context_adapter_cevap_yazisi_ilgi_mapping():
    # Kural 3: Cevap yazısında incoming evrak sayı/tarihi ilgi'ye map edilir
    state = mock_state()
    draft = mock_draft()
    
    res = build_official_writing_context(draft, state, "cevap_yazisi")
    
    ctx = res["context"]
    assert "ilgi" in ctx
    assert ctx["ilgi"][0]["sayi"] == "INCOMING-123"
    assert ctx["ilgi"][0]["tarih"] == "15.08.2026"
    assert "extraction.document_date + extraction.document_number" in res["source_map"]["ilgi"]

def test_context_adapter_signer_missing():
    # Kural 4: Signer yok, isim/unvan uydurulmuyor
    state = mock_state()
    draft = mock_draft()
    
    res = build_official_writing_context(draft, state, "ust_yazi")
    missing = res["missing_required_fields"]
    
    assert "imza.ad_soyad" in missing
    assert "imza.unvan" in missing

def test_context_adapter_routing_unit_resolved():
    # Kural 5: routing unit id gerçek display name'e çözülüyor
    # 'yazi_isleri' ID'si kurum profilinde var, "Yazı İşleri Müdürlüğü"ne çözülmeli
    state = mock_state()
    draft = mock_draft()
    draft["sender_unit"] = "yazi_isleri"
    
    res = build_official_writing_context(draft, state, "ust_yazi")
    ctx = res["context"]
    
    # "Yazı İşleri Müdürlüğü" from the real kaymakamlik profile
    assert ctx["tc_baslik"]["birim_adi"] == "Yazı İşleri Müdürlüğü"
    assert "profile.birimler" in res["source_map"]["tc_baslik.birim_adi"]

def test_context_adapter_unknown_routing_unit():
    # Kural 6: bilinmeyen routing unit kurum/birim uydurulmuyor
    state = mock_state()
    draft = mock_draft()
    draft["sender_unit"] = "bilinmeyen_bir_id"
    
    res = build_official_writing_context(draft, state, "ust_yazi")
    
    # Resolvers fallback to using the ID itself if explicit, but warn
    assert "Sender unit 'bilinmeyen_bir_id' kurum profilinde bulunamadı." in res["warnings"]

def test_context_adapter_eksik_bilgi_talebi(writing_agent):
    # Kural 7: eksik_bilgi_talebi -> template motoru zorlanmıyor
    # _try_official_render method returns early
    res = writing_agent._try_official_render(mock_draft(), "eksik_bilgi_talebi", mock_state())
    
    assert res["official_render"]["attempted"] is False

def test_context_adapter_renderer_error_fallback(writing_agent, monkeypatch):
    # Kural 8: renderer hata -> mevcut rendered_text korunur
    state = mock_state()
    draft = mock_draft()
    
    def mock_build(*args, **kwargs):
        raise Exception("Test crash")
        
    monkeypatch.setattr("backend.app.agents.writing_agent.build_official_writing_context", mock_build)
    
    res = writing_agent._try_official_render(draft, "ust_yazi", state)
    
    # It should not crash, it should return warning
    assert "Context adapter hatası: Test crash" in res["official_render_warning"]
    assert res["official_render"]["attempted"] is True
    assert res["official_render"]["success"] is False

def test_context_adapter_source_map():
    # Kural 9: source_map doğru provenance gösteriyor
    state = mock_state()
    draft = mock_draft()
    draft["sender_unit"] = "yazi_isleri"
    
    res = build_official_writing_context(draft, state, "ust_yazi")
    
    sm = res["source_map"]
    assert "extraction.subject" in sm["konu"]
    assert "draft.body (split)" in sm["metin_paragraflari"]
    assert "profile.birimler" in sm["tc_baslik.birim_adi"]

def test_try_official_render_skips_on_missing_signer_sayi_tarih(writing_agent):
    # Adapter imza/sayi/tarih gibi alanları kasten siliyor.
    # Bu nedenle _try_official_render'ın exception fırlatmadan "atlandı" uyarısı dönmesi beklenir.
    res = writing_agent._try_official_render(mock_draft(), "ust_yazi", mock_state())
    
    assert res["official_render"]["attempted"] is True
    assert res["official_render"]["success"] is False
    assert "Kritik context alanları eksik" in res["official_render_warning"]
    assert "sayi" in res["official_render_warning"]
    assert "imza.ad_soyad" in res["official_render_warning"]

def test_try_official_render_success_with_fake_fixture(writing_agent, monkeypatch):
    # Tamamen kurgusal (fake) bir context dönen mock adapter
    def mock_build_context(*args, **kwargs):
        return {
            "context": {
                "tc_baslik": {"idare_adi": "TEST KURUMU", "birim_adi": "Test Birimi"},
                "sayi": "12345",
                "tarih": "01.01.2026",
                "konu": "Test Konusu",
                "muhatap": {"tur": "kurum", "isim": "HEDEF KURUM"},
                "muhatap_turu": "kurum_ust",
                "metin_paragraflari": ["Paragraf 1"],
                "imza": {"ad_soyad": "Ahmet Yılmaz", "unvan": "Müdür", "yetki_turu": "normal"},
                "iletisim": {"adres": "", "irtibat": ""},
                "ekler": [],
                "dagitim": []
            },
            "missing_required_fields": [],
            "warnings": [],
            "source_map": {},
            "fallback_policies": {}
        }
        
    monkeypatch.setattr("backend.app.agents.writing_agent.build_official_writing_context", mock_build_context)
    
    res = writing_agent._try_official_render(mock_draft(), "ust_yazi", mock_state())
    
    assert res.get("official_render_warning") is None or res.get("official_render_warning") == ""
    assert res["official_render"]["success"] is True
    assert "TEST KURUMU" in res["official_rendered_text"]
    assert "Ahmet Yılmaz" in res["official_rendered_text"]
