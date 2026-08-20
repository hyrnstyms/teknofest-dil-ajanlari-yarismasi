import json
import logging
from pathlib import Path
from scripts.evaluation.evaluate_documents import evaluate_documents
from scripts.evaluation.evaluate_writing import evaluate_writing
from scripts.evaluation.evaluate_legal_rag import evaluate_legal_rag
from scripts.evaluation.evaluate_ocr import evaluate_ocr

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_all_evaluations():
    reports_dir = Path("reports/evaluation")
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    baseline_summary = {}
    
    # 1. Documents
    logger.info("Evaluating Documents (Routing, Extraction, Missing Fields)...")
    try:
        doc_report = evaluate_documents()
        baseline_summary["documents"] = doc_report.model_dump()
    except Exception as e:
        logger.error(f"Documents evaluation failed: {e}")
        baseline_summary["documents"] = {"status": "error", "message": str(e)}

    # 2. Legal RAG
    logger.info("Evaluating Legal RAG...")
    try:
        legal_report = evaluate_legal_rag()
        baseline_summary["legal_rag"] = legal_report.model_dump()
    except Exception as e:
        logger.error(f"Legal RAG evaluation failed: {e}")
        baseline_summary["legal_rag"] = {"status": "error", "message": str(e)}

    # 3. Writing
    logger.info("Evaluating Writing Automation...")
    try:
        writing_report = evaluate_writing()
        baseline_summary["writing"] = writing_report.model_dump()
    except Exception as e:
        logger.error(f"Writing evaluation failed: {e}")
        baseline_summary["writing"] = {"status": "error", "message": str(e)}

    # 4. OCR
    logger.info("Evaluating OCR Engine...")
    try:
        ocr_report = evaluate_ocr()
        baseline_summary["ocr"] = ocr_report.model_dump()
    except Exception as e:
        logger.error(f"OCR evaluation failed: {e}")
        baseline_summary["ocr"] = {"status": "error", "message": str(e)}

    # Save summary
    summary_path = reports_dir / "baseline_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(baseline_summary, f, ensure_ascii=False, indent=2)
        
    logger.info(f"Evaluation finished. Reports saved to {summary_path}")

if __name__ == "__main__":
    run_all_evaluations()
