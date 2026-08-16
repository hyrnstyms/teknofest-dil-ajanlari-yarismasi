import hashlib
import re
from pathlib import Path
from typing import Any

from backend.app.rag.schemas import Chunk


ARTICLE_PATTERN = re.compile(
    r"(?im)^\s*(?:MADDE|Madde)\s+\d+\s*[-–—]?"
)


def normalize_text(text: str) -> str:
    """
    Hash/dedup işlemi için metni normalize eder.
    """
    return " ".join(
        text.lower().split()
    ).strip()


def create_content_hash(
    text: str,
) -> str:
    normalized = normalize_text(text)

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


def split_long_text(
    text: str,
    max_chars: int,
    overlap_chars: int,
) -> list[str]:
    """
    Çok uzun tek blokları güvenli şekilde parçalar.
    """
    text = text.strip()

    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = min(
            start + max_chars,
            len(text),
        )

        # Mümkünse kelimenin/cümlenin ortasından kesmemeye çalış.
        if end < len(text):
            candidate = text[start:end]

            possible_breaks = [
                candidate.rfind("\n"),
                candidate.rfind(". "),
                candidate.rfind("; "),
                candidate.rfind(", "),
                candidate.rfind(" "),
            ]

            best_break = max(possible_breaks)

            # Çok erken bir noktaya dönme.
            if best_break > (max_chars * 0.6):
                end = start + best_break + 1

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(
            end - overlap_chars,
            start + 1,
        )

    return chunks


def split_by_paragraphs(
    text: str,
    max_chars: int = 1800,
    overlap_chars: int = 200,
) -> list[str]:
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(
            r"\n\s*\n|\n",
            text,
        )
        if paragraph.strip()
    ]

    if not paragraphs:
        return []

    chunks: list[str] = []
    current: list[str] = []

    for paragraph in paragraphs:
        # Tek paragraf bile çok uzunsa ayrıca parçala.
        if len(paragraph) > max_chars:
            if current:
                chunks.append(
                    "\n".join(current).strip()
                )
                current = []

            long_parts = split_long_text(
                paragraph,
                max_chars=max_chars,
                overlap_chars=overlap_chars,
            )

            chunks.extend(long_parts)
            continue

        candidate = "\n".join(
            current + [paragraph]
        )

        if (
            current
            and len(candidate) > max_chars
        ):
            completed = "\n".join(
                current
            ).strip()

            chunks.append(completed)

            # Bir miktar paragraf overlap'i tut.
            overlap_paragraphs = []
            overlap_size = 0

            for old_paragraph in reversed(current):
                if (
                    overlap_size + len(old_paragraph) > overlap_chars
                    and overlap_paragraphs
                ):
                    break

                overlap_paragraphs.append(
                    old_paragraph
                )
                overlap_size += len(
                    old_paragraph
                )

            current = list(
                reversed(overlap_paragraphs)
            )

        current.append(paragraph)

    if current:
        final_chunk = "\n".join(
            current
        ).strip()

        if final_chunk:
            chunks.append(final_chunk)

    return chunks


def split_legal_articles(
    text: str,
    max_chars: int = 4200,
    overlap_chars: int = 250,
) -> tuple[list[str], str]:
    """
    Kanun metinlerini mümkünse MADDE bazında parçalar.
    """
    matches = list(
        ARTICLE_PATTERN.finditer(text)
    )

    # MADDE yapısı yoksa normal paragraf chunking'e dön.
    if not matches:
        return (
            split_by_paragraphs(
                text,
                max_chars=2200,
                overlap_chars=200,
            ),
            "legal_paragraph",
        )

    chunks: list[str] = []

    # İlk MADDE öncesinde önemli başlık/metin varsa onu da sakla.
    preamble = text[
        : matches[0].start()
    ].strip()

    if len(preamble) >= 80:
        chunks.extend(
            split_by_paragraphs(
                preamble,
                max_chars=2200,
                overlap_chars=150,
            )
        )

    for index, match in enumerate(matches):
        start = match.start()

        if index + 1 < len(matches):
            end = matches[
                index + 1
            ].start()
        else:
            end = len(text)

        article = text[start:end].strip()

        if not article:
            continue

        if len(article) <= max_chars:
            chunks.append(article)

        else:
            # Uzun bir maddeyi alt parçalara böl.
            article_parts = split_by_paragraphs(
                article,
                max_chars=max_chars,
                overlap_chars=overlap_chars,
            )

            # Madde başlığını sonraki alt parçalarda da korumaya çalış.
            article_header = (
                article.splitlines()[0]
                .strip()
            )

            for part_index, part in enumerate(
                article_parts
            ):
                if (
                    part_index > 0
                    and not part.startswith(
                        article_header
                    )
                ):
                    part = (
                        article_header
                        + "\n"
                        + part
                    )

                chunks.append(part)

    return chunks, "legal_article"


