"""Focused behavior tests for the public TransferAgent contract."""

from backend.app.agents.transfer_agent import TransferAgent


def _transfer(**overrides):
    payload = {
        "kaynak_kurum": "kaymakamlik",
        "hedef_kurum": "belediye",
        "konu": "Altyapı koordinasyonu",
        "evrak_ozeti": "Yol ve altyapı bilgilerinin paylaşılması talebi",
    }
    payload.update(overrides)
    return TransferAgent().transfer(**payload)


def test_transfer_marks_supported_target_as_recommendation_only():
    result = _transfer()

    assert result["transfer_required"] is True
    assert result["capability_type"] == "recommendation"
    assert result["execution_status"] == "not_executed"


def test_transfer_loads_target_institution_and_unit():
    result = _transfer()

    assert result["hedef_kurum"] == "belediye"
    assert result["hedef_kurum_adi"] == "Örenli Belediyesi"
    assert result["hedef_birim"]


def test_transfer_uses_official_interinstitutional_document_types():
    result = _transfer()

    assert result["yazi_turu"] == "ust_yazi"
    assert result["evrak_turu"] == "kurumlar_arasi_yazi"
    assert result["yasal_dayanak"]


def test_transfer_preserves_source_content():
    result = _transfer(konu="Özel konu", evrak_ozeti="Özel evrak özeti")

    assert result["kaynak_kurum"] == "kaymakamlik"
    assert result["konu"] == "Özel konu"
    assert result["ozet"] == "Özel evrak özeti"


def test_transfer_missing_target_profile_fails_safe():
    result = _transfer(hedef_kurum="olmayan_kurum")

    assert result["transfer_required"] is False
    assert result["needs_human_review"] is True
    assert "Hedef kurum profili bulunamadı" in result["warnings"][0]


def test_transfer_process_intent_selects_matching_typical_unit():
    result = _transfer(process_intent="sikayet")

    assert result["transfer_required"] is True
    assert result["hedef_birim"] == "Fen İşleri Müdürlüğü"
    assert result["needs_human_review"] is False
