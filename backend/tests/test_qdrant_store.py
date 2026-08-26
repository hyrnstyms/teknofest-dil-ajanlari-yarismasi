from backend.app.rag import qdrant_store


def test_qdrant_store_passes_api_key_to_client(monkeypatch):
    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(qdrant_store, "QdrantClient", fake_client)

    qdrant_store.QdrantStore(
        url="https://qdrant.example.invalid",
        api_key="test-key",
        timeout=45,
    )

    assert captured == {
        "url": "https://qdrant.example.invalid",
        "port": None,
        "api_key": "test-key",
        "prefer_grpc": False,
        "timeout": 45,
    }


def test_qdrant_store_preserves_keyless_local_connection(monkeypatch):
    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(qdrant_store, "QdrantClient", fake_client)

    qdrant_store.QdrantStore(
        url="http://localhost:6333",
        api_key="",
    )

    assert captured == {
        "url": "http://localhost:6333",
        "port": None,
        "api_key": None,
        "prefer_grpc": False,
        "timeout": qdrant_store.QDRANT_TIMEOUT_SECONDS,
    }
