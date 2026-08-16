import json
from backend.app.agents.missing_field_agent import MissingFieldAgent
from backend.app.agents.summary_agent import SummaryAgent
from backend.app.llm.base import LLMClient
from backend.app.llm.factory import create_llm_client

def run_smoke_test():
    print("=== SMOKE TEST: Mehmet Kaya Senaryosu ===")
    
    # Mock Document Context
    document_type = "dilekce"
    process_intent = "bilgi_talebi"
    raw_text = "Ben Mehmet Kaya. Bilgi edinmek istiyorum."
    
    # Mock Extracted Fields
    extracted_fields = {
        "person_name": {"value": "Mehmet Kaya", "status": "present"},
        "national_id": {"value": "11111111110", "status": "present"},
        "phone": {"value": "05555555555", "status": "present"},
        "email": {"value": "mehmet@example.com", "status": "present"},
        # address is missing
        "request": {"value": "bilgi edinmek istiyorum", "status": "present"},
        "signature_present": {"value": None, "status": "unknown"}
    }
    
    # Legal evidence (mocked to show how agent behaves when evidence is missing vs present)
    # The requirement says: "legal basis yalnız gerçekten doğrulanmış evidence varsa gösterilmeli"
    legal_analysis_with_evidence = {
        "evidence": ["Başvuru sahibinin adı ve adresi zorunludur."],
        "sources": [{"law_number": "4982", "article": "6", "text": "Başvuru sahibinin adı ve adresi zorunludur."}]
    }
    
    # 1. Missing Field Agent
    print("\n--- Missing Field Agent Sonucu ---")
    mf_agent = MissingFieldAgent()
    mf_res = mf_agent.check_missing_fields(
        document_type, 
        process_intent, 
        extracted_fields,
        legal_analysis_with_evidence
    )
    print(json.dumps(mf_res, indent=2, ensure_ascii=False))
    
    # 2. Summary Agent
    print("\n--- Summary Agent Sonucu ---")
    llm = create_llm_client()
    summary_agent = SummaryAgent(llm=llm)
    summary_res = summary_agent.summarize(raw_text, {}, extracted_fields)
    print(json.dumps(summary_res, indent=2, ensure_ascii=False))
    
if __name__ == "__main__":
    run_smoke_test()
