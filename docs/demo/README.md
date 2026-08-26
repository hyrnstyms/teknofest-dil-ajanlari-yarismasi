# KAMUAI Demo Evrakları

Bu klasördeki belgeler sentetiktir; gerçek kişisel veri içermez. Sonuçlar uygulamada hard-code edilmemiştir.

## Kaymakamlık

Dosya: `kaymakamlik_egitim_dilekcesi.txt`

- Expected classification: `dilekce`
- Expected intent: `bilgi_talebi`
- Expected routing: `İlçe Millî Eğitim Müdürlüğü`
- Expected legal behavior: yalnız doğrulanmış kaynak varsa citation; aksi halde güvenli legal fallback
- Expected draft/review: doğrulanmış alanlarla kontrollü taslak, personel incelemesi korunur

## Belediye

Dosya: `belediye_yol_dilekcesi.txt`

- Expected classification: `dilekce`
- Expected intent: `basvuru`
- Expected routing: `Fen İşleri Müdürlüğü`
- Expected legal behavior: ilgili doğrulanmış hüküm yoksa güvenli fallback; mevzuat uydurulmaz
- Expected draft/review: yol onarım talebine dayalı kontrollü taslak, personel incelemesi korunur

## Demo mesajı

Aynı agent altyapısı, seçilen kurum profiline göre birim, routing ve süreç bağlamını değiştirir.