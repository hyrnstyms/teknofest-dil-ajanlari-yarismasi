import pytest
from rapidfuzz import fuzz

from backend.app.agents.chat_agent import (
    FALLBACK_MESAJI,
    MEVZUAT_KANIT_BULUNAMADI_MESAJI,
    MEVZUAT_SERVIS_HATASI_MESAJI,
    SSS_LISTESI,
    _get_legal_agent,
    _normalize_text,
    handle_chat_message,
    handle_legal_question,
    is_mevzuat_sorusu,
    match_faq,
)


_LEGAL_AGENT_CACHE_INFO_AFTER_IMPORT = _get_legal_agent.cache_info()


FAQ_VARIATIONS = [
    ("Bu sistem ne işe yarar acaba?", "Bu sistem ne işe yarıyor?"),
    ("Bir evrakı sisteme nasıl yükleyebilirim?", "Evrak nasıl yüklerim?"),
    ("Hangi dosya türlerini yükleyebiliriz?", "Hangi dosya türlerini yükleyebilirim?"),
    ("Belgeyi analiz et düğmesi ne yapıyor?", "Belgeyi Analiz Et ne yapar?"),
    ("Analiz aşamalarında neler var?", "Analiz aşamaları nelerdir?"),
    ("API Mevzuat DB ve LLM durumları ne gösteriyor?", "API, Mevzuat DB ve LLM durumları neyi gösterir?"),
    ("Evrak analizi bölümünde neler görüyorum?", "Evrak Analizi bölümünde ne görüyorum?"),
    ("Evrak türü ifadesi nedir?", "Evrak Türü ne demek?"),
    ("İşlem niyeti ne anlama gelir?", "İşlem Niyeti ne demek?"),
    ("Belge ID tam olarak nedir?", "Belge ID nedir?"),
    ("Kısa özet alanı neyi anlatıyor?", "Kısa Özet nedir?"),
    ("Çıkarılan bilgiler kartında neler gösteriliyor?", "Çıkarılan Bilgiler bölümünde ne var?"),
    ("Resmi yazışma format durumu neyi gösteriyor?", "Format durumu nedir?"),
    ("Güven skoru ve güven oranı ne anlama geliyor?", "Güven skoru veya güven oranı ne demek?"),
    ("Önerilen birim ne demektir?", "Önerilen birim ne anlama geliyor?"),
    ("Yönlendirme gerekçesi ne anlama geliyor?", "Yönlendirme gerekçesi nedir?"),
    ("Eksik bilgi tespiti ne şekilde çalışıyor?", "Eksik bilgi tespiti nasıl çalışır?"),
    ("Personel incelemesi gerekli uyarısı nedir?", "Personel incelemesi gerekli ne demek?"),
    ("Mevzuat hukuki analiz bölümünde ne görebilirim?", "Mevzuat veya hukuki analiz bölümünde ne görüyorum?"),
    ("Mevzuat eşleşme oranı ne anlama geliyor?", "Mevzuat eşleşme oranı ne demek?"),
    ("Hazırlanan taslak nedir ve nasıl kullanılır?", "Taslak nedir, nasıl kullanılır?"),
    ("Taslağın türü neyi ifade ediyor?", "Taslak Türü ne demek?"),
    ("Resmi görünüm ile ham taslak arasındaki fark ne?", "Resmî Görünüm ve Ham Taslak arasındaki fark nedir?"),
    ("Taslağı DOCX olarak nasıl indirebilirim?", "Taslağı nasıl indiririm?"),
    ("Belgedeki QR kod ne işe yarıyor?", "Belgedeki QR kod ne işe yarar?"),
    ("Öncelik ve aciliyet nasıl hesaplanıyor?", "Öncelik veya aciliyet nasıl belirleniyor?"),
    ("Onaylama ve reddetme düğmeleri ne yapıyor?", "Onayla ve Reddet ne yapar?"),
    ("Neden personel onayı isteniyor?", "Personel Onayı Gerekiyor bölümü neden çıkıyor?"),
    ("Sistem bir konuda emin değilse ne yapar?", "Sistem bir konuda emin değilse ne olur?"),
    ("Sistem yanlış bilgi verdiyse ne yapmalıyım?", "Sistem yanlış bir şey söylediyse ne yapmalıyım?"),
    ("Vatandaşın eski başvurularını nerede görürüm?", "Aynı vatandaşın önceki evrakını nasıl görürüm?"),
    ("Farklı kurum profiline nasıl geçebilirim?", "Başka bir kurum profiliyle nasıl çalışırım?"),
    ("Yönetici paneli ve istatistikler nerede?", "Yönetici paneli veya istatistikler nerede?"),
    ("Sistem hangi mevzuatları biliyor?", "Sistem hangi mevzuatı biliyor?"),
    ("Chatbota mevzuatla ilgili soru sorabilir miyiz?", "Chatbot'a mevzuatla ilgili soru sorabilir miyim?"),
    ("Chatbota taslağı değiştirmesini söyleyebilir miyiz?", "Chatbot'a taslağı değiştirmesini söyleyebilir miyim?"),
    ("Sistem internete veya dışarıya veri gönderir mi?", "Sistem internete veya dışarıya veri gönderiyor mu?"),
    ("Bir hata mesajı alınca ne yapmalıyım?", "Bir hata mesajı aldım, ne yapmalıyım?"),
    ("Analiz yaklaşık ne kadar sürüyor?", "Analiz ne kadar sürer?"),
    ("Bu chatbotun sınırları nelerdir?", "Bu chatbot'un sınırları neler?"),
]


def _answer_for(question: str) -> str:
    return next(item["cevap"] for item in SSS_LISTESI if item["soru"] == question)


