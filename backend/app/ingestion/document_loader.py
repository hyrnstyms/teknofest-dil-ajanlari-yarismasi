from pathlib import Path
from typing import List

from .csv_loader import load_csv
from .doc_loader import load_doc
from .docx_loader import load_docx
from .document import Document
from .excel_loader import load_excel
from .parquet_loader import load_parquet
from .pdf_loader import load_pdf
from .text_loader import load_text


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".csv",
    ".parquet",
    ".txt",
    ".xls",
    ".xlsx",
}


def create_document(
    path: Path,
    text: str,
    source_type: str,
) -> Document:
    return Document(
        id=path.stem,
        source=str(path),
        source_type=source_type,
        file_type=path.suffix.lower().lstrip("."),
        title=path.stem,
        text=text,
        metadata={
            "filename": path.name,
        },
    )


def load_file(
    path: Path,
    source_type: str,
) -> List[Document]:

    extension = path.suffix.lower()

    # PDF
    if extension == ".pdf":
        text = load_pdf(path)

        if not text:
            print(f"[OCR GEREKEBİLİR] {path}")

        return [
            create_document(
                path=path,
                text=text,
                source_type=source_type,
            )
        ]

    # DOCX
    if extension == ".docx":
        text = load_docx(path)

        return [
            create_document(
                path=path,
                text=text,
                source_type=source_type,
            )
        ]

    # Eski Word DOC
    if extension == ".doc":
        text = load_doc(path)

        return [
            create_document(
                path=path,
                text=text,
                source_type=source_type,
            )
        ]

    # Excel
    if extension in {".xls", ".xlsx"}:
        return load_excel(
            path=path,
            source_type=source_type,
        )

    # CSV
    if extension == ".csv":
        return load_csv(path)

    # Parquet
    if extension == ".parquet":
        return load_parquet(path)

    # TXT
    if extension == ".txt":
        text = load_text(path)

        return [
            create_document(
                path=path,
                text=text,
                source_type=source_type,
            )
        ]

    return []