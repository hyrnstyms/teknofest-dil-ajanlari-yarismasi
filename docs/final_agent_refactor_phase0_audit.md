# KAMUAI Final Agent Refactor — Faz 0 Audit Raporu

**Branch:** `final-agent-refactor`
**Tarih:** 2026-08-27
**Kaynak:** Yalnizca mevcut source code — hicbir bulgu tahmin/varsayim icermez.

---

## 1. Mevcut Pipeline

```
DocumentState (raw_text, kurum_profili_id)
        |
        v
[document_agent]     ->  state.document
        |
        v
[extraction_agent]   ->  state.extraction
        |
        v
[legal_agent]        ->  state.legal_analysis
        |
        v
[missing_field_agent]->  state.missing_fields
        |
        v
[summary_agent]      ->  state.summary
        |
        v
[routing_agent]      ->  state.routing
        |
        v
[writing_agent]      ->  state.draft
        |
        v
[quality_agent]      ->  state.quality
        |
        v
[human_review_agent] ->  state.human_review
        |
        v
       END
```

**Topoloji:** Tamamen dogrusal (linear). `workflow.py:59-69` — Kosullu dallanma, paralel node veya retry yok.

**Orchestration:** LangGraph `StateGraph(DocumentState)`. Hata yakalanma: `_measure_time()` sarmalayici her node'u try/except ile sarar ve node_timings'e `"status": "failed"` yazar; exception sonraki node'a ulasmay durdurmaz.

> **DIKKAT:** `_measure_time()` icindeki except blogu sadece `{"warnings": [...]}` dondurur ve devam eder. LangGraph bir node'un partial update donmesini kabul eder. **Bir node coktuegunde pipeline devam eder; sonraki agentlar bos state uzerinde calisir.** Bu sessiz veri bozulmasina yol acabilir.

---

## 2. Agent Contract Matrisi

### 2.1 DocumentAgent

| Ozellik | Deger |
|---|---|
| **Input** | `raw_text: str` |
| **Output** | `state.document = {document_type, process_intent, subject_excerpt, request_excerpt, evidence, classification_mode, needs_human_review, priority, priority_rule, priority_reason, deadline, days_remaining, decision_source, raw_llm_result, llm}` |
| **LLM cairiyor mu?** | **Evet — her zaman** (`_classify_with_llm`, sonra kosullu `_validate_semantic_classification`). Heuristic fallback LLM basarisiz olursa devreye girer. |
| **RAG cairiyor mu?** | Hayir |
| **Deterministic kisim** | `_validate_semantic_classification` (regex override), `_heuristic_classification` (regex fallback), `_extract_evidence_fallback`, `PriorityAgent.assess` (tamamen deterministic, LLM yok) |
| **Fallback davranisi** | LLM gecersiz sinif uretirse `_heuristic_classification` -> regex kurallar calisir. |
| **needs_human_review** | `document_type == "diger" OR process_intent == "diger"` |
| **Workflow bagimliliklar** | Giris noktasi — bagimlilik yok |

### 2.2 ExtractionAgent

| Ozellik | Deger |
|---|---|
| **Input** | `raw_text`, `document_context` (= `state.document`) |
| **Output** | `state.extraction = {fields: {email, phone, national_id, document_number, document_date, attachments, signature_present, authority_document_present, subject, request, person_name, address, recipient, institution, sender_unit, other_entities}, warnings, needs_human_review, llm}` |
| **LLM cairiyor mu?** | **Kosullu — bkz. §3.1** |
| **RAG cairiyor mu?** | Hayir |
| **Deterministic kisim** | email, phone, TC, document_number, document_date, attachments, signature_present, authority_document_present, person_name, address, recipient, subject, request — tamami regex/heuristic |
| **Fallback davranisi** | LLM bos/hatali donerse `warnings.append("semantic_extraction_unavailable")`, deterministic kisim korunur |
| **needs_human_review** | `invalid_national_id_candidate` WARNING varsa veya LLM extraction basarisiz olursa -> True |
| **Workflow bagimliliklar** | `state.document` (subject_excerpt, request_excerpt reuse icin) |

