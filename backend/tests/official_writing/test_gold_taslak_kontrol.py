"""
backend/tests/official_writing/test_gold_taslak_kontrol.py
────────────────────────────────────────────────────────────────────────────
gold_taslak_kontrol.py için unit testler.

Kaynak script: scripts/evaluation/gold_taslak_kontrol.py
Bu test modülü mevcut backend testlerini DEĞİŞTİRMEZ; ek olarak çalışır.
"""

import sys
import os
import json
import tempfile
from pathlib import Path

import pytest

# Proje kökünü sys.path'e ekle
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.evaluation.gold_taslak_kontrol import parse_taslak_metni
from backend.app.official_writing.format_validator import validate_format


# ──────────────────────────────────────────────────────────────────────────────
# parse_taslak_metni testleri
# ──────────────────────────────────────────────────────────────────────────────

def test_parse_taslak_metni_bos():
    """Boş metin boş dict döndürmeli."""
    result = parse_taslak_metni("")
    assert result == {}


def test_parse_taslak_metni_tc_baslik():
    """T.C. + kurum adı + birim adı içeren metin başlığı parse etmeli."""
    metin = "T.C.\nÖRNEK KAYMAKAMLIĞI\nYazı İşleri Müdürlüğü\nKonu: Test"
    result = parse_taslak_metni(metin)
    assert "tc_baslik" in result
    assert result["tc_baslik"]["idare_adi"] == "ÖRNEK KAYMAKAMLIĞI"
    assert result["tc_baslik"]["birim_adi"] == "Yazı İşleri Müdürlüğü"


def test_parse_taslak_metni_konu():
    """Konu satırı parse edilebilmeli."""
    metin = "T.C.\nÖRNEK KURUMU\nBirim\nKonu: Bilgi Edinme Talebi\nMetin gövdesi."
    result = parse_taslak_metni(metin)
    assert "konu" in result
    assert result["konu"] == "Bilgi Edinme Talebi"


def test_parse_taslak_metni_metin_paragraflari():
    """metin_paragraflari alanı oluşturulmalı."""
    metin = "T.C.\nKURUM\nBirim\nKonu: Test\nGövde metni."
    result = parse_taslak_metni(metin)
    assert "metin_paragraflari" in result
    assert isinstance(result["metin_paragraflari"], list)


# ──────────────────────────────────────────────────────────────────────────────
# validate_format entegrasyon testleri
# ──────────────────────────────────────────────────────────────────────────────

_MINIMAL_VALID_TASLAK = {
    "sayi": "E-12345678-903.07.02-100",
    "tarih": "18.08.2026",
    "konu": "Bilgi Edinme Talebi",
    "muhatap": {"tur": "kurum", "isim": "ÖRNEK KURUMU"},
    "muhatap_turu": "kurum_ust",
    "metin_paragraflari": ["Talebiniz değerlendirilmiştir."],
    "imza": {"ad_soyad": "Ahmet YILMAZ", "unvan": "Kaymakam", "yetki_turu": "normal"},
    "iletisim": {"adres": "Örnek Adres", "irtibat": "0555 000 00 00"},
    "tc_baslik": {"idare_adi": "ÖRNEK KAYMAKAMLIĞI", "birim_adi": "Yazı İşleri Müdürlüğü"},
}


def test_validate_format_gecerli_ust_yazi():
    """Geçerli üst yazı taslağı validate_format'ı pass etmeli."""
    sonuc = validate_format(_MINIMAL_VALID_TASLAK, "ust_yazi")
    assert sonuc.gecerli is True
    assert len(sonuc.hatalar) == 0


def test_validate_format_bos_sayi_hata():
    """Boş sayı alanı SAYI_FORMAT hatasına yol açmalı."""
    taslak = {**_MINIMAL_VALID_TASLAK, "sayi": ""}
    sonuc = validate_format(taslak, "ust_yazi")
    hata_kodlari = [h.kural_kodu for h in sonuc.hatalar]
    assert "SAYI_FORMAT" in hata_kodlari


def test_validate_format_cevap_yazisi_ilgi_zorunlu():
    """Cevap yazısında ilgi alanı yoksa CEVAP_ILGI_ZORUNLU hatası üretmeli."""
    taslak = {**_MINIMAL_VALID_TASLAK}
    taslak.pop("ilgi", None)
    sonuc = validate_format(taslak, "cevap_yazisi")
    hata_kodlari = [h.kural_kodu for h in sonuc.hatalar]
    assert "CEVAP_ILGI_ZORUNLU" in hata_kodlari


def test_validate_format_tekit_ilgi_zorunlu():
    """Tekit yazısında ilgi alanı yoksa TEKIT_ILGI_ZORUNLU hatası üretmeli."""
    taslak = {**_MINIMAL_VALID_TASLAK, "konu": "Tekit Yazısı", "metin_paragraflari": ["tekiden rica ederim"]}
    taslak.pop("ilgi", None)
    sonuc = validate_format(taslak, "tekit_yazisi")
    hata_kodlari = [h.kural_kodu for h in sonuc.hatalar]
    assert "TEKIT_ILGI_ZORUNLU" in hata_kodlari


def test_validate_format_gecersiz_tarih():
    """Yanlış format tarih TARIH_FORMAT hatasına yol açmalı."""
    taslak = {**_MINIMAL_VALID_TASLAK, "tarih": "2026-08-18"}
    sonuc = validate_format(taslak, "ust_yazi")
    hata_kodlari = [h.kural_kodu for h in sonuc.hatalar]
    assert "TARIH_FORMAT" in hata_kodlari


# ──────────────────────────────────────────────────────────────────────────────
# gold_taslaklar.jsonl entegrasyon testi (dosya varsa)
# ──────────────────────────────────────────────────────────────────────────────

def test_gold_taslaklar_file_exists_or_skip():
    """
    Eğer gold_taslaklar.jsonl mevcutsa, her kaydın validate_format'ı
    import hatası olmadan çalıştığını doğrular.
    Dosya yoksa test atlanır (CI ortamı için güvenli).
    """
    gold_path = _PROJECT_ROOT / "data" / "evaluation" / "gold_taslaklar.jsonl"
    if not gold_path.exists():
        pytest.skip("gold_taslaklar.jsonl bulunamadı; test atlandı.")

    with open(gold_path, "r", encoding="utf-8") as f:
        lines = [line for line in f if line.strip()]

    for line in lines:
        data = json.loads(line)
        yazi_turu = data.get("yazi_turu", "ust_yazi")
        if yazi_turu == "bilgilendirme_yazisi":
            yazi_turu = "ust_yazi"
        metin = data.get("taslak_metni", "")
        taslak_dict = parse_taslak_metni(metin)
        # Hata fırlatmamalı; sonuç tipi doğru olmalı
        sonuc = validate_format(taslak_dict, yazi_turu)
        assert isinstance(sonuc.gecerli, bool)
