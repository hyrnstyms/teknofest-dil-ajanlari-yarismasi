"""
scripts/index_kalan_kanunlar.py
──────────────────────────────────────────────────────────────────────────────
A2 (P1) — Kurumsal Mevzuatı Qdrant'a İndeksleme

index_test_pdfs.py'nin işlemediği data/regulations/ altındaki kanun ve yönetmelik PDF'leri
rag_domain="legal" etiketiyle MEVCUT koleksiyona EKLER.
Mevcut noktaları SİLMEZ, sadece yeni ekler. Upsert deterministik (uuid5).

index_test_pdfs.py'nin ZATen işledikleri (bu scriptte YOKTUR):
  - 3071kanun.pdf   (Dilekçe Hakkı)
  - 4982kanun.pdf   (Bilgi Edinme)
  - 5442_il_idaresi_kanunu.pdf (İl İdaresi)

index_official_writing.py'nin işledikleri (bu scriptte YOKTUR):
  - resmi_yazisma_yonetmeligi.pdf
  - resmiyazısmakılavuzu.pdf

Çalıştırma:
    # Dry-run (Qdrant'a yazmaz, chunk sayılarını raporlar):
    python scripts/index_kalan_kanunlar.py --dry-run

    # Gerçek indexleme:
    python scripts/index_kalan_kanunlar.py

    # Tek bir dosya:
    python scripts/index_kalan_kanunlar.py --only 657
"""

import sys
import re
import argparse
from pathlib import Path

sys.path.insert(0, ".")

import pymupdf

from backend.app.rag.point_ids import deterministic_point_id

# ─── Kaynak Listesi ──────────────────────────────────────────────────────────
# index_test_pdfs.py'de işlenenler ÇIKARILDI, çakışma yok.

