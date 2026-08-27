# EVRAG Resmî Yazı İş Akışı

EVRAG resmî yazıyı tek bir analiz çıktısı olarak değil, Case yaşam döngüsüne bağlı ve insan denetimli bir kurumsal kayıt olarak yönetir.

## Sözleşme

1. Gelen belge Case kaydına bağlanır.
2. AI analizi belge türü, süreç amacı, çıkarılan bilgiler, eksikler, mevzuat ve yönlendirme önerisini üretir.
3. Eksik bilgi varsa `MISSING_INFORMATION_REQUEST`; süreç bilgisi gerekiyorsa `INTERIM_INFORMATION` hazırlanabilir.
4. Evrak kayıt personeli yönlendirmeyi onayladığında hedef birime adresli `FORWARDING_COVER_LETTER` aynı Case altında oluşturulur.
5. Hedef birim vakayı işleme alır ve gerçek kurum tespit/kararını DepartmentAction olarak kaydeder.
6. Yalnız aynı Case'e ait doğrulanmış DepartmentAction sonrasında `OFFICIAL_RESPONSE` oluşturulur. Muhatap mevcut birim değil, Case originator bilgisidir.
7. Personel konu, muhatap ve gövdeyi doğrudan düzenleyebilir. Her kayıt yeni revision ve `EDITED` durumudur; doğrulanmış DepartmentAction değiştirilemez.
8. Yeniden oluşturma yalnız güncel doğrulanmış Case verisini kullanır ve önceki sürümü silmez.
9. İnsan onayından sonra yazı `APPROVED` olur; DOCX/PDF export ve QR doğrulama açılır.

## Yazı türleri

- `MISSING_INFORMATION_REQUEST`: eksik bilgi talebi
- `INTERIM_INFORMATION`: ara/süreç bilgilendirmesi
- `FORWARDING_COVER_LETTER`: birimler arası yönlendirme üst yazısı
- `INTERNAL_MEMO`: kurum içi yazışma
- `OFFICIAL_RESPONSE`: vatandaş veya dış kurum originator'ına nihai resmî cevap

## Yetki ve görünürlük

Backend kurum, rol ve mevcut birim kapsamını bearer token üzerinden belirler. Birim personeli yalnız kendi biriminin sahip olduğu vakaların yazılarını görür ve düzenler. Evrak kayıt personeli kendi birimindeki veya bizzat yönlendirdiği vakaların yazılarını görebilir. Frontend rol veya kurum yetkisi üretmez.

## Ürün yüzeyleri

- **Dosya Çalışma Alanı:** Genel Bakış, AI Analiz Raporu, Resmî Yazılar ve İşlem Geçmişi.
- **Resmî Yazılar:** Yetkili vakalardaki taslak, düzenleme ve onay kuyruğu.
- **AI Operasyonları:** Yalnız teknik hazırlık, ajan pipeline ve değerlendirme; taslak editörü içermez.

Güvenlik ilkesi: AI taslağı kurum işlemi değildir. Nihai cevap, doğrulanmış insan işlemi olmadan hazırlanamaz ve insan onayı olmadan dışa aktarılmaz.
