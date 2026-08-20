import json
from pathlib import Path
from backend.app.agents.writing_agent import WritingAgent
from backend.app.evaluation.schemas import EvaluationReport, CoverageInfo

def evaluate_writing() -> EvaluationReport:
    gold_path = Path("data/evaluation/writing/gold_taslaklar.jsonl")
    evraklar_path = Path("data/evaluation/synthetic/evraklar.jsonl")
    report = EvaluationReport(dataset_name="writing")
    
    if not gold_path.exists() or not evraklar_path.exists():
        report.status = "skipped"
        report.errors.append("Dataset not found")
        return report
        
    # Build a lookup dictionary for documents
    evraklar_map = {}
    with open(evraklar_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            evraklar_map[data.get("id")] = data.get("metin", "")
            
    try:
        agent = WritingAgent()
    except Exception as e:
        report.status = "failed"
        report.errors.append(f"WritingAgent init failed: {str(e)}")
        return report
        
    total = 0
    matched = 0
    skipped = 0
    
    draft_type_acc = 0.0
    val_pass = 0.0
    req_sections_acc = 0.0
    
    with open(gold_path, 'r', encoding='utf-8') as f:
        for line in f:
            total += 1
            gold = json.loads(line)
            source_id = gold.get("kaynak_evrak_id")
            gold_type = gold.get("yazi_turu")
            
            if source_id not in evraklar_map:
                report.coverage.skip_reasons["unmatched_source_id"] = report.coverage.skip_reasons.get("unmatched_source_id", 0) + 1
                skipped += 1
                continue
                
            matched += 1
            source_text = evraklar_map[source_id]
            
            try:
                # Real Public API: draft(document_summary, requested_action, ...)
                result = agent.draft(document_summary=source_text, requested_action=gold_type)
                
                # Check metrics
                pred_type = result.get("draft_type", "")
                if gold_type and pred_type and gold_type.lower() in pred_type.lower():
                    draft_type_acc += 1.0
                else:
                    if len(report.failure_examples) < 10:
                        report.failure_examples.append({
                            "step": "draft_type",
                            "id": source_id,
                            "gold": gold_type,
                            "predicted": pred_type
                        })
                        
                validator_res = result.get("validator_result", {})
                if validator_res.get("is_valid", False):
                    val_pass += 1.0
                elif len(report.failure_examples) < 10:
                    report.failure_examples.append({
                        "step": "validator",
                        "id": source_id,
                        "errors": validator_res.get("errors", [])
                    })
                    
                req = validator_res.get("sections_present", {})
                if req:
                    req_sections_acc += sum(1 for v in req.values() if v) / len(req)
                    
            except Exception as e:
                report.runtime_failures += 1
                skipped += 1
                reason = type(e).__name__
                report.coverage.skip_reasons[reason] = report.coverage.skip_reasons.get(reason, 0) + 1
                
    report.coverage.total_records = total
    report.coverage.evaluable_records = matched - report.runtime_failures
    report.coverage.skipped_records = skipped
    if total > 0:
        report.coverage.coverage_rate = matched / total
        
    evaluable = report.coverage.evaluable_records
    if evaluable > 0:
        report.metrics["draft_type_accuracy"] = draft_type_acc / evaluable
        report.metrics["validator_pass_rate"] = val_pass / evaluable
        report.metrics["required_section_coverage"] = req_sections_acc / evaluable
        report.metrics["invalid_blocked_rate"] = 1.0 - (val_pass / evaluable)
        
    return report

if __name__ == "__main__":
    rep = evaluate_writing()
    print(rep.model_dump_json(indent=2))
