"""
backend/tests/official_writing/test_docx_renderer.py
────────────────────────────────────────────────────────────────────────────
DOCX Renderer testleri.

render_to_docx() fonksiyonunun biçimlendirilmiş .docx dosyası ürettiğini
doğrular. Sadece "hata vermedi" ile yetinilmez; üretilen belge
python-docx ile geri okunup alanların metinde gerçekten geçtiği,
sayfa düzeni parametrelerinin sayısal olarak doğru olduğu kontrol edilir.
"""

from __future__ import annotations

import io

import pytest
from docx import Document
from docx.shared import Mm, Cm

from backend.app.official_writing.docx_renderer import render_to_docx


# ── Yardımcı: Tüm paragraf metinlerini toplar ─────────────────────────────

def _all_text(doc: Document) -> str:
    """Belgedeki tüm paragraf metinlerini tek string olarak birleştirir."""
    return "\n".join(p.text for p in doc.paragraphs)


# ── Ortak fixture: Minimal üst yazı context'i ──────────────────────────────

@pytest.fixture()
def ust_yazi_context() -> dict:
    """build_official_writing_context() çıktısının 'context' anahtarına
    karşılık gelen minimal üst yazı context'i."""
    return {
        "tc_baslik": {
            "idare_adi": "ISPARTA KAYMAKAMLIĞI",
            "birim_adi": "Yazı İşleri Müdürlüğü",
        },
        "sayi": "E-12345678-100.01-001",
        "tarih": "24.08.2026",
        "konu": "Personel Devamsızlık Bildirimi",
        "muhatap": {
            "tur": "kurum",
            "isim": "ISPARTA VALİLİĞİ",
        },
        "muhatap_turu": "kurum_ust",
        "kapalis_ifadesi": "arz ederim.",
        "ilgi": [],
        "metin_paragraflari": [
            "Biriminizde görevli personelin devamsızlık durumu hakkında bilgi verilmesi gerekmektedir.",
            "Konuyla ilgili gerekli işlemlerin yapılması hususunda gereğini arz ederim.",
        ],
        "imza": {
            "ad_soyad": "Mehmet YILMAZ",
            "unvan": "Kaymakam",
            "yetki_turu": "normal",
        },
        "ekler": [],
        "dagitim": None,
        "iletisim": {"adres": "", "irtibat": ""},
        "sayfa_no": None,
        "uygunsuz_belge_uyarisi": None,
    }


@pytest.fixture()
def cevap_yazisi_context() -> dict:
    """İlgi zorunlu cevap yazısı context'i."""
    return {
        "tc_baslik": {
            "idare_adi": "ISPARTA KAYMAKAMLIĞI",
            "birim_adi": "Yazı İşleri Müdürlüğü",
        },
        "sayi": "E-12345678-100.01-002",
        "tarih": "24.08.2026",
        "konu": "Bilgi Talebi Cevabı",
        "muhatap": {
            "tur": "kurum",
            "isim": "BURDUR VALİLİĞİ",
        },
        "muhatap_turu": "kurum_ust",
        "kapalis_ifadesi": "arz ederim.",
        "ilgi": [
            {
                "tarih": "10.07.2026",
                "sayi": "E-98765432-200.02-555",
                "aciklama": "ilgi yazınız",
            }
        ],
        "metin_paragraflari": [
            "İlgi yazınızda belirtilen husus incelenmiştir.",
            "Gerekli bilgiler ekte sunulmuştur.",
        ],
        "imza": {
            "ad_soyad": "Ayşe KARA",
            "unvan": "Vali Yardımcısı",
            "yetki_turu": "normal",
        },
        "ekler": [
            {"ad": "Bilgi Notu", "bilgi": "3 sayfa"},
        ],
        "dagitim": None,
        "iletisim": {"adres": "Isparta Merkez", "irtibat": "Yazı İşleri"},
        "sayfa_no": None,
        "uygunsuz_belge_uyarisi": None,
    }


# ── Test 1: Üst Yazı — Temel İçerik Kontrolü ──────────────────────────────

