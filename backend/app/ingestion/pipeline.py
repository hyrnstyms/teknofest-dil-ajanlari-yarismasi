from pathlib import Path
from typing import List

from .document import Document
from .document_loader import load_file


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


# Bunlar normal document corpus'una girmeyecek.
SPECIAL_DATASETS = {
    "qa_benchmark_gold.csv": "evaluation",
    "statute_chunks.csv": "pre_chunked_legal",
    "train-00000-of-00001.parquet": "dataset",
}


def collect_documents(
    directory: str,
    source_type: str,
) -> List[Document]:

    root = Path(directory)

    if not root.exists():
        raise FileNotFoundError(
            f"Dizin bulunamadı: {directory}"
        )

    documents = []

    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
    )

    print(f"\n[{source_type.upper()}]")
    print(f"Dizin: {directory}")
    print(f"Toplam dosya: {len(files)}")

    for path in files:

        # Benchmark ve hazır datasetleri normal corpus'a sokma.
        if path.name in SPECIAL_DATASETS:
            role = SPECIAL_DATASETS[path.name]

            print(
                f"[AYRI TUTULDU] {path.name} "
                f"(rol: {role})"
            )
            continue

        extension = path.suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            print(
                f"[ATLANDI] {path.name} "
                f"(desteklenmeyen format: {extension})"
            )
            continue

        try:
            loaded = load_file(
                path,
                source_type,
            )

            documents.extend(loaded)

            print(
                f"[OK] {path.name} "
                f"→ {len(loaded)} document"
            )

        except Exception as exc:
            print(
                f"[HATA] {path.name}: {exc}"
            )

    return documents