### 2.3 LegalAgent

| Ozellik | Deger |
|---|---|
| **Input** | Composite query: `process_intent + subject_excerpt + request_excerpt + raw_text[:1000] + document_legal_references` |
| **Output** | `state.legal_analysis = {answer, evidence, sources, retrieved_sources, retrieval_score, confidence_type, llm}` |
| **LLM cairiyor mu?** | **Evet — her zaman** (`_generate_grounded_answer`). RAG'dan sonra LLM evidence extraction |
| **RAG cairiyor mu?** | **Evet** — Qdrant `search_legal`. `strict_explicit_law=True` ise law_number filtrelenerek, aksi halde semantik |
| **Deterministic kisim** | `_validate_evidence_items` (LLM'in evidence'i kaynakta birebir aranir; yoksa elenir), `_is_query_relevant` (lexical token overlap), `_prioritize_explicit_article` |
| **Fallback davranisi** | Kaynak bulunamazsa `_empty_result` doner. `workflow.py:147-152`'de hata yakalanir. |
| **needs_human_review** | Explicit degil; bos evidence zincirde kalite uyarisina yol acar |
| **Workflow bagimliliklar** | `state.document` (process_intent, subject_excerpt, request_excerpt); `raw_text` |

> **NOT:** `workflow.py:36` — `self.document_retriever = self.legal_agent.retriever`. Bu retriever ayni zamanda `node_routing`'de de kullanilir. LegalAgent ve RoutingAgent ayni Retriever instance'ini paylasiyor.

### 2.4 MissingFieldAgent

| Ozellik | Deger |
|---|---|
| **Input** | `document_type: str`, `process_intent: str`, `extracted_fields: dict`, `legal_analysis: dict` |
| **Output** | `state.missing_fields = {required_fields, present_fields, missing_fields, uncertain_fields, field_results, legal_basis, warnings, needs_human_review}` |
| **LLM cairiyor mu?** | **Hayir** — tamamen deterministic |
| **RAG cairiyor mu?** | Hayir |
| **Deterministic kisim** | `REQUIREMENT_RULES` lookup tablosu (document_type, process_intent) -> required fields -> extraction fields ile karsilastirma |
| **Fallback davranisi** | Kural bulunamazsa `("*", "*")` generic fallback: `[person_name, signature_present, subject, request]` |
| **needs_human_review** | `signature_present` veya `authority_document_present` unknown/eksikse -> True |
| **Workflow bagimliliklar** | `state.document` (document_type, process_intent), `state.extraction` (fields) |

### 2.5 SummaryAgent

| Ozellik | Deger |
|---|---|
| **Input** | `raw_text`, `document_analysis` (= `state.document`), `extracted_fields` (= `state.extraction.fields`) |
| **Output** | `state.summary = {short_summary, summary_mode, structured_summary, source_map, warnings, needs_human_review, llm}` |
| **LLM cairiyor mu?** | **Kosullu — bkz. §3.2** |
| **RAG cairiyor mu?** | Hayir |
| **Deterministic kisim** | `applicant + subject` varsa template: `"{applicant} tarafindan {subject} konusunda basvuru yapilmistir."` |
| **Fallback davranisi** | Deterministic basarisiz olursa LLM -> hala bossa `needs_human_review=True` |
| **needs_human_review** | LLM ile ozet uretilirse -> True. Hic ozet uretilemezse -> True |
| **Workflow bagimliliklar** | `state.extraction.fields` (person_name, subject, request, document_date, institution) |

### 2.6 RoutingAgent

