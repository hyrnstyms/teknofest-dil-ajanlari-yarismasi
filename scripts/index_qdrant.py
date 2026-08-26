import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from backend.app.rag.embedding_service import EmbeddingService
from backend.app.rag.qdrant_store import (
    QdrantStore,
    LEGAL_COLLECTION,
    DOCUMENT_COLLECTION,
)
from backend.app.rag.point_ids import deterministic_point_id


DEFAULT_CHUNKS_FILE = Path(
    "data/processed/chunks.jsonl"
)


def load_chunks(chunks_file: Path = DEFAULT_CHUNKS_FILE) -> list[dict[str, Any]]:
    if not chunks_file.exists():
        raise FileNotFoundError(
            f"{chunks_file} bulunamadı."
        )

    chunks = []

    with chunks_file.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line in file:
            if not line.strip():
                continue

            chunk = json.loads(line)

            metadata = (
                chunk.get("metadata", {})
                or {}
            )

            if not metadata.get(
                "rag_eligible",
                False,
            ):
                continue

            chunks.append(chunk)

    return chunks


def point_id_for_chunk(chunk: dict[str, Any]) -> str:
    metadata = chunk.get("metadata", {}) or {}
    source_id = (
        chunk.get("source")
        or metadata.get("source")
        or chunk.get("document_id")
        or chunk.get("id")
        or "unknown"
    )
    madde_no = (
        metadata.get("madde_no")
        or metadata.get("article")
        or chunk.get("id")
        or "chunk"
    )
    chunk_index = chunk.get("chunk_index", chunk.get("id", 0))
    return deterministic_point_id(
        str(source_id),
        str(madde_no),
        chunk_index,
        str(chunk.get("text", "")),
    )


def build_payload(
    chunk: dict[str, Any],
) -> dict[str, Any]:

    metadata = (
        chunk.get("metadata", {})
        or {}
    )

    return {
        "chunk_id": chunk.get("id"),

        "document_id": chunk.get(
            "document_id"
        ),

        "source": chunk.get("source"),

        "source_type": chunk.get(
            "source_type"
        ),

        "corpus_type": chunk.get(
            "corpus_type"
        ),

        "chunk_index": chunk.get(
            "chunk_index"
        ),

        "text": chunk.get("text"),

        "content_hash": chunk.get(
            "content_hash"
        ),

        "title": metadata.get("title"),

        "rag_domain": metadata.get(
            "rag_domain"
        ),

        "chunk_strategy": metadata.get(
            "chunk_strategy"
        ),

        "law_number": metadata.get(
            "law_number"
        ),

        "madde_no": metadata.get(
            "madde_no"
        ),

        "url": metadata.get("url"),

        "trusted_source": metadata.get(
            "trusted_source",
            False,
        ),

        "synthetic": metadata.get(
            "synthetic",
            False,
        ),

        "metadata": metadata,
    }


def get_collection_name(
    chunk: dict[str, Any],
) -> str:

    corpus_type = chunk.get(
        "corpus_type"
    )

    if corpus_type == "legal_knowledge":
        return LEGAL_COLLECTION

    if corpus_type == "document_knowledge":
        return DOCUMENT_COLLECTION

    raise ValueError(
        f"Bilinmeyen corpus_type: "
        f"{corpus_type}"
    )


def get_existing_ids(
    qdrant_store: QdrantStore,
    collection_name: str,
    ids: list[str],
) -> set[str]:
    """
    Qdrant'ta zaten bulunan point ID'lerini döndürür.

    Böylece script kapatılıp tekrar çalıştırıldığında
    daha önce embed edilen chunklar tekrar hesaplanmaz.
    """

    if not ids:
        return set()

    points = (
        qdrant_store.client.retrieve(
            collection_name=collection_name,
            ids=ids,
            with_payload=False,
            with_vectors=False,
        )
    )

    return {
        str(point.id)
        for point in points
    }


def index_collection(
    collection_name: str,
    chunks: list[dict[str, Any]],
    embedding_service: EmbeddingService,
    qdrant_store: QdrantStore,
    batch_size: int,
) -> None:

    total = len(chunks)

    indexed_count = 0
    skipped_count = 0

    print()
    print(
        "================================"
    )
    print(
        f"INDEXLENİYOR: {collection_name}"
    )
    print(
        f"Seçilen chunk: {total}"
    )
    print(
        "================================"
    )

    for start in range(
        0,
        total,
        batch_size,
    ):

        end = min(
            start + batch_size,
            total,
        )

        batch = chunks[start:end]

        batch_ids = [
            point_id_for_chunk(chunk)
            for chunk in batch
        ]

        existing_ids = get_existing_ids(
            qdrant_store=qdrant_store,
            collection_name=collection_name,
            ids=batch_ids,
        )

        missing_chunks = []
        missing_ids = []

        for chunk, point_id in zip(
            batch,
            batch_ids,
        ):
            if point_id in existing_ids:
                skipped_count += 1
                continue

            missing_chunks.append(chunk)
            missing_ids.append(point_id)

        # Bütün batch daha önce indexlenmiş.
        if not missing_chunks:
            print(
                f"[ATLANDI] {end}/{total} "
                f"(zaten Qdrant'ta)"
            )
            continue

        texts = [
            str(
                chunk.get(
                    "text",
                    "",
                )
            )
            for chunk in missing_chunks
        ]

        vectors = (
            embedding_service.encode_documents(
                texts,
                batch_size=batch_size,
            )
        )

        payloads = [
            build_payload(chunk)
            for chunk in missing_chunks
        ]

        qdrant_store.upsert_batch(
            collection_name=collection_name,
            ids=missing_ids,
            vectors=vectors,
            payloads=payloads,
        )

        indexed_count += len(
            missing_chunks
        )

        print(
            f"[OK] {end}/{total} "
            f"| yeni: {len(missing_chunks)}"
        )

    print()
    print(
        f"[TAMAMLANDI] {collection_name}"
    )
    print(
        f"Yeni indexlenen: {indexed_count}"
    )
    print(
        f"Zaten vardı: {skipped_count}"
    )


