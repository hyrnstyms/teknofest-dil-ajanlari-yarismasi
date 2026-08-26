from scripts.index_document_examples import (
    build_example_chunks,
    sanitize_example_text,
)


def test_document_examples_are_labelled_and_privacy_minimized():
    chunks = build_example_chunks("all")

    assert chunks
    assert {chunk["metadata"]["institution"] for chunk in chunks} == {
        "belediye",
        "kaymakamlik",
    }
    assert all(chunk["metadata"]["expected_unit"] for chunk in chunks)
    assert all(chunk["metadata"]["rag_domain"] == "document" for chunk in chunks)
    assert all(chunk["corpus_type"] == "document_knowledge" for chunk in chunks)
    assert not any("12345678901" in chunk["text"] for chunk in chunks)


def test_sanitizer_removes_identity_and_contact_lines():
    text = "BAŞVURAN: Test Kişi\nTC KİMLİK: 12345678901\nKONU: Yol onarımı"

    assert sanitize_example_text(text) == "KONU: Yol onarımı"
