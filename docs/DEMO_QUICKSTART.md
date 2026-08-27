# EVRAG Demo Quickstart

## Hazırlık

1. `.env.example` dosyasını temel alarak yerel ayarları hazırlayın; gerçek sırları repoya yazmayın.
2. Demo yardımcıları için `DEMO_MODE=true` ayarlayın.
3. Backend'i `uvicorn backend.app.main:app --reload` ile, frontend'i `npm.cmd --prefix frontend run dev` ile başlatın.
4. `/ready` ekranında seçili LLM sağlayıcısı, Qdrant ve embedding durumunu kontrol edin. Model çağrısı gerektirmeyen demo seed ve Case akışları bu servislerden bağımsızdır.

## Persona ve senaryo

- Ayşe Kaya: Belediye · Yazı İşleri · evrak kayıt.
- Mehmet Demir: Belediye · Fen İşleri · birim personeli.
- Selin Aksoy: Kaymakamlık · Yazı İşleri · evrak kayıt.
- Murat Çelik: Kaymakamlık · İlçe Millî Eğitim · birim personeli.

Evrak kayıt ana sayfasındaki **Demo Senaryoları** kartından Yol Onarım, Belirsiz Ruhsat, Kaymakamlık veya Eksik Adres senaryosunu hazırlayın. Bu işlem gerçek Case/Analysis/CitizenRequest kayıtları üretir. **Tüm demo verisini yenile** yalnız `DEMO:*` etiketi taşıyan kayıtları siler.

## Vatandaş görünümü

Case Workspace'teki **Vatandaş görünümü** butonu yalnız demo vakasında backend'den geçerli `tracking_code + token` bağlantısı alır. Sabit veya tahmin edilebilir üretim token'ı kullanılmaz; deterministik token yalnız `DEMO_MODE` kapsamındadır.

## Kayıt öncesi kontrol

- Belediye ve Kaymakamlık persona kartları görünüyor.
- Yol Onarım senaryosu Fen İşleri öneriyor.
- Birim işlemi kaydedilince cevap taslağı otomatik oluşuyor.
- A4 önizleme, insan onayı, DOCX ve PDF aynı Case Workspace içinde çalışıyor.
- Belirsiz Ruhsat vatandaş açıklaması olmadan zorla yönlendirilmiyor.
- Copilot başlığı EVRAG ve AI Operasyonları yalnız teknik gözlemlenebilirlik gösteriyor.
