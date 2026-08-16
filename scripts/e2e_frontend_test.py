import requests
import json
import time

API_BASE = "http://localhost:8000"

def run_test():
    print("Testing API Health...")
    r = requests.get(f"{API_BASE}/health")
    assert r.status_code == 200, "API is not healthy"
    print("Health check OK.")

    text = """T.C.
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
tarafıma verilmesini arz ederim."""

    print("\nSending text to analyze...")
    r = requests.post(f"{API_BASE}/api/documents/analyze-text", json={"text": text})
    assert r.status_code == 200, f"Analysis failed: {r.text}"
    
    data = r.json()
    analysis_id = data.get("analysis_id")
    print(f"Analysis ID: {analysis_id}")
    
    print("\nVerifying extracted structure matches expectations...")
    assert data["document"]["document_type"] == "dilekce", "Type should be dilekce"
    assert data["document"]["process_intent"] == "bilgi_talebi", "Intent should be bilgi_talebi"
    
    missing = data["missing_fields"]["missing_fields"]
    assert "address" in missing, "Address should be missing"
    
    routing = data["routing"]["recommended_unit"]
    assert routing == "Bilgi Edinme Birimi", f"Expected Bilgi Edinme Birimi, got {routing}"
    
    review_status = data["human_review"]["status"]
    assert review_status == "pending_review", "Status should be pending_review"
    
    print("Draft data:", data.get("draft"))
    draft_text = data["draft"].get("rendered_text") or data["draft"].get("draft_text", "")
    assert draft_text, "Draft text should exist"
    
    print("Structure verifications passed!")
    
    # 5. Check List and Queue Endpoints BEFORE Approve
    print("\n--- Adım 5: Evrak Listesi ve İnceleme Kuyruğu Doğrulama (Onay Öncesi) ---")
    
    # Verify in pending queue
    pending_resp = requests.get(f"{API_BASE}/api/reviews/pending")
    pending_resp.raise_for_status()
    pending_data = pending_resp.json()
    print(f"Pending Kuyruğu: {len(pending_data['items'])} evrak bekliyor.")
    
    in_queue = any(item["analysis_id"] == analysis_id for item in pending_data["items"])
    assert in_queue is True, "Analiz pending queue'da olmalı."
    
    print("\nTesting Approve endpoint...")
    r = requests.post(f"{API_BASE}/api/analysis/{analysis_id}/approve")
    assert r.status_code == 200, f"Approve failed: {r.text}"
    
    r = requests.get(f"{API_BASE}/api/analysis/{analysis_id}")
    final_data = r.json()
    assert final_data["human_review"]["status"] == "approved", "Status should be approved"
    
    audit = final_data["audit_history"]
    assert any(a["event"] == "approved" for a in audit), "Audit log missing approved event"
    print("Approve verification passed!")
    
    # Verify dropped from pending queue
    pending_resp2 = requests.get(f"{API_BASE}/api/reviews/pending")
    pending_data2 = pending_resp2.json()
    in_queue2 = any(item["analysis_id"] == analysis_id for item in pending_data2["items"])
    assert in_queue2 is False, "Analiz approve edildikten sonra pending queue'dan düşmeli."
    
    # Verify still in analysis list with status approved
    list_resp = requests.get(f"{API_BASE}/api/analyses")
    list_data = list_resp.json()
    list_item = next((i for i in list_data["items"] if i["analysis_id"] == analysis_id), None)
    assert list_item is not None, "Analiz tüm evraklar listesinde bulunmalı."
    assert list_item["human_review_status"] == "approved", "Listenin içinde status approved olmalı."
    
    print("\nTesting System Status endpoint...")
    r = requests.get(f"{API_BASE}/api/system/status")
    assert r.status_code == 200, "System status failed"
    status_data = r.json()
    assert "api" in status_data
    assert "qdrant" in status_data
    print("System status verification passed!")
    
    print("\nTesting ROI endpoint...")
    r = requests.get(f"{API_BASE}/api/roi/summary")
    assert r.status_code == 200, "ROI summary failed"
    roi_data = r.json()
    assert "processed_documents" in roi_data
    assert roi_data["processed_documents"] > 0, "Processed documents should be > 0"
    print("ROI verification passed!")

    # 4.3 Check EBYS mock status
    print("\n--- Adım 4.3: EBYS Durumunu Doğrulama ---")
    ebys_resp = requests.get(f"{API_BASE}/api/integrations/ebys/status")
    ebys_resp.raise_for_status()
    ebys_data = ebys_resp.json()
    print(f"EBYS Durumu: {ebys_data}")
    assert ebys_data["adapter_type"] == "mock", "Adapter mock olmalı."
    assert ebys_data["connected"] is False, "Gerçek bağlantı olmamalı."
    
    # E2E Done
    print("\n[BAŞARILI] Uçtan uca Frontend-Backend entegrasyonu tamamen test edildi!")

if __name__ == "__main__":
    run_test()
