# EVRAG - Proje Durum Raporu

**Tarih:** 2026-08-27
**Branch:** main (3773a66)
**Backend Testleri:** 542 gecti / 1 atlandı (OCR/Qdrant haric)
**Frontend Testleri:** 58/58 gecti
**Amac:** Read-only envanter + yol haritası

---

## BOLUM A - SARTNAME KARSILASTIRMASI

| # | Madde | Durum | Kanit |
|---|-------|-------|-------|
| 1 | OCR ile belge okuma | TAMAM | backend/app/ocr/, document_loader.py; PaddleOCR + pytesseract |
| 2 | Evrak siniflandirma (document_type) | TAMAM | document_agent.py; document_type, document_subtype, process_intent cikariliyor |
| 3 | Bilgi cikarma (extraction) | TAMAM | extraction_agent.py; ExtractionAgent.extract(), fields + confidence |
| 4 | Mevzuat onerisi (legal_agent + Qdrant) | TAMAM | legal_agent.py; Qdrant regulations koleksiyonu + BGE-M3 |
| 5 | Eksik bilgi tespiti | TAMAM | missing_field_agent.py; MissingFieldAgent.detect() |
| 6 | Ozet uretimi | TAMAM | summary_agent.py; structured_summary + needs_human_review bayragi |
| 7a | Dogru birime yonlendirme - ONERI | TAMAM | routing_agent.py; skor tabanli, Top-3, score_breakdown |
| 7b | Dogru birime yonlendirme - GERCEK TESLIMAT | KISMI | cases/engine.py Case Engine var; ROUTE_CASE aksiyonuna insan onayi gerekiyor. Backend eksiksiz, frontend onay ekrani Person 3'ten merge edildi. |
| 8 | Resmi yazi taslagi uretimi | TAMAM | writing_agent.py; ust_yazi, cevap_yazisi, eksik_bilgi_talebi turleri |
| 9 | Format/bicim dogrulama | TAMAM | official_writing/format_validator.py; QualityAgent L231-236 cagiriyor |
| 10 | Eksik bilgi talep mektubu uretimi | TAMAM | writing_agent.py ALLOWED_DRAFT_TYPES icinde eksik_bilgi_talebi mevcut |
| 11 | Acik kaynak paylasim | TAMAM | LICENSE (MIT) kok dizinde; README.md; GitHub repo public |

**A Ozeti:** TAMAM: 10 | KISMI: 1 | EKSIK: 0

---

## BOLUM B - OZELLIK ENVANTERI

| # | Ozellik | Durum | Kanit |
|---|---------|-------|-------|
| 1 | EVREN entegrasyonu | TAMAM | evren_client.py; factory.py: document_agent->fast, legal_agent->large; tum ajanlarda create_llm_client |
| 2 | Ollama fallback | TAMAM | ollama_client.py; provider env'den okunuyor, ollama secelebiliyor |
| 3 | Coklu kurum (belediye + kaymakamlik) | KISMI | data/institutions/belediye/ + data/institutions/kaymakamlik/ var; routing_agent.py L10 _DEFAULT_INSTITUTION = "kaymakamlik" hardcoded |
| 4 | Kurum bazli liste filtreleme | TAMAM | GET /api/analyses -> institution_id query param; repository.py L106-113 SQL WHERE filtresi calisiyor |
| 5 | Birim bazli kuyruk (unit_id) | KISMI | routing_agent.py L96 unit_id alani var; dedicated endpoint yok, Case inbox current_department_code ile filtreleniyor |
| 6 | Eksik bilgi talebi taslagi uretimi | TAMAM | writing_agent.py eksik_bilgi_talebi turu; Case Engine REQUEST_CITIZEN_INFO aksiyonu; CitizenTracePage.tsx form |
| 7 | Akilli onceliklendirme (priority_agent) | TAMAM | priority_agent.py; orchestration.py L85, workflow.py L11, document_agent.py L79 workflow'a bagli |
| 8 | Basvuru/dosya zinciri (ilgili_evrak_id) | EKSIK | Codebase'de ilgili_evrak_id veya zincir_id gecen hicbir kayit yok |
| 9 | PII maskeleme | EKSIK | Codebase'de PII/masking fonksiyonu bulunamadi |
| 10 | Audit trail | KISMI | CaseEvent tablosu append-only mevcut; ancak kim/ne/oncesi-sonrasi field-level diff yok |
| 11 | Yonetici paneli | EKSIK | AdminPage.tsx: "Bu panel bekliyor" placeholder; GET /api/admin/stats endpoint belirsiz |
| 12 | Chatbot (4 mod) | TAMAM | chatTypes.ts: kilavuz, mevzuat, taslak_duzenleme, kucuk_sohbet + 5 ek mod; chat_agent.py hepsini destekliyor |
| 13 | DOCX cikti | TAMAM | docx_renderer.py; ornek_cikti.docx mevcut; /api/analysis/{id}/download endpoint |
| 14 | QR kod + dogrulama sayfasi | KISMI | docx_renderer.py L159+: QR DOCX'e gomul .uyor; ancak web dogrulama sayfasi (/verify/{code}) endpoint'i yok |
| 15 | Veritabani | TAMAM | SQLite/SQLAlchemy; db/models.py (Analysis, ReviewEvent) + db/case_models.py (CaseRecord, CaseEvent, CaseUser vb.); kalici |
| 16 | document_knowledge / benzer evrak | KISMI | rag/qdrant_store.py DOCUMENT_COLLECTION tanimli; chunker yukluyor; ancak frontend'de oneri bileseni yok |
| 17 | Vatandas bildirim/durum takibi | TAMAM | CitizenTracePage.tsx; cases/public_router.py; citizen_token_hash + guvenli public DTO |
| 18 | Routing_agent kurum bazli test | KISMI | test_routing_agent.py mevcut; kaymakamlik testleri var; belediye profiliyle ayri birim setiyle entegrasyon testi yok |

