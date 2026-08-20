import json
from backend.app.graph.workflow import KamuaiWorkflow
from backend.app.evaluation.adapters import map_predicted_document

def main():
    workflow = KamuaiWorkflow()
    with open("data/evaluation/synthetic/evraklar.jsonl", "r", encoding="utf-8") as f:
        line = f.readline()
        data = json.loads(line)
        text = data.get("metin", "")
        doc_id = data.get("id")
        
    result = workflow.run(text)
    pred = map_predicted_document(doc_id, result)
    
    print("Predicted Document Type:", pred.evrak_turu)
    print("Predicted Routing:", pred.hedef_birim)
    print("Missing Field:", pred.eksik_alan_var_mi)

if __name__ == "__main__":
    main()
