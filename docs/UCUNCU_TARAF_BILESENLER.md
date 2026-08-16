# Üçüncü Taraf Bileşenler

KAMUAI projesi, açık kaynak ekosisteminin güçlü bileşenleri üzerine inşa edilmiştir. Projede kullanılan temel üçüncü taraf yazılımlar ve kütüphaneler lisanslarıyla birlikte aşağıda listelenmiştir.

| Bileşen | Tür | Sürüm/Model | Kullanım | Lisans | Kaynak | Repoya Dahil mi? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Qwen2.5-3B-Instruct** | LLM Model | 3B-Instruct | Semantik Analiz, Çıkarım, Metin Üretimi | Apache 2.0 | [HuggingFace](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct) / [Ollama](https://ollama.com) | Hayır |
| **BAAI/bge-m3** | Embedding | bge-m3 | Vektörel Arama (RAG) | MIT | [HuggingFace](https://huggingface.co/BAAI/bge-m3) | Hayır |
| **Ollama** | Model Sunucusu | v0.3+ | Yerel LLM Çalıştırma | MIT | [Ollama](https://ollama.com) | Hayır |
| **FastAPI** | Backend Framework | 0.100+ | API Sunucusu | MIT | [FastAPI](https://fastapi.tiangolo.com/) | Hayır (pip) |
| **LangGraph** | Workflow Framework | 0.0.x | Agentic Workflow | MIT | [LangChain](https://python.langchain.com/) | Hayır (pip) |
| **Qdrant** | Vektör Veritabanı | 1.9+ | Embedding Depolama ve Arama | Apache 2.0 | [Qdrant](https://qdrant.tech/) | Hayır |
| **React** | Frontend Framework | 18.x | Kullanıcı Arayüzü (UI) | MIT | [React](https://react.dev/) | Hayır (npm) |
| **Vite** | Build Tool | 5.x | Frontend Geliştirme/Derleme | MIT | [Vite](https://vitejs.dev/) | Hayır (npm) |
| **TypeScript** | Programlama Dili | 5.x | Frontend Geliştirme | Apache 2.0 | [TypeScript](https://www.typescriptlang.org/) | Hayır (npm) |
| **PaddleOCR** | OCR Kütüphanesi | 2.x | Görüntüden Metin Çıkarımı | Apache 2.0 | [PaddlePaddle](https://github.com/PaddlePaddle/PaddleOCR) | Hayır (pip) |
| **PyMuPDF** | PDF İşleme | 1.24+ | PDF Okuma | GNU AGPL 3.0 / Commercial | [PyMuPDF](https://pymupdf.readthedocs.io/) | Hayır (pip) |
| **sentence-transformers** | Embedding Kütüphanesi | 3.x | Metin Vektörizasyonu | Apache 2.0 | [sbert.net](https://www.sbert.net/) | Hayır (pip) |
| **python-docx** | Word Belge İşleme | 1.1+ | DOCX Okuma/Yazma | MIT | [python-docx](https://python-docx.readthedocs.io/) | Hayır (pip) |
| **NumPy** | Matematiksel İşlemler | 1.26+ | Veri Manipülasyonu | BSD | [NumPy](https://numpy.org/) | Hayır (pip) |
| **pandas** | Veri İşleme | 2.x | Veri Manipülasyonu | BSD | [pandas](https://pandas.pydata.org/) | Hayır (pip) |
| **scikit-learn** | Makine Öğrenmesi | 1.x | Veri Ön İşleme ve Değerlendirme | BSD | [scikit-learn](https://scikit-learn.org/) | Hayır (pip) |

> *Not: Ekip teknik rehberi ve üçüncü taraf kütüphanelerin kaynak kodları/ağırlıkları, yarışma şartnamesi ve açık kaynak pratikleri gereğince projenin Git reposuna (`.gitignore` ile kısıtlanarak) eklenmemiştir. Sadece `requirements.txt` ve `package.json` üzerinden paket yöneticileriyle çekilmektedir.*
