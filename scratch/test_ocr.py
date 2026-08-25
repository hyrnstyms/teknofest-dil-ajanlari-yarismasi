import sys
sys.path.insert(0, ".")
from backend.app.ocr.ocr_service import OCRService

pdf_path = "data/regulations/resmi_yazisma_yonetmeligi.pdf"
ocr_svc = OCRService()
text = ocr_svc.extract_text_from_pdf(pdf_path)

print("--- OCR TEXT (FIRST 500 CHARS) ---")
print(text[:500])