SOURCES = [
    {
        "file": "data/regulations/3194_imar_kanunu.pdf",
        "source_id": "3194",
        "title": "\u0130mar Kanunu (3194)",
        "law_number": "3194",
        "rag_domain": "legal",
        "source_type": "law",
        "url": "https://www.mevzuat.gov.tr/MevzuatMetin/1.5.3194.pdf",
    },
    {
        "file": "data/regulations/3294_sosyal_yardimlasma_kanunu.pdf",
        "source_id": "3294",
        "title": "Sosyal Yard\u0131mla\u015fma ve Dayan\u0131\u015fmay\u0131 Te\u015fvik Kanunu (3294)",
        "law_number": "3294",
        "rag_domain": "legal",
        "source_type": "law",
        "url": "https://www.mevzuat.gov.tr/MevzuatMetin/1.5.3294.pdf",
    },
    {
        "file": "data/regulations/valilik_kaymakamlik_birimleri_yonetmeligi.pdf",
        "source_id": "valilik_kaymakamlik_birimleri_yonetmeligi",
        "title": "Valilik ve Kaymakaml\u0131k Birimleri Te\u015fkilat, G\u00f6rev ve \u00c7al\u0131\u015fma Y\u00f6netmeli\u011fi",
        "law_number": "valilik_kaymakamlik_birimleri_yonetmeligi",
        "rag_domain": "legal",
        "source_type": "regulation",
        "url": "https://icisleri.gov.tr/kurumlar/icisleri.gov.tr/IcSite/bilgiislem/egitimler/eicisleri_proje/proje_mevzuatlari/Vk_yonetmelik_eotoban.pdf",
    },
    {
        "file": "data/regulations/isyeri_acma_calisma_ruhsatlari_yonetmeligi.pdf",
        "source_id": "isyeri_acma_calisma_ruhsatlari_yonetmeligi",
        "title": "\u0130\u015fyeri A\u00e7ma ve \u00c7al\u0131\u015fma Ruhsatlar\u0131na \u0130li\u015fkin Y\u00f6netmelik",
        "law_number": "isyeri_acma_calisma_ruhsatlari_yonetmeligi",
        "rag_domain": "legal",
        "source_type": "regulation",
        "url": "https://www.mevzuat.gov.tr/MevzuatMetin/21.5.20059207.pdf",
    },
    {
        "file": "data/regulations/193kanun.pdf",
        "source_id": "193",
        "title": "Teşkilat Kanunu (193)",
        "law_number": "193",
        "rag_domain": "legal",
    },
    {
        "file": "data/regulations/213kanun.pdf",
        "source_id": "213",
        "title": "Vergi Usul Kanunu (213)",
        "law_number": "213",
        "rag_domain": "legal",
    },
    {
        "file": "data/regulations/2547kanun.pdf",
        "source_id": "2547",
        "title": "Yükseköğretim Kanunu (2547)",
        "law_number": "2547",
        "rag_domain": "legal",
    },
    {
        "file": "data/regulations/2577kanun.pdf",
        "source_id": "2577",
        "title": "İdari Yargılama Usulü Kanunu (2577)",
        "law_number": "2577",
        "rag_domain": "legal",
    },
    {
        "file": "data/regulations/4734kanun.pdf",
        "source_id": "4734",
        "title": "Kamu İhale Kanunu (4734)",
        "law_number": "4734",
        "rag_domain": "legal",
    },
    {
        "file": "data/regulations/4857kanun.pdf",
        "source_id": "4857",
        "title": "İş Kanunu (4857)",
        "law_number": "4857",
        "rag_domain": "legal",
    },
    {
        "file": "data/regulations/5018kanun.pdf",
        "source_id": "5018",
        "title": "Kamu Malî Yönetimi ve Kontrol Kanunu (5018)",
        "law_number": "5018",
        "rag_domain": "legal",
    },
    {
        "file": "data/regulations/5216kanun.pdf",
        "source_id": "5216",
        "title": "Büyükşehir Belediyesi Kanunu (5216)",
        "law_number": "5216",
        "rag_domain": "legal",
    },
    {
        "file": "data/regulations/5393kanun.pdf",
        "source_id": "5393",
        "title": "Belediye Kanunu (5393)",
        "law_number": "5393",
        "rag_domain": "legal",
    },
    {
        "file": "data/regulations/5490kanun.pdf",
        "source_id": "5490",
        "title": "Nüfus Hizmetleri Kanunu (5490)",
        "law_number": "5490",
        "rag_domain": "legal",
    },
    {
        "file": "data/regulations/5510kanun.pdf",
        "source_id": "5510",
        "title": "Sosyal Sigortalar ve Genel Sağlık Sigortası Kanunu (5510)",
        "law_number": "5510",
        "rag_domain": "legal",
    },
    {
        "file": "data/regulations/6331kanun.pdf",
        "source_id": "6331",
        "title": "İş Sağlığı ve Güvenliği Kanunu (6331)",
        "law_number": "6331",
        "rag_domain": "legal",
    },
    {
        "file": "data/regulations/6502kanun.pdf",
        "source_id": "6502",
        "title": "Tüketicinin Korunması Hakkında Kanun (6502)",
        "law_number": "6502",
        "rag_domain": "legal",
    },
    {
        "file": "data/regulations/657kanun.pdf",
        "source_id": "657",
        "title": "Devlet Memurları Kanunu (657)",
        "law_number": "657",
        "rag_domain": "legal",
    },
    {
        "file": "data/regulations/6698kanun.pdf",
        "source_id": "6698",
        "title": "Kişisel Verilerin Korunması Kanunu (6698)",
        "law_number": "6698",
        "rag_domain": "legal",
    },
    {
        "file": "data/regulations/resmigazete.pdf",
        "source_id": "resmigazete",
        "title": "Resmî Gazete (referans)",
        "law_number": "resmigazete",
        "rag_domain": "legal",
    },
]

# ─── Chunk'lama Parametreleri (index_test_pdfs.py ile aynı) ─────────────────

CHUNK_SIZE = 1500
MADDE_CHUNK_MAX = 2000

MADDE_PATTERN = re.compile(
    r"(MADDE\s+(\d+)\s*[.\-\u2012\u2013\u2014]|Madde\s+(\d+)\s*[.\-\u2012\u2013\u2014]|Madde\s+(\d+)\s*$)",
    re.MULTILINE,
)


# ─── Metin ve Chunk Fonksiyonları (index_test_pdfs.py birebir kopyası) ───────

def extract_articles_from_pdf(pdf_path: str) -> list[dict]:
    """index_test_pdfs.py::extract_articles_from_pdf() birebir kopyası."""
    doc = pymupdf.open(pdf_path)
    full_text = "\n".join(page.get_text() for page in doc)
    doc.close()

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

    if not articles:
        # Fallback (index_test_pdfs.py ile aynı mantık ama sınırsız)
        chunks = [full_text[i:i + CHUNK_SIZE] for i in range(0, len(full_text), CHUNK_SIZE)]
        for j, ch in enumerate(chunks):
            if ch.strip():
                articles.append({"madde_no": f"PART_{j + 1}", "text": ch.strip()})

    return articles


