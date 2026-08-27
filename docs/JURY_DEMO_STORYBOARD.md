# EVRAG — Jüri Demo Storyboard (3 Dakika)

> **Giriş Cümlesi:**
> "EVRAG, belediyeye gelen evrakı sadece analiz etmiyor — doğru birime havale edilebilir,
> ilgili göreve dönüştürülebilir, eksik bilgisi doğru muhataptan istenebilir
> ve sonuçlandırılabilir bir kurumsal işe dönüştürüyor."

---

## ZAMAN ÇİZELGESİ

### 0:00 – 0:20 — Yazı İşleri Dashboard

**Ekran:** Ana sayfa → `Ayşe Kaya` (Yazı İşleri, EVRAK_KAYIT) ile giriş

**Göster:**
- Sol üst: **EVRAG EVRAKTAN İŞLEME** tagline
- KPI kutuları: Yeni Evrak / Havale Bekleyen / Eksik Bilgi / Manuel Karar
- **Demo Senaryoları** paneli: 5 golden case listesi

**Söyle:**
> "Gelen kutusu. Bugün belediyeye gelen 5 evrak var.
> Sisteme bilgisayar gibi bakıyoruz: her biri farklı birim, farklı işlem, farklı muhatap."

---

### 0:20 – 0:45 — Case 1: Kaldırım Şikayeti → Akıllı İşlem Planı

**Eylem:** `yol_onarim` senaryosunu hazırla → Case Workspace aç

**Göster:**
```
EVRAG AKILLI İŞLEM PLANI
  Fen İşleri Müdürlüğü
  LEVEL 1: Yazı İşleri → Fen İşleri
  LEVEL 2: Fen İşleri → Saha Bakım Ekibi → Tekniker

  Öncelik: Yüksek (Yayalar için düşme tehlikesi)
  Görev:   Yol bakım / saha incelemesi
  Saha:    GEREKLİ
  Eksik:   Yok
```

**Vurgula:**
- Üst header'da: *"Kimden geldi / Nerede / AI ne öneriyor"* — 3 saniyede cevap
- İşlem planı AI analiz kartlarının üstünde, sayfanın ilk şeyi

**Söyle:**
> "Evrak girer girmez sistem bize şunu söylüyor:
> Bu iş Fen İşlerine gidecek, Saha Bakım Ekibine, Tekniker rolüyle.
> Fiziksel saha incelemesi gerekiyor."

---

### 0:45 – 1:00 — Havale: İnsan Kararı

**Eylem:** `[FEN İŞLERİ MÜDÜRLÜĞÜNE HAVALE ET]` butonuna tıkla → Confirm dialog

**Göster:**
- Confirm modal: "Kurumsal sorumluluk aktarılacak"
- Onay ver → Case status: `IN_DEPARTMENT`

**Söyle:**
> "AI önerir. İnsan onaylar.
> Havale butonu olmadan hiçbir şey hareket etmiyor."

---

### 1:00 – 1:20 — Fen İşleri Dashboard

**Eylem:** Üst bardan `Mehmet Demir` (Fen İşleri, BIRIM_PERSONELI) rol geçişi

**Göster:**
```
FEN İŞLERİ ÇALIŞMA MASASI
  Yeni Gelen: 1   Saha İncelemesi Gereken: 1

  BUGÜNÜN İŞLERİ — Evrak değil, tamamlanacak görevler:
  ├─ Cumhuriyet Mah. Gül Sokak — Asfalt Çökmesi
  │   → Dosyayı işleme al
```

**Vurgula:** Yazı İşleri'nden farklı — "Evrak değil GÖREV odaklı görünüm"

**Söyle:**
> "Fen İşleri gelen kutusuna baktığında evrak metni değil, ne yapması gerektiğini görüyor."

---

### 1:20 – 1:40 — Birim İçi Görev Ataması

**Eylem:** Case Workspace'te `İşleme Al` → Birim İçi Görevlendirme bölümü

**Göster:**
```
BİRİM İÇİ GÖREVLENDIRME
  Ekip:   Saha Bakım Ekibi
  Rol:    Tekniker
  Görev:  Yol bakım / saha incelemesi
  Durum:  ASSIGNMENT_PENDING (insan ataması bekleniyor)

  ⚠ EVRAG ekip ve rol önerir; gerçek personeli otomatik seçmez.
```

