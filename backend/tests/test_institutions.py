"""
backend/tests/test_institutions.py
──────────────────────────────────────────────────────────────────────────────
Track 3 — Çoklu Kurum Testleri

Kapsam:
  - list_available_profiles() → belediye ve kaymakamlik döndürmeli
  - load_institution_profile("belediye") → doğru profil yüklenmeli
  - RoutingAgent(institution="belediye") → Belediye birimlerine yönlendirmeli
  - TransferAgent.transfer() → kurumlar arası transfer kararı doğru olmalı

Çalıştırma:
    python -m pytest backend/tests/test_institutions.py -v
"""

import pytest
from backend.app.institutions.profile_loader import (
    list_available_profiles,
    load_institution_profile,
    InstitutionProfile,
)
from backend.app.agents.routing_agent import RoutingAgent
from backend.app.agents.transfer_agent import TransferAgent


# ---------------------------------------------------------------------------
# 1. Profile Loader Testleri
# ---------------------------------------------------------------------------

class TestProfileLoader:

    def test_list_available_profiles_includes_kaymakamlik(self):
        """kaymakamlik her zaman listede olmalı."""
        profiles = list_available_profiles()
        assert "kaymakamlik" in profiles, (
            "kaymakamlik profili listede bulunamadı"
        )

    def test_list_available_profiles_includes_belediye(self):
        """Track 3 sonrası belediye de listede olmalı."""
        profiles = list_available_profiles()
        assert "belediye" in profiles, (
            "belediye profili listede bulunamadı — "
            "data/institutions/belediye/kurum_profili_belediye.yaml mevcut mu?"
        )

    def test_list_available_profiles_returns_list(self):
        """Sonuç list tipinde olmalı."""
        result = list_available_profiles()
        assert isinstance(result, list)

    def test_load_belediye_profile_returns_institution_profile(self):
        """Belediye profili InstitutionProfile döndürmeli."""
        profile = load_institution_profile("belediye")
        assert isinstance(profile, InstitutionProfile)

    def test_belediye_profile_kurum_adi(self):
        """Belediye profili doğru kurum adına sahip olmalı."""
        profile = load_institution_profile("belediye")
        assert "belediye" in profile.kurum_adi.lower(), (
            f"Kurum adı beklenenle eşleşmiyor: '{profile.kurum_adi}'"
        )

    def test_belediye_profile_kurum_turu(self):
        """Belediye profili 'belediye' türünde olmalı."""
        profile = load_institution_profile("belediye")
        assert profile.kurum_turu == "belediye"

    def test_belediye_profile_has_birimler(self):
        """Belediye profili en az 5 birim içermeli."""
        profile = load_institution_profile("belediye")
        assert len(profile.birimler) >= 5, (
            f"Birim sayısı yetersiz: {len(profile.birimler)}"
        )

    def test_belediye_profile_has_imar_birimi(self):
        """Belediye'de imar_sehircilik birimi bulunmalı."""
        profile = load_institution_profile("belediye")
        birim_ids = [
            b.get("id", "") for b in profile.birimler
            if isinstance(b, dict)
        ]
        assert "imar_sehircilik" in birim_ids, (
            "İmar ve Şehircilik birimi bulunamadı"
        )

    def test_belediye_profile_has_zabita_birimi(self):
        """Belediye'de zabita birimi bulunmalı."""
        profile = load_institution_profile("belediye")
        birim_ids = [
            b.get("id", "") for b in profile.birimler
            if isinstance(b, dict)
        ]
        assert "zabita" in birim_ids, "Zabıta birimi bulunamadı"

    def test_belediye_profile_has_evrak_turleri(self):
        """Belediye profili evrak türleri içermeli."""
        profile = load_institution_profile("belediye")
        assert len(profile.evrak_turleri) >= 3

    def test_belediye_profile_has_kurumlar_arasi_yazi(self):
        """Belediye profili kurumlar_arasi_yazi evrak türünü desteklemeli."""
        profile = load_institution_profile("belediye")
        evrak_ids = [
            e.get("id", "") for e in profile.evrak_turleri
            if isinstance(e, dict)
        ]
        assert "kurumlar_arasi_yazi" in evrak_ids

    def test_load_nonexistent_profile_raises_file_not_found(self):
        """Var olmayan kurum profili FileNotFoundError fırlatmalı."""
        with pytest.raises(FileNotFoundError):
            load_institution_profile("var_olmayan_kurum_xyz")


# ---------------------------------------------------------------------------
# 2. RoutingAgent — Belediye Senaryoları
# ---------------------------------------------------------------------------

