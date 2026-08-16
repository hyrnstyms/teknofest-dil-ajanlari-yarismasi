from pathlib import Path

import pymupdf


def load_pdf(path: Path) -> str:
    """
    PDF'in mevcut text layer'ından metin çıkarır.

    Metin katmanı yoksa boş string döndürür.
    OCR işlemi daha sonra OCRService tarafından yapılacaktır.
    """

    text_parts = []

    with pymupdf.open(path) as pdf:
        for page in pdf:
            text = page.get_text("text")

            if text:
                text_parts.append(text)

    return "\n".join(text_parts).strip()