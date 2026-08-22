import json
import csv
from pathlib import Path
from typing import Any
from backend.app.agents.legal_agent import LegalAgent
from backend.app.evaluation.schemas import EvaluationReport
from backend.app.evaluation.adapters import normalize_turkish_label
import re

NORMALIZED_DOCUMENT_IDS = {
    "4982": "4982",
    "4982bilgiedinmehakkikanunu": "4982",
    "4982_bilgi_edinme_kanunu": "4982",
    "bilgiedinmekanunu": "4982",
    "3071": "3071",
    "3071dilekcehakkikanunu": "3071",
    "dilekce_hakki_kanunu": "3071",
    "3071_dilekce_hakki_kanunu": "3071",
    "5442": "5442",
    "5442ilidaresikanunu": "5442",
    "5442_il_idaresi_kanunu": "5442",
    "resmiyazismayonetmeligi": "resmi_yazisma_yonetmeligi",
    "resmi_yazisma_yonetmeligi": "resmi_yazisma_yonetmeligi",
    "resmiyazismakilavuzu": "resmi_yazisma_kilavuzu",
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

def _clean_metadata_value(value: Any) -> str:
    if value is None:
        return ""
    cleaned = str(value).strip()
    if cleaned.lower() in {"", "nan", "none", "null"}:
        return ""
    return cleaned


def canonical_source_from_corpus_row(row: dict[str, Any]) -> str:
    source_value = (_clean_metadata_value(row.get("kanun_no")) or _clean_metadata_value(row.get("kaynak")))
    return normalize_legal_source(source_value)


def canonical_source_from_retrieved(source: dict[str, Any]) -> str:
    source_value = (_clean_metadata_value(source.get("law_number")) or _clean_metadata_value(source.get("document_id")) or _clean_metadata_value(source.get("source")))
    return normalize_legal_source(source_value)


def canonical_madde_from_retrieved(source: dict[str, Any]) -> str:
    madde_value = (_clean_metadata_value(source.get("madde_no")) or _clean_metadata_value(source.get("article")))
    return normalize_madde(madde_value)


def build_canonical_corpus(csv_path: Path = Path("data/knowledge/statute_chunks.csv")) -> set[str]:
    canonical_set = set()
    if not csv_path.exists():
        return canonical_set
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            src = canonical_source_from_corpus_row(row)
            # QA rows use descriptive source names, while the canonical ID now
            # prefers kanun_no. Retain the name as a compatibility alias.
            source_alias = normalize_legal_source(_clean_metadata_value(row.get("kaynak")))
            madde = normalize_madde(_clean_metadata_value(row.get("madde_no")))
            if src and madde:
                canonical_set.add(f"{src}|{madde}")
            if source_alias and madde:
                canonical_set.add(f"{source_alias}|{madde}")
    return canonical_set


def load_active_qa_benchmark(csv_path: Path, canonical_set: set[str]) -> tuple[list[dict[str, str]], dict[str, int]]:
    items: list[dict[str, str]] = []
    stats = {"raw": 0, "active": 0, "inactive": 0, "active_supported": 0, "active_unsupported": 0}
    if not csv_path.exists():
        return items, stats
    with open(csv_path, "r", encoding="utf-8") as f:
        for index, row in enumerate(csv.DictReader(f)):
            stats["raw"] += 1
            if _clean_metadata_value(row.get("is_active")).lower() != "true":
                stats["inactive"] += 1
                continue
            stats["active"] += 1
            source = _clean_metadata_value(row.get("kaynak"))
            madde = _clean_metadata_value(row.get("madde_no"))
            canonical_key = f"{normalize_legal_source(source)}|{normalize_madde(madde)}"
            if canonical_key in canonical_set:
                stats["active_supported"] += 1
            else:
                stats["active_unsupported"] += 1
            items.append({"id": _clean_metadata_value(row.get("row_id")) or f"qa_{index}", "suite": "qa_benchmark", "question": _clean_metadata_value(row.get("soru")), "source": source, "madde": madde})
    return items, stats

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
                    "id": data.get("id") or f"rag_{len(items_to_evaluate)}",
                    "suite": "targeted_rag",
                    "question": data.get("soru", ""),
                    "source": data.get("kaynak_dokuman", ""),
                    "madde": data.get("dogru_madde_no", "")
                })
                
    # 2. Load qa_benchmark_gold.csv (290)
    p2 = Path("data/evaluation/legal/qa_benchmark_gold.csv")
    qa_items, qa_stats = load_active_qa_benchmark(p2, canonical_set)
    items_to_evaluate.extend(qa_items)
    report.unsupported["qa_benchmark"] = qa_stats

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
                src_val = canonical_source_from_retrieved(s)
                mad_val = canonical_madde_from_retrieved(s)
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
                        "suite": item["suite"],
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
