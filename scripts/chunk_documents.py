import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from backend.app.rag.chunker import (
    chunk_document,
    create_content_hash,
    extract_law_number,
)

from backend.app.rag.schemas import (
    Chunk,
)


DOCUMENTS_FILE = Path(
    "data/processed/documents.jsonl"
)

STATUTE_FILE = Path(
    "data/knowledge/statute_chunks.csv"
)

OUTPUT_FILE = Path(
    "data/processed/chunks.jsonl"
)


def load_documents(
) -> list[dict[str, Any]]:

    if not DOCUMENTS_FILE.exists():

        raise FileNotFoundError(
            f"{DOCUMENTS_FILE} bulunamadı."
        )

    documents = []

    with DOCUMENTS_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line in file:

            if not line.strip():
                continue

            document = json.loads(
                line
            )

            # Sentetikleri şimdilik
            # RAG corpus'una almıyoruz.
            if (
                document.get(
                    "source_type"
                )
                == "synthetic"
            ):
                continue

            documents.append(
                document
            )

    return documents


def load_statute_chunks(
) -> tuple[
    list[Chunk],
    set[str],
]:

    if not STATUTE_FILE.exists():

        print(
            "[UYARI] statute_chunks.csv "
            "bulunamadı."
        )

        return [], set()

    dataframe = pd.read_csv(
        STATUTE_FILE,
        dtype=str,
    ).fillna("")

    chunks: list[Chunk] = []

    law_numbers: set[str] = set()

    for row_index, row in (
        dataframe.iterrows()
    ):

        law_number = str(
            row.get(
                "kanun_no",
                "",
            )
        ).strip()

        if law_number:
            law_numbers.add(
                law_number
            )

        # retrieval_text varsa onu tercih et.
        text = str(
            row.get(
                "retrieval_text",
                "",
            )
        ).strip()

        if not text:

            text = str(
                row.get(
                    "context",
                    "",
                )
            ).strip()

        if len(text) < 40:
            continue

        content_hash = (
            create_content_hash(
                text
            )
        )

        document_id = (
            f"statute_{law_number}"
            if law_number
            else "statute_unknown"
        )

        chunk_id = (
            f"statute_"
            f"{row_index:06d}_"
            f"{content_hash[:10]}"
        )

        metadata = {
            "title": (
                row.get(
                    "kaynak",
                    ""
                )
            ),

            "law_number": (
                law_number
            ),

            "madde_no": (
                row.get(
                    "madde_no",
                    ""
                )
            ),

            "context_key": (
                row.get(
                    "context_key",
                    ""
                )
            ),

            "url": (
                row.get(
                    "url",
                    ""
                )
            ),

            "source_row": (
                row.get(
                    "source_row",
                    row_index,
                )
            ),

            "chunk_strategy": (
                "pre_chunked_legal"
            ),

            "rag_domain": "legal",

            "synthetic": False,

            "rag_eligible": True,

            "trusted_source": True,
        }

        chunks.append(
            Chunk(
                id=chunk_id,
                document_id=(
                    document_id
                ),
                source=str(
                    STATUTE_FILE
                ),
                source_type=(
                    "mevzuat"
                ),
                corpus_type=(
                    "legal_knowledge"
                ),
                chunk_index=int(
                    row_index
                ),
                text=text,
                content_hash=(
                    content_hash
                ),
                metadata=metadata,
            )
        )

    return chunks, law_numbers


def should_skip_regulation_pdf(
    document: dict[str, Any],
    statute_law_numbers: set[str],
) -> bool:
    """
    statute_chunks.csv içinde aynı kanun zaten varsa
    aynı kanun PDF'ini ikinci kez indexlememek için
    atlarız.

    Resmî Yazışma Kılavuzu gibi özel belgeler
    etkilenmez.
    """

    if (
        document.get(
            "source_type"
        )
        != "mevzuat"
    ):
        return False

    law_number = (
        extract_law_number(
            document
        )
    )

    if not law_number:
        return False

    return (
        law_number
        in statute_law_numbers
    )


def deduplicate(
    chunks: list[Chunk],
) -> tuple[
    list[Chunk],
    int,
]:

    seen_hashes: set[str] = set()

    unique_chunks = []

    duplicate_count = 0

    for chunk in chunks:

        if (
            chunk.content_hash
            in seen_hashes
        ):
            duplicate_count += 1
            continue

        seen_hashes.add(
            chunk.content_hash
        )

        unique_chunks.append(
            chunk
        )

    return (
        unique_chunks,
        duplicate_count,
    )


def main():

    documents = (
        load_documents()
    )

    print(
        f"Normalize belge sayısı: "
        f"{len(documents)}"
    )

    statute_chunks, statute_laws = (
        load_statute_chunks()
    )

    print(
        f"Hazır statute chunk: "
        f"{len(statute_chunks)}"
    )

    print(
        f"Statute kanun sayısı: "
        f"{len(statute_laws)}"
    )

    all_chunks: list[Chunk] = []

    all_chunks.extend(
        statute_chunks
    )

    skipped_duplicate_pdfs = 0

    raw_document_count = 0

    regulation_document_count = 0

    for document in documents:

        if should_skip_regulation_pdf(
            document,
            statute_laws,
        ):

            skipped_duplicate_pdfs += 1

            print(
                "[ATLANDI - statute CSV'de var]",
                document.get(
                    "title"
                ),
            )

            continue

        source_type = (
            document.get(
                "source_type"
            )
        )

        if source_type == "raw":
            raw_document_count += 1

        elif source_type == "mevzuat":
            regulation_document_count += 1

        chunks = chunk_document(
            document
        )

        all_chunks.extend(
            chunks
        )

    unique_chunks, duplicate_count = (
        deduplicate(
            all_chunks
        )
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        for chunk in unique_chunks:

            file.write(
                json.dumps(
                    chunk.model_dump(),
                    ensure_ascii=False,
                )
                + "\n"
            )

    legal_count = sum(
        1
        for chunk in unique_chunks
        if chunk.corpus_type
        == "legal_knowledge"
    )

    document_count = sum(
        1
        for chunk in unique_chunks
        if chunk.corpus_type
        == "document_knowledge"
    )

    official_writing_count = sum(
        1
        for chunk in unique_chunks
        if chunk.metadata.get(
            "rag_domain"
        )
        == "official_writing"
    )

    print()
    print(
        "================================"
    )

    print(
        "CHUNKING TAMAMLANDI"
    )

    print(
        "================================"
    )

    print(
        f"İşlenen raw belge: "
        f"{raw_document_count}"
    )

    print(
        f"İşlenen mevzuat belge: "
        f"{regulation_document_count}"
    )

    print(
        f"Atlanan duplicate kanun PDF: "
        f"{skipped_duplicate_pdfs}"
    )

    print(
        f"Duplicate chunk: "
        f"{duplicate_count}"
    )

    print(
        f"Legal knowledge: "
        f"{legal_count}"
    )

    print(
        f"Document knowledge: "
        f"{document_count}"
    )

    print(
        f"Resmî yazışma chunk: "
        f"{official_writing_count}"
    )

    print(
        f"TOPLAM: "
        f"{len(unique_chunks)}"
    )

    print(
        f"Çıktı: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()