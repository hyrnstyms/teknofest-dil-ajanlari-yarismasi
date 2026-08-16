# Lisans Uyum ve Teknik Envanter Raporu

Bu rapor, KAMUAI projesinin TEKNOFEST ve açık kaynak yarışma kurallarına uygun olarak repository hazırlığı aşamasında çıkarılan teknik uyumluluk envanteridir. **(Hukuki bir görüş değildir, teknik bir analizdir.)**

## Kategori Tanımları
- **UYUMLU:** Lisans doğrulandı ve projedeki mevcut kullanım şekli lisansla uygun görünüyor.
- **DOKÜMANTE EDİLEREK KULLANILACAK:** Modele/veriye link verilir, ağırlıklar repository'ye konmaz (Örn: Model dosyaları).
- **MANUEL KONTROL GEREKLİ:** Lisansı net olmayan veya özel izin gerektiren üçüncü parti kütüphaneler/veriler.
- **REPOSITORY'YE EKLENMEMELİ:** Kişisel veriler, özel yapılandırmalar (.env), cache'ler ve model ağırlıkları.

---

## 1. Yapay Zeka Modelleri ve Ağırlıklar

| Bileşen | Durum | Açıklama |
| :--- | :--- | :--- |
| **Qwen2.5-3B-Instruct** | DOKÜMANTE EDİLEREK KULLANILACAK | Apache 2.0. Model ağılıkları (`*.safetensors`, `*.bin`, vb.) Git reposuna dahil edilmedi. |
| **BAAI/bge-m3** | DOKÜMANTE EDİLEREK KULLANILACAK | MIT Lisansı. HuggingFace cache dizinleri repository dışında tutulacak şekilde ayarlandı. |

## 2. Yazılım Kütüphaneleri ve Çerçeveler

| Bileşen | Durum | Açıklama |
| :--- | :--- | :--- |
| **React & Vite** | UYUMLU | MIT lisansı altındadır. Kod değişikliği yapılmadan `package.json` üzerinden kullanılmaktadır. |
| **FastAPI & LangGraph** | UYUMLU | MIT lisansı altındadır. `requirements.txt` üzerinden bağımlılık olarak kurulur. |
| **Qdrant (Local)** | UYUMLU | Apache 2.0. Yalnızca Docker veya yerel binary olarak çalışır, kod içine gömülmemiştir. |
| **PyMuPDF** | UYUMLU | GNU AGPL 3.0 / Commercial. API servisi arka planda çalıştığı için AGPL kısıtlamaları dâhilinde değerlendirilmiştir. (Açık kaynak sunumlar için uygundur). |

## 3. Veri Setleri ve Dosyalar

| Veri/Bileşen | Durum | Açıklama |
| :--- | :--- | :--- |
| **Resmî Yazışma Kılavuzu** | MANUEL KONTROL GEREKLİ | Resmî/kamusal kaynaktan elde edilmiştir. Repository içinde yeniden dağıtım uygunluğu kaynak ve kullanım koşulları açısından nihai paylaşım öncesinde doğrulanmalıdır. |
| **Sentetik Demo Verileri** | UYUMLU | Tamamen ekip tarafından üretilmiştir. Tüm telif hakları projeye aittir. |
| **Qdrant Storage (`qdrant_storage/`)** | REPOSITORY'YE EKLENMEMELİ | Vektör veritabanı persist dosyaları büyük ve platforma bağımlı olduğu için Git'e dahil edilmez. |
| **Çevresel Değişkenler (`.env`)** | REPOSITORY'YE EKLENMEMELİ | Token ve yapılandırmalar içerdiği için eklenmedi. Sadece `.env.example` eklendi. |
