from scripts.evaluation.evaluate_legal_rag import evaluate_legal_rag
from pathlib import Path
import json

def run_mini_eval():
    # backup
    orig_path = Path("data/evaluation/legal/rag_test_seti.jsonl")
    backup_path = Path("data/evaluation/legal/rag_test_seti_backup.jsonl")
    backup_path.write_text(orig_path.read_text(encoding="utf-8"), encoding="utf-8")
    
    # limit to 5
    lines = backup_path.read_text(encoding="utf-8").splitlines()[:5]
    orig_path.write_text("\n".join(lines), encoding="utf-8")
    
    # run
    report = evaluate_legal_rag()
    
    print("\n--- METRICS (5 EXAMPLES) ---")
    print(json.dumps(report.metrics, indent=2))
    
    print("\n--- FAILURE EXAMPLES ---")
    print(json.dumps(report.failure_examples, indent=2))
    
    # restore
    orig_path.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
    
if __name__ == '__main__':
    run_mini_eval()
