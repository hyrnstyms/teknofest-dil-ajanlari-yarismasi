"""
backend/tests/test_routing_agent.py
────────────────────────────────────────────────────────────────
RoutingAgent V2 testleri.

Source-of-truth: data/institutions/kaymakamlik/kurum_profili_kaymakamlik.yaml
unit_registry.json KULLANILMIYOR.

Test hedefleri (Karar Belgesi §18):
  1. Profil 9 birim yükleniyor
  2. RoutingAgent Kaymakamlık birimlerini kullanıyor
  3. Eski IT/Öğrenci İşleri registry kullanılmıyor
  4. Top-3 ranked_units çalışıyor
  5. Ambiguity detection çalışıyor
  6. QualityAgent profile-dışı unit'i yakalıyor
  7. Routing ve Quality aynı profili kullanıyor
"""

import pytest
from backend.app.agents.routing_agent import RoutingAgent
from backend.app.agents.quality_agent import QualityAgent
from backend.app.institutions.profile_loader import load_institution_profile

_INSTITUTION = "kaymakamlik"


@pytest.fixture
def agent():
    return RoutingAgent(_INSTITUTION)


@pytest.fixture
def quality_agent():
    return QualityAgent(_INSTITUTION)


# ------------------------------------------------------------------
# 1. Profil 9 birim yükleniyor
# ------------------------------------------------------------------
def test_profile_loads_9_units(agent):
    units = agent._units
    assert len(units) == 9, (
        f"Kaymakamlık profilinde 9 birim bekleniyor, {len(units)} bulundu."
    )


# ------------------------------------------------------------------
# 2. Kaymakamlık birimleri kullanılıyor
# ------------------------------------------------------------------
def test_routing_uses_kaymakamlik_units(agent):
    unit_names = {u["name"] for u in agent._units}
    assert "Yazı İşleri Müdürlüğü" in unit_names
    assert "İlçe Nüfus Müdürlüğü" in unit_names
    assert "Sosyal Yardımlaşma ve Dayanışma Vakfı (SYDV)" in unit_names


# ------------------------------------------------------------------
# 3. Eski unit_registry (IT / Öğrenci İşleri vb.) kullanılmıyor
# ------------------------------------------------------------------
def test_old_registry_units_not_present(agent):
    unit_names = {u["name"] for u in agent._units}
    assert "IT" not in unit_names
    assert "Öğrenci İşleri" not in unit_names
    assert "İnsan Kaynakları" not in unit_names
    assert "Hukuk Birimi" not in unit_names  # YAML'daki değil eski registry'deki


# ------------------------------------------------------------------
# 4. Top-3 ranked_units çalışıyor
# ------------------------------------------------------------------
def test_routing_ranked_units_top3(agent):
    res = agent.route(
        "dilekce",
        "belge_talebi",
        "Nüfus kaydı talebi",
        "Nüfus kaydımı görmek istiyorum",
        {},
    )
    assert len(res["ranked_units"]) >= 1
    assert "name" in res["ranked_units"][0]
    assert "score" in res["ranked_units"][0]
    assert "unit_id" in res["ranked_units"][0]


# ------------------------------------------------------------------
# 5. Ambiguity detection çalışıyor
# ------------------------------------------------------------------
def test_routing_ambiguity_detected(agent):
    # Gerçek kaymakamlık birimlerinden düşük skor gerektiren durum
    res = agent.route(
        "dilekce",
        "",               # intent yok → düşük skor
        "genel başvuru",
        "yardım almak istiyorum",
        {},
    )
    # Score < 30 → needs_human_review
    if res["routing_score"] < 30:
        assert res["needs_human_review"] is True
    # Ambiguity ya da no_strong_match olabilir, her iki durum da geçerli
    assert res["reason"] is not None


# ------------------------------------------------------------------
# 6. QualityAgent profile-dışı unit'i yakalıyor
# ------------------------------------------------------------------
def test_quality_catches_invalid_unit(quality_agent):
    # Var olmayan bir birim ismi
    fake_routing = {
        "recommended_unit": "Hayali Birim XYZ",
        "needs_human_review": False,
        "ambiguity_reason": None,
    }
    result = quality_agent.check_quality(
        document={"document_type": "dilekce", "process_intent": "basvuru"},
        extraction={"fields": {"person_name": {"value": "Test", "evidence": "txt"}}},
        legal_analysis={"evidence": ["3071"], "sources": []},
        missing_fields={"present_fields": ["person_name"], "missing_fields": [], "uncertain_fields": [], "needs_human_review": False},
        summary={"structured_summary": {"applicant": "Test"}},
        routing=fake_routing,
        draft=None,
        human_review={"required": False},
    )
    routing_check = result["checks"].get("routing", {})
    assert routing_check.get("status") == "fail", (
        "Profile dışı birim 'fail' statüsü vermeli."
    )


