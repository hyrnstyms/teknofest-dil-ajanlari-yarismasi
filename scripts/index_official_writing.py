"""
scripts/index_official_writing.py
──────────────────────────────────────────────────────────────────────────────
A1 (P0) — official_writing RAG Alanını Doldurma

Girdi:
  - data/regulations/resmi_yazisma_yonetmeligi_2646.pdf (resmî, metin tabanlı PDF)
  - data/regulations/resmiyazısmakılavuzu.pdf        (düzyazı, fallback chunk)

Hedef:
  - Mevcut LEGAL_COLLECTION'a ekleme yapar (MEVCUT NOKTAları SİLMEZ)
  - rag_domain="official_writing" etiketiyle yeni noktalar upsert eder
  - Point ID: uuid5 deterministik → tekrar çalıştırmak güvenli

PDF Yapı Analizi (önceden doğrulandı):
  - yönetmelik PDF: görüntü tabanlı → PaddleOCR ile metin çıkarılır
  - kılavuz PDF: metin mevcut ama madde yapısı yok (4 madde/127k char)
                 → 1500-char sabit dilim fallback kullanılır

Çalıştırma:
    # Dry-run (Qdrant'a yazmaz, chunk'ları raporlar):
    python scripts/index_official_writing.py --dry-run

    # Gerçek indexleme:
    python scripts/index_official_writing.py

    # Yalnızca bir dosya:
    python scripts/index_official_writing.py --only kilavuz
    python scripts/index_official_writing.py --only yonetmelik
"""

import sys
import re
import argparse
from pathlib import Path

sys.path.insert(0, ".")

import pymupdf

from backend.app.rag.point_ids import deterministic_point_id

# ─── Kaynak Tanımları ────────────────────────────────────────────────────────

SOURCES = [
    {
        "file": "data/regulations/resmi_yazisma_yonetmeligi_2646.pdf",
        "source_id": "resmi_yazisma_yonetmeligi",
        "title": "Resmî Yazışmalarda Uygulanacak Usul ve Esaslar Hakkında Yönetmelik",
        "law_number": "resmi_yazisma_yonetmeligi",
        "rag_domain": "official_writing",
        "key": "yonetmelik",
        "source_type": "regulation",
        "url": "https://www.mevzuat.gov.tr/MevzuatMetin/21.5.2646.pdf",
        "direct_text": True,
        "ocr_required": False,
    },
    {
        "file": "data/regulations/resmiyazısmakılavuzu.pdf",
        "source_id": "resmi_yazisma_kilavuzu",
        "title": "Resmî Yazışmalar Kılavuzu",
        "law_number": "resmi_yazisma_kilavuzu",
        "rag_domain": "official_writing",
        "key": "kilavuz",
        "source_type": "guide",
        "url": None,
        "ocr_required": False,  # Metin tabanlı PDF
        "force_fallback": True, # 126k karakter, 4 madde = yetersiz; tüm metin 1500-char chunk
    },
]

CHUNK_SIZE = 1500       # Fallback chunk boyutu (index_test_pdfs.py ile aynı)
MADDE_CHUNK_MAX = 2000  # Madde bazlı chunk max boyutu (index_test_pdfs.py ile aynı)

MADDE_PATTERN = re.compile(
    r"(MADDE\s+(\d+)\s*[.\-\u2012\u2013\u2014]|Madde\s+(\d+)\s*[.\-\u2012\u2013\u2014]|Madde\s+(\d+)\s*$)",
    re.MULTILINE,
)


# ─── Metin Çıkarma ───────────────────────────────────────────────────────────

def extract_text_with_ocr(pdf_path: str) -> str:
    """PDF text layer + PaddleOCR fallback via the production OCR service."""
    from backend.app.ocr.ocr_service import OCRService

    result = OCRService().extract_text_from_pdf(pdf_path)
    if not result or not result.strip():
        raise RuntimeError("OCRService PDF'den metin çıkaramadı.")

    return result



def extract_text_direct(pdf_path: str) -> str:
    """PyMuPDF ile doğrudan metin çıkarır."""
    doc = pymupdf.open(pdf_path)
    full_text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return full_text


