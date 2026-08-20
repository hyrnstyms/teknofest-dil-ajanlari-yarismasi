import json
from scripts.evaluation.evaluate_legal_rag import normalize_legal_source, normalize_madde
from backend.app.rag.retriever import Retriever

NORMALIZED_DOCUMENT_IDS = {
    "bilgiedinmekanunu": "4982",
    "dilekce_hakki_kanunu": "3071",
    "3071_dilekce_hakki_kanunu": "3071",
    "resmi_yazisma_kurallari": "resmi_yazisma_kurallari", 
    "resmi_yazisma_kilavuzu": "resmi_yazisma_kilavuzu",
    "kvkk": "6698",
    "cezamuhakemesikanunu": "5271" # Wait, the evaluator report said 5442 returned for CMK? No, CMK is 5271.
}

def build_canonical_key(source: str, madde: str) -> str:
    norm_src = normalize_legal_source(source).replace("_pdf", "").replace(".pdf", "")
    
    # Try to map to law number if exists
    canon_src = NORMALIZED_DOCUMENT_IDS.get(norm_src, norm_src)
    
    # Fallback cleanup for "sayili_kanun"
    canon_src = canon_src.replace("_sayili_kanun", "")
    
    canon_madde = normalize_madde(madde)
    return f"{canon_src}|{canon_madde}"

def main():
    retriever = Retriever()
    with open("data/evaluation/legal/rag_test_seti.jsonl", "r", encoding="utf-8") as f:
        queries = [json.loads(f.readline()) for _ in range(5)]
        
    for q in queries:
        query_text = q["soru"]
        gold_src = q["kaynak_dokuman"]
        gold_madde = q["dogru_madde_no"]
        
        gold_raw = f"{gold_src}|{gold_madde}"
        gold_canonical = build_canonical_key(gold_src, gold_madde)
        
        print(f"\nSorgu: {query_text}")
        print(f"gold raw: {gold_raw}")
        print(f"gold normalized: {gold_canonical}")
        
        results = retriever.search_legal(query=query_text, limit=5)
        
        predicted_raw = []
        predicted_normalized = []
        
        for r in results:
            src = r.get("source", "")
            madde = r.get("madde_no", "")
            
            raw = f"{src}|{madde}"
            canon = build_canonical_key(src, madde)
            
            predicted_raw.append(raw)
            predicted_normalized.append(canon)
            
        print(f"predicted raw: {predicted_raw}")
        print(f"predicted normalized: {predicted_normalized}")
        
        match = "yes" if gold_canonical in predicted_normalized else "no"
        print(f"match: {match}")

if __name__ == '__main__':
    main()
