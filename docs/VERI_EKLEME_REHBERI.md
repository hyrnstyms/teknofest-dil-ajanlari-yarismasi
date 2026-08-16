# Veri Ekleme ve Provenance Rehberi

Ekip üyeleri repository'ye yeni veri seti veya test belgeleri eklerken, verinin doğruluğunu, lisans uyumunu ve gizlilik kurallarını korumak için aşağıdaki süreci izlemelidir.

## 1. Veri Türünü Belirleme ve Ekleme
Verinin amacına göre ilgili klasöre yerleştirin:
- **Gerçek (Anonimleştirilmiş) Veriler:** `data/raw/`
- **Resmi Mevzuat / Kılavuzlar:** `data/regulations/`
- **Sentetik / Yapay Üretim Veriler:** `data/synthetic/`
- **Test ve Demo Amaçlı Örnekler:** `data/samples/`
- **Değerlendirme (Evaluation) Benchmarkları:** `data/evaluation/`

## 2. Zorunlu Metadata (Provenance)
Yeni bir veri kümesi eklediğinizde, ilgili klasördeki README veya meta verilerinde aşağıdaki bilgilerin yer aldığından emin olun:

- `source_name`: Verinin nereden alındığı (örn. T.C. Cumhurbaşkanlığı).
- `source_url`: Varsa açık erişim bağlantısı.
- `access_date`: Verinin çekildiği/indirildiği tarih.
- `license`: Verinin lisansı veya kullanım hakları.
- `usage_purpose`: KAMUAI içinde ne amaçla kullanılacağı.
- `contains_personal_data`: PII içerip içermediği (Sistemde kesinlikle `false` olmalıdır).
- `rag_eligible`: RAG vektör veritabanına indekslenip indekslenmeyeceği (`true` / `false`).
- `evaluation_only`: Benchmark verisi olup olmadığı.
- `preprocessing_notes`: Yapılan temizleme, anonimleştirme ve chunking işlemleri.

## 3. Gizlilik ve PII (Kişisel Veri) Kontrolü
Github'a push etmeden önce veride gerçek T.C. kimlik numarası, ad-soyad, gerçek adres, telefon numarası veya gizli kurum bilgisi olup olmadığını **iki kez** kontrol edin. Bütün gerçek veriler rastgele veya sentetik verilerle maskelenmelidir.

## 4. RAG Entegrasyonu (Sadece Gerekiyorsa)
Veri `rag_eligible` ise:
1. `ingestion` (veri yükleme) scriptini çalıştırın.
2. Vektör chunk'larını üretin ve kalitelerini gözden geçirin.
3. Selective (seçici) Qdrant indekslemesini çalıştırın (Otomatik Full-Index başlatmayın).
4. Yeni indeksin RAG sonuçlarını bozmadığını benchmark seti ile doğrulayın.
