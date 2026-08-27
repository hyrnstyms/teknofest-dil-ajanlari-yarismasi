"""
backend/app/agents/transfer_agent.py
──────────────────────────────────────────────────────────────────────────────
Kurumlar Arası Transfer Ajanı

AMAÇ:
  Bir kamu kurumunda işlenen evrakın başka bir kamu kurumuna
  yönlendirilmesi gerektiğinde (örn. Kaymakamlık → Belediye),
  hedef kurumun profilini yükleyerek uygun birimi ve yazı türünü
  belirler.

ÖNEMLİ:
  - Bu ajan hiçbir LLM çağrısı yapmaz — tamamen kural tabanlıdır.
  - Kaynak kurum profilindeki `kurumlar_arasi_yazi` evrak türü
    varlığını kontrol eder.
  - Hedef kurum profili `data/institutions/<hedef_kurum>/` altında
    bulunmalıdır.

KULLANIM:
    from backend.app.agents.transfer_agent import TransferAgent
    agent = TransferAgent()
    result = agent.transfer(
        kaynak_kurum="kaymakamlik",
        hedef_kurum="belediye",
        konu="Afet Eylem Planı Koordinasyonu",
        evrak_ozeti="Altyapı bilgilerinin paylaşılması talebi",
    )
"""

from __future__ import annotations

from typing import Any

from backend.app.institutions.profile_loader import (
    load_institution_profile,
    InstitutionProfile,
)


# Kurumlar arası yazışmalar için varsayılan yazı türü
_TRANSFER_YAZI_TURU = "ust_yazi"
_TRANSFER_EVRAK_TURU = "kurumlar_arasi_yazi"


class TransferAgent:
    """
    Kurumlar arası evrak yönlendirme ajanı.

    Kaynak kurumdan hedef kuruma üst yazı formatında
    yönlendirme kararı üretir.
    """

    def transfer(
        self,
        kaynak_kurum: str,
        hedef_kurum: str,
        konu: str,
        evrak_ozeti: str,
        process_intent: str = "iletim",
    ) -> dict[str, Any]:
        """
        Kurumlar arası transfer kararı üretir.

        Args:
            kaynak_kurum:   Gönderen kurum id'si (ör. "kaymakamlik")
            hedef_kurum:    Alıcı kurum id'si (ör. "belediye")
            konu:           Evrakın konusu
            evrak_ozeti:    Evrakın kısa özeti
            process_intent: İşlem türü (varsayılan "iletim")

        Returns:
            Transfer kararı dict'i:
            {
              "transfer_required": bool,
              "kaynak_kurum": str,
              "hedef_kurum": str,
              "hedef_kurum_adi": str,
              "hedef_birim": str,
              "yazi_turu": str,
              "evrak_turu": str,
              "konu": str,
              "ozet": str,
              "yasal_dayanak": str,
              "warnings": list[str],
              "needs_human_review": bool,
              "capability_type": str,
              "execution_status": str,
            }
        """
        result: dict[str, Any] = {
            "transfer_required": False,
            "kaynak_kurum": kaynak_kurum,
            "hedef_kurum": hedef_kurum,
            "hedef_kurum_adi": "",
            "hedef_birim": "",
            "yazi_turu": _TRANSFER_YAZI_TURU,
            "evrak_turu": _TRANSFER_EVRAK_TURU,
            "konu": konu,
            "ozet": evrak_ozeti,
            "yasal_dayanak": "Resmî Yazışma Yönetmeliği",
            "warnings": [],
            "needs_human_review": False,
            "capability_type": "recommendation",
            "execution_status": "not_executed",
        }

        # 1. Hedef kurum profilini yükle
        try:
            hedef_profile: InstitutionProfile = load_institution_profile(hedef_kurum)
        except FileNotFoundError:
            result["warnings"].append(
                f"Hedef kurum profili bulunamadı: '{hedef_kurum}'. "
                f"data/institutions/{hedef_kurum}/ klasörünü kontrol edin."
            )
            result["needs_human_review"] = True
            return result

        except ValueError as exc:
            result["warnings"].append(
                f"Hedef kurum profili okunamadı: {exc}"
            )
            result["needs_human_review"] = True
            return result

        result["hedef_kurum_adi"] = hedef_profile.kurum_adi

        # 2. Hedef kurumun kurumlar_arasi_yazi evrak türünü destekleyip
        #    desteklemediğini kontrol et
        hedef_birimleri = _find_target_units(hedef_profile, process_intent)

        if hedef_birimleri:
            result["hedef_birim"] = hedef_birimleri[0]
            result["transfer_required"] = True
        else:
            # Varsayılan olarak Yazı İşleri Müdürlüğü'ne yönlendir
            result["hedef_birim"] = _fallback_unit(hedef_profile)
            result["transfer_required"] = True
            result["warnings"].append(
                f"Hedef kurum '{hedef_kurum}' için '{process_intent}' intentiyle "
                f"eşleşen birim bulunamadı. Varsayılan birime yönlendirildi: "
                f"'{result['hedef_birim']}'"
            )
            result["needs_human_review"] = True

        # 3. Yasal dayanak — hedef profilden kurumlar arası yazı tipi
        for et in hedef_profile.evrak_turleri:
            if isinstance(et, dict) and et.get("id") == _TRANSFER_EVRAK_TURU:
                yd = et.get("yasal_dayanak", "")
                if yd:
                    result["yasal_dayanak"] = yd
                break

        return result


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

def _find_target_units(
    profile: InstitutionProfile,
    process_intent: str,
) -> list[str]:
    """
    Hedef kurumun birimlerinde process_intent'i destekleyen birimlerin
    adlarını döndürür. Önce kurumlar_arasi_yazi evrak türünün tipik
    hedef birimlerini kontrol eder.
    """
    # kurumlar_arasi_yazi evrak türünden tipik hedef birimleri al
    tipik_birim_ids: list[str] = []
    for et in profile.evrak_turleri:
        if isinstance(et, dict) and et.get("id") == _TRANSFER_EVRAK_TURU:
            tipik_birim_ids = et.get("tipik_hedef_birim", [])
            break

    # Birim adlarına çevir
    birim_map: dict[str, str] = {}
    for birim in profile.birimler:
        if isinstance(birim, dict):
            bid = birim.get("id", "")
            bad = birim.get("ad", "")
            if bid:
                birim_map[bid] = bad

    # Intent eşleşmesi de kontrol et
    intent_matched: list[str] = []
    for birim in profile.birimler:
        if not isinstance(birim, dict):
            continue
        if process_intent in birim.get("supported_intents", []):
            bid = birim.get("id", "")
            if bid in tipik_birim_ids:
                # Hem tipik birim hem de intent eşleşmesi — en iyi seçim
                intent_matched.insert(0, birim.get("ad", ""))
            else:
                intent_matched.append(birim.get("ad", ""))

    if intent_matched:
        return intent_matched

    # Sadece tipik birim eşleşmesi
    return [birim_map[bid] for bid in tipik_birim_ids if bid in birim_map]


def _fallback_unit(profile: InstitutionProfile) -> str:
    """
    Hiçbir birim eşleşmezse varsayılan olarak Yazı İşleri'ni döndürür.
    """
    for birim in profile.birimler:
        if isinstance(birim, dict) and birim.get("id") == "yazi_isleri":
            return birim.get("ad", "Yazı İşleri Müdürlüğü")
    # Profile'de yazi_isleri yoksa ilk birimi al
    if profile.birimler and isinstance(profile.birimler[0], dict):
        return profile.birimler[0].get("ad", "")
    return "Yazı İşleri Müdürlüğü"
