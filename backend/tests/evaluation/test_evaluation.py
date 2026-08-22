from pathlib import Path

from scripts.evaluation.evaluate_legal_rag import (
    build_canonical_corpus,
    canonical_madde_from_retrieved,
    canonical_source_from_corpus_row,
    canonical_source_from_retrieved,
    load_active_qa_benchmark,
    normalize_madde,
    normalize_legal_source,
)
from backend.app.evaluation.schemas import EvaluationReport

def test_article_normalization():
    assert normalize_madde("Madde 3") == "3"
    assert normalize_madde("3.") == "3"
    assert normalize_madde("3-") == "3"
    assert normalize_madde("3") == "3"
    assert normalize_madde(3) == "3"
    
def test_legal_source_normalization():
    expected_sources = {
        "4982 Bilgi Edinme Hakkı Kanunu": "4982",
        "4982_bilgi_edinme_kanunu.pdf": "4982",
        "Bilgi Edinme Kanunu": "4982",
        "4982": "4982",
        "3071 Dilekçe Hakkı Kanunu": "3071",
        "3071_dilekce_hakki_kanunu.pdf": "3071",
        "3071": "3071",
        "5442 İl İdaresi Kanunu": "5442",
        "5442_il_idaresi_kanunu.pdf": "5442",
        "5442": "5442",
        "resmi yazışma yönetmeliği": "resmi_yazisma_yonetmeligi",
        "resmi_yazisma_yonetmeligi.pdf": "resmi_yazisma_yonetmeligi",
        "resmi yazışma kılavuzu": "resmi_yazisma_kilavuzu",
        "resmi_yazisma_kilavuzu.pdf": "resmi_yazisma_kilavuzu",
    }

    for source, expected in expected_sources.items():
        assert normalize_legal_source(source) == expected

def test_skipped_record_coverage():
    report = EvaluationReport(dataset_name="test")
    report.coverage.skipped_records += 1
    report.coverage.skip_reasons["source_not_found"] = 1
    assert report.coverage.skipped_records == 1
    assert report.coverage.skip_reasons["source_not_found"] == 1
    
def test_evaluation_schema_default_status():
    report = EvaluationReport(dataset_name="test")
    assert report.status == "pass"
    assert report.errors == []


def test_corpus_source_prefers_law_number():
    row = {"kaynak": "Bilgi Edinme Kanunu", "kanun_no": "4982"}
    assert canonical_source_from_corpus_row(row) == "4982"


def test_retrieved_source_falls_back_to_document_id():
    source = {"law_number": None, "document_id": "4982", "source": "Bilgi Edinme Kanunu"}
    assert canonical_source_from_retrieved(source) == "4982"


def test_retrieved_madde_falls_back_to_article():
    source = {"madde_no": None, "article": "11"}
    assert canonical_madde_from_retrieved(source) == "11"


def test_real_qa_benchmark_active_and_coverage_counts():
    project_root = Path(__file__).resolve().parents[3]
    canonical_set = build_canonical_corpus(project_root / "data" / "knowledge" / "statute_chunks.csv")
    items, stats = load_active_qa_benchmark(
        project_root / "data" / "evaluation" / "legal" / "qa_benchmark_gold.csv",
        canonical_set,
    )

    assert stats == {
        "raw": 290,
        "active": 266,
        "inactive": 24,
        "active_supported": 258,
        "active_unsupported": 8,
    }
    assert len(items) == 266
    assert {item["suite"] for item in items} == {"qa_benchmark"}
