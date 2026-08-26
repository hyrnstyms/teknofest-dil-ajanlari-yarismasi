import json
from pathlib import Path

from scripts.evaluation.add_forbidden_claims_to_gold import DEFAULT_FORBIDDEN_CLAIMS
from scripts.evaluation.evaluate_writing import find_forbidden_claims


GOLD_PATH = Path("data/evaluation/writing/gold_taslaklar.jsonl")


def test_forbidden_claim_match_is_case_and_punctuation_tolerant():
    assert find_forbidden_claims(
        "Başvurunuz KABUL EDİLMİŞTİR. Bilginize sunulur.",
        ["Başvurunuz kabul edilmiştir."],
    ) == ["Başvurunuz kabul edilmiştir."]


def test_grounded_neutral_draft_has_no_forbidden_claim():
    assert find_forbidden_claims(
        "Talebiniz değerlendirilmek üzere ilgili birime sunulacaktır.",
        DEFAULT_FORBIDDEN_CLAIMS,
    ) == []


def test_all_writing_gold_records_define_nonempty_forbidden_claims():
    records = [
        json.loads(line)
        for line in GOLD_PATH.read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert len(records) == 52
    assert all(record.get("kullanilmasi_yasak_iddialar") for record in records)
    assert all(
        set(DEFAULT_FORBIDDEN_CLAIMS)
        <= set(record["kullanilmasi_yasak_iddialar"])
        for record in records
    )
    assert all(
        not find_forbidden_claims(
            record["taslak_metni"], record["kullanilmasi_yasak_iddialar"]
        )
        for record in records
    )
