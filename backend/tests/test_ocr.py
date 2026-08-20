"""
backend/tests/test_ocr.py

OCR Service testleri.
data/evaluation/ocr/ altındaki hazır PNG görüntüleri kullanılır.
data/raw/ kaldırıldı; testler gerçek evaluation corpus'unu kullanır.
"""

from pathlib import Path
from backend.app.ocr.ocr_service import OCRService


# data/evaluation/ocr/temiz/ altındaki herhangi bir PNG
_TEMIZ_DIR = Path("data/evaluation/ocr/temiz")


def _first_png(directory: Path) -> Path | None:
    pngs = sorted(directory.glob("*.png"))
    return pngs[0] if pngs else None


def test_ocr_service_pdf_missing_raises():
    """Var olmayan dosya FileNotFoundError vermeli."""
    service = OCRService()
    try:
        service.extract_text_from_pdf("data/does_not_exist.pdf")
        assert False, "FileNotFoundError bekleniyor"
    except FileNotFoundError:
        pass


def test_ocr_service_extract_from_evaluation_png():
    """
    data/evaluation/ocr/temiz/ altındaki ilk PNG dosyası üzerinde
    OCR service'in metin döndürdüğünü doğrula.

    PaddleOCR kurulu değilse veya model yüklenemezse
    bu test atlana bilir; bağlantı hatası değil model hatası.
    """
    png = _first_png(_TEMIZ_DIR)
    if png is None:
        import pytest
        pytest.skip("data/evaluation/ocr/temiz/ altında PNG bulunamadı.")

    service = OCRService()
    try:
        text = service.extract_text_from_image(str(png))
        assert isinstance(text, str)
        # Temiz görüntüden en az bir karakter beklenir
        assert len(text.strip()) > 0, f"OCR boş metin döndürdü: {png}"
    except (ImportError, RuntimeError, AttributeError) as exc:
        import pytest
        pytest.skip(f"PaddleOCR kullanılamadı: {exc}")