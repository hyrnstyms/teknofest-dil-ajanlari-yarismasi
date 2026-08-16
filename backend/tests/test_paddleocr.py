from paddleocr import PaddleOCR


def test_paddleocr_initialization():
    ocr = PaddleOCR(lang="tr")

    print("\nPaddleOCR başarıyla oluşturuldu.")
    print(ocr)

    assert ocr is not None