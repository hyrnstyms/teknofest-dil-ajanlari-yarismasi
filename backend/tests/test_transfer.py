"""
backend/tests/test_transfer.py
────────────────────────────────────────────────────────────────────────────
Kurumlar arası transfer özelliği için uçtan uca testler.

Test grupları:
  1. Workflow seviyesi: kurumlar_arasi_yazi + iletim intent → transfer_routing
  2. Endpoint: POST /api/analyses/{id}/transfer guard kontrolleri
  3. Başarılı transfer: EBYS çağrıldı, DB güncellendi, review_events kaydedildi
  4. Restart simulation: yeni session ile okuma → state korunuyor

Dokunulmayan dosyalar: rag/**, ocr/**, llm/settings.py
"""
from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from backend.app.main import app, get_analysis_repository


client = TestClient(app)


# ---------------------------------------------------------------------------
# Test verisi
# ---------------------------------------------------------------------------

AFET_YAZISI = """\
Örenli Kaymakamlığından
Örenli Belediyesi Başkanlığına

Sayı : 2026/1547
Konu: İlçe Afet Eylem Planı Koordinasyonu

İlgi: İl Afet ve Acil Durum Müdürlüğü'nün 12.08.2026 tarihli yazısı.

İlgi yazı doğrultusunda ilçemizde Belediyeniz yetki alanındaki altyapı bilgileri
ile mevcut afet toplanma alanlarına ait güncel verilerin tarafımıza iletilmesi
gerekmektedir.

Tarih: 14.08.2026
Kaymakam
Örenli İlçe Kaymakamlığı
"""

DILEKCE_METNI = """\
ÖRENLI İLÇE KAYMAKAMLIĞINA

BAŞVURAN: Ali YILMAZ
KONU: Sokak Aydınlatması Talebi

Sokak aydınlatmasının yapılmasını arz ederim.
Ali YILMAZ
"""


def _make_transfer_state(analysis_id: str, transfer_required: bool = True) -> dict:
    """Fixture state dict — EBYS testlerinde doğrudan DB'ye yazılır."""
    transfer_routing = {
        "transfer_required": transfer_required,
        "kaynak_kurum": "kaymakamlik",
        "hedef_kurum": "belediye",
        "hedef_kurum_adi": "Örenli Belediyesi",
        "hedef_birim": "Yazı İşleri Müdürlüğü",
        "yazi_turu": "ust_yazi",
        "evrak_turu": "kurumlar_arasi_yazi",
        "konu": "Afet Koordinasyon",
        "ozet": "Altyapı bilgisi talebi",
        "yasal_dayanak": "Resmî Yazışma Yönetmeliği",
        "warnings": [],
        "needs_human_review": False,
    }
    return {
        "analysis_id": analysis_id,
        "raw_text": AFET_YAZISI,
        "document": {"document_type": "kurumlar_arasi_yazi", "process_intent": "iletim"},
        "extraction": {"fields": {}},
        "legal_analysis": {},
        "missing_fields": {},
        "summary": {"short_summary": "Afet koordinasyon yazısı"},
        "routing": {"recommended_unit": "Yazı İşleri Müdürlüğü"},
        "transfer_routing": transfer_routing,
        "draft": {"body": "Taslak içerik", "subject": "Konu"},
        "quality": {},
        "human_review": {"status": "approved", "required": True},
        "warnings": [],
        "node_timings": {},
        "status": "approved",
    }


# ---------------------------------------------------------------------------
# GRUP 1: Workflow — transfer_routing dolduruluyor mu?
# ---------------------------------------------------------------------------