# ------------------------------------------------------------------
# 7. Routing ve Quality aynı profili kullanıyor
# ------------------------------------------------------------------
def test_routing_and_quality_same_profile(agent, quality_agent):
    routing_unit_names = {u["name"] for u in agent._units}
    quality_unit_names = quality_agent.valid_units
    assert routing_unit_names == quality_unit_names, (
        "RoutingAgent ve QualityAgent aynı birim setini kullanmalı."
    )


# ------------------------------------------------------------------
# 8. Profile boşsa fail-safe davranış
# ------------------------------------------------------------------
def test_routing_profile_empty_fallback(monkeypatch):
    agent = RoutingAgent(_INSTITUTION)
    agent._units = []  # simüle et
    res = agent.route("dilekce", "basvuru", "konu", "metin", {})
    assert res["recommended_unit"] is None
    assert res["needs_human_review"] is True
    assert "profile_empty" == res.get("ambiguity_reason")


# ------------------------------------------------------------------
# 9. Sosyal yardım → SYDV yönlendirme
# ------------------------------------------------------------------
def test_routing_sosyal_yardim(agent):
    res = agent.route(
        "dilekce",
        "basvuru",
        "Sosyal Yardım Başvurusu",
        "maddi destek almak istiyorum, muhtaçlık",
        {},
    )
    assert res["recommended_unit"] is not None
    assert res["routing_score"] >= 20
    assert "intent_score" in res["score_breakdown"]


# ------------------------------------------------------------------
# 10. Intent match skor katkısı
# ------------------------------------------------------------------
def test_routing_intent_score_contribution(agent):
    # 'basvuru' intent'i Nüfus için geçerli.
    res = agent.route(
        "dilekce",
        "basvuru",
        "Kimlik Başvurusu",
        "kimlik",
        {},
    )
    assert res["recommended_unit"] == "İlçe Nüfus Müdürlüğü"
    assert res["score_breakdown"]["intent_score"] == 20
    assert res["score_breakdown"]["keyword_score"] == 50
    assert res["score_breakdown"]["doc_type_score"] == 30


# ------------------------------------------------------------------
# 11. Keyword yok ama intent match var
# ------------------------------------------------------------------
def test_routing_intent_only_match(agent):
    # "sydv" için 'basvuru' geçerli. Metinde hiç anahtar kelime olmasın.
    res = agent.route(
        "dilekce",
        "basvuru",
        "Alakasız Konu",
        "alakasız metin içeriği",
        {},
    )
    # Dilekçe için üç tipik hedef birim 30 evrak türü + 20 intent
    # puanıyla eşit kalır. Güvenli davranış, rastgele birim seçmek yerine
    # otomatik öneriyi reddedip insan incelemesine yönlendirmektir.
    assert res["recommended_unit"] is None
    assert res["routing_score"] == 0
    assert res["needs_human_review"] is True
    assert len(res["ranked_units"]) == 3
    assert all(unit["score"] == 50 for unit in res["ranked_units"])


def test_high_confidence_document_exemplar_breaks_safe_tie(agent):
    res = agent.route(
        "dilekce",
        "basvuru",
        "Alakasız Konu",
        "alakasız metin içeriği",
        {},
        retrieved_documents=[{
            "score": 0.91,
            "institution": "kaymakamlik",
            "expected_unit": "sydv",
        }],
    )

    assert res["recommended_unit"] == "Sosyal Yardımlaşma ve Dayanışma Vakfı (SYDV)"
    assert any(
        detail["signal"] == "document_exemplar_match"
        for detail in res["score_breakdown"]["details"]
    )


def test_low_confidence_document_exemplar_is_ignored(agent):
    res = agent.route(
        "dilekce",
        "basvuru",
        "Alakasız Konu",
        "alakasız metin içeriği",
        {},
        retrieved_documents=[{
            "score": 0.54,
            "expected_unit": "sydv",
        }],
    )

    assert res["recommended_unit"] is None
    assert res["needs_human_review"] is True