# ─── Ana Fonksiyon ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Kurumsal kanun ve yönetmelikleri Qdrant'a indexler."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Qdrant'a yazmadan chunk sayılarını raporlar.",
    )
    parser.add_argument(
        "--only",
        default=None,
        help="Yalnızca belirtilen law_number'ı işler (örn. --only 657).",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("=" * 60)
        print("DRY-RUN modu: Qdrant'a veri yazılmayacak.")
        print("=" * 60)

    store = None
    embedding_service = None
    legal_collection = None
    cnt_before = None

    if not args.dry_run:
        from backend.app.rag.embedding_service import EmbeddingService
        from backend.app.rag.qdrant_store import QdrantStore, LEGAL_COLLECTION

        embedding_service = EmbeddingService()
        store = QdrantStore()
        store.ensure_all_collections()
        legal_collection = LEGAL_COLLECTION

        try:
            cnt_before = store.client.count(collection_name=legal_collection)
            print(f"\n[KONTROL] Başlangıç nokta sayısı: {cnt_before.count}")
        except Exception as e:
            print(f"[UYARI] Nokta sayısı alınamadı: {e}")

    total_indexed = 0
    total_skipped = 0
    per_source = []

    for src in SOURCES:
        if args.only and src["law_number"] != args.only:
            continue

        print(f"\n{'=' * 60}")
        print(f"Kaynak  : {src['title']}")
        print(f"Dosya   : {src['file']}")

        file_path = Path(src["file"])
        if not file_path.exists():
            print(f"  HATA: Dosya bulunamadı: {file_path} — atlanıyor.")
            continue

        try:
            articles = extract_articles_from_pdf(str(file_path))
        except Exception as e:
            print(f"  HATA: PDF okunamadı: {e} — atlanıyor.")
            continue

        articles = [
            {**article, "chunk_index": index}
            for index, article in enumerate(articles)
        ]
        ids = [
            deterministic_point_id(
                src["source_id"],
                article["madde_no"],
                article["chunk_index"],
                article["text"],
            )
            for article in articles
        ]
        print(f"  Chunk sayısı: {len(articles)}")

        if args.dry_run:
            preview = articles[0]["text"][:80].replace("\n", " ").replace("\u2012", "-") if articles else ""
            print(f"  İlk chunk   : '{preview}...'")
            per_source.append((src["law_number"], len(articles)))
            total_indexed += len(articles)
            continue

        # Mevcut ID kontrolü
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
            print(f"  Zaten mevcut: {skipped} chunk atlandı.")
            total_skipped += skipped

        if not new_articles:
            print(f"  Tümü zaten indexlenmiş.")
            per_source.append((src["law_number"], 0))
            continue

        print(f"  Yeni indexlenecek: {len(new_articles)} chunk")

        new_texts = [a["text"] for a in new_articles]
        vectors = embedding_service.encode_documents(new_texts, batch_size=8)

        payloads = [
            {
                "chunk_id": pid,
                "document_id": src["source_id"],
                "source": src["source_id"],
                "source_type": src.get("source_type", "law"),
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
                    "source_type": src.get("source_type", "law"),
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

        store.upsert_batch(
            collection_name=legal_collection,
            ids=new_ids,
            vectors=vectors,
            payloads=payloads,
        )

        print(f"  OK: {len(new_articles)} chunk indexlendi.")
        total_indexed += len(new_articles)
        per_source.append((src["law_number"], len(new_articles)))

        # Ara nokta sayısı
        try:
            cnt_mid = store.client.count(collection_name=legal_collection)
            print(f"  [KONTROL] Anlık nokta sayısı: {cnt_mid.count}")
        except Exception:
            pass

    # Final rapor
    print(f"\n{'=' * 60}")
    if args.dry_run:
        print("DRY-RUN TAMAMLANDI")
        print(f"{'Kaynak':<12} {'Chunk':>6}")
        print("-" * 20)
        for law, cnt in per_source:
            print(f"{law:<12} {cnt:>6}")
        print(f"{'TOPLAM':<12} {total_indexed:>6}")
    else:
        print("INDEXLEME TAMAMLANDI")
        print(f"Toplam yeni indexlenen  : {total_indexed}")
        print(f"Toplam atlanan (mevcut) : {total_skipped}")
        try:
            cnt_after = store.client.count(collection_name=legal_collection)
            print(f"\n[KONTROL] Başlangıç nokta sayısı : {cnt_before.count if cnt_before else '?'}")
            print(f"[KONTROL] Final nokta sayısı     : {cnt_after.count}")
            print(f"[KONTROL] Fark (yeni eklenen)    : {cnt_after.count - (cnt_before.count if cnt_before else 0)}")
        except Exception as e:
            print(f"[UYARI] Final nokta sayısı alınamadı: {e}")


if __name__ == "__main__":
    main()
