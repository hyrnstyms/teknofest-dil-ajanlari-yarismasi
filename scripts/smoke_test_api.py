import json
from fastapi.testclient import TestClient
from backend.app.main import app

def run_api_smoke_test():
    print("=== SMOKE TEST: Mehmet Kaya API E2E ===")
    
    client = TestClient(app)
    
    text = """
T.C.
ÖRNEK KAMU KURUMU
Bilgi Edinme Birimine

Sayı: 2026/145
Tarih: 16.08.2026

Konu: Proje Harcamaları Hakkında Bilgi Talebi

Başvuru Sahibi: Mehmet Kaya
T.C. Kimlik No: 10000000146
Telefon: 0532 111 22 33
E-posta: mehmet.kaya@example.com

Kurumunuz tarafından yürütülen Akıllı Şehir Projesi hakkında
bilgi edinmek istiyorum.

Projenin 2026 yılı harcamalarına ilişkin bilgi ve belgelerin
tarafıma verilmesini arz ederim.
"""
    
    # 1. Analyze text
    print("\n[1] POST /api/documents/analyze-text çağrılıyor...")
    res = client.post("/api/documents/analyze-text", json={"text": text})
    assert res.status_code == 200, res.text
    data = res.json()
    
    analysis_id = data["analysis_id"]
    print(f"Başarıyla analiz edildi. Analysis ID: {analysis_id}")
    
    doc_type = data.get("document", {}).get("document_type")
    intent = data.get("document", {}).get("process_intent")
    print(f"Document: {doc_type} / {intent}")
    
    missing_address = "address" in data.get("missing_fields", {}).get("missing_fields", [])
    print(f"Address Missing: {missing_address}")
    
    routing = data.get("routing", {}).get("recommended_unit")
    print(f"Routing Unit: {routing}")
    
    hr_status = data.get("human_review", {}).get("status")
    print(f"Human Review Status: {hr_status}")
    
    # 2. Get Analysis
    print(f"\n[2] GET /api/analysis/{analysis_id} çağrılıyor...")
    res = client.get(f"/api/analysis/{analysis_id}")
    assert res.status_code == 200
    print("Analiz kaydı getirildi.")
    
    # 3. Approve
    print(f"\n[3] POST /api/analysis/{analysis_id}/approve çağrılıyor...")
    res = client.post(f"/api/analysis/{analysis_id}/approve")
    assert res.status_code == 200
    
    # Verify final status
    res = client.get(f"/api/analysis/{analysis_id}")
    final_data = res.json()
    new_status = final_data.get("human_review", {}).get("status")
    print(f"Yeni Human Review Status: {new_status}")
    
    # Audit history
    audits = final_data.get("audit_history", [])
    print(f"\nAudit History: {len(audits)} event(s)")
    for a in audits:
        print(f" - [{a['event']}] {a['message']}")
        
    print("\nAPI E2E Smoke Test Başarılı!")

if __name__ == "__main__":
    run_api_smoke_test()
