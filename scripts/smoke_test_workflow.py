import json
from backend.app.graph.workflow import KamuaiWorkflow

def run_smoke_test():
    print("=== SMOKE TEST: Mehmet Kaya Workflow End-to-End ===")
    
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
    
    workflow = KamuaiWorkflow()
    final_state = workflow.run(text)
    
    print("\n--- Final Workflow State ---")
    
    # We remove some massive objects for clean print
    if "document" in final_state:
        print("\n[DOCUMENT]")
        print(json.dumps(final_state["document"], indent=2, ensure_ascii=False))
        
    if "extraction" in final_state:
        print("\n[EXTRACTION]")
        print("Fields count:", len(final_state["extraction"].get("fields", {})))
        if "address" not in final_state["extraction"].get("fields", {}):
            print("Address is missing.")
            
    if "missing_fields" in final_state:
        print("\n[MISSING FIELDS]")
        print(json.dumps(final_state["missing_fields"], indent=2, ensure_ascii=False))
        
    if "summary" in final_state:
        print("\n[SUMMARY]")
        print(final_state["summary"].get("short_summary"))
        
    if "routing" in final_state:
        print("\n[ROUTING]")
        print(json.dumps(final_state["routing"], indent=2, ensure_ascii=False))
        
    if "quality" in final_state:
        print("\n[QUALITY]")
        print("Status:", final_state["quality"].get("status"))
        
    if "human_review" in final_state:
        print("\n[HUMAN REVIEW]")
        print(json.dumps(final_state["human_review"], indent=2, ensure_ascii=False))
        
    if "node_timings" in final_state:
        print("\n[NODE TIMINGS]")
        print(json.dumps(final_state["node_timings"], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    run_smoke_test()
