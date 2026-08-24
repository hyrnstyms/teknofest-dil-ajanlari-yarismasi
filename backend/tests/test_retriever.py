from types import SimpleNamespace

from backend.app.rag.retriever import Retriever


def test_result_mapping_preserves_new_payload_metadata():
    point = SimpleNamespace(
        score=0.91,
        payload={
            "document_id": "statute_4982",
            "source": "data/knowledge/statute_chunks.csv",
            "law_number": "4982",
            "madde_no": "11",
            "text": "...",
        },
    )

    result = Retriever._result_from_point(point)

    assert result["law_number"] == "4982"
    assert result["document_id"] == "statute_4982"
    assert result["madde_no"] == "11"


def test_result_mapping_falls_back_to_legacy_payload_metadata():
    point = SimpleNamespace(
        score=0.84,
        payload={
            "document_id": "4982",
            "metadata": {
                "source": "Bilgi Edinme Kanunu",
                "article": "11",
            },
            "text": "...",
        },
    )

    result = Retriever._result_from_point(point)

    assert result["document_id"] == "4982"
    assert result["source"] == "Bilgi Edinme Kanunu"
    assert result["article"] == "11"
