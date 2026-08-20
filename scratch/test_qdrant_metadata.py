import json
from backend.app.rag.retriever import Retriever

def main():
    retriever = Retriever()
    
    with open("data/evaluation/legal/rag_test_seti.jsonl", "r", encoding="utf-8") as f:
        queries = [json.loads(f.readline()) for _ in range(3)]
        
    for q in queries:
        query_text = q["soru"]
        print(f"\n--- QUERY: {query_text} ---")
        
        results = retriever.search_legal(query=query_text, top_k=2)
        for i, res in enumerate(results):
            print(f"Result {i+1} score: {res.score}")
            print(f"Metadata: {json.dumps(res.metadata, indent=2, ensure_ascii=False)}")
            print("-----")

if __name__ == '__main__':
    main()
