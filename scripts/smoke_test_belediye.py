"""
scripts/smoke_test_belediye.py
──────────────────────────────────────────────────────────────────────────────
Track 3 — Belediye Smoke Test

Amaç:
  - Belediye kurum profilinin yüklenip yüklenmediğini doğrular
  - RoutingAgent(institution="belediye") ile 3 farklı evrak senaryosunu çalıştırır
  - TransferAgent ile Kaymakamlık→Belediye transfer senaryosunu çalıştırır
  - Tüm sonuçları stdout'a yazar (demo kanıtı)

LLM veya Qdrant gerektirmez — sadece kural tabanlı bileşenleri test eder.

Çalıştırma:
    python scripts/smoke_test_belediye.py
"""

import sys
import json
from pathlib import Path

# Proje kökünü path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.institutions.profile_loader import (
    list_available_profiles,
    load_institution_profile,
)
from backend.app.agents.routing_agent import RoutingAgent
from backend.app.agents.transfer_agent import TransferAgent


SEPARATOR = "=" * 70


def print_section(title: str):
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def print_result(label: str, value):
    if isinstance(value, dict):
        print(f"  {label}:")
        for k, v in value.items():
            print(f"    {k}: {v}")
    else:
        print(f"  {label}: {value}")


def main():
    print("\nKAMUAI — Track 3 Belediye Smoke Test")
    print(f"{'─' * 70}")

    # ------------------------------------------------------------------
    # 1. Mevcut kurumları listele
    # ------------------------------------------------------------------
    print_section("1. Mevcut Kurum Profilleri")
    profiles = list_available_profiles()
    print(f"  Bulunan kurumlar: {profiles}")
    assert "belediye" in profiles, "HATA: belediye profili bulunamadı!"
    assert "kaymakamlik" in profiles, "HATA: kaymakamlik profili bulunamadı!"
    print("  ✓ Her iki kurum profili mevcut")

    # ------------------------------------------------------------------
    # 2. Belediye profilini yükle
    # ------------------------------------------------------------------
    print_section("2. Belediye Kurum Profili")
    belediye = load_institution_profile("belediye")
    print(f"  Kurum Adı   : {belediye.kurum_adi}")
    print(f"  Kurum Türü  : {belediye.kurum_turu}")
    print(f"  Birim Sayısı: {len(belediye.birimler)}")
    birim_adlari = [
        b.get("ad", "?") for b in belediye.birimler if isinstance(b, dict)
    ]
    for ad in birim_adlari:
        print(f"    • {ad}")
    assert len(belediye.birimler) >= 5
    print("  ✓ Belediye profili başarıyla yüklendi")

    # ------------------------------------------------------------------
    # 3. Routing Agent — 3 Senaryo
    # ------------------------------------------------------------------
    print_section("3. RoutingAgent — Belediye Senaryoları")
    routing_agent = RoutingAgent(institution="belediye")

    senaryolar = [
        {
            "no": "3a",
            "baslik": "İşyeri Ruhsatı Başvurusu",
            "document_type": "ruhsat_basvurusu",
            "process_intent": "basvuru",
            "subject": "İşyeri Açma Ruhsatı Talebi",
            "request_text": (
                "Atatürk Caddesi No:14'te açmayı planladığım unlu mamüller "
                "satış işyeri için ruhsat başvurusunda bulunmak istiyorum."
            ),
        },
        {
            "no": "3b",
            "baslik": "Bozuk Yol Şikayeti",
            "document_type": "sikayet",
            "process_intent": "sikayet",
            "subject": "Gül Sokak Asfalt Sorunu",
            "request_text": (
                "Cumhuriyet Mahallesi Gül Sokak'ta asfalt çökmesi ve çukur "
                "oluştu. Onarım yapılmasını talep ediyorum."
            ),
        },
        {
            "no": "3c",
            "baslik": "İmar Durumu Belgesi Talebi",
            "document_type": "imar_talebi",
            "process_intent": "belge_talebi",
            "subject": "124 Ada 8 Parsel İmar Durumu",
            "request_text": (
                "Bahçelievler Mahallesi 124 ada 8 parselde imar durumu belgesi "
                "ve yapı ruhsatı talep ediyorum."
            ),
        },
    ]

    for s in senaryolar:
        print(f"\n  [{s['no']}] {s['baslik']}")
        result = routing_agent.route(
            document_type=s["document_type"],
            process_intent=s["process_intent"],
            subject=s["subject"],
            request_text=s["request_text"],
            extracted_fields={},
        )
        print(f"    → Önerilen Birim : {result['recommended_unit']}")
        print(f"    → Yönlendirme Skoru: {result['routing_score']}")
        print(f"    → İnsan Incelemesi: {result['needs_human_review']}")
        if result.get("ranked_units"):
            print(f"    → Top-3 Birim    : {[u['name'] for u in result['ranked_units']]}")
        assert result["recommended_unit"] is not None, (
            f"HATA [{s['no']}]: Önerilen birim None döndü"
        )
        print(f"    ✓ Yönlendirme başarılı")

    # ------------------------------------------------------------------
    # 4. TransferAgent — Kaymakamlık → Belediye
    # ------------------------------------------------------------------
    print_section("4. TransferAgent — Kaymakamlık → Belediye")
    transfer_agent = TransferAgent()
    transfer_result = transfer_agent.transfer(
        kaynak_kurum="kaymakamlik",
        hedef_kurum="belediye",
        konu="İlçe Afet Eylem Planı Koordinasyonu",
        evrak_ozeti=(
            "Altyapı bilgileri (yol, köprü, içme suyu şebekesi) ve "
            "afet toplanma alanlarına ait güncel verilerin iletilmesi talebi."
        ),
        process_intent="iletim",
    )
    print(f"  Transfer Gerekli  : {transfer_result['transfer_required']}")
    print(f"  Kaynak Kurum      : {transfer_result['kaynak_kurum']}")
    print(f"  Hedef Kurum       : {transfer_result['hedef_kurum']}")
    print(f"  Hedef Kurum Adı   : {transfer_result['hedef_kurum_adi']}")
    print(f"  Hedef Birim       : {transfer_result['hedef_birim']}")
    print(f"  Yazı Türü         : {transfer_result['yazi_turu']}")
    print(f"  Evrak Türü        : {transfer_result['evrak_turu']}")
    print(f"  Yasal Dayanak     : {transfer_result['yasal_dayanak']}")
    if transfer_result["warnings"]:
        print(f"  Uyarılar          : {transfer_result['warnings']}")

    assert transfer_result["transfer_required"] is True, (
        "HATA: Transfer kararı üretilmedi"
    )
    assert transfer_result["hedef_birim"] != "", (
        "HATA: Hedef birim boş"
    )
    print("  ✓ Kurumlar arası transfer kararı başarıyla üretildi")

    # ------------------------------------------------------------------
    # 5. Özet
    # ------------------------------------------------------------------
    print_section("5. Sonuç Özeti")
    print("  ✓ Belediye kurum profili yüklendi")
    print("  ✓ RoutingAgent 3/3 senaryo başarıyla yönlendirdi")
    print("  ✓ TransferAgent Kaymakamlık→Belediye transferi üretti")
    print(f"\n  Smoke test BAŞARILI ✓")
    print()


if __name__ == "__main__":
    main()