def is_toc_like(
    text: str,
) -> bool:
    """
    İçindekiler tablosuna benzeyen chunkları tespit eder.
    """
    if not text:
        return False

    dotted_lines = len(
        re.findall(
            r"\.{5,}",
            text,
        )
    )

    # Çok sayıda noktalı sayfa referansı varsa
    # büyük ihtimalle İçindekiler bölümüdür.
    return dotted_lines >= 4


def is_official_writing_guide(
    document: dict[str, Any],
) -> bool:
    source = str(
        document.get(
            "source",
            "",
        )
    ).lower()

    title = str(
        document.get(
            "title",
            "",
        )
    ).lower()

    filename = str(
        document.get(
            "metadata",
            {},
        ).get(
            "filename",
            "",
        )
    ).lower()

    combined = (
        source
        + " "
        + title
        + " "
        + filename
    )

    return (
        "resmiyaz" in combined
        or "resmi yaz" in combined
        or "resmî yaz" in combined
    )


def extract_law_number(
    document: dict[str, Any],
) -> str | None:
    filename = str(
        document.get(
            "metadata",
            {},
        ).get(
            "filename",
            "",
        )
    )

    if not filename:
        filename = Path(
            str(
                document.get(
                    "source",
                    "",
                )
            )
        ).name

    match = re.match(
        r"^(\d+)\s*kanun",
        filename.lower(),
    )

    if not match:
        return None

    return match.group(1)


def chunk_document(
    document: dict[str, Any],
) -> list[Chunk]:
    text = str(
        document.get(
            "text",
            "",
        )
    ).strip()

    if len(text) < 40:
        return []

    source_type = str(
        document.get(
            "source_type",
            "",
        )
    )

    document_id = str(
        document.get(
            "id",
            "",
        )
    )

    source = str(
        document.get(
            "source",
            "",
        )
    )

    original_metadata = dict(
        document.get(
            "metadata",
            {},
        )
        or {}
    )

    # MEVZUAT
    if source_type == "mevzuat":
        corpus_type = "legal_knowledge"

        # Resmî Yazışma Kılavuzu
        if is_official_writing_guide(
            document
        ):
            texts = split_by_paragraphs(
                text,
                max_chars=2200,
                overlap_chars=250,
            )

            # İçindekiler tablosunu RAG corpus'una alma.
            texts = [
                chunk_text
                for chunk_text in texts
                if not is_toc_like(
                    chunk_text
                )
            ]

            strategy = (
                "official_writing_paragraph"
            )

            rag_domain = (
                "official_writing"
            )

        # Normal kanun / mevzuat
        else:
            texts, strategy = (
                split_legal_articles(
                    text
                )
            )

            rag_domain = "legal"

    # NORMAL BELGE / DİLEKÇE
    else:
        corpus_type = (
            "document_knowledge"
        )

        texts = split_by_paragraphs(
            text,
            max_chars=1800,
            overlap_chars=180,
        )

        strategy = (
            "document_paragraph"
        )

        rag_domain = "document"

    chunks: list[Chunk] = []

    for chunk_index, chunk_text in enumerate(
        texts
    ):
        chunk_text = chunk_text.strip()

        if len(chunk_text) < 40:
            continue

        content_hash = (
            create_content_hash(
                chunk_text
            )
        )

        chunk_id = (
            f"{document_id}_"
            f"{chunk_index:04d}_"
            f"{content_hash[:10]}"
        )

        metadata = dict(
            original_metadata
        )

        metadata.update(
            {
                "title": document.get(
                    "title"
                ),
                "chunk_strategy": (
                    strategy
                ),
                "rag_domain": (
                    rag_domain
                ),
                "synthetic": False,
                "rag_eligible": True,
            }
        )

        chunks.append(
            Chunk(
                id=chunk_id,
                document_id=document_id,
                source=source,
                source_type=source_type,
                corpus_type=corpus_type,
                chunk_index=chunk_index,
                text=chunk_text,
                content_hash=content_hash,
                metadata=metadata,
            )
        )

    return chunks