# KAMUAI Final Robustness ve Performance Raporu

## Özet

Final sprint kapsamında hazırlanan robustness ve acceptance harness doğrulanmıştır.
Tam acceptance çalışması 28/28 senaryoda başarılı olmuş, herhangi bir crash veya
beklenmeyen HTTP 500 yanıtı gözlenmemiştir.

- Branch: `final-robustness-performance`
- Commit: `caaa32c test: add final robustness and performance acceptance suite`
- Tam acceptance: **28/28 PASS**
- Crash: **0**
- Beklenmeyen HTTP 500: **0**
- Backend regresyonu: **409 passed, 1 skipped**
- Production kodu değişikliği: **Yok**
- `.env` değişikliği: **Yok**
- Remote Qdrant yazma/silme işlemi: **Yok**

## 1. Kod Audit Sonucu

- Ollama istemcisinin `OLLAMA_KEEP_ALIVE` üzerinden varsayılan `30m`
  `keep_alive` kullandığı doğrulandı.
- Workflow nesnelerinin institution bazında `lru_cache` ile saklandığı doğrulandı.
- BGE-M3 ve Qdrant istemcilerinin paylaşılan, cache'lenen nesneler kullandığı
  doğrulandı.
- FastAPI süreci içinde Qwen model ağırlıklarını ayrıca yükleyen ikinci bir yol
  tespit edilmedi.
- Düşük riskli bir production performans düzeltmesi gerektiren bulgu çıkmadı.
- `backend/app/main.py`, DB kodu, frontend, data corpus, `docker-compose.yml`,
  `requirements.txt` ve agent implementasyonları değiştirilmedi.

## 2. Eklenen Harness Dosyaları

- `scripts/robustness/__init__.py`
- `scripts/robustness/common.py`
- `scripts/final_readiness.py`
- `scripts/final_failure_harness.py`
- `scripts/benchmark_ocr.py`
- `scripts/benchmark_providers.py`
- `scripts/final_acceptance.py`
- `backend/tests/test_final_robustness_harness.py`

Toplam değişiklik: **8 yeni dosya, 946 eklenen satır**.

## 3. Readiness Kontrolü

Readiness script'i aşağıdaki servisleri credential veya secret değerlerini
yazdırmadan kontrol etmektedir:

| Kontrol | Sonuç | Açıklama |
|---|---|---|
| PostgreSQL | SKIP | Projede aktif olmadığı için değiştirilmedi |
| Ollama | PASS | Servis erişilebilir |
| `qwen2.5:3b-instruct` | PASS | İstenen model bulundu |
| EVREN | PASS | Güvenli probe başarılı |
| Local Qdrant | PASS | 3 collection görüldü; salt okunur kontrol |
| Backend health | PASS | Health endpoint başarılı |
| Backend readiness | PASS | Readiness endpoint başarılı |
| Frontend root | PASS | Vite root erişilebilir |
| Frontend `/src/App.tsx` | FAIL | `react-router-dom` çözümlenemiyor |

Readiness harness hazırdır. Tam startup acceptance için kalan engel frontend
tarafındaki `react-router-dom` bağımlılık çözümlemesidir. Frontend bu sprintin
ownership alanı dışında olduğu için değiştirilmemiştir.

## 4. Service Failure ve Bad-input Güvenliği

İzole failure harness ile Qdrant ve Ollama servis kesintileri güvenli biçimde
mock edilmiştir.

| Senaryo | Sonuç |
|---|---|
| Qdrant unavailable | PASS |
| Ollama unavailable | PASS |
| Success response içinde stack trace | Yok |
| Failure harness gate | PASS |

Acceptance kapsamında boş metin, çok kısa metin, gibberish, çok uzun metin ve
desteklenmeyen dosya test edilmiştir. Desteklenmeyen dosya güvenli HTTP 400
üretmiş; diğer girdiler crash veya beklenmeyen HTTP 500 oluşturmadan güvenli
yanıt vermiştir.

## 5. Provider Karşılaştırması

Gerçek `.env` dosyası değiştirilmemiştir. Ollama ve EVREN karşılaştırması
process-level environment override ile, aynı yedi temsilî ve hassas olmayan
prompt kullanılarak yapılmıştır.

| Provider | Başarı | Correctness | Schema | Citation | Timeout | p50 latency |
|---|---:|---:|---:|---:|---:|---:|
| Ollama `qwen2.5:3b-instruct` | 7/7 | PASS | PASS | PASS | 0 | 2779 ms |
| EVREN | 7/7 | PASS | PASS | PASS | 0 | 273 ms |

Ollama tarafında `keep_alive=30m` doğrulanmıştır. İlk Ollama benchmarkında
belirsiz bir harness promptu nedeniyle sonuç 6/7 olmuş; production koduna
dokunulmadan prompt netleştirilmiş ve adil karşılaştırma için iki provider da
yeniden çalıştırılmıştır. Yukarıdaki değerler son ortak prompt setine aittir.

EVREN provider benchmarkı yalnız hassas olmayan sentetik promptlarla
çalıştırılmıştır. PII içeren örnek belgeler dış servise gönderilmemiş; tam API
acceptance local Ollama ve local Qdrant ile gerçekleştirilmiştir.

## 6. OCR Benchmarkı

Tam 17 sayfalık PDF yeniden işlenmemiştir. Mevcut OCR seçenekleriyle üç temiz
ve iki zor temsilî tek sayfa PNG kullanılmıştır.

