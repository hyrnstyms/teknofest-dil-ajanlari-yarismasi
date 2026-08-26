# KAMUAI

## Proje Nedir?
KAMUAI, kamu evrakları için geliştirilmiş yapay zekâ tabanlı bir karar destek sistemidir. Gelen resmi evrakların analiz edilmesi, eksik bilgilerin tespiti, uygun birime yönlendirilmesi ve taslak metin oluşturulması süreçlerini otonom agent'lar yardımıyla gerçekleştirir.

Ana Akış:
Belge → Ingestion/OCR → Document Agent → Extraction Agent → Legal Agent → Missing Field Agent → Summary Agent → Routing Agent → Writing Agent → Quality Agent → Personel İncelemesi

## Resmî Yazışma Format Motoru

KAMUAI, Writing Agent çıktısını deterministik ve LLM-bağımsız bir biçimsel doğrulama katmanından geçirir.

```
Writing Agent (LLM)
  ↓ structured draft (subject, body)
Official Writing Context Adapter (backend/app/official_writing/)
  ↓ Jinja2 render (StrictUndefined)
template_renderer → rendered_text (ust_yazi.jinja2 / cevap_yazisi.jinja2 / tekit_yazisi.jinja2)
  ↓
format_validator → deterministic kural kontrolleri (Madde 11–34)
  ↓
Quality Agent → official_writing_format check
  ↓
Human Review
```

- `backend/app/official_writing/format_validator.py` — Tamamen deterministik; LLM çağrısı içermez.
- `backend/app/official_writing/template_renderer.py` — Jinja2 tabanlı biçimsel render; StrictUndefined ile güvenli.
- Şablonlar: `ust_yazi.jinja2`, `cevap_yazisi.jinja2`, `tekit_yazisi.jinja2`

> Bu katman ekip arkadaşımız tarafından geliştirilmiştir.

## Temel Teknolojiler
- Python 3.12
- FastAPI
- LangGraph
- Ollama
- qwen2.5:3b-instruct
- BAAI/bge-m3
- Qdrant
- React
- TypeScript
- Vite

## Kurulum

Python 3.12 önerilir. Aynı `requirements.txt` ve `docker-compose.yml` macOS ile
Windows'ta kullanılır.

### Ortak adımlar (Docker: Postgres + Qdrant)

Docker Desktop'ı Linux container desteğiyle başlatın ve depo kökünde çalıştırın:

```text
docker compose up -d postgres qdrant
docker compose ps
```

Ortam dosyasını `.env.example` üzerinden oluşturun. Varsayılan geliştirme
bağlantıları PostgreSQL için `localhost:5432`, Qdrant için `localhost:6333`
adreslerini kullanır. Ollama modelini bir kez indirin:

```text
ollama pull qwen2.5:3b-instruct
```

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn backend.app.main:app --reload
```

Normal Python kurulumlarında locale ayarı gerekmez. Yalnız bazı Conda Python
3.13 kurulumlarında macOS'un tanımadığı `LANG=C.UTF-8` değeri `readline`
yüklenirken interpreter çökmesine yol açabilir. `python -c "import readline"`
komutu aynı şekilde çökerse bu host ortamı için geçerli bir locale seçin:

```bash
export LANG=C
export LC_ALL=C
```

Bu ayar KAMUAI'nin veya testlerin gereksinimi değildir ve Windows'ta
kullanılmaz.

### Windows

Docker Desktop'ın Linux containers modunda çalıştığını doğrulayın. PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn backend.app.main:app --reload
```

Aktivasyon kurum politikasıyla engellenirse execution policy değiştirmek
zorunlu değildir; sanal ortam Python'ı doğrudan kullanılabilir:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

Paketler desteklenen Python sürümlerinde wheel olarak kurulur; Visual C++ Build
Tools normal kurulum için gerekli değildir.

### Test çalıştırma

Aktif sanal ortamda her iki platformda da aynı komut kullanılır:

```text
python -m pytest backend/tests -q
```

Yukarıdaki macOS locale notu yalnız belirtilen bozuk host/Conda birleşimine
özgüdür; standart macOS Python ve Windows ortamlarında ek env-var gerekmez.

## Backend Çalıştırma

