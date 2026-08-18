"""
data/synthetic/evraklar.jsonl — kalite kontrol scripti

Kontroller:
1. Her evrak_turu_dogru, kurum_profili YAML'daki 6 id'den biri mi?
2. Her hedef_birim_dogru, YAML'daki 9 birim id'sinden biri mi?
3. Tür başına kaç örnek var?
4. bilgi_edinme kayıtlarında sabit kalıp cümle birebir aynı mı?

NOT: Bu script mevcut veri setlerini değiştirmez; yalnız kontrol raporlar.
"""
import json
import sys
from pathlib import Path
from collections import Counter

_PROJECT_ROOT = Path(__file__).parent.parent.parent  # scripts/evaluation -> scripts -> proje kökü
JSONL_PATH = _PROJECT_ROOT / "data" / "synthetic" / "evraklar.jsonl"

GECERLI_EVRAK_TURLERI = {
    "dilekce",
    "bilgi_edinme",
    "kurumlar_arasi_yazi",
    "ihale_itirazi",
    "sosyal_yardim_basvuru",
    "tapu_kadastro_basvuru",
}

GECERLI_BIRIMLER = {
    "yazi_isleri",
    "nufus",
    "sydv",
    "milli_egitim",
    "saglik",
    "mal_mudurlugu",
    "tapu",
    "tarim",
    "emniyet",
}

SABIT_KALIP = (
    "4982 sayılı Bilgi Edinme Hakkı Kanunu gereğince istediğim bilgi "
    "veya belgeler aşağıda belirtilmiştir. Gereğini arz ederim."
)

MOJIBAKE_ISARETLER = ["Ã–", "Ä°", "Ã‡", "ÅŸ", "Äž", "Ã¼", "Ã¶", "Ä±", "Ã§", "Ãœ", "Ã", "â€", "â€˜", "Ã¢"]

def mojibake_tespiti(metin: str) -> bool:
    return any(iz in metin for iz in MOJIBAKE_ISARETLER)

def dogrula():
    satirlar = JSONL_PATH.read_text(encoding="utf-8").strip().splitlines()
    kayitlar = []
    parse_hatalari = []

    for i, satir in enumerate(satirlar, 1):
        satir = satir.strip()
        if not satir:
            continue
        try:
            kayitlar.append(json.loads(satir))
        except json.JSONDecodeError as e:
            parse_hatalari.append(f"  Satır {i}: {e}")

    print(f"Toplam satır (boş dahil): {len(satirlar)}")
    print(f"Başarıyla parse edilen kayıt: {len(kayitlar)}")
    if parse_hatalari:
        print("PARSE HATALARI:")
        for h in parse_hatalari:
            print(h)
    print()

    # 1. evrak_turu kontrolü
    tur_hatalar = []
    for k in kayitlar:
        tur = k.get("evrak_turu_dogru", "")
        if tur not in GECERLI_EVRAK_TURLERI:
            tur_hatalar.append(f"  {k['id']}: geçersiz evrak_turu_dogru='{tur}'")
    print(f"[1] evrak_turu_dogru kontrolü: {len(tur_hatalar)} hata")
    for h in tur_hatalar:
        print(h)

    # 2. birim kontrolü
    birim_hatalar = []
    for k in kayitlar:
        birim = k.get("hedef_birim_dogru", "")
        if birim not in GECERLI_BIRIMLER:
            birim_hatalar.append(f"  {k['id']}: geçersiz hedef_birim_dogru='{birim}'")
    print(f"\n[2] hedef_birim_dogru kontrolü: {len(birim_hatalar)} hata")
    for h in birim_hatalar:
        print(h)

    # 3. Tür başına örnek sayısı
    sayac = Counter(k["evrak_turu_dogru"] for k in kayitlar)
    print("\n[3] Tür başına örnek sayısı:")
    for tur in sorted(GECERLI_EVRAK_TURLERI):
        sayi = sayac.get(tur, 0)
        isaretli = "OK" if 25 <= sayi <= 35 else "!? "
        print(f"  {isaretli} {tur}: {sayi} kayıt")
    print(f"  Toplam: {sum(sayac.values())}")

    # 4. bilgi_edinme sabit kalıp kontrolü
    bilgi_edinme_kayitlar = [k for k in kayitlar if k.get("evrak_turu_dogru") == "bilgi_edinme"]
    kalip_hatalar = []
    for k in bilgi_edinme_kayitlar:
        metin = k.get("metin", "")
        if SABIT_KALIP not in metin:
            kalip_hatalar.append(f"  {k['id']}: sabit kalıp bulunamadı")
    print(f"\n[4] bilgi_edinme sabit kalıp kontrolü ({len(bilgi_edinme_kayitlar)} kayıt): {len(kalip_hatalar)} hata")
    for h in kalip_hatalar:
        print(h)

    # 5. Mojibake Kontrolü
    mojibake_hatalar = []
    for k in kayitlar:
        metin = json.dumps(k, ensure_ascii=False)
        if mojibake_tespiti(metin):
            mojibake_hatalar.append(f"  {k.get('id', 'Bilinmeyen ID')}: mojibake karakterleri tespit edildi")
    print(f"\n[5] Mojibake kontrolü: {len(mojibake_hatalar)} hata")
    for h in mojibake_hatalar:
        print(h)

    # Sonuç
    print()
    toplam_hata = len(parse_hatalari) + len(tur_hatalar) + len(birim_hatalar) + len(kalip_hatalar) + len(mojibake_hatalar)
    if toplam_hata == 0:
        print("TUM KONTROLLER BASARILI -- 0 hata")
    else:
        print(f"HATA: TOPLAM {toplam_hata} HATA BULUNDU")
    return toplam_hata

if __name__ == "__main__":
    sys.exit(dogrula())
