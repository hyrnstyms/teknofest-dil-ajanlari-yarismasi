import sys, json
sys.path.insert(0, ".")
from backend.app.agents.legal_agent import LegalAgent

TARGET_IDS = ["RAG-028", "RAG-040"]
agent = LegalAgent()
output_data = []

with open("data/evaluation/legal/rag_test_seti.jsonl", encoding="utf-8") as f:
    records = [json.loads(line) for line in f if line.strip()]

for rec in records:
    if rec["id"] in TARGET_IDS:
        result = agent.analyze(query=rec["soru"], top_k=3)
        retrieved = result.get("retrieved_sources", [])
        
        if retrieved:
            output_data.append({
                "id": rec["id"],
                "zorluk": rec.get("zorluk"),
                "soru": rec["soru"],
                "dogru_metin_ozeti": rec.get("dogru_metin_ozeti", "YOK"),
                "madde_no": retrieved[0].get("madde_no"),
                "text": retrieved[0].get("text")
            })

with open("chunk_output.json", "w", encoding="utf-8") as out_f:
    json.dump(output_data, out_f, ensure_ascii=False, indent=4)
