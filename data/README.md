# KAMUAI Veri Yönetimi

Bu klasör, projenin OCR, RAG (Retrieval-Augmented Generation) ve test (Evaluation) süreçleri için gereken verilerin tutulduğu ana dizindir.

## Klasör Yapısı ve Amacı

- **`data/raw/`**: Sistem tarafından işlenecek normal, yapılandırılmamış belge kaynaklarının (ör. kurum içi rehberler, taranmış pdf'ler) bulunduğu dizindir.
- **`data/regulations/`**: Resmi mevzuat belgeleri, kanunlar ve yönetmeliklerin tutulduğu yerdir.
- **`data/processed/`**: `ingestion` (veri alma) servisinden geçen, temizlenen ve chunklara (vektörel metin parçalarına) ayrılan çıktıların saklandığı klasördür. Repository'ye koymak zorunlu değildir; pipeline ile kaynak veriden yeniden üretilebilir.
- **`data/evaluation/`**: Benchmark testleri için hazırlanan "Gold" soru-cevap veri setleridir. **Bu klasördeki veriler RAG sistemine indekslenmez.**
- **`data/synthetic/`**: Agent davranışlarını güvenli ortamda test edebilmek için LLM aracılığıyla sentetik olarak türetilen kontrollü veriler. (Kişisel veri içermez, RAG'e indekslenmez.)
- **`data/routing/`**: Yönlendirme agent'ının kullanacağı kurumsal birim tanımlarını içeren statik JSON/CSV kaynaklarıdır.

## Veri Ekleme Kuralları (Ekip Üyeleri İçin)
Lütfen repository'ye yeni bir dosya eklemeden önce şu adımları izleyin:

1. **Veri türünü belirleyin:** Mevzuat ise `regulations`, sentetik test ise `synthetic`, benchmark ise `evaluation` altına ekleyin.
2. Uygun klasöre yerleştirdikten sonra varsa README dosyasını güncelleyerek verinin kaynağını (provenance) dokümante edin. (Bkz. `docs/VERI_EKLEME_REHBERI.md`)
3. **Gizlilik Kontrolü:** İçerikte gerçek vatandaş bilgisi (PII) kalmadığından emin olun.
4. Gerekli ise, ingestion pipeline'ı çalıştırarak yeni veriyi chunk formatına çevirin.
5. Yeni chunk'ların kalitesini manuel olarak gözden geçirin.
6. Yalnızca gerekliyse RAG'e dahil etmek için selective Qdrant indekslemesi çalıştırın.
7. Benchmark testlerini (evaluation) çalıştırıp model performansını test ettikten sonra geliştirme yapın.

## ⚠️ Önemli Uyarılar

1. `statute_chunks.csv`: Bu dosya zaten parçalanmış (pre-chunked) durumdadır. Yeniden chunk işleminden geçirilmemelidir!
2. `qa_benchmark_gold.csv`: Sadece ve sadece değerlendirme (evaluation) içindir. RAG'e eklenirse sistem modeli ezberleyeceği (data leakage) için testler geçersiz kalır.
3. `synthetic/debug`: `rag_eligible=false` olarak işaretlenmiştir. RAG'e eklemeyin.
4. **Kısmi İndeksler (Partial Index):** Qdrant vektör veritabanındaki resmi evrak ve mevzuat indeksi (storage alanı çok büyük olduğu için) kısmi olabilir. Sistemin ana menüsündeki "Sistem Durumu" sayfasından güncel indekslenen parça (point) sayısını doğrulayabilirsiniz.