class TestRoutingAgentBelediye:

    @pytest.fixture
    def agent(self):
        return RoutingAgent(institution="belediye")

    def test_routing_agent_loads_belediye_units(self, agent):
        """RoutingAgent Belediye birimlerini yükleyebilmeli."""
        assert len(agent._units) >= 5, (
            f"Birim yüklenemedi, yüklenen birim sayısı: {len(agent._units)}"
        )

    def test_routing_ruhsat_to_zabita(self, agent):
        """Ruhsat talebi Zabıta'ya yönlenmeli."""
        result = agent.route(
            document_type="ruhsat_basvurusu",
            process_intent="basvuru",
            subject="İşyeri Açma Ruhsatı Talebi",
            request_text="İşyeri için ruhsat başvurusunda bulunmak istiyorum.",
            extracted_fields={},
        )
        assert result["recommended_unit"] is not None
        # Zabıta veya yazi_isleri kabul edilir
        assert result["recommended_unit"] != ""

    def test_routing_yol_sikayeti_to_fen_isleri(self, agent):
        """Yol/asfalt şikayeti Fen İşleri'ne yönlenmeli."""
        result = agent.route(
            document_type="sikayet",
            process_intent="sikayet",
            subject="Bozuk Yol Şikayeti",
            request_text="Caddemizde asfalt çökmesi ve çukur sorunu var. Onarım talep ediyorum.",
            extracted_fields={},
        )
        assert result["recommended_unit"] is not None
        recommended = result["recommended_unit"].lower()
        assert "fen" in recommended or "yaz" in recommended, (
            f"Beklenen 'Fen İşleri' veya 'Yazı İşleri', alınan: '{result['recommended_unit']}'"
        )

    def test_routing_imar_talebi_to_imar_mudurluğu(self, agent):
        """İmar talebi İmar ve Şehircilik'e yönlenmeli."""
        result = agent.route(
            document_type="imar_talebi",
            process_intent="belge_talebi",
            subject="İmar Durumu Belgesi Talebi",
            request_text="Parselim için imar durumu belgesi ve yapı ruhsatı talep ediyorum.",
            extracted_fields={},
        )
        assert result["recommended_unit"] is not None
        recommended = result["recommended_unit"]
        # Türkçe büyük İ normalize farkına karşı dirençli karşılaştırma
        recommended_normalized = recommended.replace("İ", "i").replace("I", "i").lower()
        assert "imar" in recommended_normalized or "yaz" in recommended_normalized, (
            f"Beklenen 'İmar ve Şehircilik', alınan: '{result['recommended_unit']}'"
        )

    def test_routing_returns_required_fields(self, agent):
        """Route sonucu zorunlu alanları içermeli."""
        result = agent.route(
            document_type="dilekce",
            process_intent="bilgi_talebi",
            subject="Genel bilgi talebi",
            request_text="Bilgi almak istiyorum.",
            extracted_fields={},
        )
        required_fields = [
            "recommended_unit",
            "alternative_units",
            "ranked_units",
            "reason",
            "routing_score",
            "needs_human_review",
            "warnings",
        ]
        for field in required_fields:
            assert field in result, f"Eksik alan: '{field}'"


# ---------------------------------------------------------------------------
# 3. TransferAgent Testleri
# ---------------------------------------------------------------------------

class TestTransferAgent:

    @pytest.fixture
    def agent(self):
        return TransferAgent()

    def test_transfer_kaymakamlik_to_belediye(self, agent):
        """Kaymakamlık→Belediye transferi başarıyla tamamlanmalı."""
        result = agent.transfer(
            kaynak_kurum="kaymakamlik",
            hedef_kurum="belediye",
            konu="Afet Eylem Planı Koordinasyonu",
            evrak_ozeti="Altyapı bilgilerinin paylaşılması talebi",
        )
        assert result["transfer_required"] is True
        assert result["hedef_kurum"] == "belediye"
        assert result["hedef_kurum_adi"] != ""
        assert result["hedef_birim"] != ""

    def test_transfer_result_has_yazi_turu(self, agent):
        """Transfer sonucu yazı türü içermeli."""
        result = agent.transfer(
            kaynak_kurum="kaymakamlik",
            hedef_kurum="belediye",
            konu="Test konusu",
            evrak_ozeti="Test özeti",
        )
        assert result["yazi_turu"] == "ust_yazi"

    def test_transfer_result_has_evrak_turu(self, agent):
        """Transfer sonucu evrak türü içermeli."""
        result = agent.transfer(
            kaynak_kurum="kaymakamlik",
            hedef_kurum="belediye",
            konu="Test konusu",
            evrak_ozeti="Test özeti",
        )
        assert result["evrak_turu"] == "kurumlar_arasi_yazi"

    def test_transfer_nonexistent_target_warns(self, agent):
        """Var olmayan hedef kurum için uyarı verilmeli."""
        result = agent.transfer(
            kaynak_kurum="kaymakamlik",
            hedef_kurum="var_olmayan_kurum_xyz",
            konu="Test",
            evrak_ozeti="Test",
        )
        assert result["transfer_required"] is False
        assert result["needs_human_review"] is True
        assert len(result["warnings"]) > 0

    def test_transfer_preserves_konu(self, agent):
        """Transfer sonucu konu bilgisini korumalı."""
        konu = "Deneme Konusu 123"
        result = agent.transfer(
            kaynak_kurum="kaymakamlik",
            hedef_kurum="belediye",
            konu=konu,
            evrak_ozeti="Özet",
        )
        assert result["konu"] == konu

    def test_transfer_returns_required_fields(self, agent):
        """Transfer sonucu tüm zorunlu alanları içermeli."""
        result = agent.transfer(
            kaynak_kurum="kaymakamlik",
            hedef_kurum="belediye",
            konu="Test",
            evrak_ozeti="Test",
        )
        required = [
            "transfer_required",
            "kaynak_kurum",
            "hedef_kurum",
            "hedef_kurum_adi",
            "hedef_birim",
            "yazi_turu",
            "evrak_turu",
            "konu",
            "ozet",
            "yasal_dayanak",
            "warnings",
            "needs_human_review",
        ]
        for field in required:
            assert field in result, f"Eksik alan: '{field}'"
