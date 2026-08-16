# Veri Kaynakları

KAMUAI sisteminin Retrieval-Augmented Generation (RAG) indeksleme ve Evaluation (test/doğrulama) altyapısında kullanılan kaynaklar aşağıda dokümante edilmiştir.

| Veri Adı | Dosya / Klasör | Veri Türü | Kaynak | Lisans / Kullanım | RAG Dahil? | Sentetik? | PII (Kişisel Veri)? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Resmî Yazışma Kılavuzu** | `data/regulations/resmiyazışmakılavuzu.pdf` | Mevzuat/Rehber | T.C. Cumhurbaşkanlığı İdari İşler B. | Resmî/kamusal kaynaktan elde edilmiştir. Repository içinde yeniden dağıtım uygunluğu kaynak ve kullanım koşulları açısından nihai paylaşım öncesinde doğrulanmalıdır. | Evet | Hayır | Belirsiz |
| **Statute Chunks** | `data/raw/statute_chunks.csv` | Chunked Data | Külliyat / Mevzuat | Manuel Doğrulama Gerekli | Evet | Hayır | Belirsiz |
| **QA Benchmark Gold** | `data/evaluation/qa_benchmark_gold.csv` | Değerlendirme Seti | İç Üretim | Proje Özel | **Hayır (Eval-Only)** | Kısmen | Belirsiz |
| **Sentetik Dilekçeler** | `data/synthetic/*` | Metin Belgeleri | AI Destekli Üretim | Proje Özel | **Hayır** | Evet | Belirsiz |
| **Birim Tanımları** | `data/routing/*` | Yapılandırılmış Data | İç Üretim | Proje Özel | Kısmen | Hayır | Belirsiz |

## Önemli Veri Kuralları

- **Mevzuat Verisi:** `data/regulations` altındaki resmi belgelerin lisansları kamusal kullanım çerçevesinde değerlendirilmiştir. Ancak doğrudan scraping yapılan ek kaynakların telif hakları ekibe aittir.
- **RAG Ayrımı:** Değerlendirme setleri (`qa_benchmark_gold.csv`) ve sentetik hata ayıklama dosyaları kesinlikle RAG vektör indeksine dahil edilmez. Bu, benchmark sızıntısını (data leakage) engellemek içindir.
- **Kişisel Veriler:** Mevcut taramada belirgin kişisel veri tespit edilmemiştir; nihai paylaşım öncesi manuel kontrol önerilir. Bir veri setinin PII içerip içermediği dosya bazında titizlikle incelenmelidir.
