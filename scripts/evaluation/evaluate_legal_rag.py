import json
import csv
from pathlib import Path
from backend.app.agents.legal_agent import LegalAgent
from backend.app.evaluation.schemas import EvaluationReport, CoverageInfo
from backend.app.evaluation.adapters import normalize_turkish_label
import re

NORMALIZED_DOCUMENT_IDS = {
    "bilgiedinmekanunu": "4982",
    "dilekce_hakki_kanunu": "3071",
    "3071_dilekce_hakki_kanunu": "3071",
    "resmi_yazisma_kurallari": "resmi_yazisma_kurallari", 
    "resmi_yazisma_kilavuzu": "resmi_yazisma_kilavuzu",
    "kvkk": "6698",
    "cezamuhakemesikanunu": "5271"
}

def normalize_legal_source(source: str) -> str:
    """Normalize legal source string to canonical ID/law number"""
    if not source:
        return ""
    # strip .pdf BEFORE normalization
    s = str(source).replace(".pdf", "")
    norm = normalize_turkish_label(s)
    norm = re.sub(r'\s+', '_', norm)
    norm = norm.replace("hakk", "hakki")
    norm = norm.replace("hakkii", "hakki")
    
    # Try mapping
    return NORMALIZED_DOCUMENT_IDS.get(norm, norm)

def normalize_madde(madde: str) -> str:
    if not madde:
        return ""
    m = str(madde).lower().strip()
    m = m.replace("madde", "").replace(".", "").replace("-", "").strip()
    return m

def build_canonical_corpus() -> set:
    canonical_set = set()
    csv_path = Path("data/knowledge/statute_chunks.csv")
    if not csv_path.exists():
        return canonical_set
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            src = normalize_legal_source(row.get("kaynak", ""))
            madde = normalize_madde(row.get("madde_no", ""))
            if src and madde:
                canonical_set.add(f"{src}|{madde}")
    return canonical_set

def evaluate_legal_rag() -> EvaluationReport:
    report = EvaluationReport(dataset_name="legal_rag")
    agent = LegalAgent()
    canonical_set = build_canonical_corpus()
    
    total = 0
    matched_corpus = 0
    skipped = 0
    
    # metrics
    hits_1 = 0
    hits_3 = 0
    hits_5 = 0
    mrr_sum = 0.0
    
    items_to_evaluate = []
    
    # 1. Load rag_test_seti.jsonl (45)
    p1 = Path("data/evaluation/legal/rag_test_seti.jsonl")
    if p1.exists():
        with open(p1, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                items_to_evaluate.append({
                    "id": f"rag_{len(items_to_evaluate)}",
                    "question": data.get("soru", ""),
                    "source": data.get("kaynak_dokuman", ""),
                    "madde": data.get("dogru_madde_no", "")
                })
                
    # 2. Load qa_benchmark_gold.csv (290)
    p2 = Path("data/evaluation/legal/qa_benchmark_gold.csv")
    if p2.exists():
        with open(p2, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                items_to_evaluate.append({
                    "id": f"qa_{i}",
                    "question": row.get("soru", ""),
                    "source": row.get("kaynak", ""),
                    "madde": row.get("madde_no", "")
                })

    for item in items_to_evaluate:
        total += 1
        gold_src = normalize_legal_source(item["source"])
        gold_madde = normalize_madde(item["madde"])
        canonical_key = f"{gold_src}|{gold_madde}"
        
        if canonical_key not in canonical_set:
            report.unsupported["unsupported_corpus"] = report.unsupported.get("unsupported_corpus", 0) + 1
            report.coverage.skip_reasons["corpus_missing"] = report.coverage.skip_reasons.get("corpus_missing", 0) + 1
            continue
            
        matched_corpus += 1
        
        try:
            sources = agent.retriever.search_legal(query=item["question"], limit=5)
            # res = agent.analyze(item["question"])
            # sources = res.get("sources", [])
            retrieved_keys = []
            
            for s in sources:
                src_val = normalize_legal_source(s.get("law_number", s.get("source", "")))
                mad_val = normalize_madde(s.get("madde_no", s.get("article", "")))
                retrieved_keys.append(f"{src_val}|{mad_val}")
                
            rank = -1
            for idx, rk in enumerate(retrieved_keys):
                if rk == canonical_key:
                    rank = idx + 1
                    break
                    
            if rank != -1:
                if rank <= 1: hits_1 += 1
                if rank <= 3: hits_3 += 1
                if rank <= 5: hits_5 += 1
                mrr_sum += 1.0 / rank
            else:
                if len(report.failure_examples) < 10:
                    report.failure_examples.append({
                        "step": "retrieval",
                        "id": item["id"],
                        "gold": canonical_key,
                        "retrieved": retrieved_keys[:3]
                    })
        except Exception as e:
            report.runtime_failures += 1
            reason = type(e).__name__
            report.coverage.skip_reasons[reason] = report.coverage.skip_reasons.get(reason, 0) + 1

    report.coverage.total_records = total
    report.coverage.evaluable_records = matched_corpus - report.runtime_failures
    report.coverage.skipped_records = total - matched_corpus
    if total > 0:
        report.coverage.coverage_rate = matched_corpus / total
        
    evaluable = report.coverage.evaluable_records
    if evaluable > 0:
        report.metrics["hit@1"] = hits_1 / evaluable
        report.metrics["hit@3"] = hits_3 / evaluable
        report.metrics["hit@5"] = hits_5 / evaluable
        report.metrics["mrr"] = mrr_sum / evaluable
        
    return report

if __name__ == "__main__":
    rep = evaluate_legal_rag()
    print(rep.model_dump_json(indent=2))
