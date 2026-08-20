"""
scripts/evaluation/index_test_pdfs.py
──────────────────────────────────────
RAG test seti için gereken 4 PDF ve 1 Markdown kaynağını Qdrant'a indexler.
Test seti kaynakları:
- 3071_dilekce_hakki_kanunu.pdf  (data/regulations/3071kanun.pdf)
- 4982_bilgi_edinme_kanunu.pdf   (data/regulations/4982kanun.pdf)  
- 5442_il_idaresi_kanunu.pdf     (data/regulations/5442_il_idaresi_kanunu.pdf)
- format_kurallari_checklist.md  (docs/format_kurallari_checklist.md) -> resmi_yazisma_yonetmeligi yerine
- resmi_yazisma_kilavuzu.pdf     (data/regulations/resmiyazısmakılavuzu.pdf)

Calıştırma:
    set PYTHONPATH=.
    .venv\Scripts\python scripts/evaluation/index_test_pdfs.py
"""
import sys
import uuid
import re

sys.path.insert(0, ".")

import fitz  # pymupdf

from backend.app.rag.embedding_service import EmbeddingService
from backend.app.rag.qdrant_store import QdrantStore, LEGAL_COLLECTION

# ─── Kaynak Mapping ──────────────────────────────────────────────────────────

SOURCES = [
    {
        "file": "data/regulations/3071kanun.pdf",
        "source_id": "3071",
        "title": "Dilekçe Hakkının Kullanılmasına Dair Kanun",
        "law_number": "3071",
        "rag_domain": "legal",
        "type": "pdf"
    },
    {
        "file": "data/regulations/4982kanun.pdf",
        "source_id": "4982",
        "title": "Bilgi Edinme Hakkı Kanunu",
        "law_number": "4982",
        "rag_domain": "legal",
        "type": "pdf"
    },
    {
        "file": "data/regulations/5442_il_idaresi_kanunu.pdf",
        "source_id": "5442",
        "title": "İl İdaresi Kanunu",
        "law_number": "5442",
        "rag_domain": "legal",
        "type": "pdf"
    },
    {
        "file": "docs/format_kurallari_checklist.md",
        "source_id": "resmi_yazisma_yonetmeligi (checklist uzerinden)",
        "title": "Resmî Yazışmalarda Uygulanacak Usul ve Esaslar Hakkında Yönetmelik (Checklist)",
        "law_number": "resmi_yazisma_yonetmeligi",
        "rag_domain": "official_writing",
        "type": "md"
    },
    {
        "file": "data/regulations/resmiyazısmakılavuzu.pdf",
        "source_id": "resmi_yazisma_kilavuzu",
        "title": "Resmî Yazışma Kılavuzu",
        "law_number": "resmi_yazisma_kilavuzu",
        "rag_domain": "official_writing",
        "type": "pdf"
    },
]

# ─── Yardımcı Fonksiyonlar ───────────────────────────────────────────────────

def extract_articles_from_pdf(pdf_path: str) -> list[dict]:
    """PDF'den madde bazlı metin blokları çıkarır."""
    doc = fitz.open(pdf_path)
    full_text = "\n".join(page.get_text() for page in doc)
    doc.close()

    madde_pattern = re.compile(
        r"(MADDE\s+(\d+)\s*[.\-–—]|Madde\s+(\d+)\s*[.\-–—]|Madde\s+(\d+)\s*$)",
        re.MULTILINE,
    )

    matches = list(madde_pattern.finditer(full_text))

    articles = []
    for i, m in enumerate(matches):
        groups = m.groups()
        madde_no = next(g for g in groups[1:] if g is not None)

        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        text = full_text[start:end].strip()

        if len(text) < 20:
            continue

        if len(text) > 2000:
            text = text[:2000]

        articles.append({
            "madde_no": madde_no,
            "text": text,
        })

    if not articles:
        chunks = [full_text[i:i+1500] for i in range(0, min(len(full_text), 15000), 1500)]
        for j, ch in enumerate(chunks):
            articles.append({
                "madde_no": f"PART_{j+1}",
                "text": ch.strip(),
            })

    return articles