**Söyle:**
> "Sistem ekibi ve rolü öneriyor. Gerçek personel ataması insan kararı —
> AI bunu asla kendi başına yapmıyor."

---

### 1:40 – 2:00 — Case 2: Konum Eksik → Doğru Muhatap

**Eylem:** `Ayşe Kaya`'ya geri dön → `eksik_adres` senaryosunu aç

**Göster:**
```
EKSİK BİLGİ ÇÖZÜMÜ
  Eksik:          Olay konumu
  Neden gerekli?: Saha incelemesi yapılamaz
  Kimden alınmalı?: Başvuru sahibi (VATANDAS)
  Önerilen işlem: Konum bilgisi talep et

  [Vatandaştan Konum Bilgisi İste]
```

**Vurgula (kırmızı kutu / zoom):** "Kimden alınmalı: Başvuru sahibi"

**Söyle:**
> "EVRAG eksik bilgiyi yalnız bulmuyor —
> **kimden alınması gerektiğini de belirliyor.**
> Kurumlar arası yazıda vatandaşa dönmez; gönderen kuruma döner."

---

### 2:00 – 2:25 — İşlem Sonucu → Grounded Cevap Taslağı

**Ayşe'ye geri dön → `yol_onarim` case → Fen İşleri işlemi tamamlandı sonrası**

**Eylem:** Kurum işlem sonucunu kaydet:
```
İşlem Türü: Saha İncelemesi
Sonuç:      Cumhuriyet Mah. Gül Sokak yerinde incelendi.
            Asfalt deformasyonu tespit edildi.
Karar:      Bakım programına alındı.
```

**Ardından yazı taslağını göster:**
```
RESMÎ CEVAP TASLAGI
  Konu: Yol Onarım Talebiniz Hk.
  [Vatandaşın talebi] doğrultusunda saha incelemesi yapıldı.
  Tespit sonucu bakım programına alınmıştır.

  ℹ Taslak yalnızca kayıtlı işlem sonucundan üretilmiştir.
```

**Söyle:**
> "Taslak tamamen kayıtlı insan kararından geliyor.
> AI 'onarım tamamlandı' demez; sadece kaydedilen gerçeği düzenler."

---

### 2:25 – 2:45 — Timeline

**Göster:**
```
DOSYA ZAMAN ÇİZELGESİ
  ✓ Evrak sisteme alındı
  ✓ EVRAG analizi tamamlandı
  ✓ Yazı İşleri → Fen İşleri havalesi insan tarafından onaylandı
  ✓ Fen İşleri saha bakım ekibi görevi oluşturuldu
  ✓ Birim işlem sonucu kaydedildi
  → Resmî yazı taslağı oluşturuldu
```

**Söyle:**
> "Her adım kayıt altında. İnsan mı yaptı, AI mi önerdi — ayrımı açık."

---

### 2:45 – 3:00 — Final Kapanış

**Göster:** Case 5 (Dış Kurum) → source_type badge: `DIS_KURUM`

**Söyle:**
> "Son 10 saniye.
> Bu sistem vatandaş dilekçesini de,
> Kaymakamlık resmi yazısını da,
> konum eksik şikayeti de,
> ruhsat başvurusunu da —
> hepsini **farklı birim, farklı işlem, farklı muhatap** olarak sonuçlandırıyor.
>
> **EVRAG evrakı sadece okumuyor;
> belediye içinde sonuçlandırılabilir bir işe dönüştürüyor.**"

---

## TEKNİK JÜRİ SORULARINA KISA CEVAPLAR

### Neden LLM her kararı vermiyor?

LLM belirsizlik altında yanlış birim önerebilir. Routing, eksik alan tespiti ve öncelik belirleme deterministik süreç profillerinden (YAML) yapılır; LLM yalnız özet ve taslak üretiminde kullanılır.

### Missing fields neden process profile ile belirleniyor?

"Adres eksik mi?" sorusu belge türüne değil *sürece* bağlıdır: saha şikayeti → konum zorunlu; bilgi edinme başvurusu → fiziksel adres zorunlu değil. Bu mantık `process_profiles.py`'da kodlanmıştır, LLM'e bırakılmaz.

