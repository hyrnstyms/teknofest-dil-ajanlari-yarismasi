from pathlib import Path
import sys


# Proje kökünü Python path'e ekle
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from backend.app.ingestion.pipeline import collect_documents
from backend.app.ingestion.jsonl_writer import write_jsonl


def main():

    raw_documents = collect_documents(
        "data/raw",
        "raw",
    )

    regulations = collect_documents(
        "data/regulations",
        "mevzuat",
    )

    documents = raw_documents + regulations

    print()
    print("================================")
    print("GENEL ÖZET")
    print("================================")
    print(f"Raw documents       : {len(raw_documents)}")
    print(f"Regulation documents: {len(regulations)}")
    print(f"Toplam              : {len(documents)}")

    write_jsonl(
        documents,
        "data/processed/documents.jsonl",
    )


if __name__ == "__main__":
    main()