| Ozellik | Deger |
|---|---|
| **Input** | `document_type`, `process_intent`, `subject`, `request_text`, `extracted_fields`, `retrieved_documents` |
| **Output** | `state.routing = {recommended_unit, alternative_units, ranked_units, reason, evidence, routing_score, score_type, score_breakdown, registry_source, needs_human_review, warnings}` |
| **LLM cairiyor mu?** | **Hayir** — tamamen deterministic kural tabanli |
| **RAG cairiyor mu?** | **Evet** — `workflow.py:193-205`'te `self.document_retriever.search_documents()` cagrilir. Retriever sonuclari RoutingAgent'a parametre olarak gecilir. |
| **Deterministic kisim** | Explicit target match (regex), doc_type_mapping, intent match, keyword match, exemplar score scoring |
| **Fallback davranisi** | Score < 30 -> `needs_human_review=True`, `recommended_unit=None`. 30 <= score < 40 -> human_review. Margin < 15 -> ambiguous |
| **needs_human_review** | Profil yuklenemezse, score yetersizse veya margin dusukse -> True |
| **Workflow bagimliliklar** | `state.document`, `state.extraction.fields`, `self.document_retriever` (LegalAgent'tan paylasmli) |
| **Institution baglantisi** | `load_institution_profile(institution)` -> `birimler` + `evrak_turleri` |

> **UYARI — Institution Propagation Sorunu:** `workflow.py:39` — `RoutingAgent(institution=institution)` dogru sekilde gecilir. Ancak `QualityAgent()` -> institution parametresi **hardcode "kaymakamlik"**. Farkli bir kurum secildiginde QualityAgent degismez.

### 2.7 WritingAgent

| Ozellik | Deger |
|---|---|
| **Input** | `document_summary`, `requested_action`, `missing_fields`, `verified_facts`, `legal_context`, `document_legal_references`, `recipient`, `sender_unit`, `state: dict` |
| **Output** | `state.draft = {draft_type, draft_type_reason, draft_generation_mode, draft, rendered_text, official_render, process_explanation, applied_rules, supporting_rules, rule_validation, sources, retrieval_score, llm, verified_facts_used, requires_human_approval, needs_additional_context, warning}` |
| **LLM cairiyor mu?** | **Evet — birden fazla potansiyel cagri. Bkz. §3.3** |
| **RAG cairiyor mu?** | **Evet** — `search_official_writing()` (Resmi Yazisma Kilavuzu corpus'u) |
| **Deterministic kisim** | `_decide_draft_type` (missing_fields varsa -> eksik_bilgi_talebi, forwarding markers -> ust_yazi, response markers -> cevap_yazisi), `_validate_rules`, `_extract_supporting_rules`, `_sanitize_draft`, `_ensure_document_legal_references`, `_build_missing_info_fallback`, `_build_verified_facts_fallback` |
| **Fallback davranisi** | RAG bossa early return + `requires_human_approval=True`. Draft bossa repair -> deterministic fallback -> blocked |
| **needs_human_review** | Her zaman `requires_human_approval=True` (kamu personeli onayi) |
| **Workflow bagimliliklar** | `state.summary`, `state.document`, `state.missing_fields`, `state.extraction.fields`, `state.routing`, `state.legal_analysis`, `state.kurum_profili_id`, `state.muhatap`, `state.muhatap_turu` |
| **Official Render** | `_try_official_render` -> `build_official_writing_context` -> `render_ust_yazi` / `render_cevap_yazisi` |

**WritingAgent Icindeki Ayri Sorumluluklar:**

| Sorumluluk | Metod | Tur |
|---|---|---|
| Draft type decision | `_decide_draft_type` | Deterministic + conditional LLM |
| Retrieval | `draft()` icindeki `search_official_writing` | RAG |
| Generation | `_generate_draft` | LLM |
| Repair | `_repair_draft` | LLM |
| Deterministic fallback | `_build_missing_info_fallback`, `_build_verified_facts_fallback` | Deterministic |
| Official rendering | `_try_official_render` -> template_renderer | Template engine |
| Validation | `_validate_rules`, `_is_draft_complete` | Deterministic |
| Legal grounding | `_ensure_document_legal_references` | Deterministic + prompting |

### 2.8 QualityAgent

| Ozellik | Deger |
|---|---|
| **Input** | `document, extraction, legal_analysis, missing_fields, summary, routing, draft, human_review` |
| **Output** | `state.quality = {status, checks, issues, warnings, requires_human_review}` |
| **LLM cairiyor mu?** | **Hayir** — tamamen deterministic |
| **RAG cairiyor mu?** | Hayir |
| **Deterministic kisim** | 8 check: document_classification, extraction, missing_fields_consistency, legal_evidence, routing, summary_consistency, draft, official_writing_format |
| **Fallback davranisi** | Format validator yuklenemezse atlanir (try/except import) |
| **needs_human_review** | `requires_human_review=True` olarak herhangi bir check fail/warning verirse |
| **Institution baglantisi** | **BUG:** `_DEFAULT_INSTITUTION = "kaymakamlik"` — hardcode. `QualityAgent()` workflow'dan `institution=institution` almiyor |

### 2.9 HumanReviewAgent (inline, workflow.py)

| Ozellik | Deger |
|---|---|
| **Input** | `state.quality`, `state.missing_fields`, `state.routing`, `state.draft` |
| **Output** | `state.human_review = {required: bool, status: "pending_review" \| "approved_auto"}` |
| **LLM cairiyor mu?** | Hayir |
| **Deterministic kisim** | OR kombinasyonu: quality.requires_human_review OR missing_fields.needs_human_review OR routing.needs_human_review |
| **Fallback** | Yok; default `approved_auto` |

> **DIKKAT:** `workflow.py:343-344` — `if s.draft.get("draft_text"):` — `draft_text` alani mevcut `WritingAgent` output contract'inda **bulunmuyor**. WritingAgent `"draft"` (dict), `"rendered_text"` (str) uretiyor. `draft_text` legacy state field'i (state.py L45). Bu check her zaman `False` donduruyor.

---

## 3. LLM Cagri Haritasi

### 3.1 ExtractionAgent — LLM Kosullari

```python
# extraction_agent.py:165-168
semantic_candidates = ["person_name", "address", "institution", "sender_unit", "recipient", "subject", "request"]
target_semantic = [k for k in semantic_candidates if k not in fields]
target_semantic.append("other_entities")    # <- HER ZAMAN eklenir

llm_fields = self._extract_with_llm(text, target_semantic)
```

**Sonuc:** `target_fields` listesi her zaman en az `"other_entities"` icerir -> ExtractionAgent **pratikte her zaman LLM cagirir**.

> **ONEMLI:** `extraction_agent.py:167` — `target_semantic.append("other_entities")` satiri, tum semantic alanlar deterministic olarak doldu olsa bile LLM cagrisini garanti eder. Bu tasarim karari bilincliyse belgelenmemis.

### 3.2 SummaryAgent — LLM Kosullari

**LLM CAGIRILMAZ:** `applicant` (person_name) VE `subject` ikisi de mevcut -> deterministic template yeterli -> `summary_mode="deterministic"` -> `llm.status="not_required"`

**LLM CAGIRILIR:** `person_name` veya `subject` extraction'dan cikarilabiliyorsa + `not result["short_summary"]` kosulu True ise

**LLM sonrasi:** Summary mode `"llm_grounded"` -> `needs_human_review=True` otomatik set edilir.

### 3.3 WritingAgent — LLM Cagri Sirasi

| Adim | Cagri | Kosul |
|---|---|---|
| 1 | `_decide_draft_type` LLM | Deterministik kurallar eslesemezse (belirsiz durum) |
| 2 | `_generate_draft` LLM | Her zaman (RAG basariliysaysa) |
| 3 | `_repair_draft` LLM | Draft bos/eksikse ve `draft_type != "eksik_bilgi_talebi"` |

**Toplam max LLM cagrisi WritingAgent icinde:** 3 (decide_type + generate + repair)

---

## 4. Taxonomy Tutarsizliklari

### 4.1 document_type — DocumentAgent vs MissingFieldAgent

**DocumentAgent `ALLOWED_DOCUMENT_TYPES`** (document_agent.py:10-20):
```
dilekce, resmi_yazi, form, tutanak, rapor, karar, tebligat, eposta, diger
```

**MissingFieldAgent `REQUIREMENT_RULES` key'leri** (missing_field_agent.py:5-27):
```
dilekce, bilgi_edinme, sosyal_yardim_basvuru, tapu_kadastro_basvuru,
ihale_itirazi, kurumlar_arasi_yazi, (*, *)
```

> **KRITIK BUG — Taxonomy Mismatch:** MissingFieldAgent'taki `bilgi_edinme`, `sosyal_yardim_basvuru`, `tapu_kadastro_basvuru`, `ihale_itirazi`, `kurumlar_arasi_yazi` degerleri DocumentAgent'in ALLOWED_DOCUMENT_TYPES'inda **bulunmuyor**. DocumentAgent bu degerleri uretemiyor. MissingFieldAgent'taki 5 ozel kural **hicbir zaman eslesmez** — her zaman `("*", "*")` generic fallback kullanilir. **Bu 5 kural olu koddur.**

**Institution Profile `evrak_turleri` id'leri** (kurum_profili_kaymakamlik.yaml):
```
dilekce, bilgi_edinme, kurumlar_arasi_yazi, ihale_itirazi, sosyal_yardim_basvuru, tapu_kadastro_basvuru
```

Bu id'ler DocumentAgent output'undaki `document_type` enum'uyla eslesmez; institution YAML taxonomy'si de hizasiz.

### 4.2 process_intent Taxonomy

**DocumentAgent `ALLOWED_PROCESS_INTENTS`:**
```
bilgi_talebi, belge_talebi, basvuru, sikayet, itiraz, izin_talebi, bildirim, cevap, iletim, diger
```

**RoutingAgent (profile.birimler[].supported_intents):**
```
bilgi_talebi, belge_talebi, basvuru, sikayet, itiraz, izin_talebi, bildirim, cevap, iletim, diger
```
**-> Tutarli.**

### 4.3 draft_type Taxonomy

**WritingAgent `ALLOWED_DRAFT_TYPES`** (writing_agent.py:22-28):
```
ust_yazi, cevap_yazisi, bilgilendirme_metni, eksik_bilgi_talebi, diger
```

**QualityAgent `RESMI_YAZI_TURLERI`** (quality_agent.py:257-262):
```
ust_yazi -> ust_yazi
bilgilendirme_metni -> ust_yazi  (ayri sablon yok, TASARIM KARARI)
cevap_yazisi -> cevap_yazisi
tekit_yazisi -> tekit_yazisi     <- SADECE QUALITY'DE VAR
```

> **UYARI:** `tekit_yazisi` QualityAgent mapping'inde bulunuyor ancak WritingAgent `ALLOWED_DRAFT_TYPES`'da **yok**. WritingAgent hic `tekit_yazisi` uretmez; bu QualityAgent kodu erisilemez bir daldir.

### 4.4 priority Taxonomy

**PriorityAgent output** (priority_agent.py:7):
```python
PriorityLevel = Literal["HIGH", "MEDIUM", "LOW"]
```

**Frontend presentation.ts:**
```typescript
low: "Normal", medium: "Orta", high: "Yuksek", urgent: "Acil"
```

Notlar:
- `presentation.ts:14` — `key = value.trim().toLocaleLowerCase("tr-TR")` ile normalize ediliyor, dolayisiyla `"HIGH" -> "high"` -> label bulunur. **OK.**
- `"urgent"` priority degeri mevcut PriorityAgent'ta **uretilmiyor**. Frontend bunu biliyor (label var) ama backend hic uretmez. Olu label.
- `labels.ts:DOC_TYPE_LABELS` icinde priority icin entry yok; sadece `presentation.ts`'te var. Split tanim.

### 4.5 human_review status Taxonomy

**HumanReviewAgent output** (workflow.py:349):
```python
{"required": req, "status": "pending_review" if req else "approved_auto"}
```

**Frontend `STATUS_LABELS`** (labels.ts:1-9):
```typescript
pending_review: "Inceleme Bekliyor"
approved: "Onaylandi"
edited: "Duzenlendi"
rejected: "Reddedildi"
```

`approved_auto` frontend `STATUS_LABELS`'ta **tanimli degil** (`labels.ts`'te yok, sadece `presentation.ts`'te var). Bu split tanim karisikliga yol acar.

**Backend API state gecisleri:**
- `approve` endpoint -> `status = "approved"`
- `reject`  endpoint -> `status = "rejected"`
- Baslangicta: `"pending_review"` veya `"approved_auto"`

### 4.6 signature_present status Taxonomy

**ExtractionAgent output** (extraction_agent.py:95-103):
```python
{"value": True/None, "status": "present"/"unknown", ...}
```

`signature_present.status` icin frontend'de Turkce label mapping yok; `FIELD_LABELS["signature_present"] = "Imza Durumu"` label'i var ama `"present"` / `"unknown"` string'leri icin degil.

---

## 5. Institution Propagation Analizi

### 5.1 Workflow Initialization

```python
# workflow.py:19, 39, 41
KamuaiWorkflow(institution="kaymakamlik")
RoutingAgent(institution=institution)   # OK — dogru geciliyor
QualityAgent()                          # BUG — DEFAULT "kaymakamlik" sabit
```

### 5.2 Agent-by-Agent Institution Kullanimi

| Agent | Institution Kullaniyor mu? | Nasil? |
|---|---|---|
| DocumentAgent | Hayir | — |
| ExtractionAgent | Hayir | — |
| LegalAgent | Hayir | Qdrant'tan hukuki kaynak arar, kurum filtresi yok |
| MissingFieldAgent | Hayir | REQUIREMENT_RULES kurum bagimsiz |
| SummaryAgent | Hayir | — |
| RoutingAgent | **Evet** | `load_institution_profile(institution)` -> birimler + evrak_turleri |
| WritingAgent | **Kismen** | `state["kurum_profili_id"]` context_adapter'a gecilir -> `_get_profile()` cagirilir |
| QualityAgent | **Hayir (bug)** | `_DEFAULT_INSTITUTION = "kaymakamlik"` hardcode |

> **KRITIK BUG — QualityAgent Institution:** `quality_agent.py:19, 53` — QualityAgent her zaman `"kaymakamlik"` profilini yukler. Belediye gibi farkli bir kurum secilirse:
>
> 1. `self.valid_units` kaymakamlik birimlerini icerir
> 2. RoutingAgent belediye birimini onerir
> 3. QualityAgent routing check'inde `rec_unit in self.valid_units` -> **False** -> "Onerilen birim registry'de bulunamadi" -> `fail` check + `requires_human_review=True`
>
> Farkli kurum secildiginde Quality check yanlis sonuc uretir.

### 5.3 WritingAgent'a Institution Gecisi

`workflow.py:269`:
```python
"kurum_profili_id": s.kurum_profili_id,
"muhatap":          s.muhatap,
"muhatap_turu":     s.muhatap_turu,
```

`state.kurum_profili_id` -> `workflow.run()` icinde `kurum_profili_id=self.institution` set edilir. `context_adapter._get_profile()` fonksiyonu `"kaymakamlik_v1"` -> `"kaymakamlik"` parse eder. **Dogru.**

---

## 6. State Duplikasyon ve Legacy Alanlari

`state.py` iki katman iceriyor:

### 6.1 Active Component State (dict)
```python
document, extraction, legal_analysis, missing_fields, summary,
routing, transfer_routing, draft, quality, human_review, telemetry
```

### 6.2 Legacy Top-Level Fields (state.py:33-48)
Bunlar LangGraph state uzerinde **tanimli** ama hicbir agent tarafindan **yazilmiyor**:

| Field | Gercek Veri Kaynagi | Durum |
|---|---|---|
| `file_name` | `main.py`'de `analysis_id` ile yonetiliyor | Olu |
| `document_type` | `state.document["document_type"]` | Duplike |
| `confidence` | — | Kullanilmiyor |
| `document_confidence` | — | Kullanilmiyor |
| `entities` | `state.extraction["fields"]` | Duplike |
| `missing_information` | `state.missing_fields["missing_fields"]` | Duplike |
| `legal_references` | `state.legal_analysis["evidence"]` | Duplike |
| `legal_confidence` | — | Kullanilmiyor |
| `department` | `state.routing["recommended_unit"]` | Duplike |
| `routing_confidence` | `state.routing["routing_score"]` | Duplike |
| `routing_reason` | `state.routing["reason"]` | Duplike |
| `draft_type` | `state.draft["draft_type"]` | Duplike |
| `draft_text` | `state.draft["rendered_text"]` | Duplike — legacy check'te kullaniliyor (workflow.py:343) ama WritingAgent yazmaz |
| `quality_score` | — | Kullanilmiyor |
| `requires_human_review` | `state.human_review["required"]` | Duplike |
| `status` | — | Kullanilmiyor |

> **UYARI:** `muhatap`, `muhatap_turu`, `karar_kaynagi` alanlari state'te tanimli ama pipeline icinde **bunlari set eden agent yok**. Yalnizca WritingAgent state dict uzerinden okur; context_adapter bu alanlari kullanir. Ancak yazilan yer belirsiz.

---

## 7. UI/Frontend Raw Key Leak Noktalari

### 7.1 AIOperationsPage.tsx

`humanize()` fonksiyonu (satir 363-365) backend key'leri basit kelime ayirimi ile Turkcelestiriyor ancak **tam dogruluğu garantilenmiyor**:

| Backend Key | humanize() Ciktisi | Dogru Turkce |
|---|---|---|
| `pending_review` | "Pending Review" | "Inceleme Bekliyor" |
| `approved_auto` | "Approved Auto" | "Otomatik Onaylandi" |
| `kaymakamlik` | "Kaymakamlik" | "Kaymakamlık" (i eksik) |
| `LOW` | "LOW" | "Normal" |

**Satir 139:**
```typescript
<Metric label="Oncelik" value={analysis.document?.priority} />
```
`humanize()` **cagrilmiyor** — raw `"HIGH"` / `"LOW"` deger dogrudan render edilir.

### 7.2 presentation.ts — Eksik Enum Mapping'leri

`ENUM_LABELS` icinde olmayan degerler (fallback: `"_" -> " "` donusumu):

| Backend Value | Fallback Sonuc | Sorun |
|---|---|---|
| `form`, `tutanak`, `rapor`, `karar`, `tebligat` | "Form", "Tutanak", vb. | Yeterince anlasilabilir |
| `eposta` | "Eposta" | "E-posta" olmasi gerekirdi |
| `izin_talebi` | "Izin Talebi" | "I" buyuk harf - `toLocaleUpperCase` ile "İ" olabilir — test gerekli |
| `diger` | "Diger" | "Diger" (diger) — aksansiz |
| `blocked_insufficient_context` | "Blocked Insufficient Context" | Tamamen Ingilizce |
| `llm_repair` | "Llm Repair" | Tamamen Ingilizce |
| `HIGH` | "High" | Kucuk harfte "high" label'la eslesmez — ama `toLocaleLowerCase` korur |

### 7.3 labels.ts — DOC_TYPE_LABELS Eksiklikleri

`DOC_TYPE_LABELS` icinde DocumentAgent taxonomy'sinden eksikler:
- `form`, `tutanak`, `rapor`, `karar`, `tebligat`, `eposta`, `diger` -> tanimli degil

> **ONEMLI:** Iki ayri label sistemi (`labels.ts` + `presentation.ts`) birbiriyle tam ortusmuyor. `getLabel()` `labels.ts`'ten, `formatDisplayName()` `presentation.ts`'ten kullaniliyor. Hangi component hangi sistemi kullandigi henuz denetlenmedi — biri eksik diger'de tanimlidir.

---

## 8. Risk Listesi

| Risk | Seviye | Kaynak |
|---|---|---|
| MissingFieldAgent ozel kurallari hic tetiklenmiyor (taxonomy mismatch) | **YUKSEK** | `missing_field_agent.py:5-27` |
| QualityAgent farkli kurumda yanlis valid_units kullaniyor | **YUKSEK** | `quality_agent.py:19` |
| Pipeline sessizce devam ediyor node failure sonrasi | **ORTA** | `workflow.py:78-80` |
| `draft_text` legacy field check hic calismiyor | **ORTA** | `workflow.py:343` |
| ExtractionAgent her zaman LLM cairiyor (other_entities) | **ORTA** | `extraction_agent.py:167` |
| `muhatap`/`muhatap_turu` state'e yazilmiyor | **ORTA** | `state.py:11-12` |
| `tekit_yazisi` QualityAgent'ta ama WritingAgent'ta yok | **DUSUK** | `quality_agent.py:261` |
| `priority` raw string AIOperationsPage'de humanize yapilmiyor | **DUSUK** | `AIOperationsPage.tsx:139` |
| `approved_auto` labels.ts'te eksik | **DUSUK** | `labels.ts` |
| Legacy state alanlari 16 adet | **DUSUK** | `state.py:33-48` |
| `kaymakamlik_v1` kurum ID'si context_adapter'da ozel parse ediliyor | **DUSUK** | `context_adapter.py:49` |

---

## 9. Test Baseline Sonuclari

### 9.1 Calisan Testler

```
backend/tests/test_institutions.py        PASS
backend/tests/test_routing_agent.py       PASS
backend/tests/test_missing_fields.py      PASS
backend/tests/test_priority_agent.py      PASS
backend/tests/test_chunk_metadata.py      PASS
backend/tests/test_point_ids.py           PASS
backend/tests/test_telemetry.py           PASS

Toplam: 65 test PASSED
```

### 9.2 Import Hatasi Nedeniyle Calisaamayan Testler

Tum hatalar `openai`, `fastapi`, `sqlalchemy`, `docx`, `sentence_transformers` modullerinin sistem Python'unda kurulu olmamasindan kaynaklaniyor. **Production kodu degistirilmedi; bu venv izolasyon sorunudur.**

```
openai eksik         -> test_document_classification_validation, test_extraction_agent,
                        test_legal_agent_prompt, test_legal_explicit_retrieval,
                        test_llm_factory, evaluation/test_evaluation
fastapi eksik        -> test_api, test_ebys, test_lists, test_final_robustness_harness
sqlalchemy eksik     -> test_db_repository
docx eksik           -> official_writing/test_context_adapter, test_docx_renderer, test_quality_agent
sentence_transformers-> test_document_example_index
```

### 9.3 git diff --check

```
Exit code: 0 — whitespace hatasi yok
```

---

## 10. Faz 1-6 Icin Onerilen Degistirme Sirasi

### Faz 1 — Taxonomy Duzeltme (Sifir Davranis Degisikligi)
- `MissingFieldAgent.REQUIREMENT_RULES` key'lerini DocumentAgent taxonomy'siyle hizala
- Veya DocumentAgent'a yeni document_type'lar ekle (institution evrak_turleri id'leriyle eslestir)
- `tekit_yazisi`'ni ALLOWED_DRAFT_TYPES'a ekle **veya** QualityAgent mapping'den cikar

### Faz 2 — QualityAgent Institution Fix
- `QualityAgent.__init__` -> `institution` parametresi al
- `workflow.py:41` -> `QualityAgent(institution=institution)`

### Faz 3 — State Temizligi
- Legacy 16 alani kaldir (`state.py:33-48`)
- `muhatap`, `muhatap_turu` hangi agent tarafindan set edilecegini belirle ve yaz
- `transfer_routing` alaninin aktif kullanimini dogrula

### Faz 4 — Pipeline Hata Izolasyonu
- `_measure_time` except bloğunu guclendir; node failure durumunda state corruption onle
- `draft_text` legacy check'ini duzelt (`workflow.py:343` -> `rendered_text` kullan)

### Faz 5 — ExtractionAgent LLM Optimizasyonu
- `other_entities` kosullu ekle: tum semantic alanlar doluysa LLM cagirma

### Faz 6 — UI Label Tamamlama
- `labels.ts`'e eksik enums ekle: `form`, `tutanak`, `rapor`, `karar`, `tebligat`, `eposta`, `diger`, `approved_auto`
- `AIOperationsPage.tsx:139` -> priority icin `humanize()` veya `formatDisplayName()` kullan
- `presentation.ts` ENUM_LABELS'a `izin_talebi`, `diger`, `eposta` ekle (Turkce karakter sorunlari)
- Iki label sistemi (`labels.ts` + `presentation.ts`) arasindaki tutarsizligi coz

---

*Bu rapor yalnizca source code okuma ile dogrulanan bulgulari icermektedir. Hicbir production kodu degistirilmemistir.*
