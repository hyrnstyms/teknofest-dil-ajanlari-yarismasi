from backend.app.evaluation.adapters import normalize_routing_unit
from scripts.evaluation.evaluate_legal_rag import normalize_madde, normalize_legal_source
from backend.app.evaluation.schemas import EvaluationReport
from scripts.evaluation.run_all import run_all

def test_article_normalization():
    assert normalize_madde("Madde 3") == "3"
    assert normalize_madde("3.") == "3"
    assert normalize_madde("3-") == "3"
    assert normalize_madde("3") == "3"
    assert normalize_madde(3) == "3"
    
def test_legal_source_normalization():
    assert normalize_legal_source("4982 Bilgi Edinme Hakkı Kanunu") == "4982_bilgi_edinme_kanunu"
    assert normalize_legal_source("4982_bilgi_edinme_kanunu.pdf") == "4982_bilgi_edinme_kanunu"
    assert normalize_legal_source("3071 Dilekçe Hakkı Kanunu") == "3071_dilekce_hakki_kanunu"
    assert normalize_legal_source("resmi yazışma yönetmeliği") == "resmi_yazisma_yonetmeligi"

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
