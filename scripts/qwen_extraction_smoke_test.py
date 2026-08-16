import sys
from backend.app.agents.extraction_agent import ExtractionAgent

def run_smoke_test():
    doc = """T.C.
ÖRNEK KAMU KURUMU
Bilgi Edinme Birimine

Sayı: 2026/145
Tarih: 16.08.2026

Konu: Proje Harcamaları Hakkında Bilgi Talebi

Başvuru Sahibi: Mehmet Kaya
T.C. Kimlik No: 10000000146
Adres: Örnek Mahallesi Çiçek Sokak No: 12
Kadıköy / İstanbul
Telefon: 0532 111 22 33
E-posta: mehmet.kaya@example.com

Kurumunuz tarafından yürütülen Akıllı Şehir Projesi
hakkında bilgi edinmek istiyorum.

Projenin 2026 yılı harcamalarına ilişkin bilgi ve belgelerin
tarafıma verilmesini arz ederim.

Ekler:
1. Başvuru Formu"""

    agent = ExtractionAgent()
    print("Agent initialized. Running extraction with real LLM...")
    try:
        result = agent.extract(text=doc)
        print("=== EXTRACTION RESULT ===")
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("=== SMOKE TEST FINISHED ===")
    except Exception as e:
        print(f"Error during smoke test: {e}")

if __name__ == "__main__":
    run_smoke_test()
