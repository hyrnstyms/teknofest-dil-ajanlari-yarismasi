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


def test_retrievers_share_default_process_services(monkeypatch):
    import backend.app.rag.retriever as retriever_module

    embeddings = []
    stores = []
    monkeypatch.setattr(
        "backend.app.rag.embedding_service.EmbeddingService",
        lambda: embeddings.append(object()) or embeddings[-1],
    )
    monkeypatch.setattr(
        "backend.app.rag.qdrant_store.QdrantStore",
        lambda: stores.append(object()) or stores[-1],
    )
    retriever_module.get_shared_embedding_service.cache_clear()
    retriever_module.get_shared_qdrant_store.cache_clear()
    try:
        first = Retriever()
        second = Retriever()
        assert first.embedding_service is second.embedding_service
        assert first.store is second.store
        assert len(embeddings) == 1
        assert len(stores) == 1
    finally:
        retriever_module.get_shared_embedding_service.cache_clear()
        retriever_module.get_shared_qdrant_store.cache_clear()