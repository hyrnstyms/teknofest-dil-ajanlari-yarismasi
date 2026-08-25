import csv
import json
from collections import Counter
from pathlib import Path

import pytest

import scripts.evaluation.evaluate_legal_rag as evaluator
from scripts.evaluation.legal_answer_diagnostic import (
    AttributionStatus,
    attribute_answer_to_article,
    normalize_answer,
    split_context_into_articles,
)
from scripts.evaluation.evaluate_legal_rag import normalize_madde


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _attribute(anchor: str, actual: str):
    context = (
        f"MADDE {anchor} - Başlangıç maddesine ait ilgisiz düzenleme.\n"
        f"MADDE {actual} - Başvurunun kesin cevabı otuz gün içinde bildirilir."
    )
    return attribute_answer_to_article(
        context,
        "Başvurunun kesin cevabı otuz gün içinde bildirilir.",
        anchor,
        f"{anchor},{actual}",
        normalize_madde,
    )


def test_answer_normalization_is_turkish_aware():
    assert normalize_answer("İDARÎ İşlem") == "idari işlem"
    assert normalize_answer("ÇAĞRI, ŞÜPHELİ; ölçüm!") == "çağri şüpheli ölçüm"

def test_context_is_split_on_article_boundaries():
    segments = split_context_into_articles(
        "MADDE 19 - Birinci hüküm.\nMADDE 20 - İkinci hüküm.",
        "19,20",
        normalize_madde,
    )
    assert [segment.article for segment in segments] == ["19", "20"]


@pytest.mark.parametrize(
    ("anchor", "actual"),
    [("259", "260"), ("19", "20"), ("264", "265")],
)
def test_neighbor_anchor_is_high_confidence_mismatch(anchor, actual):
    result = _attribute(anchor, actual)
    assert (result.status, result.primary_article) == (
        AttributionStatus.HIGH_CONFIDENCE_MISMATCH,
        actual,
    )


def test_single_article_same():
    result = attribute_answer_to_article(
        "Tek maddelik bağlamdaki kesin cevap budur.",
        "Kesin cevap budur.",
        "7",
        "7",
        normalize_madde,
    )
    assert (result.status, result.primary_article, result.article_count) == (
        AttributionStatus.HIGH_CONFIDENCE_SAME,
        "7",
        1,
    )


def test_repeated_exact_answer_is_ambiguous():
    context = "MADDE 1 - Aynı cevap burada.\nMADDE 2 - Aynı cevap burada."
    result = attribute_answer_to_article(
        context, "Aynı cevap burada.", "1", "1,2", normalize_madde
    )
    assert result.status == AttributionStatus.AMBIGUOUS


def test_unsupported_answer():
    context = "MADDE 1 - Elma armut.\nMADDE 2 - Masa sandalye."
    result = attribute_answer_to_article(
        context, "Ceza zamanaşımı düzenlemesi", "1", "1,2", normalize_madde
    )
    assert result.status == AttributionStatus.ANSWER_NOT_SUPPORTED


def test_temporary_and_normal_article_identity_limitation_is_explicit():
    segments = split_context_into_articles(
        "GEÇİCİ MADDE 1 - Geçici hüküm.\nMADDE 1 - Kalıcı hüküm.",
        "1,1",
        normalize_madde,
    )
    assert [segment.article for segment in segments] == ["1", "1"]


def test_real_qa_attribution_invariants_and_known_examples():
    counts = Counter()
    attributions = {}
    path = PROJECT_ROOT / "data/evaluation/legal/qa_benchmark_gold.csv"
    with path.open(encoding="utf-8") as stream:
        active_rows = [
            row for row in csv.DictReader(stream)
            if row["is_active"].lower() == "true"
        ]

    for row in active_rows:
        result = attribute_answer_to_article(
            row["context"],
            row["cevap"],
            row["madde_no"],
            row["madde_nolari_context"],
            normalize_madde,
        )
        counts[result.status] += 1
        attributions[row["row_id"].split(".")[0]] = result
        if result.status in {
            AttributionStatus.HIGH_CONFIDENCE_SAME,
            AttributionStatus.HIGH_CONFIDENCE_MISMATCH,
        }:
            assert result.primary_article

    assert len(active_rows) == 266
    assert sum(counts.values()) == 266
    assert set(counts) <= set(AttributionStatus)
    assert attributions["3367"].primary_article == "260"
    assert attributions["3379"].primary_article == "265"
    assert attributions["7630"].primary_article == "20"
    assert attributions["8061"].primary_article == "244"

def test_diagnostic_integration_does_not_change_real_fixture_legacy_metrics(
    monkeypatch,
):
    canonical = evaluator.build_canonical_corpus()
    aliases = evaluator.build_source_aliases()
    qa_items, _ = evaluator.load_active_qa_benchmark(
        PROJECT_ROOT / "data/evaluation/legal/qa_benchmark_gold.csv",
        canonical,
        aliases,
    )
    expected = {
        item["question"]: (item["source"], normalize_madde(item["madde"]))
        for item in qa_items
    }
    targeted_path = PROJECT_ROOT / "data/evaluation/legal/rag_test_seti.jsonl"
    for line in targeted_path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        expected[row["soru"]] = (
            evaluator.normalize_legal_source(row["kaynak_dokuman"]),
            normalize_madde(row["dogru_madde_no"]),
        )

    class DeterministicRetriever:
        def search_legal(self, query, limit=5):
            source, article = expected[query]
            rank = sum(query.encode("utf-8")) % 6
            results = [
                {"law_number": "deterministic_distractor", "madde_no": str(index)}
                for index in range(1, 6)
            ]
            if rank:
                results[rank - 1] = {"law_number": source, "madde_no": article}
            return results[:limit]

    class FakeAgent:
        def __init__(self):
            self.retriever = DeterministicRetriever()

    monkeypatch.setattr(evaluator, "LegalAgent", FakeAgent)
    monkeypatch.chdir(PROJECT_ROOT)

    real_attribution = evaluator.attribute_answer_to_article

    def fail_if_diagnostic_attribution_runs(*args, **kwargs):
        raise AssertionError("diagnostic attribution ran while disabled")

    monkeypatch.setattr(
        evaluator,
        "attribute_answer_to_article",
        fail_if_diagnostic_attribution_runs,
    )
    legacy_only = evaluator.evaluate_legal_rag(
        include_answer_aware_diagnostic=False
    )

    monkeypatch.setattr(
        evaluator,
        "attribute_answer_to_article",
        real_attribution,
    )
    with_diagnostic = evaluator.evaluate_legal_rag(
        include_answer_aware_diagnostic=True
    )
    # The restored 45-record targeted fixture participates in coverage;
    # diagnostic enablement must still be fully isolated from legacy metrics.
    assert legacy_only.coverage.evaluable_records == 276
    assert with_diagnostic.coverage.evaluable_records == 276
    assert with_diagnostic.metrics == legacy_only.metrics
    assert set(with_diagnostic.metrics) == {"hit@1", "hit@3", "hit@5", "mrr"}
    assert legacy_only.diagnostics == {}
    assert "answer_aware_not_official" in with_diagnostic.diagnostics