**B Ozeti:** TAMAM: 8 | KISMI: 6 | EKSIK: 4

---

## BOLUM C - BILINEN ACIK SORUNLARIN GUNCEL DURUMU

| # | Sorun | Guncel Durum | Kanit |
|---|-------|--------------|-------|
| 1 | Taslakta yanlis muhatap | COZULDU (kismi) | quality_agent.py L238-242: uyari uretiliyor; _originator_recipient() var; otomatik duzeltme yok |
| 2 | LegalAgent kanitinin WritingAgent'a ulasmasi | TAMAM | graph/workflow.py L310: legal_evidence pipeline'da akiyor; intelligence/case_writing.py L184 |
| 3 | Imza tespiti (Turkce B/K harf) | COZULDU | quality_agent.py L39: I->i, normealize; unicodedata.NFKC |
| 4 | Sahte tarih/referans numarasi uretimi | COZULDU | quality_agent.py L27-31: _FAKE_REFERENCE_PATTERNS; L272-280: uyari uretiliyor |
| 5 | Format Durumu Bilinmiyor sorunu | COZULDU | quality_agent.py L231-236: _OW_VALIDATOR_AVAILABLE bayragi; bilinmiyor string'i artik codebase'de yok |
| 6 | Kurum bazli liste filtreleme canlida | TAMAM (backend) | repository.py L112-113 SQL WHERE calisiyor; frontend api.ts L204 parametre gonderiyor |
| 7 | Legal retrieval komsu madde sorunu | KISMI | test_legal_explicit_retrieval.py mevcut; TRACK1_OVERNIGHT_REPORT.md ele almis; Qdrant canli olmadan son dogrulama yapilamilyor |

---

## BOLUM D - TEST SAGLIGI

### Backend Testleri (ham cikti)

```
.venv\Scripts\python.exe -m pytest backend/tests/ -q
--ignore=test_ocr.py --ignore=test_qdrant_store.py
--ignore=test_paddleocr.py --ignore=test_retriever.py

542 passed, 1 skipped in 71.02s
```

**Test dosyasi sayisi:** 43 adet

| Ajan | Test Durumu |
|------|-------------|
| document_agent | test_workflow.py, test_api.py araciligiyla TAMAM |
| extraction_agent | test_extraction_agent.py TAMAM |
| summary_agent | test_summary_agent.py TAMAM |
| legal_agent | test_legal_agent_prompt.py + test_legal_explicit_retrieval.py TAMAM |
| missing_field_agent | test_missing_fields.py TAMAM |
| routing_agent | test_routing_agent.py TAMAM |
| writing_agent | test_writing_agent.py TAMAM |
| quality_agent | test_quality_agent.py TAMAM |
| priority_agent | test_priority_agent.py TAMAM |
| chat_agent | test_chat_agent.py TAMAM |
| transfer_agent | DOGRUDAN TEST YOK |
| clarification_agent | DOGRUDAN TEST YOK (190 byte, sadece stub) |
| Case Engine | test_case_workflow.py, test_case_orchestration.py, test_post_merge_integration.py TAMAM |

