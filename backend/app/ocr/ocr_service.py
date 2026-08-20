from pathlib import Path
import pymupdf

from paddleocr import PaddleOCR


class OCRService:
    def __init__(self):
        self.paddle_ocr = None

    def _get_paddle_ocr(self):
        """
        PaddleOCR modelini ihtiyaç olduğunda yükler.
        Böylece metin tabanlı PDF'lerde gereksiz model yüklenmez.
        """
        if self.paddle_ocr is None:
            self.paddle_ocr = PaddleOCR(
                lang="tr"
            )

        return self.paddle_ocr

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        PDF'den metin çıkarır.

        Öncelik:
        1. PDF'in mevcut metin katmanı
        2. Metin bulunamazsa PaddleOCR
        """

        path = Path(pdf_path)

        if not path.exists():
            raise FileNotFoundError(
                f"PDF dosyası bulunamadı: {pdf_path}"
            )

        # --------------------------------------------------
        # 1. PDF METİN KATMANINI DENE
        # --------------------------------------------------

        doc = pymupdf.open(path)

        extracted_pages = []

        for page in doc:
            text = page.get_text("text")

            if text and text.strip():
                extracted_pages.append(text.strip())

        doc.close()

        text_result = "\n\n".join(extracted_pages).strip()

        # Yeterli metin varsa OCR'a gerek yok
        if len(text_result) >= 50:
            return text_result

        # --------------------------------------------------
        # 2. OCR FALLBACK
        # --------------------------------------------------

        return self._extract_with_paddleocr(path)

    def extract_text_from_image(self, image_path: str) -> str:
        """
        Görsel dosyasından (PNG, JPG, vb.) doğrudan metin çıkarır.
        """
        path = Path(image_path)
        
        if not path.exists():
            raise FileNotFoundError(
                f"Görsel dosyası bulunamadı: {image_path}"
            )
            
        ocr = self._get_paddle_ocr()
        result = ocr.predict(str(path))
        
        return self._parse_paddle_result(result)

    def _extract_with_paddleocr(self, pdf_path: Path) -> str:
        """
        Metin katmanı bulunmayan/taranmış PDF'lerde
        PaddleOCR kullanır.
        """

        ocr = self._get_paddle_ocr()

        doc = pymupdf.open(pdf_path)

        all_text = []

        for page_number, page in enumerate(doc):

            pix = page.get_pixmap(
                matrix=pymupdf.Matrix(2, 2)
            )

            image_path = (
                pdf_path.parent /
                f"_ocr_temp_page_{page_number}.png"
            )

            pix.save(image_path)

            result = ocr.predict(
                str(image_path)
            )

            page_text = self._parse_paddle_result(result)

            if page_text:
                all_text.append(page_text)

            image_path.unlink(missing_ok=True)

        doc.close()

        return "\n\n".join(all_text).strip()

    def _parse_paddle_result(self, result) -> str:
        """
        PaddleOCR çıktısından metinleri çıkarır.
        """

        texts = []

        for res in result:

            data = getattr(res, "json", None)

            if callable(data):
                data = data()

            if isinstance(data, dict):

                res_data = data.get("res", data)

                rec_texts = res_data.get(
                    "rec_texts",
                    []
                )

                texts.extend(rec_texts)

        return "\n".join(
            text.strip()
            for text in texts
            if text and text.strip()
        )