def test_ambiguous_document_exemplars_are_ignored(agent):
    res = agent.route(
        "dilekce",
        "basvuru",
        "Alakasız Konu",
        "alakasız metin içeriği",
        {},
        retrieved_documents=[
            {"score": 0.70, "expected_unit": "sydv"},
            {"score": 0.68, "expected_unit": "nufus"},
        ],
    )

    assert res["recommended_unit"] is None
    assert res["needs_human_review"] is True


# ------------------------------------------------------------------
# 12. Yanlış intent unit'i boost etmiyor
# ------------------------------------------------------------------
def test_routing_wrong_intent_no_boost(agent):
    # 'cevap' intent'i nufus için GEÇERLİ DEĞİL
    # Sadece nufus kalsın, böylece best unit o olur ve breakdown'unu inceleyebiliriz
    agent._units = [u for u in agent._units if u["unit_id"] == "nufus"]
    
    res = agent.route(
        "dilekce",
        "cevap",
        "Kimlik",
        "kimlik",
        {},
    )
    # Kimlik kelimesi nufus ile eşleşiyor -> keyword_score = 50
    # Dilekçe evrak türü nufus için tipik hedef -> doc_type_score = 30
    # intent_score = 0 olmalı
    assert res["score_breakdown"]["intent_score"] == 0
    assert res["score_breakdown"]["keyword_score"] == 50
    assert res["score_breakdown"]["doc_type_score"] == 30


@pytest.mark.parametrize(
    ("subject", "request_text", "expected_unit"),
    [
        (
            "Okul güvenlik planları",
            "Planların İlçe Millî Eğitim Müdürlüğünce hazırlanması gerekmektedir.",
            "İlçe Millî Eğitim Müdürlüğü",
        ),
        (
            "Asayiş ihbarı",
            "Mahalledeki güvenlik ve asayiş sorununun incelenmesini talep ediyorum.",
            "İlçe Emniyet Müdürlüğü",
        ),
        (
            "Sağlık kuruluşu başvurusu",
            "Yeni sağlık ocağı ve sağlık raporu işlemleri hakkında bilgi talep ediyorum.",
            "İlçe Sağlık Müdürlüğü",
        ),
    ],
)
def test_kaymakamlik_routing_regression(
    subject,
    request_text,
    expected_unit,
):
    result = RoutingAgent(institution="kaymakamlik").route(
        document_type="diger",
        process_intent="bildirim",
        subject=subject,
        request_text=request_text,
        extracted_fields={},
    )

    assert result["recommended_unit"] == expected_unit
    assert result["needs_human_review"] is False


@pytest.mark.parametrize(
    ("document_type", "subject", "request_text", "expected_unit"),
    [
        (
            "sikayet",
            "Bozuk yol şikayeti",
            "Caddedeki çukur ve asfalt hasarının onarılmasını talep ediyorum.",
            "Fen İşleri Müdürlüğü",
        ),
        (
            "imar_talebi",
            "Yapı ruhsatı talebi",
            "Parselim için imar durumu ve yapı ruhsatı düzenlenmesini talep ediyorum.",
            "İmar ve Şehircilik Müdürlüğü",
        ),
        (
            "sikayet",
            "Çöp toplama şikayeti",
            "Mahallede biriken çöp ve atıkların temizlenmesini talep ediyorum.",
            "Temizlik İşleri Müdürlüğü",
        ),
    ],
)
def test_belediye_routing_regression(
    document_type,
    subject,
    request_text,
    expected_unit,
):
    result = RoutingAgent(institution="belediye").route(
        document_type=document_type,
        process_intent="sikayet",
        subject=subject,
        request_text=request_text,
        extracted_fields={},
    )

    assert result["recommended_unit"] == expected_unit
    assert result["needs_human_review"] is False


def test_generic_ruhsat_does_not_force_health_routing():
    result = RoutingAgent(institution="kaymakamlik").route(
        document_type="dilekce",
        process_intent="bilgi_talebi",
        subject="Ruhsat hakkında bilgi",
        request_text="Ruhsat başvurumun durumunu öğrenmek istiyorum.",
        extracted_fields={},
    )

    assert result["recommended_unit"] != "İlçe Sağlık Müdürlüğü"
    assert result["needs_human_review"] is True
    assert result["routing_score"] == 0