def extract_articles_from_md(md_path: str) -> list[dict]:
    """Markdown'dan H2 (##) başlıklarına göre bölümler çıkarır."""
    with open(md_path, 'r', encoding='utf-8') as f:
        full_text = f.read()

    header_pattern = re.compile(r"^(##\s+.*?)(?=\n##\s+|\Z)", re.MULTILINE | re.DOTALL)
    
    matches = header_pattern.findall(full_text)
    
    articles = []
    for block in matches:
        block = block.strip()
        if not block:
            continue
            
        first_line = block.split('\n')[0]
        
        madde_search = re.search(r"Madde\s+([0-9,\s]+)", first_line, re.IGNORECASE)
        
        if madde_search:
            madde_no = madde_search.group(1).replace(" ", "")
        else:
            num_match = re.match(r"##\s+(\d+)\.", first_line)
            if num_match:
                madde_no = f"Bolum_{num_match.group(1)}"
            else:
                madde_no = "Ek_Bolum"
                
        articles.append({
            "madde_no": madde_no,
            "text": block,
        })
        
    return articles


def point_id(source_id: str, madde_no: str) -> str:
    return str(uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"kamuai_eval:{source_id}:{madde_no}",
    ))


# ─── Ana Indexleme ───────────────────────────────────────────────────────────

def main():
    print(f"Index Test PDFs başlatılıyor ({LEGAL_COLLECTION} hedefleniyor)...")
    embedding_service = EmbeddingService()
    store = QdrantStore()
    store.ensure_all_collections()

    total_indexed = 0

    for src in SOURCES:
        file_path = src["file"]
        print(f"\n{'='*60}")
        print(f"Kaynak: {src['title']}")
        print(f"Dosya: {file_path}")

        try:
            if src["type"] == "pdf":
                articles = extract_articles_from_pdf(file_path)
            else:
                articles = extract_articles_from_md(file_path)
        except Exception as e:
            print(f"HATA: Dosya okuma hatası: {e}")
            continue

        print(f"Bulunan madde/bölüm: {len(articles)}")

        if not articles:
            print("Madde bulunamadı, atlanıyor.")
            continue

        texts = [a["text"] for a in articles]
        ids = [point_id(src["source_id"], a["madde_no"]) for a in articles]

        existing = set()
        try:
            pts = store.client.retrieve(
                collection_name=LEGAL_COLLECTION,
                ids=ids,
                with_payload=False,
                with_vectors=False,
            )
            existing = {str(p.id) for p in pts}
        except Exception:
            pass

        new_texts = [t for t, pid in zip(texts, ids) if pid not in existing]
        new_ids = [pid for pid in ids if pid not in existing]
        new_articles = [a for a, pid in zip(articles, ids) if pid not in existing]

        if not new_texts:
            print(f"Tümü zaten indexlenmiş ({len(ids)} madde), atlaniyor.")
            total_indexed += len(ids)
            continue

        print(f"Yeni indexlenecek: {len(new_texts)} / {len(texts)}")

        vectors = embedding_service.encode_documents(new_texts, batch_size=8)

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

        store.upsert_batch(
            collection_name=LEGAL_COLLECTION,
            ids=new_ids,
            vectors=vectors,
            payloads=payloads,
        )

        print(f"OK: {len(new_texts)} madde indexlendi.")
        total_indexed += len(new_texts)

    print(f"\n{'='*60}")
    print(f"TOPLAM INDEXLENEN: {total_indexed}")
    
    try:
        cnt = store.client.count(collection_name=LEGAL_COLLECTION)
        print(f"Qdrant {LEGAL_COLLECTION} koleksiyon boyutu: {cnt.count}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
