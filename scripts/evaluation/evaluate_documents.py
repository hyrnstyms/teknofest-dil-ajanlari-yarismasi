import json
from pathlib import Path
from backend.app.graph.workflow import KamuaiWorkflow
from backend.app.evaluation.schemas import PredictedDocument, EvaluationReport, CoverageInfo
from backend.app.evaluation.adapters import (
    get_routing_unit_map, 
    normalize_routing_unit,
    normalize_document_type,
    map_gold_document, 
    map_predicted_document
)
from backend.app.evaluation.metrics import (
    calculate_accuracy,
    calculate_precision_recall_f1
)
import traceback

def evaluate_documents() -> EvaluationReport:
    jsonl_path = Path("data/evaluation/synthetic/evraklar.jsonl")
    report = EvaluationReport(dataset_name="documents")
    
    if not jsonl_path.exists():
        report.status = "skipped"
        report.errors.append("Dataset not found")
        return report
        
    try:
        workflow = KamuaiWorkflow()
    except Exception as e:
        report.status = "failed"
        report.errors.append(f"Workflow init failed: {str(e)}")
        return report
        
    unit_map = get_routing_unit_map()
    # document_agent.ALLOWED_DOCUMENT_TYPES
    allowed_doc_types = {'dilekce', 'resmi_yazi', 'form', 'tutanak', 'rapor', 'karar', 'tebligat', 'eposta', 'diger'}
    
    total = 0
    evaluated_doc = 0
    evaluated_route = 0
    evaluated_extract = 0
    skipped = 0
    
    doc_acc = 0.0
    rout_top1 = 0.0
    rout_top3 = 0.0
    
    mf_acc = 0.0
    
    ext_precision_sum = 0.0
    ext_recall_sum = 0.0
    ext_f1_sum = 0.0
    
    unsupported_doc = set()
    unsupported_route = set()
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            total += 1
            data = json.loads(line)
            gold_doc = map_gold_document(data)
            
            # Semantic matching
            gold_doc_type = normalize_document_type(gold_doc.evrak_turu_dogru)
            gold_unit = normalize_routing_unit(gold_doc.hedef_birim_dogru, unit_map) if gold_doc.hedef_birim_dogru else ""
            
            is_supported_doc = gold_doc_type in allowed_doc_types
            is_supported_route = gold_unit in unit_map.values()
            
            if not is_supported_doc:
                unsupported_doc.add(gold_doc.evrak_turu_dogru)
                report.unsupported["document_type"] = report.unsupported.get("document_type", 0) + 1
            if not is_supported_route and gold_doc.hedef_birim_dogru:
                unsupported_route.add(gold_doc.hedef_birim_dogru)
                report.unsupported["routing_label"] = report.unsupported.get("routing_label", 0) + 1
            
            try:
                result = workflow.run(gold_doc.metin)
                pred = map_predicted_document(gold_doc.id, result)
                
                # Document Type Eval
                if is_supported_doc:
                    evaluated_doc += 1
                    if pred.evrak_turu == gold_doc_type:
                        doc_acc += 1.0
                    else:
                        if len(report.failure_examples) < 10:
                            report.failure_examples.append({
                                "step": "document_type",
                                "id": gold_doc.id,
                                "gold": gold_doc_type,
                                "predicted": pred.evrak_turu
                            })
                            
                # Routing Eval
                if is_supported_route and gold_unit:
                    evaluated_route += 1
                    pred_unit = normalize_routing_unit(pred.hedef_birim, unit_map)
                    if pred_unit == gold_unit:
                        rout_top1 += 1.0
                    elif len(report.failure_examples) < 10:
                        report.failure_examples.append({
                            "step": "routing",
                            "id": gold_doc.id,
                            "gold": gold_unit,
                            "predicted": pred_unit,
                            "top3": pred.ranked_units[:3] if pred.ranked_units else []
                        })
                        
                    norm_ranked = [normalize_routing_unit(u, unit_map) for u in (pred.ranked_units or [])]
                    if gold_unit in norm_ranked[:3]:
                        rout_top3 += 1.0
                
                # Missing Field (gold_missing vs pred_missing)
                if gold_doc.eksik_alan_var_mi is not None:
                    # gold
                    g_miss = bool(gold_doc.eksik_alan_var_mi)
                    # pred: check if missing_fields list has elements
                    missing_agent = result.get("missing_field_agent", {})
                    missing_list = missing_agent.get("missing_fields", [])
                    p_miss = len(missing_list) > 0
                    
                    if g_miss == p_miss:
                        mf_acc += 1.0
                
                # Extraction beklenen_alanlar mapping
                # The user states beklenen_alanlar is the set of fields that SHOULD be extracted.
                # So gold is list of keys in beklenen_alanlar. Pred is list of keys in extracted_fields that are present.
                if gold_doc.beklenen_alanlar:
                    evaluated_extract += 1
                    gold_fields = list(gold_doc.beklenen_alanlar.keys())
                    
                    # only count fields that have a value or status="present"
                    pred_fields = []
                    for k, v in pred.extracted_fields.items():
                        if isinstance(v, dict):
                            val = v.get("value")
                            status = v.get("status")
                            if val is not None or status == "present":
                                pred_fields.append(k)
                        elif v is not None:
                            pred_fields.append(k)
                            
                    metrics = calculate_precision_recall_f1(gold_fields, pred_fields)
                    ext_precision_sum += metrics["precision"]
                    ext_recall_sum += metrics["recall"]
                    ext_f1_sum += metrics["f1"]

            except Exception as e:
                skipped += 1
                report.runtime_failures += 1
                reason = type(e).__name__
                report.coverage.skip_reasons[reason] = report.coverage.skip_reasons.get(reason, 0) + 1

    report.coverage.total_records = total
    report.coverage.evaluable_records = max(evaluated_doc, evaluated_route)
    report.coverage.skipped_records = skipped
    if total > 0:
        report.coverage.coverage_rate = report.coverage.evaluable_records / total
        
    report.unsupported["unsupported_doc_types"] = list(unsupported_doc)
    report.unsupported["unsupported_routing_labels"] = list(unsupported_route)
    
    if evaluated_doc > 0:
        report.metrics["document_type_accuracy"] = doc_acc / evaluated_doc
    if evaluated_route > 0:
        report.metrics["routing_top1_accuracy"] = rout_top1 / evaluated_route
        report.metrics["routing_top3_accuracy"] = rout_top3 / evaluated_route
    if max(evaluated_doc, evaluated_route) > 0:
        report.metrics["missing_field_accuracy"] = mf_acc / report.coverage.evaluable_records
    if evaluated_extract > 0:
        report.metrics["extraction_precision"] = ext_precision_sum / evaluated_extract
        report.metrics["extraction_recall"] = ext_recall_sum / evaluated_extract
        report.metrics["extraction_f1"] = ext_f1_sum / evaluated_extract
        
    return report

if __name__ == "__main__":
    rep = evaluate_documents()
    print(rep.model_dump_json(indent=2))
