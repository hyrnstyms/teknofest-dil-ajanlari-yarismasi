import pytest
from rapidfuzz import fuzz

from backend.app.agents.chat_agent import (
    FALLBACK_MESAJI,
    SSS_LISTESI,
    _normalize_text,
    match_faq,
)


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
