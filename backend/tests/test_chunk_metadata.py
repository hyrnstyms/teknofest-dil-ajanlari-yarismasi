from backend.app.rag.chunker import extract_law_number


def _document(filename: str) -> dict:
    return {"metadata": {"filename": filename}, "source": filename}


def test_extract_law_number_supports_prefixed_regulation_filenames():
    assert extract_law_number(_document("3194_imar_kanunu.pdf")) == "3194"
    assert extract_law_number(_document("3294_sosyal_yardimlasma_kanunu.pdf")) == "3294"
    assert extract_law_number(_document("5442_il_idaresi_kanunu.pdf")) == "5442"


def test_extract_law_number_supports_named_regulations():
    assert extract_law_number(
        _document("isyeri_acma_calisma_ruhsatlari_yonetmeligi.pdf")
    ) == "isyeri_acma_calisma_ruhsatlari_yonetmeligi"
    assert extract_law_number(
        _document("valilik_kaymakamlik_birimleri_yonetmeligi.pdf")
    ) == "valilik_kaymakamlik_birimleri_yonetmeligi"
