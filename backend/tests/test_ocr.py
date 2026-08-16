from backend.app.ocr.ocr_service import OCRService


def test_pdf_text_extraction():
    service = OCRService()

    text = service.extract_text_from_pdf(
        "data/raw/Dikili Kaymakamlığı - örnek dilekçe.pdf"
    )

    print("\n--- ÇIKARILAN METİN ---")
    print(text)

    assert isinstance(text, str)
    assert len(text.strip()) > 0