class TestRenderToDocxUstYazi:
    """Üst yazı DOCX üretiminin içerik doğruluğu."""

    def test_produces_valid_docx(self, ust_yazi_context):
        """render_to_docx() geçerli bir .docx BytesIO döndürür."""
        result = render_to_docx(ust_yazi_context)
        assert isinstance(result, io.BytesIO)
        # Geri okuyabilmeli — bozuk dosya ise Document() hata verir
        doc = Document(result)
        assert len(doc.paragraphs) > 0

    def test_contains_tc_baslik(self, ust_yazi_context):
        """T.C. başlık bloğu belgede geçmeli."""
        result = render_to_docx(ust_yazi_context)
        doc = Document(result)
        text = _all_text(doc)
        assert "T.C." in text
        assert "ISPARTA KAYMAKAMLIĞI" in text
        assert "Yazı İşleri Müdürlüğü" in text

    def test_contains_sayi_and_tarih(self, ust_yazi_context):
        """Sayı ve Tarih belgede geçmeli."""
        result = render_to_docx(ust_yazi_context)
        doc = Document(result)
        text = _all_text(doc)
        assert "E-12345678-100.01-001" in text
        assert "24.08.2026" in text

    def test_contains_konu(self, ust_yazi_context):
        """Konu alanı belgede geçmeli."""
        result = render_to_docx(ust_yazi_context)
        doc = Document(result)
        text = _all_text(doc)
        assert "Personel Devamsızlık Bildirimi" in text

    def test_contains_muhatap(self, ust_yazi_context):
        """Muhatap belgede geçmeli."""
        result = render_to_docx(ust_yazi_context)
        doc = Document(result)
        text = _all_text(doc)
        assert "ISPARTA VALİLİĞİ" in text

    def test_contains_metin_paragraflari(self, ust_yazi_context):
        """Metin paragrafları belgede geçmeli."""
        result = render_to_docx(ust_yazi_context)
        doc = Document(result)
        text = _all_text(doc)
        assert "devamsızlık durumu" in text
        assert "gereğini arz ederim" in text

    def test_contains_kapalis_ifadesi(self, ust_yazi_context):
        """Kapanış ifadesi belgede geçmeli."""
        result = render_to_docx(ust_yazi_context)
        doc = Document(result)
        text = _all_text(doc)
        assert "arz ederim." in text

    def test_contains_imza_block(self, ust_yazi_context):
        """İmza bloğu (ad soyad + unvan) belgede geçmeli."""
        result = render_to_docx(ust_yazi_context)
        doc = Document(result)
        text = _all_text(doc)
        assert "Mehmet YILMAZ" in text
        assert "Kaymakam" in text


# ── Test 2: Cevap Yazısı — İlgi + Ek Kontrolü ─────────────────────────────

class TestRenderToDocxCevapYazisi:
    """Cevap yazısı DOCX üretiminin içerik doğruluğu."""

    def test_contains_ilgi(self, cevap_yazisi_context):
        """İlgi satırı belgede geçmeli."""
        result = render_to_docx(cevap_yazisi_context)
        doc = Document(result)
        text = _all_text(doc)
        assert "10.07.2026" in text
        assert "E-98765432-200.02-555" in text
        assert "ilgi yazınız" in text

    def test_contains_kapalis_arz_ederim(self, cevap_yazisi_context):
        """Kurum üst makam kapanışı 'arz ederim.' olmalı."""
        result = render_to_docx(cevap_yazisi_context)
        doc = Document(result)
        text = _all_text(doc)
        assert "arz ederim." in text

    def test_contains_ek(self, cevap_yazisi_context):
        """Ek listesi belgede geçmeli."""
        result = render_to_docx(cevap_yazisi_context)
        doc = Document(result)
        text = _all_text(doc)
        assert "Bilgi Notu" in text
        assert "3 sayfa" in text

    def test_contains_iletisim(self, cevap_yazisi_context):
        """İletişim bilgisi belgede geçmeli."""
        result = render_to_docx(cevap_yazisi_context)
        doc = Document(result)
        text = _all_text(doc)
        assert "Isparta Merkez" in text

    def test_contains_imza(self, cevap_yazisi_context):
        """İmza bloğu belgede geçmeli."""
        result = render_to_docx(cevap_yazisi_context)
        doc = Document(result)
        text = _all_text(doc)
        assert "Ayşe KARA" in text
        assert "Vali Yardımcısı" in text


# ── Test 3: Sayfa Düzeni — Sayısal Doğrulama ──────────────────────────────

