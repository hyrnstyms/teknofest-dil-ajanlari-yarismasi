from scripts.evaluation.evaluate_documents import evaluate_documents
from pathlib import Path
import json

def run_mini_eval():
    # backup
    Path("data/evaluation/synthetic/evraklar_backup.jsonl").write_text(Path("data/evaluation/synthetic/evraklar.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
    
    # limit to 5
    lines = Path("data/evaluation/synthetic/evraklar_backup.jsonl").read_text(encoding="utf-8").splitlines()[:5]
    Path("data/evaluation/synthetic/evraklar.jsonl").write_text("\n".join(lines), encoding="utf-8")
    
    # run
    report = evaluate_documents()
    print("\n--- METRICS (5 EXAMPLES) ---")
    print(json.dumps(report.metrics, indent=2))
    
    # restore
    Path("data/evaluation/synthetic/evraklar.jsonl").write_text(Path("data/evaluation/synthetic/evraklar_backup.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
    
if __name__ == '__main__':
    run_mini_eval()
