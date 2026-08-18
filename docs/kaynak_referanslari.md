# Mevzuat Kaynak Referansları

Bu dosya, `data/raw/mevzuat/` klasöründeki her kaynağın nereden alındığını,
ne zaman indirildiğini ve hangi amaçla kullanılacağını belgeler.
Şartname madde 7'nin "kaynaklar bilimsel atıf kurallarına uygun
belirtilmeli" şartını karşılamak ve final raporun kaynakçasını
buradan türetebilmek için tutulur.

| Dosya | Kaynak (URL) | Erişim Tarihi | Hangi Ajan/Bileşen İçin |
|---|---|---|---|
| `resmi_yazisma_yonetmeligi.pdf` | mevzuat.gov.tr — Resmî Yazışmalarda Uygulanacak Usul ve Esaslar Hakkında Yönetmelik (RG 10.06.2020/31151, No. 2646) | 2026-08-06 | Format Motoru (Pipeline 2) — biçim kuralları kaynağı |
| `resmi_yazisma_kilavuzu.pdf` | tccb.gov.tr — Resmî Yazışma Kılavuzu (Cumhurbaşkanlığı, 2022 güncel sürüm) | 2026-08-06 | Format Motoru (Pipeline 2) — örnek şablonlar (Örnek 1-24) |
| `3071_dilekce_hakki_kanunu.pdf` | mevzuat.gov.tr — 3071 sayılı Dilekçe Hakkının Kullanılmasına Dair Kanun | 2026-08-09 | Ajan 4 (Mevzuat RAG) — dilekçe evrak türü yasal dayanağı |
| `4982_bilgi_edinme_kanunu.pdf` | mevzuat.gov.tr — 4982 sayılı Bilgi Edinme Hakkı Kanunu | 2026-08-09 | Ajan 4 (Mevzuat RAG) — bilgi edinme evrak türü yasal dayanağı |
| `5442_il_idaresi_kanunu.pdf` | mevzuat.gov.tr — 5442 sayılı İl İdaresi Kanunu | 2026-08-09 | Ajan 7 (Yönlendirme) — kurum profili (Pipeline 4) birim listesi dayanağı |

## Reddedilen Kaynaklar

Aşağıdaki kaynaklar değerlendirilmiş ancak güncel olmadığı/doğrulanamadığı
için kullanılmamıştır (bkz. `docs/format_kurallari_checklist.md`):

- `24193939_Resmi_Yazışma_Kuralları.pdf` — 2020 öncesi DETSİS-öncesi sayı
  formatı içeriyor, güncel yönetmelikle (Madde 11, Madde 37) çelişiyor.
- `669020121106121401.pdf` — metin içeriği taranamaz/boş durumda.

## Not

Yukarıdaki erişim tarihleri, dosyanın bilgisayara indirildiği tarihtir.
Final teslim öncesinde tüm kaynakların hâlâ güncel olduğu (yönetmelik
değişikliği olmadığı) bir kez daha teyit edilmelidir.
