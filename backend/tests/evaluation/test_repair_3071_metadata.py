from types import SimpleNamespace

import pytest

from scripts.evaluation.repair_3071_metadata import (
    EXPECTED_POINT_COUNT, infer_article, plan_repairs, repaired_payload,
)


def test_infer_article_from_3071_heading():
    assert infer_article("Madde 7 – Başvuruların sonucu...") == "7"
    assert infer_article("DİLEKÇE HAKKININ KULLANILMASINA DAİR KANUN") == ""


def test_repaired_payload_preserves_metadata_and_adds_canonical_fields():
    update, article = repaired_payload(
        {"text": "Madde 4 – Zorunlu şartlar", "metadata": {"rag_eligible": True}}
    )
    assert article == "4"
    assert update["law_number"] == "3071"
    assert update["madde_no"] == update["article"] == "4"
    assert update["metadata"] == {
        "rag_eligible": True, "law_number": "3071", "madde_no": "4", "article": "4",
    }


def test_plan_repairs_refuses_unexpected_point_count():
    points = [
        SimpleNamespace(
            id=str(index),
            payload={"document_id": "3071kanun", "rag_domain": "legal"},
        )
        for index in range(EXPECTED_POINT_COUNT - 1)
    ]
    with pytest.raises(RuntimeError, match="Refusing to continue"):
        plan_repairs(points)