# ─── Chunk'lama ──────────────────────────────────────────────────────────────

def chunk_by_article(full_text: str, force_fallback: bool = False) -> list[dict]:
    """
    index_test_pdfs.py'deki extract_articles_from_pdf() mantığını birebir taklit eder.
    force_fallback=True olduğunda madde regex atlanır, tüm metin 1500-char
    dilimlere bölünür (15k sınırı YOKTUR — tüm belge işlenir).
    """
    if not force_fallback:
        matches = list(MADDE_PATTERN.finditer(full_text))

        articles = []
        for i, m in enumerate(matches):
            groups = m.groups()
            madde_no = next(g for g in groups[1:] if g is not None)

            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
            text = full_text[start:end].strip()

            if len(text) < 20:
                continue
            if len(text) > MADDE_CHUNK_MAX:
                text = text[:MADDE_CHUNK_MAX]

            articles.append({"madde_no": madde_no, "text": text})

        if articles:
            return articles

    # Fallback: tüm metni 1500-char dilimlere böl (sınır yok)
    articles = []
    for j, start in enumerate(range(0, len(full_text), CHUNK_SIZE)):
        ch = full_text[start:start + CHUNK_SIZE].strip()
        if ch:
            articles.append({"madde_no": f"CHUNK_{j + 1}", "text": ch})
    return articles


# ─── Point ID ────────────────────────────────────────────────────────────────

