"""Index privacy-minimized, labelled synthetic document exemplars.

Only repository-owned synthetic examples are accepted. Runtime/user uploads
are deliberately excluded from this persistent collection.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from backend.app.rag.chunker import chunk_document
from backend.app.rag.qdrant_store import DOCUMENT_COLLECTION, QdrantStore
from scripts.index_qdrant import index_collection


KAYMAKAMLIK_EXAMPLES = Path(
    "data/institutions/kaymakamlik/ornek_evraklar/curated_scenarios.jsonl"
)
BELEDIYE_EXAMPLES = Path("data/institutions/belediye/ornek_evraklar")

BELEDIYE_UNIT_BY_FILE = {
    "01_ruhsat_basvurusu.txt": "zabita",
    "02_yol_onarim_talebi.txt": "fen_isleri",
    "03_gurultu_sikayeti.txt": "zabita",
    "04_imar_durumu_talebi.txt": "imar_sehircilik",
    "05_su_faturasi_itiraz.txt": "mali_hizmetler",
    "06_cop_toplama_sikayet.txt": "temizlik_isleri",
    "07_park_bakim_talebi.txt": "park_bahce",
    "08_imar_plani_itiraz.txt": "imar_sehircilik",
    "09_kurumlar_arasi_afet_koordinasyon.txt": "zabita",
    "10_kacak_yapi_sikayet.txt": "zabita",
    "11_su_aboneligi_basvuru.txt": "su_kanal",
    "12_bilgi_edinme_basvuru.txt": "yazi_isleri",
}

SENSITIVE_LINE_RE = re.compile(
    r"^\s*(?:başvuran|şikayet eden|t\.\s*c\.|tc\s*kimlik|adres|telefon|"
    r"vergi\s*no|imza|tarih)\s*:",
    re.IGNORECASE,
)
PHONE_RE = re.compile(r"\b0?5\d{2}(?:[\s.-]*\d{3}){2}[\s.-]*\d{2}\b")
IDENTITY_RE = re.compile(r"\b\d{11}\b")


def sanitize_example_text(text: str) -> str:
    """Remove identity/contact lines before a synthetic example leaves disk."""
    lines = [
        line
        for line in str(text).splitlines()
        if not SENSITIVE_LINE_RE.match(line)
    ]
    cleaned = "\n".join(lines)
    cleaned = PHONE_RE.sub("[TELEFON]", cleaned)
    cleaned = IDENTITY_RE.sub("[KIMLIK]", cleaned)
    return cleaned.strip()


def _document(
    *,
    example_id: str,
    institution: str,
    expected_unit: str,
    text: str,
    source: str,
    coverage_tag: str = "",
) -> dict[str, Any]:
    return {
        "id": f"{institution}_{example_id}",
        "source": source,
        "source_type": "synthetic_example",
        "title": example_id,
        "text": sanitize_example_text(text),
        "metadata": {
            "institution": institution,
            "expected_unit": expected_unit,
            "coverage_tag": coverage_tag,
            "synthetic": True,
            "rag_eligible": True,
            "trusted_source": False,
        },
    }


def load_example_documents(institution: str = "all") -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []

    if institution in {"all", "kaymakamlik"}:
        for line in KAYMAKAMLIK_EXAMPLES.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            expected_unit = str(row.get("gold", {}).get("expected_unit") or "")
            if not expected_unit:
                continue
            documents.append(_document(
                example_id=str(row["id"]),
                institution="kaymakamlik",
                expected_unit=expected_unit,
                text=str(row.get("text") or ""),
                source=str(KAYMAKAMLIK_EXAMPLES),
                coverage_tag=str(row.get("coverage_tag") or ""),
            ))

    if institution in {"all", "belediye"}:
        for filename, expected_unit in BELEDIYE_UNIT_BY_FILE.items():
            path = BELEDIYE_EXAMPLES / filename
            documents.append(_document(
                example_id=path.stem,
                institution="belediye",
                expected_unit=expected_unit,
                text=path.read_text(encoding="utf-8"),
                source=str(path),
            ))

    return documents


def build_example_chunks(institution: str = "all") -> list[dict[str, Any]]:
    chunks = []
    for document in load_example_documents(institution):
        chunks.extend(chunk.model_dump() for chunk in chunk_document(document))
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--institution",
        choices=["all", "kaymakamlik", "belediye"],
        default="all",
    )
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    chunks = build_example_chunks(args.institution)
    by_institution: dict[str, int] = {}
    for chunk in chunks:
        key = str(chunk["metadata"]["institution"])
        by_institution[key] = by_institution.get(key, 0) + 1

    print(f"Document exemplar chunk sayısı: {len(chunks)}")
    print(f"Kurum dağılımı: {by_institution}")
    if args.dry_run:
        return

    from backend.app.rag.embedding_service import EmbeddingService

    store = QdrantStore()
    store.ensure_all_collections()
    index_collection(
        collection_name=DOCUMENT_COLLECTION,
        chunks=chunks,
        embedding_service=EmbeddingService(device=args.device),
        qdrant_store=store,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