def select_chunks(
    all_chunks: list[dict[str, Any]],
    mode: str,
    law_number: str | None,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:

    legal_chunks = [
        chunk
        for chunk in all_chunks
        if chunk.get("corpus_type")
        == "legal_knowledge"
    ]

    document_chunks = [
        chunk
        for chunk in all_chunks
        if chunk.get("corpus_type")
        == "document_knowledge"
    ]

    # Şu an kullanacağımız küçük geliştirme corpus'u:
    #
    # 4982 Bilgi Edinme Hakkı Kanunu
    # + Resmî Yazışma Kılavuzu
    # + gerçek belge örnekleri
    if mode == "bootstrap":

        legal_chunks = [
            chunk
            for chunk in legal_chunks
            if (
                str(
                    chunk.get(
                        "metadata",
                        {},
                    ).get(
                        "law_number",
                        "",
                    )
                )
                == "4982"
                or
                chunk.get(
                    "metadata",
                    {},
                ).get(
                    "rag_domain"
                )
                == "official_writing"
            )
        ]

        return (
            legal_chunks,
            document_chunks,
        )

    # Sadece belirli bir kanun.
    if mode == "law":

        if not law_number:
            raise ValueError(
                "--mode law kullanılırken "
                "--law-number verilmelidir."
            )

        legal_chunks = [
            chunk
            for chunk in legal_chunks
            if str(
                chunk.get(
                    "metadata",
                    {},
                ).get(
                    "law_number",
                    "",
                )
            )
            == str(law_number)
        ]

        return legal_chunks, []

    # Sadece Resmî Yazışma Kılavuzu.
    if mode == "official":

        legal_chunks = [
            chunk
            for chunk in legal_chunks
            if chunk.get(
                "metadata",
                {},
            ).get(
                "rag_domain"
            )
            == "official_writing"
        ]

        return legal_chunks, []

    # Sadece gerçek belge örnekleri.
    if mode == "documents":
        return [], document_chunks

    # Bütün corpus.
    if mode == "all":
        return (
            legal_chunks,
            document_chunks,
        )

    raise ValueError(
        f"Bilinmeyen mode: {mode}"
    )


def main(
    batch_size: int,
    mode: str,
    law_number: str | None,
    chunks_file: Path = DEFAULT_CHUNKS_FILE,
    device: str = "cpu",
) -> None:

    all_chunks = load_chunks(chunks_file)

    legal_chunks, document_chunks = (
        select_chunks(
            all_chunks=all_chunks,
            mode=mode,
            law_number=law_number,
        )
    )

    print()
    print(
        "================================"
    )
    print(
        f"INDEX MODU: {mode}"
    )
    print(
        "================================"
    )

    print(
        f"Seçilen legal chunk: "
        f"{len(legal_chunks)}"
    )

    print(
        f"Seçilen document chunk: "
        f"{len(document_chunks)}"
    )

    print()

    embedding_service = (
        EmbeddingService(device=device)
    )

    qdrant_store = QdrantStore()

    qdrant_store.health_check()

    qdrant_store.ensure_all_collections()

    if legal_chunks:
        index_collection(
            collection_name=(
                LEGAL_COLLECTION
            ),
            chunks=legal_chunks,
            embedding_service=(
                embedding_service
            ),
            qdrant_store=(
                qdrant_store
            ),
            batch_size=batch_size,
        )

    if document_chunks:
        index_collection(
            collection_name=(
                DOCUMENT_COLLECTION
            ),
            chunks=document_chunks,
            embedding_service=(
                embedding_service
            ),
            qdrant_store=(
                qdrant_store
            ),
            batch_size=batch_size,
        )

    legal_count = (
        qdrant_store.count_points(
            LEGAL_COLLECTION
        )
    )

    document_count = (
        qdrant_store.count_points(
            DOCUMENT_COLLECTION
        )
    )

    print()
    print(
        "================================"
    )
    print(
        "QDRANT MEVCUT DURUM"
    )
    print(
        "================================"
    )

    print(
        f"legal_knowledge: "
        f"{legal_count}"
    )

    print(
        f"document_knowledge: "
        f"{document_count}"
    )

    print(
        f"TOPLAM: "
        f"{legal_count + document_count}"
    )


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
    )

    parser.add_argument(
        "--mode",
        choices=[
            "bootstrap",
            "law",
            "official",
            "documents",
            "all",
        ],
        default="bootstrap",
    )

    parser.add_argument(
        "--device",
        choices=["cpu", "cuda"],
        default="cpu",
    )

    parser.add_argument(
        "--chunks-file",
        type=Path,
        default=DEFAULT_CHUNKS_FILE,
    )

    parser.add_argument(
        "--law-number",
        type=str,
        default=None,
    )

    args = parser.parse_args()

    main(
        batch_size=args.batch_size,
        mode=args.mode,
        law_number=args.law_number,
        chunks_file=args.chunks_file,
        device=args.device,
    )
