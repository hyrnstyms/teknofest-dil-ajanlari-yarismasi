import json
from pathlib import Path


def test_kaymakamlik_curated_scenarios_have_locked_gold_coverage():
    path = Path("data/institutions/kaymakamlik/ornek_evraklar/curated_scenarios.jsonl")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert 12 <= len(rows) <= 15
    assert len({row["id"] for row in rows}) == len(rows)
    assert all(row["synthetic"] is True for row in rows)
    required = {
        "expected_document_type",
        "expected_process_intent",
        "expected_unit",
        "expected_missing_behavior",
        "expected_legal_source",
    }
    assert all(required <= set(row["gold"]) for row in rows)
    units = {row["gold"]["expected_unit"] for row in rows}
    assert {"yazi_isleri", "milli_egitim", "nufus", "sydv", "saglik", "tarim", "emniyet", "tapu"} <= units
    tags = {row["coverage_tag"] for row in rows}
    assert {"missing_ambiguous", "explicit_target", "official_correspondence", "information_request"} <= tags


def test_belediye_examples_cover_ambiguous_ruhsat_without_personal_data():
    text = Path("data/institutions/belediye/ornek_evraklar/13_ambiguous_ruhsat.txt").read_text(encoding="utf-8")

    assert "yapı ruhsatı" in text
    assert "işyeri açma ruhsatı" in text
    assert "anlaşılamamaktadır" in text
    assert "T.C. Kimlik" not in text