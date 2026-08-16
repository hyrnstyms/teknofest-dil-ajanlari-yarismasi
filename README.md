# KAMUAI

## Proje Nedir?
KAMUAI, kamu evrakları için geliştirilmiş yapay zekâ tabanlı bir karar destek sistemidir. Gelen resmi evrakların analiz edilmesi, eksik bilgilerin tespiti, uygun birime yönlendirilmesi ve taslak metin oluşturulması süreçlerini otonom agent'lar yardımıyla gerçekleştirir.

Ana Akış:
Belge → Ingestion/OCR → Document Agent → Extraction Agent → Legal Agent → Missing Field Agent → Summary Agent → Routing Agent → Writing Agent → Quality Agent → Personel İncelemesi

## Temel Teknolojiler
- Python 3.11
- FastAPI
- LangGraph
- Ollama
- qwen2.5:3b-instruct
- BAAI/bge-m3
- Qdrant
- React
- TypeScript
- Vite

## İlk Kurulum

Windows / PowerShell için gerekli kurulum adımları:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Çevresel değişkenleri yapılandırmak için örnek dosyayı kopyalayın:
```powershell
Copy-Item .env.example .env
```

Yapay zekâ modelini Ollama ile indirin:
```powershell
ollama pull qwen2.5:3b-instruct
```

> **Not:** Sistem vektör veritabanı olarak Qdrant'ı kullanır. Qdrant'ın arka planda `localhost:6333` üzerinden erişilebilir durumda çalıştığından emin olun.

## Backend Çalıştırma

Backend API sunucusunu başlatmak için:
```powershell
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

Backend (Mevcut baseline: 59 passed):
```powershell
python -m pytest backend/tests -q
```

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