| Örnek | Tür | Süre | Çıktı | Sonuç |
|---|---|---:|---:|---|
| SENT-0003 | Clean | 65919 ms | 764 karakter | PASS |
| SENT-0004 | Clean | 49110 ms | 566 karakter | PASS |
| SENT-0008 | Clean | 70167 ms | 1249 karakter | PASS |
| SENT-0001 | Difficult | 32754 ms | 4 karakter | FAIL |
| SENT-0018 | Difficult | 31868 ms | 0 karakter | FAIL |

- OCR p50: **49110 ms**
- Kullanılabilir metin: **3/5**
- Runtime crash: **0/5**
- oneDNN/PIR runtime hatası: **Oluşmadı**

Zor görüntülerde düşük OCR kalitesi devam etmektedir. Bu, crash/stuck problemi
değil kalite riskidir. Sprint kısıtları gereği model değişikliği veya yüksek
riskli OCR refactor uygulanmamıştır.

## 7. API Acceptance

Tam local acceptance çalışması local Ollama ve local Qdrant kullanılarak
gerçekleştirilmiştir.

Kapsanan akışlar:

- Kaymakamlık ve Belediye için 5 text analysis
- 2 tek sayfa OCR/file upload
- Active summary, missing fields, routing, legal ve unsupported sınıflarını
  kapsayan 10 chat isteği
- Institution switch
- 3071 sayılı Kanun Madde 7 sorgusu
- Approve ve reject işlemleri
- DOCX üretimi
- Analyses listesi
- Pending reviews listesi
- Bad-input senaryoları

Sonuç:

- **28/28 PASS**
- **0 crash**
- **0 beklenmeyen HTTP 500**
- 3071 Madde 7 sorgusunda ilgili ve doğru içerik döndü.
- DOCX üretimi başarılı oldu.
- Approval/reject ve liste endpointleri başarılı oldu.

Başarılı response gövdelerinin rapora hassas veya binary veri sızdırmaması için
raporlama güvenli hale getirildikten sonra OCR atlanarak tekrar doğrulama
yapılmıştır:

- **26/26 PASS**
- **0 crash**
- **0 beklenmeyen HTTP 500**
- Başarılı response detayları redacted/boş tutuldu.

## 8. Performans Sonuçları

Tam, OCR içeren acceptance çalışmasının p50 değerleri:

| İşlem | p50 latency |
|---|---:|
| Ready | 6552 ms |
| İlk/sıcak text grubu | 20154 ms |
| OCR | 66662.5 ms |
| Bad input | 19780 ms |
| Chat | 2460.5 ms |
| DOCX | 163 ms |
| List endpointleri | 3 ms |
| Review işlemleri | 3 ms |
| Genel | 2610 ms |

OCR atlanan son güvenli raporlama doğrulamasının p50 değerleri:

| İşlem | p50 latency |
|---|---:|
| Ready | 2098 ms |
| Text analysis | 17465 ms |
| Bad input | 20189 ms |
| Chat | 2441.5 ms |
| DOCX | 36 ms |
| List endpointleri | 2.5 ms |
| Review işlemleri | 2.5 ms |
| Genel | 2469.5 ms |

Tam acceptance çalışmasında en yavaş node'lar:

| Node | p50 latency |
|---|---:|
| `writing_agent` | 7990 ms |
| `legal_agent` | 4305 ms |
| `document_agent` | 4043 ms |
| `extraction_agent` | 3894 ms |

OCR atlanan son doğrulamada node p50 değerleri:

| Node | p50 latency |
|---|---:|
| `writing_agent` | 6994 ms |
| `document_agent` | 3933 ms |
| `extraction_agent` | 3802 ms |
| `legal_agent` | 3360 ms |

## 9. Backend Regresyonu

Yeni harness testleri:

- **5 passed in 13.04s**

İlk tam pytest çalışması Windows global temp dizini izin problemi nedeniyle test
kurulumunda dört error üretmiştir. Bunlar uygulama/test failure değil,
`C:\Users\ASUS\AppData\Local\Temp\pytest-of-Hayrunnisa` erişim problemidir.
Aynı suite workspace içinde benzersiz `--basetemp` ile tekrar çalıştırılmıştır:

- **409 passed, 1 skipped, 2 warnings in 88.45s**
- Failure: **0**

İki warning Qdrant version probe ve sistemde `ccache` bulunmamasıyla ilgilidir.
Ek olarak `compileall` başarılı olmuş ve commit için whitespace kontrolü temiz
sonuçlanmıştır.

## 10. Kalan Riskler

1. Frontend Vite module kontrolü `react-router-dom` çözümlenemediği için
   başarısızdır. Bu sprintte frontend değişikliği yapılmamıştır.
2. İki zor OCR örneği kullanılabilir metin üretememiştir. OCR runtime kararlıdır
   ancak düşük kaliteli görüntüler için tanıma kalitesi riski sürmektedir.
3. Text analysis içindeki en yüksek gecikme `writing_agent` tarafındadır.
4. İlk readiness/model yükleme süresi sıcak çağrılara göre belirgin biçimde
   yüksektir.
5. EVREN ile hassas belge içeren tam API acceptance yapılmamıştır; EVREN yalnız
   hassas olmayan ortak provider benchmarkıyla doğrulanmıştır.

## Sonuç

**ROBUSTNESS GATE READY:** Backend robustness ve acceptance harness hazırdır;
28/28 tam acceptance senaryosu crash ve beklenmeyen HTTP 500 olmadan geçmiştir.
Tam uçtan uca startup readiness için kalan dış engel frontend
`react-router-dom` bağımlılık çözümlemesidir.
