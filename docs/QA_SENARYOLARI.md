# KAMUAI Demo QA Senaryoları

Test tarihi: 26 Ağustos 2026  
Aktif kurum bağlamı: `kaymakamlik` (mevcut analiz API'sinin varsayılanı)

Bu dosyadaki beklenen sonuçlar canlı çağrılar yapılmadan önce yazılmıştır.
Kişi, adres ve kimlik bilgileri yalnızca kurgusal test verisidir.

## Önceden belirlenen beklentiler

| # | Senaryo | Girdi | Beklenen evrak türü | Beklenen birim | Beklenen eksik alan | Beklenen mevzuat | Beklenen taslak tipi |
|---|---|---|---|---|---|---|---|
| 1 | Düzgün dilekçe | Kurgusal öğrencinin adres değişikliği nedeniyle okul nakli talebi; ad, adres, kimlik, konu, talep, tarih ve imza mevcut | `dilekce` | `milli_egitim` | Yok | 3071 sayılı Kanun veya doğrulanmış ilgili eğitim mevzuatı; kanıt yoksa “bulunamadı” | `cevap_yazisi` veya güvenli `ust_yazi` |
| 2 | Eksik bilgili dilekçe | Gürültü şikâyeti ve inceleme talebi var; başvuran adı, adresi, tarih ve imza yok | `dilekce` | `emniyet` veya eşitlikte insan incelemesi | En az `sender_name`, `address`, `date`, `signature` | Doğrulanmış ilgili kaynak; kanıt yoksa “bulunamadı” | Eksik bilgi nedeniyle `eksik_bilgi_talebi` veya güvenli taslak üretmeme |
| 3 | Yanlış/uygunsuz kurum başvurusu | Belediye yetkisindeki yol çukuru ve asfalt onarımı talebi Kaymakamlık bağlamına gönderilir | `dilekce` | Kaymakamlık birimine güvenli eşleşme yoksa `null`; aksi durumda insan incelemesi | Yok | Doğrulanmış kaynak yoksa “bulunamadı” | Kurumlar arası iletim gerekiyorsa `ust_yazi`; aksi halde güvenli taslak üretmeme |
| 4 | Mevzuat gerektiren başvuru | 4982 sayılı Kanun kapsamında bilgi edinme başvurusuna cevap süresi sorulur | `bilgi_edinme` | `yazi_isleri` | Yok | 4982 sayılı Kanun, cevap süresi için Madde 11 | `cevap_yazisi` |
| 5 | OCR gerektiren taranmış belge | Mevcut temiz OCR fixture'ı: `data/evaluation/ocr/temiz/SENT-0003_temiz.png` | OCR metnine göre sınıflandırılmış gerçek tür | OCR metnine göre doğrulanmış birim veya insan incelemesi | OCR metninde bulunmayan zorunlu alanlar | OCR metniyle ilgili doğrulanmış kaynak; kanıt yoksa “bulunamadı” | İçeriğe uygun güvenli taslak veya taslak üretmeme |

## Canlı test sonuçları

| # | HTTP sonucu / analiz ID | Gerçek tür | Gerçek birim | Gerçek eksik alanlar | Gerçek mevzuat | Gerçek taslak tipi | Sonuç |
|---|---|---|---|---|---|---|---|
| 1 | HTTP 200 — `f2708364-0f20-4bbe-b2df-3c88a8e229b3` | `dilekce` / `basvuru` | İlçe Millî Eğitim Müdürlüğü, skor 70 | Eksik yok; `signature_present` belirsiz | 0 kanıt; RAG `WinError 10061` | Üretilmedi | **FAIL** — tür/birim doğru, mevzuat ve taslak yok |
| 2 | HTTP 200 — `6c7c85ca-6e6e-4574-b7fe-60012d0e3270` | `dilekce` / `sikayet` | Yazı İşleri Müdürlüğü, skor 50 | `person_name`, `address`; imza belirsiz | 0 kanıt; RAG `WinError 10061` | Üretilmedi | **FAIL** — eksikler kısmen doğru; beklenen yönlendirme ve taslak yok |
| 3 | HTTP 200 — `17c2b794-6cab-442d-946e-61a371b4b5ff` | `dilekce` / `basvuru` | `null`, skor 0, insan incelemesi | Eksik yok; imza belirsiz | 0 kanıt; RAG `WinError 10061` | Üretilmedi | **PASS** — uygunsuz kurum başvurusu güvenli biçimde yönlendirilmedi |
| 4 | HTTP 200 — `4c5fb1fb-f582-4b47-bcf4-1c1636284678` | `dilekce` / `bilgi_talebi` | `null`, skor 0, insan incelemesi | Eksik yok; imza belirsiz | 0 kanıt; RAG `WinError 10061`; Madde 11 yok | Üretilmedi | **FAIL** — tür, birim, mevzuat ve taslak beklentileri karşılanmadı |
| 5 | HTTP 500 — analiz ID oluşmadı | Oluşmadı | Oluşmadı | Kontrol edilemedi | Kontrol edilemedi | Üretilmedi | **FAIL** — backend `ocr_error`: “Belge OCR ile okunamadı.” |

Toplam: **1 PASS, 4 FAIL**. HTTP 200 dönmesi tek başına başarı sayılmamış,
beklenen iş çıktılarının tamamı karşılaştırılmıştır.

## Çıktı kontrolleri

- DOCX: Senaryo 1 için gerçek
  `GET /api/analysis/f2708364-0f20-4bbe-b2df-3c88a8e229b3/export/docx`
  isteği yapıldı. Sonuç: **HTTP 200**,
  `application/vnd.openxmlformats-officedocument.wordprocessingml.document`,
  `attachment; filename=resmi_yazi_taslak.docx`, **38.324 bayt**.
- Print/PDF: Üretim CSS'inde A4 sayfa ölçüsü ve yalnızca belgeyi yazdıran
  `@media print` kuralları üretim build'iyle doğrulandı. Tarayıcının işletim
  sistemi yazdırma penceresinde fiziksel PDF oluşturmak manuel kontroldür; bu
  oturumda GUI yazdırma penceresi otomatikleştirilmedi.

## Bulgular

1. Backend analiz endpoint'i ve EVREN çalışıyor; Senaryo 1 belge çıktısı
   sağlayıcıyı `evren`, modeli `llm-fast` olarak raporladı.
2. Dört metin senaryosunda LegalAgent yerel RAG/Qdrant yolunda
   `WinError 10061` verdi. RAG/Qdrant yapılandırmasına müdahale edilmedi.
3. WritingAgent doğrulanmış mevzuat kanıtı olmayınca taslak üretmedi. DOCX
   endpoint'i teknik olarak çalışsa da Senaryo 1 analizinde taslak metni yoktur.
4. Temiz OCR fixture'ı upload endpoint'inde `ocr_error` ile reddedildi. OCR
   bileşenine veya verisine müdahale edilmedi.

## Görev 4

**BEKLİYOR.** `GET /api/admin/stats`, `GET /api/verify/{id}`,
öncelik/zincir/maskeleme ve audit alanları Kişi 1'in backend çalışması merge
edilmeden bağlanmayacaktır.
