# KAMUAI – Data Dizini

Bu dizin KAMUAI sisteminin veri bileşenlerini içerir.

---

## data/knowledge/

**Production Legal RAG knowledge base.**

| Dosya | İçerik | Kullanım |
|---|---|---|
| `statute_chunks.csv` | 6350 satır, pre-chunked mevzuat | `chunk_documents.py` → Qdrant |

> **NEVER RE-CHUNK.** Bu dosya zaten madde düzeyinde bölünmüş (pre-chunked) hâlde gelir.
> Bir sonraki adım: `scripts/chunk_documents.py` → `scripts/index_qdrant.py`

---

## data/regulations/

**Resmî kanun ve yönetmelik PDF'leri (orijinal kaynak / provenance).**

Buradaki PDF'ler statute_chunks.csv'nin orijinal kaynaklarıdır.
Provenance ve başvuru amacıyla korunmaktadır.

RAG için canonical kaynak `data/knowledge/statute_chunks.csv`'dir.
Aynı kanun hem CSV'de hem PDF'de varsa chunk pipeline PDF'i atlar.

Başlıca belgeler:
- `3071kanun.pdf` — Dilekçe Hakkının Kullanılmasına Dair Kanun
- `4982kanun.pdf` — Bilgi Edinme Hakkı Kanunu
- `5442_il_idaresi_kanunu.pdf` — İl İdaresi Kanunu
- `resmi_yazisma_yonetmeligi.pdf` — Resmî Yazışma Yönetmeliği
- `resmiyazısmakılavuzu.pdf` — Resmî Yazışma Kılavuzu
- *(diğerleri: 657, 193, 213, 2547, 2577, 4734, 4857, 5018, 5216, 5393, 5490, 5510, 6331, 6502, 6698, resmigazete)*

---

## data/institutions/

**Kurum Profil Paketleri (Institution Packs).**

Her kurum, kendi alt klasöründe YAML profil dosyası içerir.

```
data/institutions/
└── kaymakamlik/
    └── kurum_profili_kaymakamlik.yaml   ← Aktif demo kurumu
```

Bu YAML dosyası:
- Routing Agent için **tek source-of-truth** olarak kullanılır.
- Quality Agent birim doğrulama için bu dosyayı okur.
- `unit_registry.json` KALDIRILDI.

---

## data/evaluation/

**Benchmark ve değerlendirme verileri. Production RAG'e HİÇBİR ZAMAN dahil edilmez.**

```
data/evaluation/
├── legal/
│   ├── rag_test_seti.jsonl        (45 soru — LegalAgent RAG kalitesi)
│   └── qa_benchmark_gold.csv      (290 soru-cevap — RAG benchmark)
├── synthetic/
│   └── evraklar.jsonl             (161 kayıt — ExtractionAgent / RoutingAgent)
├── writing/
│   └── gold_taslaklar.jsonl       (52 kayıt — WritingAgent taslak kalitesi)
└── ocr/
    ├── temiz/                     (24 PNG — kolay OCR)
    ├── orta_kalite/               (24 PNG — orta güçlük OCR)
    └── zor/                       (24 PNG — zor OCR)
```

Değerlendirme scriptleri: `scripts/evaluation/`

---

## Silinmiş Yapılar

| Eski Yol | Durum | Gerekçe |
|---|---|---|
| `data/raw/` | SİLİNDİ | Tüm içerik ya `data/knowledge/`'a ya `data/evaluation/legal/`'e taşındı veya silindi |
| `data/routing/unit_registry.json` | SİLİNDİ | Kurum profili YAML single source-of-truth oldu |
| `data/processed/` | GİTİGNORE | Generated cache; `chunk_documents.py` çalıştırılınca yeniden üretilir |
| `data/synthetic/` | SİLİNDİ | Sentetik üretim pipeline'ı kaldırıldı |
| `train-00000-of-00001.parquet` | SİLİNDİ | Üçüncü taraf HuggingFace seti, production RAG için uygun değil |