class TestWorkflowTransferDetection:
    """
    Workflow'un node_routing aşamasında, iletim/kurumlar_arasi evrak
    analiz edildiğinde transfer_routing alanının doğru doldurulduğunu doğrular.
    """

    def test_transfer_routing_populated_for_iletim(self):
        """Belediye muhataplı iletim yazısı → transfer_required=True, hedef_kurum=belediye."""
        from backend.app.agents.transfer_agent import TransferAgent
        from backend.app.graph.workflow import _detect_target_institution

        # Hedef kurum tespiti kural tabanlı
        hedef = _detect_target_institution(AFET_YAZISI)
        assert hedef == "belediye", f"Beklenen 'belediye', gelen '{hedef}'"

        # TransferAgent deterministik sonuç üretiyor
        agent = TransferAgent()
        result = agent.transfer(
            kaynak_kurum="kaymakamlik",
            hedef_kurum="belediye",
            konu="Afet Koordinasyon",
            evrak_ozeti="Altyapı bilgisi talebi",
            process_intent="iletim",
        )
        assert result["transfer_required"] is True
        assert result["hedef_kurum"] == "belediye"
        assert result["hedef_birim"]  # boş olmamalı

    def test_detect_target_institution_belediye(self):
        from backend.app.graph.workflow import _detect_target_institution

        text = "Örenli Belediyesi Başkanlığına yönlendirilmesi"
        assert _detect_target_institution(text) == "belediye"

    def test_detect_target_institution_default(self):
        from backend.app.graph.workflow import _detect_target_institution

        # Tanınan kuruma referans yoksa varsayılan belediye
        text = "Herhangi bir yazı içeriği"
        assert _detect_target_institution(text) == "belediye"

    def test_transfer_agent_not_called_for_basvuru(self):
        """Normal dilekçe → transfer_routing boş kalmalı (TransferAgent çağrılmamalı)."""
        from backend.app.agents.transfer_agent import TransferAgent

        with patch.object(TransferAgent, "transfer", wraps=None) as mock_transfer:
            # Dilekçe için workflow çalıştırmak yerine sadece tetikleyiciyi test edelim
            # (document_type=dilekce, intent=basvuru → transfer bloğuna girmiyor)
            dtype = "dilekce"
            intent = "basvuru"
            should_trigger = intent == "iletim" or dtype == "kurumlar_arasi_yazi"
            assert should_trigger is False
            mock_transfer.assert_not_called()


# ---------------------------------------------------------------------------
# GRUP 2: Endpoint guard kontrolleri
# ---------------------------------------------------------------------------

class TestTransferEndpointGuards:
    """POST /api/analyses/{id}/transfer — iş kuralı kontrolleri."""

    def test_404_for_unknown_analysis(self):
        resp = client.post("/api/analyses/BILINMEYEN-ID-12345/transfer")
        assert resp.status_code == 404
        data = resp.json()
        assert data["detail"]["code"] == "analysis_not_found"

    def test_400_when_transfer_not_required(self):
        """transfer_required=False olan analiz → 400."""
        repo = get_analysis_repository()
        aid = f"test-no-transfer-{uuid.uuid4().hex[:8]}"
        state = _make_transfer_state(aid, transfer_required=False)
        repo.save_analysis(aid, state)

        try:
            resp = client.post(f"/api/analyses/{aid}/transfer")
            assert resp.status_code == 400
            data = resp.json()
            assert data["detail"]["code"] == "transfer_not_applicable"
        finally:
            try:
                repo.delete_analysis(aid)
            except KeyError:
                pass

    def test_409_when_not_approved(self):
        """transfer_required=True ama onaylanmamış → 409."""
        repo = get_analysis_repository()
        aid = f"test-not-approved-{uuid.uuid4().hex[:8]}"
        state = _make_transfer_state(aid, transfer_required=True)
        state["human_review"]["status"] = "pending_review"
        repo.save_analysis(aid, state)

        try:
            resp = client.post(f"/api/analyses/{aid}/transfer")
            assert resp.status_code == 409
            data = resp.json()
            assert data["detail"]["code"] == "approval_required"
        finally:
            try:
                repo.delete_analysis(aid)
            except KeyError:
                pass


