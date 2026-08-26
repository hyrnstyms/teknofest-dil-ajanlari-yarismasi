from backend.app.rag.point_ids import deterministic_point_id


def test_different_chunks_under_same_article_have_different_ids():
    first = deterministic_point_id("3071", "7", 0, "Birinci metin")
    second = deterministic_point_id("3071", "7", 1, "İkinci metin")

    assert first != second


def test_same_chunk_always_has_same_id():
    first = deterministic_point_id("3071", "7", 3, "Aynı metin")
    second = deterministic_point_id("3071", "7", 3, "Aynı metin")

    assert first == second


def test_whitespace_normalization_is_stable():
    first = deterministic_point_id("3071", "7", 3, "Aynı\n  metin")
    second = deterministic_point_id("3071", "7", 3, "Aynı metin")

    assert first == second
