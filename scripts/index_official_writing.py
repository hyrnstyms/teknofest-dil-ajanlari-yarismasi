"""
scripts/index_official_writing.py
──────────────────────────────────────────────────────────────────────────────
A1 (P0) — official_writing RAG Alanını Doldurma

Girdi:
  - data/regulations/resmi_yazisma_yonetmeligi.pdf  (taranmış/OCR gerekiyor)
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
import uuid
import re
import argparse
from pathlib import Path

sys.path.insert(0, ".")

import pymupdf

# ─── Kaynak Tanımları ────────────────────────────────────────────────────────

SOURCES = [
    {
        "file": "data/regulations/resmi_yazisma_yonetmeligi.pdf",
        "source_id": "resmi_yazisma_yonetmeligi",
        "title": "Resmî Yazışmalarda Uygulanacak Usul ve Esaslar Hakkında Yönetmelik",
        "law_number": "resmi_yazisma_yonetmeligi",
        "rag_domain": "official_writing",
        "key": "yonetmelik",
        "ocr_required": True,   # Taranmış PDF
    },
    {
        "file": "data/regulations/resmiyazısmakılavuzu.pdf",
        "source_id": "resmi_yazisma_kilavuzu",
        "title": "Resmî Yazışmalar Kılavuzu",
        "law_number": "resmi_yazisma_kilavuzu",
        "rag_domain": "official_writing",
        "key": "kilavuz",
        "ocr_required": False,  # Metin tabanlı PDF
        "force_fallback": True, # 126k karakter, 4 madde = yetersiz; tüm metin 1500-char chunk
    },
]

CHUNK_SIZE = 1500       # Fallback chunk boyutu (index_test_pdfs.py ile aynı)
MADDE_CHUNK_MAX = 2000  # Madde bazlı chunk max boyutu (index_test_pdfs.py ile aynı)

MADDE_PATTERN = re.compile(
    r"(MADDE\s+(\d+)\s*[.\-\u2013\u2014]|Madde\s+(\d+)\s*[.\-\u2013\u2014]|Madde\s+(\d+)\s*$)",
    re.MULTILINE,
)


# ─── Metin Çıkarma ───────────────────────────────────────────────────────────

def extract_text_with_ocr(pdf_path: str) -> str:
    """
    Taranmış PDF'den pytesseract + pdf2image ile metin çıkarır.
    (backend/app/ocr/ocr_service.py'ye BAĞIMSIZ — Track C'ye dokunmaz)

    Bağımlılıklar (bu script'e özgü):
        pip install pytesseract pdf2image
        brew install tesseract tesseract-lang poppler
    """
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError as e:
        print(f"  HATA: Eksik bağımlılık: {e}")
        print("  Çözüm: pip install pytesseract pdf2image && brew install poppler")
        return ""

    try:
        print("  PDF sayfalara dönüştürülüyor (dpi=200)...")
        pages = convert_from_path(pdf_path, dpi=200)
        print(f"  Toplam sayfa: {len(pages)}")
    except Exception as e:
        print(f"  HATA: PDF→görüntü dönüştürme başarısız: {e}")
        return ""

    all_text = []
    for i, page in enumerate(pages):
        try:
            text = pytesseract.image_to_string(page, lang="tur")
            if text.strip():
                all_text.append(text.strip())
                if i < 2:  # İlk 2 sayfa için önizleme
                    print(f"  [Sayfa {i+1} önizleme]: {text.strip()[:120].replace(chr(10), ' ')}")
        except Exception as e:
            print(f"  [Sayfa {i+1}] OCR hatası: {e}")

    result = "\n\n".join(all_text)
    if result.strip():
        print(f"  OCR başarılı: {len(result)} karakter çıkarıldı ({len(pages)} sayfa)")
    else:
        print("  OCR sonuç boş.")
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

def point_id(source_id: str, madde_no: str) -> str:
    """index_test_pdfs.py ile aynı uuid5 deterministik ID üretimi."""
    return str(uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"kamuai_eval:{source_id}:{madde_no}",
    ))


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
        if src["ocr_required"]:
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

        # ID'ler
        ids = [point_id(src["source_id"], a["madde_no"]) for a in articles]

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
            total_indexed += len(ids)
            continue

        print(f"  Yeni indexlenecek: {len(new_articles)} chunk")

        # Embed
        new_texts = [a["text"] for a in new_articles]
        vectors = embedding_service.encode_documents(new_texts, batch_size=8)

        # Payload (index_test_pdfs.py şeması birebir)
        payloads = [
            {
                "chunk_id": pid,
                "source": src["source_id"],
                "title": src["title"],
                "law_number": src["law_number"],
                "rag_domain": src["rag_domain"],
                "madde_no": a["madde_no"],
                "text": a["text"],
                "trusted_source": True,
                "corpus_type": "legal_knowledge",
                "metadata": {
                    "rag_eligible": True,
                    "law_number": src["law_number"],
                    "rag_domain": src["rag_domain"],
                    "madde_no": a["madde_no"],
                    "source": src["source_id"],
                    "title": src["title"],
                    "trusted_source": True,
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