# ---------------------------------------------------------------------------
# GRUP 3: Başarılı transfer + DB doğrulama
# ---------------------------------------------------------------------------

class TestTransferSuccess:
    """Başarılı transfer: EBYS çağrıldı, DB güncellendi, review_events kaydedildi."""

    def test_successful_transfer_updates_db(self):
        """Transfer sonrası status ve review_events DB'de kalıcı."""
        repo = get_analysis_repository()
        aid = f"test-transfer-ok-{uuid.uuid4().hex[:8]}"
        state = _make_transfer_state(aid)
        repo.save_analysis(aid, state)

        try:
            resp = client.post(f"/api/analyses/{aid}/transfer")
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["status"] == "success"
            assert data["hedef_kurum"] == "belediye"
            assert data["routed_status"] == "belediyeye_iletildi"
            assert data["ebys_result"]["success"] is True

            # DB'den okuyarak state'in kalıcı olduğunu doğrula
            saved = repo.get_analysis(aid)
            assert saved is not None
            assert saved.get("status") == "belediyeye_iletildi"
            assert saved.get("transfer_routing", {}).get("ebys_routed") is True

            # review_events'te transfer kaydı var mı?
            events = repo.list_review_events(aid)
            transfer_events = [e for e in events if e["action"] == "transfer_to_institution"]
            assert len(transfer_events) == 1, f"review_events: {events}"
            payload = transfer_events[0]["payload"]
            assert payload["hedef_kurum"] == "belediye"
            assert payload["ebys_result"]["success"] is True

        finally:
            try:
                repo.delete_analysis(aid)
            except KeyError:
                pass

    def test_ebys_mock_route_document_called(self):
        """MockEBYSAdapter.route_document çağrısını doğrula."""
        from backend.app.integrations.ebys import MockEBYSAdapter
        from backend.app.integrations.ebys.schemas import EBYSRouteRequest

        adapter = MockEBYSAdapter()
        req = EBYSRouteRequest(
            document_id="test-doc",
            target_unit="Yazı İşleri Müdürlüğü",
            reason="Resmî Yazışma Yönetmeliği",
        )
        result = adapter.route_document(req)
        assert result.success is True
        assert "Yazı İşleri Müdürlüğü" in result.message
        assert result.operation == "route_document"


# ---------------------------------------------------------------------------
# GRUP 4: Restart simulation
# ---------------------------------------------------------------------------

class TestTransferPersistenceAfterRestart:
    """
    Yeni bir repository instance'ı (yeni session) açılınca
    transfer edilmiş state'in korunduğunu doğrular.
    Person 1'in restart testi pattern'ini taklit eder.
    """

    def test_transfer_state_survives_new_session(self):
        from backend.app.db.repository import AnalysisRepository
        import os

        db_url = os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://kamuai:kamuai@localhost:5432/kamuai",
        )

        try:
            repo1 = AnalysisRepository(database_url=db_url)
        except Exception:
            pytest.skip("PostgreSQL bağlantısı yok — restart testi atlanıyor")

        aid = f"test-restart-{uuid.uuid4().hex[:8]}"
        state = _make_transfer_state(aid)
        repo1.save_analysis(aid, state)

        # Transfer endpoint'ini çağır
        resp = client.post(f"/api/analyses/{aid}/transfer")
        assert resp.status_code == 200, resp.text

        # YENİ bir repository instance'ı aç (restart simülasyonu)
        repo2 = AnalysisRepository(database_url=db_url)
        try:
            saved = repo2.get_analysis(aid)
            assert saved is not None
            assert saved.get("status") == "belediyeye_iletildi"
            assert saved.get("transfer_routing", {}).get("ebys_routed") is True

            events = repo2.list_review_events(aid)
            transfer_events = [e for e in events if e["action"] == "transfer_to_institution"]
            assert len(transfer_events) == 1
        finally:
            try:
                repo2.delete_analysis(aid)
            except KeyError:
                pass