# ─── Ana Fonksiyon ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="official_writing belgelerini Qdrant'a indexler."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Qdrant'a yazmadan chunk'ları raporlar.",
    )
    parser.add_argument(
        "--only",
        choices=["kilavuz", "yonetmelik"],
        default=None,
        help="Yalnızca belirtilen kaynağı işler.",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("=" * 60)
        print("DRY-RUN modu: Qdrant'a veri yazılmayacak.")
        print("=" * 60)

    # Qdrant ve Embedding — dry-run'da başlatılmaz
    store = None
    embedding_service = None
    legal_collection = None

    if not args.dry_run:
        from backend.app.rag.embedding_service import EmbeddingService
        from backend.app.rag.qdrant_store import QdrantStore, LEGAL_COLLECTION

        embedding_service = EmbeddingService()
        store = QdrantStore()
        store.ensure_all_collections()
        legal_collection = LEGAL_COLLECTION

        # Başlangıç nokta sayısı (mevcut noktalar korunuyor mu kanıtı)
        try:
            cnt_before = store.client.count(collection_name=legal_collection)
            print(f"\n[KONTROL] Başlangıç nokta sayısı: {cnt_before.count}")
        except Exception as e:
            print(f"[UYARI] Nokta sayısı alınamadı: {e}")

    total_indexed = 0
    total_skipped = 0

    for src in SOURCES:
        if args.only and src["key"] != args.only:
            continue

        print(f"\n{'=' * 60}")
        print(f"Kaynak : {src['title']}")
        print(f"Dosya  : {src['file']}")
        print(f"Domain : {src['rag_domain']}")

        file_path = Path(src["file"])
        if not file_path.exists():
            print(f"HATA: Dosya bulunamadı: {file_path}")
            continue

        # Metin çıkar
        if src["ocr_required"] and not src.get("direct_text", False):
            print("  OCR gerekiyor (taranmış PDF)...")
            full_text = extract_text_with_ocr(str(file_path))
        else:
            print("  Doğrudan metin çıkarılıyor...")
            full_text = extract_text_direct(str(file_path))

        if not full_text or not full_text.strip():
            print("  Metin çıkarılamadı, atlanıyor.")
            continue

        print(f"  Çıkarılan metin: {len(full_text)} karakter")

        # Chunk'la
        force_fb = src.get("force_fallback", False)
        articles = chunk_by_article(full_text, force_fallback=force_fb)
        print(f"  Chunk sayısı   : {len(articles)} ({'force-fallback' if force_fb else 'madde/fallback'})")

        if not articles:
            print("  Chunk üretilemedi, atlanıyor.")
            continue

        articles = [
            {**article, "chunk_index": index}
            for index, article in enumerate(articles)
        ]

        # ID'ler
        ids = [
            deterministic_point_id(
                src["source_id"],
                article["madde_no"],
                article["chunk_index"],
                article["text"],
            )
            for article in articles
        ]

        if args.dry_run:
            # Dry-run: sadece chunk özetini göster
            print(f"\n  -- DRY-RUN chunk özeti --")
            for i, (a, pid) in enumerate(zip(articles[:5], ids[:5])):
                preview = a["text"][:80].replace("\n", " ")
                print(f"    [{i+1}] madde_no={a['madde_no']:10s}  id={pid[:12]}...  metin='{preview}...'")
            if len(articles) > 5:
                print(f"    ... ve {len(articles) - 5} chunk daha")
            total_indexed += len(articles)
            continue

        # Mevcut ID kontrolü (tekrar indexlemeyi önle)
        existing = set()
        try:
            pts = store.client.retrieve(
                collection_name=legal_collection,
                ids=ids,
                with_payload=False,
                with_vectors=False,
            )
            existing = {str(p.id) for p in pts}
        except Exception:
            pass

        new_articles = [a for a, pid in zip(articles, ids) if pid not in existing]
        new_ids = [pid for pid in ids if pid not in existing]
        skipped = len(ids) - len(new_ids)

        if skipped:
            print(f"  Zaten indexlenmiş: {skipped} chunk atlandı.")
            total_skipped += skipped

        if not new_articles:
            print("  Tümü zaten mevcut, upsert yapılmadı.")
            continue

        print(f"  Yeni indexlenecek: {len(new_articles)} chunk")

        # Embed
        new_texts = [a["text"] for a in new_articles]
        vectors = embedding_service.encode_documents(new_texts, batch_size=8)

        # Payload (index_test_pdfs.py şeması birebir)
        payloads = [
            {
                "chunk_id": pid,
                "document_id": src["source_id"],
                "source": src["source_id"],
                "source_type": src["source_type"],
                "title": src["title"],
                "law_number": src["law_number"],
                "rag_domain": src["rag_domain"],
                "madde_no": a["madde_no"],
                "section_id": a["madde_no"],
                "chunk_index": a["chunk_index"],
                "text": a["text"],
                "trusted_source": True,
                "url": src.get("url"),
                "corpus_type": "legal_knowledge",
                "metadata": {
                    "rag_eligible": True,
                    "document_id": src["source_id"],
                    "source_type": src["source_type"],
                    "law_number": src["law_number"],
                    "rag_domain": src["rag_domain"],
                    "madde_no": a["madde_no"],
                    "section_id": a["madde_no"],
                    "chunk_index": a["chunk_index"],
                    "source": src["source_id"],
                    "title": src["title"],
                    "trusted_source": True,
                    "url": src.get("url"),
                },
            }
            for pid, a in zip(new_ids, new_articles)
        ]

        # Upsert
        store.upsert_batch(
            collection_name=legal_collection,
            ids=new_ids,
            vectors=vectors,
            payloads=payloads,
        )

        print(f"  OK: {len(new_articles)} chunk indexlendi.")
        total_indexed += len(new_articles)

    # Final rapor
    print(f"\n{'=' * 60}")
    if args.dry_run:
        print(f"DRY-RUN TAMAMLANDI")
        print(f"Toplam işlenecek chunk (gerçek çalıştırmada): {total_indexed}")
    else:
        print(f"INDEXLEME TAMAMLANDI")
        print(f"Toplam yeni indexlenen  : {total_indexed}")
        print(f"Toplam atlanan (mevcut) : {total_skipped}")

        # Final nokta sayısı (mevcut noktalar silinmedi kanıtı)
        try:
            cnt_after = store.client.count(collection_name=legal_collection)
            print(f"\n[KONTROL] Final nokta sayısı  : {cnt_after.count}")
            print(f"[KONTROL] Fark (yeni eklenen) : {cnt_after.count - cnt_before.count}")
        except Exception as e:
            print(f"[UYARI] Final nokta sayısı alınamadı: {e}")


if __name__ == "__main__":
    main()
