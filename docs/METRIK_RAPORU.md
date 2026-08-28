# Şartname Bölüm 9 — Metrik Raporu

> Ölçüm tarihi: 2026-08-28T04:50:02+03:00  
> Veri seti: `decision_boundary_120` — SHA-256 `319d74572806821a52534a96fa6672eefced58347860449297bc15e9f6c420e2`  
> Kod durumu: Git `d3820e1b4b5b1796252b523a1bfbfd9bfddcc061`; çalışma ağacı değişiklik içeriyor.

## Sunuma hazır sonuç tablosu

| Şartname Kriteri | Metrik | Sonuç |
|---|---|---|
| Sınıflandırma doğruluğu | `document_agent` geniş evrak türü exact accuracy | **117/120 — %97.50** |
| Yönlendirme başarımı | `routing_agent` Top-1 / Top-3 (yönlendirilebilir 85 vaka) | **Top-1 51/85 — %60.00; Top-3 76/85 — %89.41** |
| Eksik bilgi tespiti | `missing_field_agent` herhangi bir eksik alan var/yok doğruluğu | **72/120 — %60.00** (alan bazlı F1: **%12.50**) |
| Özetleme kalitesi | Altın konu/başlığın `short_summary` içinde korunması | **95/120 — %79.17** |
| Taslak/format kalitesi | `format_validator` hatasız (`gecerli=True`, uyarı olabilir) / doğrulanmamış sonuç iddiası yok | **120/120 — %100.00** format hatasız; **120/120 — %100.00** iddiasız |
| Gerçek zamana yakınlık | Tam workflow, 20 kayıt, sıralı duvar saati | **Ort. 5.009 sn; medyan 4.692 sn; en hızlı DB-030 (3.646 sn); en yavaş DB-079 (7.481 sn)** |

## Taslak kalitesi dağılımı

| Format sonucu | Adet | Oran |
|---|---:|---:|
| Uygun | 0 | %0.00 |
| Kontrol Gerekli | 120 | %100.00 |
| Hata | 0 | %0.00 |
| **Toplam** | **120** | **%100,00** |

Tamamen uyarısız `Uygun` sonucu **0/120 (%0.00)** düzeyindedir. Doğrulayıcı 120/120 taslağa uygulanabildi; bunların 120 tanesi format hatası üretmedi, 0 tanesi hata üretti. Uyarılı fakat `gecerli=True` sonuçlar üçlü dağılımda `Kontrol Gerekli`, hatasız-geçiş metriğinde ise hatasız sayılmıştır.

`Kontrol Gerekli` sınıfındaki 120 kaydın 120 tanesi doğrulayıcıdan hatasız fakat EBYS/personel alanı uyarılarıyla geçti; 0 tanesi desteklenen resmî yazı türlerinin dışında kaldığı için doğrulayıcı kapsamı dışındaydı. `Hata` vakaları: format hatası yok; üretilemeyen taslak yok.

Doğrulanmamış sonuç iddiası **0/120 (%0.00)** taslakta tespit edildi. Dolayısıyla **120/120 (%100.00)** taslakta bu uyarı yoktu. Kontrolün değerlendirilebilir olduğu kayıt sayısı 120/120; uyarı üreten vakalar: yok.

## Hesaplama yöntemi ve kapsam

- **İlk üç metrik yeniden üretilmiştir.** Sınıflandırma, yönlendirme ve eksik bilgi sonuçları bu birleşik koşudan hemen önce yeniden oluşturulan `reports/evaluation/decision_boundary_agents.json` dosyasından aynen alınmıştır; bu raporda yeniden yorumlanmamıştır.
- **Özetleme:** Her kaydın altın `title` alanı normalize edilip `short_summary` ile karşılaştırıldı. Başlık ifadesinin aynen bulunması, bilgilendirici başlık sözcüklerinin en az %60'ının bulunması veya RapidFuzz `token_set_ratio >= 75` ve `partial_ratio >= 80` koşullarının birlikte sağlanması başarıdır. Boş/üretilemeyen özet başarısız sayılır.
- **Format:** Resmî yazı türlerinde `official_render.context`, üretimde kullanılan deterministik `validate_format` fonksiyonuna verildi. Hatasız ve uyarısız sonuç `Uygun`; yalnız uyarı bulunan ya da doğrulayıcı kapsamı dışında kalan taslak `Kontrol Gerekli`; doğrulama hatası veya üretilemeyen taslak `Hata` sayıldı. Kapsam dışı taslaklar başarı hanesine yazılmadı. `gecerli=True` olup yalnız uyarı taşıyan taslaklar hatasız-geçiş metriğine dahil edildi, ancak `Uygun` kategorisine geçirilmedi.
- **Doğrulanmamış sonuç iddiası:** `quality_agent.checks.unverified_outcome_claim.status == fail` tespit olarak sayıldı. Workflow hatası olan kayıtlar korumacı biçimde 'iddiasız' sayılmadı.
- **Uçtan uca süre:** Dört veri kovasının her birinden sabit tohumla beşer kayıt seçildi. Kayıtlar paralel değil, sırayla çalıştırıldı. Duvar saati document, extraction, legal, missing-field, summary, routing, writing, quality ve workflow'un son human-review karar adımını kapsar.

## Ölçüm bütünlüğü

- 120 kayıtlık kalite koşusu: 0 workflow hatası, 0 düğüm-hatası içeren kayıt.
- 20 kayıtlık süre koşusu: 20 başarılı, 0 başarısız.
- Süre örneklemi: `DB-002, DB-015, DB-030, DB-032, DB-037, DB-044, DB-049, DB-052, DB-053, DB-059, DB-077, DB-079, DB-081, DB-082, DB-100, DB-103, DB-104, DB-107, DB-118, DB-119`.
- Ham ve kayıt-bazlı sonuçlar: `reports/evaluation/section9_metrics.json`.

## Yeniden üretme

```powershell
.venv\Scripts\python.exe scripts\evaluation\evaluate_decision_boundary_agents.py --workers 4
.venv\Scripts\python.exe scripts\evaluation\evaluate_section9_metrics.py
```

Script yolu: `scripts/evaluation/evaluate_section9_metrics.py`. Mevcut üç metriğin scripti: `scripts/evaluation/evaluate_decision_boundary_agents.py`.