class TestRenderToDocxPageLayout:
    """Sayfa düzeni parametrelerinin sayısal olarak doğruluğu.

    python-docx dahili olarak EMU (English Metric Units) kullanır.
    Mm/Cm dönüşümlerinde küçük yuvarlama farkları olabilir;
    bu nedenle tolerans payı bırakılır (±1000 EMU ≈ ±0.1 mm).
    """

    EMU_TOLERANCE = 5000  # ~0.5 mm tolerans

    def test_page_width_is_a4(self, ust_yazi_context):
        """Sayfa genişliği A4 = 210 mm olmalı (±0.5mm tolerans)."""
        result = render_to_docx(ust_yazi_context)
        doc = Document(result)
        section = doc.sections[0]
        expected = Mm(210)
        actual = section.page_width
        assert abs(actual - expected) <= self.EMU_TOLERANCE, (
            f"Sayfa genişliği {actual} EMU, beklenen {expected} EMU "
            f"(fark: {abs(actual - expected)} EMU, tolerans: {self.EMU_TOLERANCE} EMU)"
        )

    def test_page_height_is_a4(self, ust_yazi_context):
        """Sayfa yüksekliği A4 = 297 mm olmalı (±0.5mm tolerans)."""
        result = render_to_docx(ust_yazi_context)
        doc = Document(result)
        section = doc.sections[0]
        expected = Mm(297)
        actual = section.page_height
        assert abs(actual - expected) <= self.EMU_TOLERANCE, (
            f"Sayfa yüksekliği {actual} EMU, beklenen {expected} EMU "
            f"(fark: {abs(actual - expected)} EMU, tolerans: {self.EMU_TOLERANCE} EMU)"
        )

    def test_top_margin_is_1_5_cm(self, ust_yazi_context):
        """Üst kenar boşluğu 1,5 cm olmalı (±0.5mm tolerans)."""
        result = render_to_docx(ust_yazi_context)
        doc = Document(result)
        section = doc.sections[0]
        expected = Cm(1.5)
        actual = section.top_margin
        assert abs(actual - expected) <= self.EMU_TOLERANCE, (
            f"Üst kenar boşluğu {actual} EMU, beklenen {expected} EMU "
            f"(fark: {abs(actual - expected)} EMU, tolerans: {self.EMU_TOLERANCE} EMU)"
        )

    def test_bottom_margin_is_1_5_cm(self, ust_yazi_context):
        """Alt kenar boşluğu 1,5 cm olmalı (±0.5mm tolerans)."""
        result = render_to_docx(ust_yazi_context)
        doc = Document(result)
        section = doc.sections[0]
        expected = Cm(1.5)
        actual = section.bottom_margin
        assert abs(actual - expected) <= self.EMU_TOLERANCE, (
            f"Alt kenar boşluğu {actual} EMU, beklenen {expected} EMU "
            f"(fark: {abs(actual - expected)} EMU, tolerans: {self.EMU_TOLERANCE} EMU)"
        )

    def test_left_margin_is_1_5_cm(self, ust_yazi_context):
        """Sol kenar boşluğu 1,5 cm olmalı (±0.5mm tolerans)."""
        result = render_to_docx(ust_yazi_context)
        doc = Document(result)
        section = doc.sections[0]
        expected = Cm(1.5)
        actual = section.left_margin
        assert abs(actual - expected) <= self.EMU_TOLERANCE, (
            f"Sol kenar boşluğu {actual} EMU, beklenen {expected} EMU "
            f"(fark: {abs(actual - expected)} EMU, tolerans: {self.EMU_TOLERANCE} EMU)"
        )

    def test_right_margin_is_1_5_cm(self, ust_yazi_context):
        """Sağ kenar boşluğu 1,5 cm olmalı (±0.5mm tolerans)."""
        result = render_to_docx(ust_yazi_context)
        doc = Document(result)
        section = doc.sections[0]
        expected = Cm(1.5)
        actual = section.right_margin
        assert abs(actual - expected) <= self.EMU_TOLERANCE, (
            f"Sağ kenar boşluğu {actual} EMU, beklenen {expected} EMU "
            f"(fark: {abs(actual - expected)} EMU, tolerans: {self.EMU_TOLERANCE} EMU)"
        )

    def test_font_is_times_new_roman_12pt(self, ust_yazi_context):
        """İlk içerikli paragrafın yazı tipi Times New Roman 12pt olmalı."""
        result = render_to_docx(ust_yazi_context)
        doc = Document(result)
        # İlk paragraf "T.C." olmalı
        first_para = doc.paragraphs[0]
        assert first_para.text.strip() == "T.C."
        run = first_para.runs[0]
        assert run.font.name == "Times New Roman"
        from docx.shared import Pt
        assert run.font.size == Pt(12)