### Routing skoru probability mi?

Hayır. Skor, kurum profilindeki anahtar kelime eşleşmesi + intent uyumu + belge türü ağırlığından oluşan deterministik bir sayıdır. "0.87 olasılıkla fen işleri" gibi bir hukuki iddia içermez.

### AI neden otomatik havale yapmıyor?

Kurumsal sorumluluk transferi (havale) hatalara açık ve geri alınamaz bir kamu işlemidir. Her havale, görev atama, resmi yazı gönderme ve final onay insan `confirmed=True` parametresi olmadan gerçekleşmez — `engine.route_case` API'sinde zorunlu.

### Kuruma nasıl özelleştiriliyor?

`data/institutions/{kurum}/kurum_profili_{kurum}.yaml` dosyası birimler, anahtar kelimeler, evrak türleri ve desteklenen süreçleri tanımlar. Yeni kurum = yeni YAML dosyası.

### Aynı core başka belediyeye nasıl uyarlanır?

Yeni bir `kurum_profili.yaml` yazılır; backend ve frontend `institution_id` parametresiyle çalışır. Core logic değişmez.

### Hukuki hallucination nasıl engelleniyor?

Hukuki analiz RAG tabanlıdır: yalnız indexlenmiş mevzuat belgelerinden alıntı üretilir. `citation` alanı boşsa "doğrulanamadı" gösterilir, uydurma citation üretilmez. Deadline "hukuki kesinlik" iddiası içermez; yalnız kaynağa dayalı süre gösterilir.

### İnsan onayı nerelerde var?

1. Havale (route): `confirmed=True` + kullanıcı butonu
2. Görev ataması: personel seçimi insan yapar
3. Resmî yazı gönderme: draft approve → insan onayı
4. Final onay: `WAITING_FINAL_APPROVAL` statüsü
5. İşlem sonucu: doğrulanmış veri olarak manuel girilir

### EBYS entegrasyonu nasıl yapılabilir?

`source_channel=EBYS` alanı mevcut. EBYS API webhook'u `POST /api/documents/analyze-text` veya `/api/documents/upload` endpoint'ine entegre edilir. Case yaratımı `intake.py` üzerinden gerçekleşir.

### Evrakın sahte olduğunu kesin tespit ediyor musunuz?

**Hayır.** Sistem sahte evrak hakkında kesin hüküm vermez. Tutarsızlık, eksik imza, format anomalisi gibi sinyalleri `risk_level` olarak çıkarır ve insan incelemesine sunar. Son karar her zaman personelin.

---

## DEMO KULLANICI HESAPLARI

| Kullanıcı | Rol | Kurum | Birim |
|---|---|---|---|
| `ayse_kaya` | EVRAK_KAYIT | Belediye | Yazı İşleri |
| `mehmet_demir` | BIRIM_PERSONELI | Belediye | Fen İşleri |
| `selin_aksoy` | EVRAK_KAYIT | Kaymakamlık | Yazı İşleri |
| `murat_celik` | BIRIM_PERSONELI | Kaymakamlık | Millî Eğitim |

Demo girişi: `POST /api/auth/demo-login` `{"user_key": "ayse_kaya"}`

---

## DEMO HAZIRLAMA

```bash
# Backend (DEMO_MODE=true gerekli)
python -m uvicorn backend.app.main:app --reload

# Frontend
cd frontend && npm run dev

# Demo senaryolarını hazırla (tek tıkla)
# → RoleHomePage → Demo Senaryoları → [Senaryoyu Hazırla]

# Veya API üzerinden:
POST /api/demo/scenarios/yol_onarim/prepare   (ayse_kaya token)
POST /api/demo/scenarios/eksik_adres/prepare
POST /api/demo/scenarios/belirsiz_ruhsat/prepare
POST /api/demo/scenarios/cop_temizlik/prepare
POST /api/demo/scenarios/dis_kurum_afet/prepare
```

> **Not:** Demo fixture olduğu `DemoScenarioCenter` panelinde açıkça belirtilir.
> Reset: `POST /api/demo/scenarios/reset`
