import json
import random
import time
from pathlib import Path
from typing import Dict, Any

from backend.app.graph.workflow import KamuaiWorkflow
from backend.app.evaluation.adapters import (
    normalize_document_type,
    get_routing_unit_map,
    normalize_routing_unit,
    has_missing_fields,
    normalize_extracted_fields
)

def get_stratified_sample(filepath: str, k: int = 15, seed: int = 42):
    random.seed(seed)
    
    docs_by_type = {}
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line.strip())
            dtype = data.get("evrak_turu_dogru", "unknown")
            if dtype not in docs_by_type:
                docs_by_type[dtype] = []
            docs_by_type[dtype].append(data)
            
    # Try to pick evenly
    sampled = []
    types = list(docs_by_type.keys())
    
    # If k=15, and we have ~6 types, pick 2-3 per type
    while len(sampled) < k and types:
        for t in types:
            if docs_by_type[t]:
                doc = docs_by_type[t].pop(random.randrange(len(docs_by_type[t])))
                sampled.append(doc)
            if len(sampled) >= k:
                break
        types = [t for t in types if docs_by_type[t]]
        
    return sampled

def evaluate_missing(gold, pred):
    if gold and pred:
        return "TP"
    elif not gold and not pred:
        return "TN"
    elif not gold and pred:
        return "FP"
    elif gold and not pred:
        return "FN"

def normalize_text(text: Any) -> str:
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    
    # Strip whitespace
    text = " ".join(text.split())
    # Lowercase (basic turkish handling)
    trans = str.maketrans("IİÖÜÇĞŞıöüçğş", "iioucgsioucgs")
    text = text.translate(trans).lower()
    
    # Normalize date formats (basic)
    import re
    # 2026-08-12 -> 12.08.2026
    text = re.sub(r'(\d{4})-(\d{2})-(\d{2})', r'\3.\2.\1', text)
    # 12/08/2026 -> 12.08.2026
    text = re.sub(r'(\d{2})/(\d{2})/(\d{4})', r'\1.\2.\3', text)
    
    return text
    
def match_field(gold_val, pred_val) -> str:
    if not gold_val and not pred_val:
        return "gold_missing"
    if not gold_val and pred_val:
        return "gold_missing"
    if gold_val and not pred_val:
        return "missing"
    
    gold_norm = normalize_text(gold_val)
    pred_norm = normalize_text(pred_val)
    
    if gold_norm == pred_norm:
        return "correct"
    return "wrong"

def main():
    print("Loading samples...")
    samples = get_stratified_sample("data/evaluation/synthetic/evraklar.jsonl", 15, 42)
    print(f"Loaded {len(samples)} samples.")
    
    workflow = KamuaiWorkflow()
    unit_map = get_routing_unit_map("kaymakamlik")
    
    results = []
    
    for i, sample in enumerate(samples):
        print(f"Processing sample {i+1}/15 (ID: {sample['id']})...")
        start_time = time.time()
        
        # Run workflow
        final_state = workflow.run(raw_text=sample["metin"], document_id=sample["id"])
        end_time = time.time()
        
        # Extract workflow raw outputs
        raw_doc_type = final_state.get("document", {}).get("document_type", "")
        # Get raw fields and pass through adapter manually since we bypass adapters in workflow output
        raw_extraction = final_state.get("extraction", {}).get("fields", {})
        norm_extracted = normalize_extracted_fields(raw_extraction)
        
        raw_routing_dict = final_state.get("routing", {}).get("recommended_unit", "")
        raw_routing = raw_routing_dict.get("name", "") if isinstance(raw_routing_dict, dict) else raw_routing_dict
        
        raw_missing = final_state.get("missing_fields", {})
        
        # Apply Normalizations
        norm_doc_type = normalize_document_type(raw_doc_type)
        norm_routing = normalize_routing_unit(raw_routing, unit_map)
        
        gold_routing_norm = normalize_routing_unit(sample.get("hedef_birim_dogru", ""), unit_map)
        
        pred_missing_bool = has_missing_fields(raw_missing)
        gold_missing_bool = sample.get("eksik_alan_var_mi", False)
        
        # Calculate Extraction match
        gold_fields = sample.get("beklenen_alanlar", {})
        field_evals = {}
        for k in ["referans_no", "gonderen_adi", "talep_metni", "konu", "tarih"]:
            gold_val = gold_fields.get(k)
            pred_val = norm_extracted.get(k)
            field_evals[k] = match_field(gold_val, pred_val)
        
        gold_doc_type_raw = sample.get("evrak_turu_dogru", "")
        gold_doc_type_norm = normalize_document_type(gold_doc_type_raw)
        
        res = {
            "id": sample["id"],
            "gold_doc_type_raw": gold_doc_type_raw,
            "gold_doc_type_normalized": gold_doc_type_norm,
            "pred_doc_type_raw": raw_doc_type,
            "pred_doc_type_normalized": norm_doc_type,
            "doc_type_raw_match": gold_doc_type_raw == raw_doc_type,
            "doc_type_norm_match": gold_doc_type_norm == norm_doc_type,
            
            "gold_routing": sample.get("hedef_birim_dogru"),
            "raw_routing": raw_routing,
            "norm_routing": norm_routing,
            "routing_match": norm_routing == gold_routing_norm,
            
            "gold_missing": gold_missing_bool,
            "pred_missing": pred_missing_bool,
            "missing_eval": evaluate_missing(gold_missing_bool, pred_missing_bool),
            
            "extraction_evals": field_evals,
            "raw_extraction_keys": list(raw_extraction.keys()),
            "duration": end_time - start_time
        }
        results.append(res)
        
    with open("mini_eval_results_v2.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("Done!")

if __name__ == "__main__":
    main()
