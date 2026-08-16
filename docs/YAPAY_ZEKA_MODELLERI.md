# Yapay Zekâ Modelleri

KAMUAI projesi, yerel cihazlarda çalışacak şekilde optimize edilmiş, veri gizliliğini maksimum seviyede tutan lokal yapay zekâ modelleri kullanmaktadır.

## 1. Qwen 2.5 (Büyük Dil Modeli)

- **Model Adı:** Qwen2.5-3B-Instruct
- **Tam Model Kimliği:** `qwen2.5:3b-instruct`
- **Kullanım Amacı:** Document Agent, Extraction Agent, Legal Agent, Summary Agent, Writing Agent ve Routing Agent içindeki semantik metin analizi, yapılandırılmış veri çıkarımı ve doğal dil üretimi.
- **Sürüm / Tag:** 3B-Instruct
- **Sağlayıcı / Geliştirici:** Alibaba Cloud (Qwen Team)
- **Erişim Kaynağı:** [HuggingFace](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct) / [Ollama Library](https://ollama.com/library/qwen2.5)
- **Lisans Adı:** Apache 2.0 License
- **Lisans Kaynağı:** [Qwen2.5 License](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/LICENSE)
- **Sisteme Nasıl Yüklendiği:** Ollama platformu aracılığıyla.
- **Kullanım Komutu:** `ollama pull qwen2.5:3b-instruct`
- **Repository Dahiliyet:** **Model ağırlıkları KAMUAI repository'sine dahil edilmemiştir.** Model, kullanıcı tarafından yerel Ollama sunucusu üzerinden ayrıca edinilmelidir. 
- **Donanım Notu:** 3 milyar parametreli bu model, minimum 8GB RAM'e sahip standart bilgisayarlarda CPU/GPU hibrit olarak yüksek hızda çalışabilmektedir.

## 2. BGE-M3 (Gömme / Embedding Modeli)

- **Model Adı:** BAAI/bge-m3
- **Tam Model Kimliği:** `BAAI/bge-m3`
- **Kullanım Amacı:** Mevzuat ve kurum içi belgelerin vektörel arama (RAG - Retrieval-Augmented Generation) altyapısı için yüksek boyutlu (1024) vektör (embedding) üretimi.
- **Sürüm / Tag:** v1.0
- **Sağlayıcı / Geliştirici:** BAAI (Beijing Academy of Artificial Intelligence)
- **Erişim Kaynağı:** [HuggingFace](https://huggingface.co/BAAI/bge-m3)
- **Lisans Adı:** MIT License
- **Lisans Kaynağı:** [BGE-M3 License](https://huggingface.co/BAAI/bge-m3/blob/main/LICENSE)
- **Sisteme Nasıl Yüklendiği:** `sentence-transformers` Python kütüphanesi aracılığıyla HuggingFace Hub'dan otomatik olarak indirilmektedir.
- **Kullanım Komutu:** Python içerisinde `SentenceTransformer('BAAI/bge-m3')` ile çağrılmaktadır.
- **Repository Dahiliyet:** **Model ağırlıkları KAMUAI repository'sine dahil edilmemiştir.** HuggingFace cache dizinleri (`.cache/huggingface`) repository dışında tutulmaktadır.
- **Donanım Notu:** Çok dilli (Multi-lingual) destek sunan BGE-M3, RAG sistemi için en iyi performans/boyut dengesini sunmaktadır.