Backend API sunucusunu başlatmak için:
```text
python -m uvicorn backend.app.main:app --reload
```
URL: `http://localhost:8000`
Swagger Dokümantasyonu: `http://localhost:8000/docs`

## Frontend

Kullanıcı arayüzünü çalıştırmak için:
```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```
URL: `http://localhost:5173`

## Testler

Backend test komutu yukarıdaki “Test çalıştırma” bölümünde macOS ve Windows
için ortaktır.

Frontend Derleme Testi:
```powershell
cd frontend
npm run build
```


## Veri Ekleme
Sistemdeki verilerin yerleşim düzeni:
- Normal evraklar: `data/raw/`
- Mevzuat belgeleri: `data/regulations/`
- Evaluation (değerlendirme) setleri: `data/evaluation/`
- Sentetik veriler: `data/synthetic/`

> RAG sistemine dahil edilen veriler ile değerlendirme seti (evaluation) kesinlikle birbirine karıştırılmaz. Tüm detaylar için `data/README.md` dosyasını inceleyin.

## Önemli Veri Kuralları
- `statute_chunks.csv` dosyası zaten chunk edilmiştir, **tekrar chunk edilmez.**
- `qa_benchmark_gold.csv` yalnızca değerlendirme (evaluation) amaçlıdır, **RAG corpus'a eklenmez.**
- `synthetic/debug` verileri **RAG'e eklenmez.**
- **Gerçek vatandaş verisi (PII) public repository'ye eklenmez.**
- Full indexing gelişigüzel çalıştırılmaz. (Kısmi indeksler sistem durumu sayfasında açıkça belirtilir).

## Indexing
Örnek indeksleme komutu (Sadece ilgili kanunu vektörize eder):
```powershell
python scripts/index_qdrant.py --mode law --law-number 4982 --batch-size 16
```
> `--mode all` komutu yalnız bilinçli olarak son full-index aşamasında çalıştırılmalıdır.

## Git Çalışma Düzeni
Önerilen geliştirme branch'leri:
- `feature/ai-rag`
- `feature/data-ocr`
- `feature/backend`
- `feature/frontend`

---

## Açık Kaynak Lisansı
KAMUAI ekibi tarafından geliştirilen kaynak kodları Apache License 2.0 kapsamında lisanslanmaktadır. Üçüncü taraf bileşenler, yapay zekâ modelleri ve veri kümeleri kendi lisans ve kullanım koşullarına tabidir. Detaylar için `LICENSE` dosyasına bakınız.

## Kullanılan Yapay Zekâ Modelleri
Sistemimizde kullanılan dil ve gömme modellerinin detayları, kaynakları ve lisansları `docs/YAPAY_ZEKA_MODELLERI.md` içerisinde belirtilmiştir.

## Üçüncü Taraf Bileşenler
Kullandığımız açık kaynak kütüphaneler ve çerçeveler `docs/UCUNCU_TARAF_BILESENLER.md` dosyasında belgelenmiştir.

## Veri Kaynakları
Mevzuat, örnek evrak ve sentetik datasetlerimizin telif/lisans hakları için `docs/VERI_KAYNAKLARI.md` dosyasına bakınız. Yeni veri eklerken `docs/VERI_EKLEME_REHBERI.md` dosyasındaki talimatlara uyun.

## Bilimsel Kaynaklar ve Atıflar
Projenin mimarisi ve Ar-Ge süreci akademik çalışmalardan beslenmektedir. Kullanılan makaleler ve RAG mimari referansları `docs/KAYNAKLAR.md` içerisindedir.

## Veri Gizliliği
Github reposunda hiçbir gerçek vatandaş verisi, imza veya özel iletişim bilgisi bulunmamaktadır. Tüm demo ve test dosyaları sentetik olarak üretilmiş veya maskelenmiştir. 

## Model Ağırlıkları Hakkında
Üçüncü taraf yapay zekâ model ağırlıkları (safetensors, gguf, bin vb.) boyutları ve lisans uygunlukları nedeniyle **KAMUAI repository'sine dahil edilmemiştir.** Modeller ilgili platformlardan (Ollama/HuggingFace) çekilerek kullanılmaktadır.
