import pytest

from backend.app.agents.document_agent import DocumentAgent


class StaticLLM:
    def chat(self, *args, **kwargs):
        return "{}"

    def get_model_name(self):
        return "static"

    def get_provider_name(self):
        return "test"


@pytest.fixture
def agent():
    return DocumentAgent(llm=StaticLLM())


@pytest.mark.parametrize(
    ("text", "initial_type", "initial_intent", "expected_type", "expected_intent"),
    [
        ("T.C. ORNEK KAYMAKAMLIGINA\nKonu: Park\nPark aydinlatmalarinin onarilmasini arz ederim.", "dilekce", "bilgi_talebi", "dilekce", "basvuru"),
        ("T.C. ORNEK BELEDIYE BASKANLIGINA\n4982 sayili Kanun bilgi edinme kapsaminda faaliyet raporunu talep ediyorum.", "rapor", "bilgi_talebi", "dilekce", "bilgi_talebi"),
        ("T.C. ORNEK BELEDIYE BASKANLIGINA\nGece gürültüsü nedeniyle şikâyetçiyim. Gereğinin yapılmasını arz ederim.", "dilekce", "diger", "dilekce", "sikayet"),
        ("T.C. ORNEK KAYMAKAMLIGI\nSayi: 125\nKonu: Liste\nILCE MILLI EGITIM MUDURLUGUNE\nListenin gonderilmesi hususunda geregini rica ederim.", "dilekce", "bilgi_talebi", "resmi_yazi", "iletim"),
        ("T.C. ORNEK BELEDIYE BASKANLIGINA\nKonu: Isyeri acma ruhsati basvurusu\nRuhsat basvurumun isleme alinmasini arz ederim.", "form", "basvuru", "form", "basvuru"),
        ("T.C. ORNEK KAYMAKAMLIGI\nSayi: 210\nKonu: Toplanti\nILGILI BIRIMLERE\nToplanti yapilacaktir. Bilgilerinizi rica ederim.", "resmi_yazi", "bildirim", "resmi_yazi", "bildirim"),
        ("T.C. ORNEK BELEDIYE BASKANLIGI\nSayi: 88\nKonu: Basvurunuza cevap\nIlgi: Dilekceniz\nBasvurunuz incelenmis olup uygun bulundugu bilgilerinize sunulur.", "karar", "bildirim", "resmi_yazi", "cevap"),
    ],
)
def test_high_confidence_semantic_validation(
    agent, text, initial_type, initial_intent, expected_type, expected_intent
):
    result, _ = agent._validate_semantic_classification(
        text,
        {"document_type": initial_type, "process_intent": initial_intent, "evidence": []},
    )
    assert result["document_type"] == expected_type
    assert result["process_intent"] == expected_intent


def test_konu_alone_does_not_override_to_official(agent):
    result, overridden = agent._validate_semantic_classification(
        "Konu hakkinda bilgi almak istiyorum.",
        {"document_type": "dilekce", "process_intent": "diger", "evidence": []},
    )
    assert result["document_type"] == "dilekce"
    assert overridden is False


def test_incidental_complaint_word_does_not_override_intent(agent):
    result, overridden = agent._validate_semantic_classification(
        "Toplantida sikayet sureclerine iliskin genel bilgi verildi.",
        {"document_type": "resmi_yazi", "process_intent": "bildirim", "evidence": []},
    )
    assert result["process_intent"] == "bildirim"
    assert overridden is False