**Test kapsami olmayan ajanlar:** transfer_agent, clarification_agent

### Frontend Testleri

```
npm run test:run  => 58/58 PASSED (6 test suites)
npm run build     => SUCCESS (tsc + vite, 781ms)
git diff --check  => PASS
```

---

## BOLUM E - ONCELIKLENDIRILMIS YOL HARITASI

### P0 - ACIL (Demo calismıyor sayilir)

| # | Sorun | Kim | Efor | Etkilenen Dosyalar |
|---|-------|-----|------|---------------------|
| P0-1 | Yonetici paneli bos - AdminPage.tsx sadece placeholder; juri analiz metrikleri goremiyor | Kisi 1 + Kisi 3 | Orta | frontend/src/pages/AdminPage.tsx + yeni /api/admin/stats endpoint |
| P0-2 | RoutingAgent hardcoded kaymakamlik - belediye belgeleri kaymakamlik birimleriyle yonlendiriliyor | Kisi 1 | Kucuk | routing_agent.py L10, quality_agent.py L19: institution_id parametreden alinmali |
| P0-3 | QR dogrulama endpoint yok - DOCX'te QR var ama taranan URL 404 doniyor | Kisi 1 | Kucuk | backend/app/main.py veya yeni router |
| P0-4 | Admin stats endpoint belirsiz - frontend baglantisi kopuk | Kisi 1 | Orta | backend/app/main.py veya yeni admin router |

### P1 - Onemli (Sartname/puan etkiler)

| # | Sorun | Kim | Efor | Etkilenen Dosyalar |
|---|-------|-----|------|---------------------|
| P1-1 | Belediye multi-institution testi eksik | Kisi 1 | Kucuk | backend/tests/test_routing_agent.py |
| P1-2 | Basvuru/dosya zinciri (ilgili_evrak_id) yok | Kisi 1 | Buyuk | db/case_models.py, cases/engine.py, CaseWorkspacePage.tsx |
| P1-3 | PII maskeleme yok | Kisi 1 | Orta | Yeni utils/pii.py; extraction_agent.py, main.py |
| P1-4 | Audit trail field-level degil | Kisi 1 | Orta | db/case_models.py, cases/engine.py |
| P1-5 | transfer_agent + clarification_agent test yok | Kisi 1 | Kucuk | Yeni test_transfer_agent.py |
| P1-6 | document_knowledge frontend'de gozukmuyor | Kisi 3 | Orta | frontend/src/pages/DocumentWorkspacePage.tsx |
| P1-7 | Muhatap uyumsuzlugu uyariyor ama duzeltmiyor | Kisi 1 | Kucuk | backend/app/agents/writing_agent.py |

### P2 - Ozgunluk / Nice-to-have

| # | Ozellik | Kim | Efor |
|---|---------|-----|------|
| P2-1 | QR dogrulama sayfasi (frontend) | Kisi 3 | Orta |
| P2-2 | Analitik dashboard (gercek API metrikler) | Kisi 3 | Orta |
| P2-3 | Birim bazli dedicated kuyruk endpoint | Kisi 1 | Kucuk |
| P2-4 | Legal retrieval komsu madde dogrulugu | Track 1 | Buyuk |
| P2-5 | Vatandas e-posta/SMS bildirimi | Kisi 1 | Buyuk |

---

## OZET TABLO

| Bolum | TAMAM | KISMI | EKSIK |
|-------|-------|-------|-------|
| A - Sartname (11 madde) | 10 | 1 | 0 |
| B - Ozellik Envanteri (18 madde) | 8 | 6 | 4 |
| **Toplam** | **18** | **7** | **4** |

### P0 Listesi (Tam)

1. **P0-1** - Yonetici paneli bos (AdminPage.tsx sadece placeholder)
2. **P0-2** - RoutingAgent hardcoded kaymakamlik; belediye belgeleri yanlis yonlendiriliyor
3. **P0-3** - QR dogrulama backend endpoint yok (404)
4. **P0-4** - GET /api/admin/stats frontend baglantisi kopuk

> UYARI: Hicbir dosya bu rapor icin degistirilmemistir.
> Bu belge tamamen read-only bir envanter ciktisidir.
