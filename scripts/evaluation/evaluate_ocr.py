import json
import re
from pathlib import Path
from backend.app.evaluation.schemas import EvaluationReport
from backend.app.evaluation.metrics import calculate_cer_wer
from backend.app.evaluation.adapters import normalize_turkish_label

def normalize_for_ocr(text: str) -> str:
    if not text: return ""
    t = normalize_turkish_label(text)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def check_equivalence(gt_text: str, ocr_text: str) -> bool:
    """Check if ground truth metin is substantially present in OCR result."""
    norm_gt = normalize_for_ocr(gt_text)
    norm_ocr = normalize_for_ocr(ocr_text)
    
    if not norm_gt:
        return False
        
    gt_words = set(norm_gt.split())
    ocr_words = set(norm_ocr.split())
    
    if not gt_words: return False
    
    intersection = gt_words.intersection(ocr_words)
    overlap = len(intersection) / len(gt_words)
    
    # if at least 50% of ground truth words are in the image, we consider it the same document render
    return overlap > 0.5

def evaluate_ocr() -> EvaluationReport:
    report = EvaluationReport(dataset_name="ocr")
    
    ocr_base_dir = Path("data/evaluation/ocr")
    evrak_path = Path("data/evaluation/synthetic/evraklar.jsonl")
    
    if not ocr_base_dir.exists() or not evrak_path.exists():
        report.status = "skipped"
        report.errors.append("Dataset not found")
        return report
        
    # Build GT map
    gt_map = {}
    with open(evrak_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            gt_map[data["id"]] = data.get("metin", "")
            
    try:
        from backend.app.ocr.ocr_service import OCRService
        ocr_service = OCRService()
    except Exception as e:
        report.status = "failed"
        report.errors.append(f"OCRService initialization failed: {str(e)}")
        return report
        
    report.metrics = {
        "temiz": {"total": 0, "gt_matched": 0, "attempted": 0, "successful": 0, "failed": 0, "cer_evaluable": 0, "cer_sum": 0.0, "wer_sum": 0.0},
        "orta_kalite": {"total": 0, "gt_matched": 0, "attempted": 0, "successful": 0, "failed": 0, "cer_evaluable": 0, "cer_sum": 0.0, "wer_sum": 0.0},
        "zor": {"total": 0, "gt_matched": 0, "attempted": 0, "successful": 0, "failed": 0, "cer_evaluable": 0, "cer_sum": 0.0, "wer_sum": 0.0},
        "overall": {"total": 0, "gt_matched": 0, "attempted": 0, "successful": 0, "failed": 0, "cer_evaluable": 0, "cer_sum": 0.0, "wer_sum": 0.0}
    }
    
    for category in ["temiz", "orta_kalite", "zor"]:
        cat_dir = ocr_base_dir / category
        if not cat_dir.exists(): continue
        
        for img_path in cat_dir.glob("*.png"):
            report.metrics[category]["total"] += 1
            report.metrics["overall"]["total"] += 1
            
            # e.g., SENT-0012_temiz.png -> SENT-0012
            fname = img_path.name
            doc_id = fname.split("_")[0]
            
            if doc_id not in gt_map:
                report.coverage.skip_reasons["unmatched_id"] = report.coverage.skip_reasons.get("unmatched_id", 0) + 1
                continue
                
            report.metrics[category]["gt_matched"] += 1
            report.metrics["overall"]["gt_matched"] += 1
            
            gt_text = gt_map[doc_id]
            report.metrics[category]["attempted"] += 1
            report.metrics["overall"]["attempted"] += 1
            
            try:
                ocr_result = ocr_service.extract_text_from_image(str(img_path))
                report.metrics[category]["successful"] += 1
                report.metrics["overall"]["successful"] += 1
                
                if check_equivalence(gt_text, ocr_result):
                    metrics = calculate_cer_wer(gt_text, ocr_result)
                    report.metrics[category]["cer_evaluable"] += 1
                    report.metrics["overall"]["cer_evaluable"] += 1
                    
                    report.metrics[category]["cer_sum"] += metrics["cer"]
                    report.metrics[category]["wer_sum"] += metrics["wer"]
                    report.metrics["overall"]["cer_sum"] += metrics["cer"]
                    report.metrics["overall"]["wer_sum"] += metrics["wer"]
                else:
                    report.coverage.skip_reasons["ground_truth_not_equivalent"] = report.coverage.skip_reasons.get("ground_truth_not_equivalent", 0) + 1
                    
            except Exception as e:
                report.metrics[category]["failed"] += 1
                report.metrics["overall"]["failed"] += 1
                report.runtime_failures += 1
                reason = type(e).__name__
                report.coverage.skip_reasons[reason] = report.coverage.skip_reasons.get(reason, 0) + 1
                if len(report.failure_examples) < 10:
                    report.failure_examples.append({
                        "step": "ocr_runtime",
                        "id": doc_id,
                        "category": category,
                        "error": str(e)
                    })
                    
    # Calculate means
    for cat in ["temiz", "orta_kalite", "zor", "overall"]:
        m = report.metrics[cat]
        if m["attempted"] > 0:
            m["success_rate"] = m["successful"] / m["attempted"]
        if m["cer_evaluable"] > 0:
            m["mean_CER"] = m["cer_sum"] / m["cer_evaluable"]
            m["mean_WER"] = m["wer_sum"] / m["cer_evaluable"]
            
    report.coverage.total_records = report.metrics["overall"]["total"]
    report.coverage.evaluable_records = report.metrics["overall"]["cer_evaluable"]
    report.coverage.skipped_records = report.metrics["overall"]["total"] - report.metrics["overall"]["cer_evaluable"]
    if report.coverage.total_records > 0:
        report.coverage.coverage_rate = report.coverage.evaluable_records / report.coverage.total_records
        
    return report

if __name__ == "__main__":
    rep = evaluate_ocr()
    print(rep.model_dump_json(indent=2))