@pytest.mark.parametrize(("variation", "question"), FAQ_VARIATIONS)
def test_each_faq_matches_a_natural_variation(variation: str, question: str):
    assert match_faq(variation) == _answer_for(question)


def test_irrelevant_message_returns_fallback():
    assert match_faq("Akşam yemeği için hangi çorbayı pişirmeliyim?") == FALLBACK_MESAJI


def test_score_at_threshold_is_accepted_and_just_above_is_rejected():
    message = "Birim önerisinin anlamı nedir?"
    scores = [
        fuzz.partial_ratio(_normalize_text(message), _normalize_text(item["soru"]))
        for item in SSS_LISTESI
    ]
    best_score = max(scores)
    expected_answer = SSS_LISTESI[scores.index(best_score)]["cevap"]

    assert 65 <= best_score <= 80
    assert match_faq(message, esik=best_score) == expected_answer
    assert match_faq(message, esik=best_score + 0.01) == FALLBACK_MESAJI


def test_empty_message_always_returns_a_string_fallback():
    result = match_faq("")
    assert result == FALLBACK_MESAJI
    assert isinstance(result, str)


def test_every_faq_has_exactly_a_question_and_answer():
    assert len(FAQ_VARIATIONS) == len(SSS_LISTESI)
    assert all(set(item) == {"soru", "cevap"} for item in SSS_LISTESI)


def test_legal_agent_is_still_lazy_after_import_and_all_mod_a_tests():
    initial = _LEGAL_AGENT_CACHE_INFO_AFTER_IMPORT
    current = _get_legal_agent.cache_info()

    assert initial.hits + initial.misses == 0
    assert current.hits + current.misses == 0


@pytest.mark.parametrize(
    "message",
    [
        "4982 sayılı kanunda cevap süresi ne kadar?",
        "3071 sayılı Kanun Madde 7 neyi düzenler?",
        "Resmî yazışmalar yönetmeliğine göre sayı alanı nasıl yazılır?",
    ],
)
def test_is_mevzuat_sorusu_detects_explicit_legal_questions(message: str):
    assert is_mevzuat_sorusu(message) is True


@pytest.mark.parametrize(
    "message",
    [
        "Evrak nasıl yüklenir?",
        "Mevzuat eşleşme oranı ne demek?",
        "Chatbot'a mevzuatla ilgili soru sorabilir miyim?",
    ],
)
def test_is_mevzuat_sorusu_preserves_mod_a_usage_questions(message: str):
    assert is_mevzuat_sorusu(message) is False


class FakeLegalAgent:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def analyze(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.result


def test_handle_legal_question_calls_agent_and_formats_grounded_result(monkeypatch):
    agent = FakeLegalAgent({
        "answer": (
            "Mevzuat kaynağında soruyla ilgili şu bilgiler yer almaktadır:\n\n"
            "- Erişim on beş iş günü içinde sağlanır. "
            "[Bilgi Edinme Kanunu, 4982, Madde 11]"
        ),
        "evidence": [{
            "evidence": "Erişim on beş iş günü içinde sağlanır.",
            "source": "K1",
        }],
        "sources": [{
            "title": "Bilgi Edinme Kanunu",
            "law_number": "4982",
            "madde_no": "11",
        }],
        "retrieval_score": 0.824,
    })
    monkeypatch.setattr(
        "backend.app.agents.chat_agent._get_legal_agent",
        lambda: agent,
    )

    message = "4982 sayılı Kanun Madde 11 kapsamında erişim süresi nedir?"
    response = handle_legal_question(message)

    assert agent.calls == [{"query": message}]
    assert "[Bilgi Edinme Kanunu, 4982, Madde 11]" in response
    assert "Kaynak eşleşme skoru: %82,4" in response
    assert "hukuki doğruluk olasılığı değil" in response


def test_handle_legal_question_returns_agent_no_evidence_message(monkeypatch):
    agent = FakeLegalAgent({
        "answer": "İlgili mevzuat kaynağı bulunamadı.",
        "evidence": [],
        "sources": [],
        "retrieval_score": 0.0,
    })
    monkeypatch.setattr(
        "backend.app.agents.chat_agent._get_legal_agent",
        lambda: agent,
    )

    assert handle_legal_question("9999 sayılı kanun nedir?") == (
        "İlgili mevzuat kaynağı bulunamadı."
    )


def test_handle_legal_question_uses_safe_fallback_for_empty_result(monkeypatch):
    agent = FakeLegalAgent({"answer": "", "evidence": [], "sources": []})
    monkeypatch.setattr(
        "backend.app.agents.chat_agent._get_legal_agent",
        lambda: agent,
    )

    assert handle_legal_question("Kanun maddesi nedir?") == (
        MEVZUAT_KANIT_BULUNAMADI_MESAJI
    )


def test_handle_legal_question_hides_service_exception(monkeypatch):
    agent = FakeLegalAgent(error=ConnectionError("Qdrant bağlantısı kurulamadı"))
    monkeypatch.setattr(
        "backend.app.agents.chat_agent._get_legal_agent",
        lambda: agent,
    )

    assert handle_legal_question("3071 sayılı kanun nedir?") == (
        MEVZUAT_SERVIS_HATASI_MESAJI
    )


def test_handle_chat_message_routes_legal_question_first(monkeypatch):
    monkeypatch.setattr(
        "backend.app.agents.chat_agent.handle_legal_question",
        lambda message: f"LEGAL:{message}",
    )

    message = "4982 sayılı kanunda süre ne kadar?"
    assert handle_chat_message(message) == f"LEGAL:{message}"


def test_handle_chat_message_keeps_mod_a_behavior():
    message = "Evrakı sisteme nasıl yükleyebilirim?"
    assert handle_chat_message(message) == match_faq(message)
