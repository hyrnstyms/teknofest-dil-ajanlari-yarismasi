"""
validators/format_validator.py
──────────────────────────────────────────────────────────────────────────────
Resmî Yazışma Format Doğrulayıcı
Kaynak: Resmî Yazışmalarda Uygulanacak Usul ve Esaslar Hakkında Yönetmelik
        (RG 10.06.2020/31151, No. 2646) + Cumhurbaşkanlığı Kılavuzu (2022)

TASARIM İLKESİ:
  Her kural KÜÇÜK ve BAĞIMSIZ bir Python fonksiyonu olarak implemente
  edilmiştir.  Fonksiyonlar deterministik olup hiçbir LLM/AI çağrısı
  içermez; tamamen kod-tabanlıdır.

  TODO — BİLGİLENDİRME YAZISI İMZA YETKİSİ:
    Bilgilendirme yazısı biçimsel olarak ust_yazi.jinja2 şablonunu
    kullanır (ayrı şablon yoktur — [TASARIM KARARI]).  Bakan Yardımcısının
    da imzalayabilmesi bir YETKİ kuralıdır, FORMAT kuralı değildir.
    Bu kural bu validator'da ELE ALINMAMAKTADIR; ayrı bir yetki kontrol
    modülünde (MVP kapsamı dışı) implemente edilmelidir.

[TASARIM KARARI] İşaretli Kararlar:
  1. Satır aralığı: 1.0 (düz metin çıktısında sayısal kontrol yapılmaz,
     kelime işlemci katmanında uygulanır.)
  2. Ek/Dağıtım öncesi boşluk: 2 satır (validator boş satır sayısını
     kontrol eder.)
  3. Kısaltma kuralı: Sadece kurumsal/özel isim kısaltmaları (TBMM, KEP
     vb.) ilk kullanımda açık biçim + parantez içi kısaltma kuralına
     tabidir; yaygın genel kısaltmalar (vb., TL, m²) muaftır.
  4. 9pt küçültme: MVP'de uygulanmaz.
  5. Arz/rica (kurum muhatap, hiyerarşi belirsiz): varsayılan "arz ederim."
  6. Bilgilendirme yazısı şablonu: ust_yazi.jinja2 kullanılır.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


# ──────────────────────────────────────────────────────────────────────────────
# Veri Yapıları
# ──────────────────────────────────────────────────────────────────────────────

YaziTuru = Literal["ust_yazi", "cevap_yazisi", "tekit_yazisi"]


@dataclass
class DogrulamaHatasi:
    """Tek bir kural ihlalini temsil eder."""
    kural_kodu: str          # ör. "SAYI_FORMAT"
    mesaj: str               # İnsan-okunabilir hata açıklaması
    madde_ref: str = ""      # ör. "Madde 11" veya "[TASARIM KARARI]"
    tasarim_karari: bool = False  # True ise yönetmelik hükmü değil


@dataclass
class DogrulamaSonucu:
    """validate_format() çıktısı."""
    gecerli: bool = True
    hatalar: list[DogrulamaHatasi] = field(default_factory=list)
    uyarilar: list[DogrulamaHatasi] = field(default_factory=list)

    def hata_ekle(self, kural_kodu: str, mesaj: str,
                  madde_ref: str = "", tasarim_karari: bool = False) -> None:
        self.gecerli = False
        self.hatalar.append(
            DogrulamaHatasi(kural_kodu, mesaj, madde_ref, tasarim_karari)
        )

    def uyari_ekle(self, kural_kodu: str, mesaj: str,
                   madde_ref: str = "", tasarim_karari: bool = False) -> None:
        self.uyarilar.append(
            DogrulamaHatasi(kural_kodu, mesaj, madde_ref, tasarim_karari)
        )


# ──────────────────────────────────────────────────────────────────────────────
# Kural Fonksiyonları
# ──────────────────────────────────────────────────────────────────────────────


# ─── Madde 11: Sayı Formatı ───────────────────────────────────────────────────

# Geçerli sayı formatı: [E|Z|O]-DETSİS_no-dosya_plan_kodu-kayıt_no
# DETSİS no: sayısal
# dosya_plan_kodu: nokta ile ayrılmış sayılar (ör. 903.07.02)
# kayıt_no: sayısal
_SAYI_PATTERN = re.compile(
    r"^[EZO]-\d+-[\d.]+(-[\d]+)+$"
)


def sayi_formati_dogru_mu(sayi: str) -> tuple[bool, str]:
    """
    Sayı alanının [E|Z|O]-DETSİS_no-dosya_plan_kodu-kayıt_no formatına
    uygunluğunu kontrol eder (Madde 11).

    Returns:
        (gecerli: bool, hata_mesaji: str)  hata_mesaji geçerliyse boş string.
    """
    if not sayi:
        return False, "Sayı alanı boş olamaz."
    if not _SAYI_PATTERN.match(sayi):
        return False, (
            f"Sayı formatı hatalı: '{sayi}'. "
            "Beklenen format: [E|Z|O]-DETSİS_no-dosya_plan_kodu-kayıt_no "
            "(ör. E-67915368-903.07.02-4752)"
        )
    # Ön ek kontrolü
    if sayi[0] not in ("E", "Z", "O"):
        return False, (
            f"Sayı öneki '{sayi[0]}' geçersiz; E, Z veya O olmalıdır."
        )
    return True, ""


# ─── Madde 12: Tarih Formatı ──────────────────────────────────────────────────

# GG.AA.YYYY (nokta ile) VEYA harfle yazım (10 Ekim 2019)
_TARIH_SAYISAL_PATTERN = re.compile(
    r"^\d{2}\.\d{2}\.\d{4}$"
)
_TURK_AYLAR = {
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
}
_TARIH_HARFLI_PATTERN = re.compile(
    r"^\d{1,2} [A-ZÇĞİÖŞÜa-zçğışöşü]+ \d{4}$"
)


def tarih_formati_dogru_mu(tarih: str) -> tuple[bool, str]:
    """
    Tarih alanının GG.AA.YYYY veya harfli formatta olduğunu doğrular
    (Madde 12).  Harfli formatta ay adı Türkçe olmalıdır.
    """
    if not tarih:
        return False, "Tarih alanı boş olamaz."

    if _TARIH_SAYISAL_PATTERN.match(tarih):
        # Sayısal: gün/ay aralık kontrolü
        gun, ay, yil = tarih.split(".")
        if not (1 <= int(gun) <= 31):
            return False, f"Tarihte gün değeri ({gun}) 1-31 aralığında olmalıdır."
        if not (1 <= int(ay) <= 12):
            return False, f"Tarihte ay değeri ({ay}) 1-12 aralığında olmalıdır."
        return True, ""

    if _TARIH_HARFLI_PATTERN.match(tarih):
        parcalar = tarih.split()
        ay_adi = parcalar[1]
        if ay_adi not in _TURK_AYLAR:
            return False, (
                f"Harfli tarihte ay adı '{ay_adi}' tanınmıyor; "
                f"Türkçe ay adı olmalıdır (ör. Ekim)."
            )
        return True, ""

    return False, (
        f"Tarih formatı hatalı: '{tarih}'. "
        "GG.AA.YYYY (ör. 10.10.2019) veya harfli (ör. 10 Ekim 2019) olmalıdır."
    )


# ─── Madde 13: Konu Alanı ─────────────────────────────────────────────────────

def konu_formati_dogru_mu(konu: str) -> tuple[bool, str]:
    """
    Konu alanının sonunda noktalama işareti olmadığını ve boş olmadığını
    kontrol eder (Madde 13).
    """
    if not konu:
        return False, "Konu alanı boş olamaz."
    if konu[-1] in (".", ",", ";", ":", "!", "?"):
        return False, (
            f"Konu alanı noktalama işaretiyle bitemez (son karakter: '{konu[-1]}')."
        )
    return True, ""


# ─── Madde 14: Muhatap Formatı ────────────────────────────────────────────────

def muhatap_formati_dogru_mu(
    muhatap_turu: str,
    muhatap_metni: str,
) -> tuple[bool, str]:
    """
    Muhatap satırının kurallara uygunluğunu kontrol eder (Madde 14).

    muhatap_turu: "kurum" | "gercek_kisi" | "dagitim"
    muhatap_metni: şablondan üretilen muhatap satırı (trim edilmiş)
    """
    if not muhatap_metni:
        return False, "Muhatap alanı boş olamaz."

    metni = muhatap_metni.strip()

    if muhatap_turu == "dagitim":
        if metni != "DAĞITIM YERLERİNE":
            return False, (
                "Çoklu muhatap için 'DAĞITIM YERLERİNE' kullanılmalıdır."
            )
        return True, ""

    if muhatap_turu == "kurum":
        if metni != metni.upper():
            return False, (
                "Kurum muhatabı BÜYÜK HARF yazılmalıdır."
            )
        return True, ""

    if muhatap_turu == "gercek_kisi":
        if not metni.startswith("Sayın "):
            return False, (
                "Gerçek kişi muhatabı 'Sayın ' ile başlamalıdır."
            )
        return True, ""

    return False, f"Bilinmeyen muhatap türü: '{muhatap_turu}'."


# ─── Madde 15: İlgi Formatı ───────────────────────────────────────────────────

_ILGI_PATTERN = re.compile(
    r"tarihli ve .+sayılı .+\.$"
)


def ilgi_formati_dogru_mu(ilgi_satirlari: list[str]) -> tuple[bool, str]:
    """
    İlgi satır(lar)ının "...tarihli ve ...sayılı..." kalıbını içerdiğini
    ve nokta ile bittiğini kontrol eder (Madde 15).

    ilgi_satirlari: "İlgi:" öneki dahil ilgi satırları listesi
    """
    for satir in ilgi_satirlari:
        if not satir.strip().startswith("İlgi:"):
            return False, f"İlgi satırı 'İlgi:' ile başlamalıdır: '{satir}'."
        if not _ILGI_PATTERN.search(satir):
            return False, (
                f"İlgi satırı '...tarihli ve ...sayılı...' kalıbını içermeli "
                f"ve nokta ile bitmeli: '{satir}'."
            )
    return True, ""


# ─── Madde 16/12: Kapanış İfadesi ─────────────────────────────────────────────

_GECERLI_KAPANISLAR_GERCEK_KISI = {
    "Saygılarımla.", "İyi dileklerimle.", "Bilgilerinize sunulur."
}
_GECERLI_KAPANISLAR_KURUM = {
    "rica ederim.", "arz ederim.", "arz ve rica ederim."
}


def arz_rica_dogru_mu(
    kapalis_ifadesi: str,
    muhatap_turu: str,
) -> tuple[bool, str]:
    """
    Kapanış ifadesinin muhatap türüne göre doğruluğunu kontrol eder
    (Madde 16/12, Madde 31/7).

    muhatap_turu: "kurum_alt" | "kurum_ust" | "kurum_ayni" |
                  "kurum_karisik" | "gercek_kisi"

    [TASARIM KARARI] Muhatap kurum ve hiyerarşi belirsizse
                     varsayılan "arz ederim." — yorum: kurum_ust davranışı.
    """
    ifade = kapalis_ifadesi.strip()

    if muhatap_turu == "gercek_kisi":
        # Gerçek kişi: arz/rica KULLANILMAZ (Madde 31/7)
        if ifade in _GECERLI_KAPANISLAR_KURUM:
            return False, (
                "Gerçek kişi muhatabında arz/rica kullanılamaz (Madde 31/7). "
                f"Kullanılan: '{ifade}'. "
                "Geçerliler: " + str(_GECERLI_KAPANISLAR_GERCEK_KISI)
            )
        if ifade not in _GECERLI_KAPANISLAR_GERCEK_KISI:
            return False, (
                f"Gerçek kişi muhatabı için geçersiz kapanış: '{ifade}'. "
                "Geçerliler: " + str(_GECERLI_KAPANISLAR_GERCEK_KISI)
            )
        return True, ""

    # Kurum muhatap (tüm kurum_* türleri)
    if ifade in _GECERLI_KAPANISLAR_GERCEK_KISI:
        return False, (
            "Kurum muhatabında 'Saygılarımla.' gibi kişisel kapanışlar "
            "kullanılamaz. "
            "Geçerliler: " + str(_GECERLI_KAPANISLAR_KURUM)
        )

    if muhatap_turu == "kurum_alt" and ifade != "rica ederim.":
        return False, (
            f"Alt makama yazıda kapanış 'rica ederim.' olmalıdır; "
            f"kullanılan: '{ifade}'."
        )
    if muhatap_turu in ("kurum_ust", "kurum_ayni") and ifade != "arz ederim.":
        return False, (
            f"Üst/aynı düzey makama yazıda kapanış 'arz ederim.' olmalıdır; "
            f"kullanılan: '{ifade}'."
        )
    if muhatap_turu == "kurum_karisik" and ifade != "arz ve rica ederim.":
        return False, (
            f"Karışık dağıtımlı yazıda kapanış 'arz ve rica ederim.' olmalıdır; "
            f"kullanılan: '{ifade}'."
        )

    if ifade not in _GECERLI_KAPANISLAR_KURUM:
        return False, (
            f"Geçersiz kapanış ifadesi: '{ifade}'. "
            "Geçerliler: " + str(_GECERLI_KAPANISLAR_KURUM)
        )

    return True, ""


# ─── Madde 17: İmza Bloğu ─────────────────────────────────────────────────────

def imza_blogu_dogru_mu(
    imza_ad_soyad: str,
    imza_unvan: str,
    yetki_turu: str = "normal",
    vekil_makam: str = "",
) -> tuple[bool, str]:
    """
    İmza bloğu alanlarının temel kurallarını kontrol eder (Madde 17).

    - ad_soyad: "Ad SOYAD" formatı (ilk kelime baş harf, diğerleri büyük)
    - unvan: boş olamaz
    - yetki_devri: vekil_makam zorunlu, " a." ile bitmeli
    - vekaletname: vekil_makam zorunlu, " V." ile bitmeli
    """
    if not imza_ad_soyad:
        return False, "İmza ad-soyad alanı boş olamaz."
    if not imza_unvan:
        return False, "İmza unvan alanı boş olamaz."

    # Ad SOYAD formatı: en az 2 kelime, son kelime büyük harf
    kelimeler = imza_ad_soyad.strip().split()
    if len(kelimeler) < 2:
        return False, (
            f"İmza adı '{imza_ad_soyad}' en az Ad ve SOYAD içermelidir."
        )
    soyad = kelimeler[-1]
    if soyad != soyad.upper():
        return False, (
            f"İmzada soyad '{soyad}' BÜYÜK HARF olmalıdır (Madde 17)."
        )

    if yetki_turu == "yetki_devri":
        if not vekil_makam:
            return False, "Yetki devrinde vekil_makam boş olamaz."

    if yetki_turu == "vekaletname":
        if not vekil_makam:
            return False, "Vekâlette vekil_makam boş olamaz."

    return True, ""


# ─── Madde 18: Ek Listesi ─────────────────────────────────────────────────────

def ek_listesi_dogru_mu(
    ekler: list[dict] | None,
) -> tuple[bool, str]:
    """
    Ek listesinin temel kurallarını kontrol eder (Madde 18).

    ekler: None veya [] ise "Ek konulmadı" beklenir (hata değil).
    Her ek dict'i { 'ad': str, 'bilgi': str } içermelidir.
    """
    if not ekler:
        return True, ""  # Ek yoksa geçerli

    for i, ek in enumerate(ekler, 1):
        if not ek.get("ad"):
            return False, f"Ek #{i} için 'ad' alanı boş olamaz."
        if not ek.get("bilgi"):
            return False, f"Ek #{i} için 'bilgi' alanı boş olamaz."

    return True, ""


# ─── Madde 19: Dağıtım Listesi ────────────────────────────────────────────────

def dagitim_listesi_dogru_mu(
    dagitim: dict | None,
) -> tuple[bool, str]:
    """
    Dağıtım listesinin temel yapısını kontrol eder (Madde 19).

    dagitim: { 'geregi': list[str], 'bilgi': list[str] (opsiyonel) }
    'geregi' zorunludur; 'bilgi' opsiyoneldir.
    """
    if dagitim is None:
        return True, ""  # Dağıtım yoksa geçerli

    if "geregi" not in dagitim or not dagitim["geregi"]:
        return False, (
            "Dağıtım listesinde 'Gereği' alanı boş olamaz (Madde 19)."
        )

    for yer in dagitim["geregi"]:
        if not yer or not yer.strip():
            return False, "Dağıtım 'Gereği' listesinde boş eleman olamaz."

    if "bilgi" in dagitim:
        for yer in dagitim["bilgi"]:
            if not yer or not yer.strip():
                return False, "Dağıtım 'Bilgi' listesinde boş eleman olamaz."

    return True, ""


# ─── Madde 34: Tekit Yazısı Özel Kuralları ────────────────────────────────────

_TEKIT_METIN_PATTERN = re.compile(
    r"tekiden rica ederim", re.IGNORECASE
)


def tekit_konu_dogru_mu(konu: str) -> tuple[bool, str]:
    """
    Tekit yazısında konu alanının 'Tekit Yazısı' olduğunu doğrular
    (Madde 34).
    """
    if konu.strip() != "Tekit Yazısı":
        return False, (
            f"Tekit yazısında konu 'Tekit Yazısı' olmalıdır; "
            f"bulunan: '{konu}'."
        )
    return True, ""


def tekit_ilgi_zorunlu_mu(ilgi_mevcut: bool) -> tuple[bool, str]:
    """
    Tekit yazısında ilgi alanının mevcut olduğunu doğrular (Madde 34).
    """
    if not ilgi_mevcut:
        return False, (
            "Tekit yazısında ilgi alanı ZORUNLUDUR (Madde 34). "
            "Önceki yazının tarih ve sayısı belirtilmelidir."
        )
    return True, ""


def tekit_metin_kalibi_dogru_mu(metin: str) -> tuple[bool, str]:
    """
    Tekit yazısı metninin 'tekiden rica ederim' ifadesini içerdiğini
    doğrular (Madde 34 / Kılavuz Örnek 24).
    """
    if not _TEKIT_METIN_PATTERN.search(metin):
        return False, (
            "Tekit yazısı metni 'tekiden rica ederim' ifadesini içermelidir "
            "(Madde 34)."
        )
    return True, ""


# ─── [TASARIM KARARI] Cevap Yazısı: İlgi Zorunluluğu ─────────────────────────
# [TASARIM KARARI] Cevap yazısında ilgi zorunludur. Bu kural yönetmelikte
# cevap yazısı için kaynaklı değildir; tekit yazısı için Madde 34'te
# kaynaklıdır. Cevap yazısı bağlamında zorunluluk ekip kararıdır.

def cevap_ilgi_zorunlu_mu(ilgi_mevcut: bool) -> tuple[bool, str]:
    """
    Cevap yazısında ilgi alanının mevcut olduğunu doğrular.

    [TASARIM KARARI] Cevap yazısı için ilgi zorunluluğu yönetmelikte
    kaynaklı değildir; bu ekip kararıdır.
    """
    if not ilgi_mevcut:
        return False, (
            "[TASARIM KARARI] Cevap yazısında ilgi alanı zorunludur. "
            "Cevap verilen yazının tarih ve sayısı belirtilmelidir."
        )
    return True, ""


# ─── Madde 10 / 11: TC Başlık Yapısı ─────────────────────────────────────────

def tc_baslik_dogru_mu(
    ilk_satir: str,
    idare_adi: str,
    birim_adi: str,
) -> tuple[bool, str]:
    """
    Sayfa başlığının T.C. / idare adı BÜYÜK / birim adı yapısını kontrol
    eder (Madde 10).
    """
    if ilk_satir.strip() != "T.C.":
        return False, (
            f"Başlık ilk satırı 'T.C.' olmalıdır; bulunan: '{ilk_satir}'."
        )
    if idare_adi != idare_adi.upper():
        return False, (
            f"İdare adı '{idare_adi}' BÜYÜK HARF olmalıdır (Madde 10)."
        )
    if not birim_adi:
        return False, "Birim adı boş olamaz (Madde 10)."
    return True, ""


# ─── Sayfa Numarası Formatı ───────────────────────────────────────────────────

_SAYFA_NO_PATTERN = re.compile(r"^\d+/\d+$")


def sayfa_no_formati_dogru_mu(sayfa_no: str) -> tuple[bool, str]:
    """
    Sayfa numarasının '1/2' formatında olduğunu kontrol eder (Madde 10).
    """
    if not _SAYFA_NO_PATTERN.match(sayfa_no):
        return False, (
            f"Sayfa numarası '1/2' formatında olmalıdır; bulunan: '{sayfa_no}'."
        )
    return True, ""


# ─── [TASARIM KARARI] Kısaltma Kuralı ────────────────────────────────────────
# [TASARIM KARARI] Kısaltma kuralı sadece kurumsal/özel isim kısaltmalarına
# (TBMM, KEP vb.) uygulanır. Yaygın genel kısaltmalar (vb., TL, m²) muaftır.
# Yönetmelik/kılavuzda bu ayrım net değildir; ekip kararıdır.
#
# Bu fonksiyon yalnızca BİLİNEN kurumsal kısaltmaların ilk kullanımda
# açık biçim + parantez içi kısaltma içerip içermediğini kontrol eder.
# Genel kısaltmalar muaf listesine alınmıştır.

_MUAF_KISALTMALAR = {
    "vb.", "vd.", "vs.", "TL", "m²", "km", "cm", "kg", "m³",
    "no", "No", "md.", "Md.", "bkz.", "ör.", "s.", "ss.",
}

_KURUMSAL_KISALTMA_PATTERN = re.compile(
    r"\b([A-ZÇĞİÖŞÜ]{2,})\b"
)


def kisaltma_aciklama_mevcut_mu(
    metin: str,
    bilinen_kurumsal_kisaltmalar: set[str] | None = None,
) -> tuple[bool, list[str]]:
    """
    Metinde geçen kurumsal kısaltmaların ilk kullanımda açık biçim +
    parantez içinde kısaltma içerip içermediğini kontrol eder.

    [TASARIM KARARI] Sadece kurumsal kısaltmalar kontrol edilir;
    yaygın genel kısaltmalar (vb., TL) muaftır.

    bilinen_kurumsal_kisaltmalar: kontrol edilecek kısaltma kümesi.
        None ise otomatik tespite çalışır (tüm 2+ büyük harf dizisi).

    Returns:
        (tumu_aciklanmis: bool, aciklanmamis_kisaltmalar: list[str])
    """
    aciklanmamis = []
    bulunan = _KURUMSAL_KISALTMA_PATTERN.findall(metin)
    hedefler = (
        bilinen_kurumsal_kisaltmalar
        if bilinen_kurumsal_kisaltmalar is not None
        else set(bulunan)
    )

    for kisaltma in hedefler:
        if kisaltma in _MUAF_KISALTMALAR:
            continue
        # Açık biçim + parantez kontrolü: "(KISALTMA)" ifadesi metinde var mı?
        acik_bicim_pattern = re.compile(
            r"\b\w[\w\s]+" + re.escape(f"({kisaltma})")
        )
        if not acik_bicim_pattern.search(metin):
            aciklanmamis.append(kisaltma)

    return len(aciklanmamis) == 0, aciklanmamis


# ──────────────────────────────────────────────────────────────────────────────
# Ana Doğrulama Fonksiyonu
# ──────────────────────────────────────────────────────────────────────────────


def validate_format(taslak: dict, yazi_turu: YaziTuru) -> DogrulamaSonucu:
    """
    Verilen yazı taslağının biçim kurallarına uygunluğunu doğrular.

    taslak: Şablona geçirilecek parametreler sözlüğü (jinja2 context ile aynı)
    yazi_turu: "ust_yazi" | "cevap_yazisi" | "tekit_yazisi"

    Returns:
        DogrulamaSonucu — gecerli=True ise tüm kurallar karşılandı.

    NOT: Bu fonksiyon deterministik ve tamamen kod-tabanlıdır.
         Hiçbir LLM/AI çağrısı içermez.

    TODO — BİLGİLENDİRME YAZISI İMZA YETKİSİ:
        Bilgilendirme yazısı biçimsel olarak "ust_yazi" türünü kullanır.
        Bakan Yardımcısının da imzalayabilmesi bir yetki kuralıdır;
        bu validator'da ele alınmaz — ayrı yetki modülünde implemente
        edilmelidir (MVP kapsamı dışı).
    """
    sonuc = DogrulamaSonucu()

    # ── 1. Sayı Formatı (Madde 11) ────────────────────────────────────────────
    sayi = taslak.get("sayi", "")
    gecerli, mesaj = sayi_formati_dogru_mu(sayi)
    if not gecerli:
        sonuc.hata_ekle("SAYI_FORMAT", mesaj, "Madde 11")

    # ── 2. Tarih Formatı (Madde 12) ───────────────────────────────────────────
    tarih = taslak.get("tarih", "")
    gecerli, mesaj = tarih_formati_dogru_mu(tarih)
    if not gecerli:
        sonuc.hata_ekle("TARIH_FORMAT", mesaj, "Madde 12")

    # ── 3. Konu Formatı (Madde 13) ────────────────────────────────────────────
    konu = taslak.get("konu", "")

    if yazi_turu == "tekit_yazisi":
        gecerli, mesaj = tekit_konu_dogru_mu(konu)
        if not gecerli:
            sonuc.hata_ekle("TEKIT_KONU", mesaj, "Madde 34")
    else:
        gecerli, mesaj = konu_formati_dogru_mu(konu)
        if not gecerli:
            sonuc.hata_ekle("KONU_FORMAT", mesaj, "Madde 13")

    # ── 4. Muhatap Formatı (Madde 14) ─────────────────────────────────────────
    muhatap = taslak.get("muhatap", {})
    muhatap_tur = muhatap.get("tur", "")
    muhatap_isim = muhatap.get("isim", "")

    # Basit muhatap metni oluştur (validator için)
    if muhatap_tur == "dagitim":
        muhatap_metni = "DAĞITIM YERLERİNE"
    elif muhatap_tur == "kurum":
        muhatap_metni = muhatap_isim.upper()
    elif muhatap_tur == "gercek_kisi":
        muhatap_metni = f"Sayın {muhatap_isim}"
    else:
        muhatap_metni = muhatap_isim

    gecerli, mesaj = muhatap_formati_dogru_mu(muhatap_tur, muhatap_metni)
    if not gecerli:
        sonuc.hata_ekle("MUHATAP_FORMAT", mesaj, "Madde 14")

    # ── 5. İlgi Formatı (Madde 15) ────────────────────────────────────────────
    ilgi = taslak.get("ilgi", [])
    ilgi_mevcut = bool(ilgi)

    if ilgi_mevcut:
        ilgi_satirlari = []
        for item in ilgi:
            satir = (
                f"İlgi: {item.get('tarih', '')}tarihli ve "
                f"{item.get('sayi', '')}sayılı {item.get('aciklama', '')}."
            )
            ilgi_satirlari.append(satir)
        gecerli, mesaj = ilgi_formati_dogru_mu(ilgi_satirlari)
        if not gecerli:
            sonuc.hata_ekle("ILGI_FORMAT", mesaj, "Madde 15")

    # ── 5a. Tekit yazısında ilgi zorunlu (Madde 34) ───────────────────────────
    if yazi_turu == "tekit_yazisi":
        gecerli, mesaj = tekit_ilgi_zorunlu_mu(ilgi_mevcut)
        if not gecerli:
            sonuc.hata_ekle("TEKIT_ILGI_ZORUNLU", mesaj, "Madde 34")

        # Tekit metni kalıbı
        metin_parcalari = taslak.get("metin_paragraflari", [])
        metin_ek = taslak.get("metin_ek", "")
        tam_metin = " ".join(metin_parcalari) + " " + metin_ek
        gecerli, mesaj = tekit_metin_kalibi_dogru_mu(tam_metin)
        if not gecerli:
            sonuc.hata_ekle("TEKIT_METIN_KALIBI", mesaj, "Madde 34")

    # ── 5b. Cevap yazısında ilgi zorunlu [TASARIM KARARI] ────────────────────
    if yazi_turu == "cevap_yazisi":
        gecerli, mesaj = cevap_ilgi_zorunlu_mu(ilgi_mevcut)
        if not gecerli:
            sonuc.hata_ekle(
                "CEVAP_ILGI_ZORUNLU", mesaj, "[TASARIM KARARI]",
                tasarim_karari=True
            )

    # ── 7. Kapanış İfadesi (Madde 16/12) ──────────────────────────────────────
    # Tekit yazısında kapanış şablona sabitlenmiştir; validator kontrolü atlanır.
    if yazi_turu != "tekit_yazisi":
        kapalis = taslak.get("kapalis_ifadesi", "")
        muhatap_turu_param = taslak.get("muhatap_turu", "")
        if kapalis:
            gecerli, mesaj = arz_rica_dogru_mu(kapalis, muhatap_turu_param)
            if not gecerli:
                sonuc.hata_ekle("ARZ_RICA", mesaj, "Madde 16/12, Madde 31/7")

    # ── 8. İmza Bloğu (Madde 17) ──────────────────────────────────────────────
    imza = taslak.get("imza", {})
    gecerli, mesaj = imza_blogu_dogru_mu(
        imza_ad_soyad=imza.get("ad_soyad", ""),
        imza_unvan=imza.get("unvan", ""),
        yetki_turu=imza.get("yetki_turu", "normal"),
        vekil_makam=imza.get("vekil_makam", ""),
    )
    if not gecerli:
        sonuc.hata_ekle("IMZA_BLOKU", mesaj, "Madde 17")

    # ── 9. Ek Listesi (Madde 18) ──────────────────────────────────────────────
    ekler = taslak.get("ekler", None)
    gecerli, mesaj = ek_listesi_dogru_mu(ekler)
    if not gecerli:
        sonuc.hata_ekle("EK_LISTESI", mesaj, "Madde 18")

    # ── 10. Dağıtım Listesi (Madde 19) ────────────────────────────────────────
    dagitim = taslak.get("dagitim", None)
    gecerli, mesaj = dagitim_listesi_dogru_mu(dagitim)
    if not gecerli:
        sonuc.hata_ekle("DAGITIM_LISTESI", mesaj, "Madde 19")

    # ── TC Başlık (Madde 10) ──────────────────────────────────────────────────
    tc_baslik = taslak.get("tc_baslik", {})
    gecerli, mesaj = tc_baslik_dogru_mu(
        ilk_satir="T.C.",  # Şablon her zaman T.C. yazar; içerik parametreli
        idare_adi=tc_baslik.get("idare_adi", ""),
        birim_adi=tc_baslik.get("birim_adi", ""),
    )
    if not gecerli:
        sonuc.hata_ekle("TC_BASLIK", mesaj, "Madde 10")

    # ── Sayfa No Formatı (Madde 10) ───────────────────────────────────────────
    sayfa_no = taslak.get("sayfa_no", "")
    if sayfa_no:
        gecerli, mesaj = sayfa_no_formati_dogru_mu(sayfa_no)
        if not gecerli:
            sonuc.hata_ekle("SAYFA_NO_FORMAT", mesaj, "Madde 10")

    return sonuc
