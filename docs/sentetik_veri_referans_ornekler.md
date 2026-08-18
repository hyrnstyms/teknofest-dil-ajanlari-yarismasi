# Sentetik Evrak Üretimi — Referans Yapısal Kalıplar

Bu doküman, gerçek kaynaklardan (kaymakamlık web siteleri, resmî
dilekçe formları, .gov.tr uzantılı yayınlar) çıkarılan **yapısal
kalıpları** içerir. Hiçbir gerçek kişi/kurum verisi veya birebir metin
kopyalanmamıştır — sadece "hangi bölüm nerede, hangi sırayla" bilgisi
alınmıştır. LLM üretimi bu kalıplara göre yönlendirilecek.

## Kaynaklar

- T.C. Kabataş Kaymakamlığı — Örnek Dilekçe ve Formlar sayfası
- T.C. Almus Kaymakamlığı — Örnek Dilekçe ve Formlar sayfası
- MEB — Bilgi Edinme Başvurusu Formu (resmî, .gov.tr)
- Çeşitli kaymakamlık siteleri — şikayet/tecavüz, ruhsat başvurusu
  dilekçe örnekleri (yapısal referans olarak)

## Genel Dilekçe Yapısı (Tüm Türlerde Ortak İskelet)

1. **Üst kısım — Muhatap:** Kurum adı BÜYÜK HARF + hitap eki (örn.
   "...KAYMAKAMLIĞINA")
2. **Başvuran bilgileri:** Ad Soyad, T.C. Kimlik No, Adres, Telefon
   (bazı formlarda "BAŞVURAN:" başlığı altında, bazılarında dilekçe
   sonunda)
3. **Konu satırı:** Kısa, net — "KONU: [...] Talebi" kalıbı yaygın
4. **Açıklamalar (gövde):** Numaralandırılmış paragraflar:
   - Durumun/talebin tarifi
   - Varsa yasal dayanak atfı (kanun/yönetmelik madde numarası)
   - Varsa daha önceki başvuru/yazışma referansı (tarih + sayı)
5. **Talep cümlesi:** "...talep ediyorum/ederim", "...arz ederim",
   "...gereğini arz ederim" gibi kapanış
6. **Ekler:** Numaralandırılmış liste (varsa)
7. **Tarih ve imza**

## Evrak Türüne Göre Özel Kalıplar

### Vatandaş Dilekçesi (genel)
Yukarıdaki genel iskelet birebir uygulanır. Konu çeşitliliği yüksek
(izin, şikayet, talep). Şikayet türü dilekçelerde ek olarak "ŞİKAYET
EDEN" / "ŞİKAYET EDİLEN (varsa)" / "OLAYIN YERİ" gibi ayrı alanlar
görülebilir.

### Bilgi Edinme Başvurusu
Resmî form yapısı (MEB örneğinden): Ad Soyad, Adres, T.C. Kimlik No,
İmza + sabit bir kalıp cümle ("4982 sayılı Bilgi Edinme Hakkı Kanunu
gereğince istediğim bilgi veya belgeler aşağıda belirtilmiştir.
Gereğini arz ederim.") + açık uçlu "istenen bilgi/belge" alanı.
Formun serbest dilekçe biçiminde de yazılabileceği görülüyor, ama
formdaki alan sırası (kimlik + sabit kalıp + istenen bilgi tarifi)
üretimde referans alınmalı.

### Sosyal Yardım Başvurusu
Daha az resmî/katı bir kalıp; genellikle "Yardım Talebinin Sebepleri"
ve "Talep Edilen Yardım Türü" gibi iki ayrı bölüm içeriyor. Aile/gelir
durumu açıklaması yaygın bir unsur.

### İzin/Ruhsat Başvurusu (kurumlar arası yazışma ve ihale itirazı ile
### ilişkili konularda referans olarak kullanılabilir)
BAŞVURAN bilgileri + KONU ("...Ruhsatı Talebi" kalıbı) + AÇIKLAMALAR
(işyeri/faaliyet tarifi, yasal dayanak — genelde spesifik bir kanun
maddesine atıf) + EKLER (tapu, kira sözleşmesi, teknik belge gibi).

### Taşınmaz/Tapu Konulu Şikayet-Talep
"ŞİKAYET EDEN" / "MÜTECAVİZ" (karşı taraf, varsa) / "TAŞINMAZIN
MEVKİİ" gibi ek kimlik alanları + AÇIKLAMALAR bölümünde tapu/parsel
bilgisi ve önceki başvuru referansı (tarih + sayı) yaygın.

## Üretimde Kullanım Notu

Sentetik evrak üretiminde bu kalıplar **iskelet** olarak kullanılacak;
LLM içerik (isim, adres, olay detayı) tamamen kurgusal üretecek.
Gerçek kaynaklardaki hiçbir kişi adı, adres veya spesifik olay detayı
kullanılmayacak — sadece yapısal sıra ve tipik ifade kalıpları
(örn. "Gereğini arz ederim", "...talebimden ibarettir") referans
alınacak.
