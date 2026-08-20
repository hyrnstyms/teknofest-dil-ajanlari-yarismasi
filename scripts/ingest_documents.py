"""
scripts/ingest_documents.py
───────────────────────────────────────────────────────────────
Belge ingestion pipeline.

data/raw/ kaldırıldı.

Şu an ingestion için yalnız:
  - data/regulations/   → mevzuat PDF'leri (canonical source)
  - (kullanıcı yükleme) → runtime upload, ayrı API üzerinden

statute_chunks.csv → data/knowledge/statute_chunks.csv
  chunk_documents.py tarafından doğrudan okunur;
  bu script'e dahil EDİLMEZ (pre-chunked, re-chunk yok).

qa_benchmark_gold.csv → data/evaluation/legal/
  Hiçbir zaman ingestion'a girmez.
"""

from pathlib import Path
import sys


# Proje kökünü Python path'e ekle
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from backend.app.ingestion.pipeline import collect_documents
from backend.app.ingestion.jsonl_writer import write_jsonl


def main():

    regulations = collect_documents(
        "data/regulations",
        "mevzuat",
    )

    documents = regulations

    print()
    print("================================")
    print("GENEL ÖZET")
    print("================================")
    print(f"Regulation documents: {len(regulations)}")
    print(f"Toplam              : {len(documents)}")

    write_jsonl(
        documents,
        "data/processed/documents.jsonl",
    )


if __name__ == "__main__":
    main()