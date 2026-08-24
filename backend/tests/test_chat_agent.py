import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from rapidfuzz import fuzz

from backend.app.agents.chat_agent import (
    FALLBACK_MESAJI,
    MEVZUAT_KANIT_BULUNAMADI_MESAJI,
    MEVZUAT_SERVIS_HATASI_MESAJI,
    SSS_LISTESI,
    TASLAK_DUZENLEME_GUVENLI_FALLBACK_MESAJI,
    TASLAK_DUZENLEME_SISTEM_PROMPTU,
    _get_evren_client,
    _get_legal_agent,
    _normalize_text,
    handle_chat_message,
    handle_draft_edit,
    handle_legal_question,
    is_mevzuat_sorusu,
    is_taslak_duzenleme_talebi,
    match_faq,
)


_LEGAL_AGENT_CACHE_INFO_AFTER_IMPORT = _get_legal_agent.cache_info()
_EVREN_CLIENT_CACHE_INFO_AFTER_IMPORT = _get_evren_client.cache_info()


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


def test_evren_client_is_still_lazy_after_import_and_all_mod_a_tests():
    initial = _EVREN_CLIENT_CACHE_INFO_AFTER_IMPORT
    current = _get_evren_client.cache_info()

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


class FakeEvrenClient:
    def __init__(self, *, content=None, error=None):
        self.content = content
        self.error = error
        self.calls = []
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self.content),
                )
            ]
        )


def _valid_context(subject="Başvuru İncelemesi", body=None):
    return {
        "tc_baslik": {
            "idare_adi": "ÖRENLİ KAYMAKAMLIĞI",
            "birim_adi": "Yazı İşleri Müdürlüğü",
        },
        "sayi": "E-12345678-100.01-1",
        "tarih": "24.08.2026",
        "konu": subject,
        "muhatap": {"tur": "kurum", "isim": "ÖRNEK KURUMU"},
        "muhatap_turu": "kurum_ust",
        "kapalis_ifadesi": "arz ederim.",
        "ilgi": [],
        "metin_paragraflari": [
            body or "Başvurunuz incelenmiş ve işlem tamamlanmıştır."
        ],
        "imza": {
            "ad_soyad": "Ada ÖRNEK",
            "unvan": "Birim Yetkilisi",
            "yetki_turu": "normal",
        },
        "ekler": [],
        "dagitim": None,
        "iletisim": {"adres": "", "irtibat": ""},
        "sayfa_no": None,
        "uygunsuz_belge_uyarisi": None,
    }


def _current_draft(
    *,
    draft_type="ust_yazi",
    subject="Başvuru İncelemesi",
    body="Başvurunuz incelenmiş ve işlem tamamlanmıştır.",
):
    context = _valid_context(subject=subject, body=body)
    return {
        "draft_type": draft_type,
        "draft_generation_mode": "llm",
        "draft": {
            "sender_unit": "Yazı İşleri Müdürlüğü",
            "recipient": "ÖRNEK KURUMU",
            "subject": subject,
            "body": body,
            "closing": None,
        },
        "rendered_text": body,
        "official_rendered_text": "Önceki resmî görünüm",
        "official_render": {
            "attempted": True,
            "success": True,
            "template": "ust_yazi.jinja2",
            "context": context,
            "missing_fields": [],
            "warnings": [],
            "source_map": {
                "konu": "extraction.fields.subject.value",
                "metin_paragraflari": "draft.body",
            },
            "fallback_policies": {},
        },
        "verified_facts_used": ["İşlem Türü: inceleme"],
        "requires_human_approval": True,
    }


def _evren_payload(*, target=None, old=None, new=None, answer=None):
    edit = None
    if target is not None:
        edit = {
            "hedef_bolum": target,
            "eski_metin": old,
            "yeni_metin": new,
        }
    return {
        "sohbet_yaniti": answer or "Taslak değişikliği hazırlandı.",
        "belge_duzenlemesi": edit,
    }


def _install_fake_evren(monkeypatch, *, payload=None, raw=None, error=None):
    content = raw if raw is not None else json.dumps(payload, ensure_ascii=False)
    client = FakeEvrenClient(content=content, error=error)
    monkeypatch.setattr(
        "backend.app.agents.chat_agent._get_evren_client",
        lambda: client,
    )
    return client


@pytest.mark.parametrize(
    "message",
    [
        "Taslağın konusundaki Başvuru İncelemesi ifadesini değiştir.",
        "Gövde metnine sonuç paragrafını ekle.",
        "İkinci paragrafı yeniden yaz.",
    ],
)
def test_is_taslak_duzenleme_talebi_detects_explicit_edits(message):
    assert is_taslak_duzenleme_talebi(message) is True


@pytest.mark.parametrize(
    "message",
    [
        "Chatbot'a taslağı değiştirmesini söyleyebilir miyim?",
        "Taslak nedir, nasıl kullanılır?",
        "4982 sayılı kanun maddesini açıklar mısın?",
        "Mevzuat eşleşme oranı ne demek?",
        "Evrakı sisteme nasıl yüklerim?",
    ],
)
def test_is_taslak_duzenleme_talebi_does_not_conflict_with_mod_a_or_b(message):
    assert is_taslak_duzenleme_talebi(message) is False


def test_handle_draft_edit_sends_exact_evren_parameters(monkeypatch):
    payload = _evren_payload(
        target="govde",
        old="işlem tamamlanmıştır",
        new="işlem uygun şekilde tamamlanmıştır",
    )
    client = _install_fake_evren(monkeypatch, payload=payload)

    result = handle_draft_edit("Gövde metnini düzelt.", _current_draft(), {})

    assert result["status"] == "applied"
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["model"] == "llm-fast"
    assert call["temperature"] == 0
    assert call["max_tokens"] == 1200
    assert call["response_format"] == {"type": "json_object"}
    assert call["extra_body"] == {"enable_thinking": False}
    assert call["timeout"] == 30.0
    assert call["messages"][0] == {
        "role": "system",
        "content": TASLAK_DUZENLEME_SISTEM_PROMPTU,
    }


def test_handle_draft_edit_accepts_null_edit_without_changing_draft(monkeypatch):
    current = _current_draft()
    original = deepcopy(current)
    _install_fake_evren(
        monkeypatch,
        payload=_evren_payload(answer="Mevcut taslak için değişiklik önerilmedi."),
    )

    result = handle_draft_edit("Taslağı kontrol et.", current, {})

    assert result["status"] == "no_change"
    assert result["updated_draft"] is None
    assert current == original


def test_handle_draft_edit_applies_unique_subject_patch(monkeypatch):
    _install_fake_evren(
        monkeypatch,
        payload=_evren_payload(
            target="konu",
            old="Başvuru İncelemesi",
            new="Başvuru Sonucu",
            answer="Konu değişikliği hazırlandı.",
        ),
    )

    result = handle_draft_edit("Taslağın konusunu değiştir.", _current_draft(), {})

    assert result["status"] == "applied"
    updated = result["updated_draft"]
    assert updated["draft"]["subject"] == "Başvuru Sonucu"
    assert updated["official_render"]["context"]["konu"] == "Başvuru Sonucu"
    assert updated["mod_c_validated_context"]["konu"] == "Başvuru Sonucu"
    assert "Başvuru Sonucu" in updated["official_rendered_text"]


def test_handle_draft_edit_applies_unique_body_patch(monkeypatch):
    _install_fake_evren(
        monkeypatch,
        payload=_evren_payload(
            target="govde",
            old="işlem tamamlanmıştır",
            new="işlem uygun şekilde tamamlanmıştır",
        ),
    )

    result = handle_draft_edit("Gövde metnini düzelt.", _current_draft(), {})

    assert result["status"] == "applied"
    updated = result["updated_draft"]
    assert "uygun şekilde" in updated["draft"]["body"]
    assert "uygun şekilde" in updated["official_rendered_text"]
    assert updated["official_render"]["context"]["metin_paragraflari"] == [
        updated["draft"]["body"]
    ]


def test_handle_draft_edit_rejects_missing_old_text(monkeypatch):
    _install_fake_evren(
        monkeypatch,
        payload=_evren_payload(
            target="govde",
            old="taslakta bulunmayan ifade",
            new="yeni bilgi metni",
        ),
    )

    result = handle_draft_edit("Gövde metnini değiştir.", _current_draft(), {})

    assert result["status"] == "rejected"
    assert result["updated_draft"] is None
    assert "bulunamadı" in result["sohbet_yaniti"]


def test_handle_draft_edit_rejects_repeated_old_text(monkeypatch):
    current = _current_draft(body="Bilgi verildi. Bilgi yeniden verildi.")
    _install_fake_evren(
        monkeypatch,
        payload=_evren_payload(
            target="govde",
            old="Bilgi",
            new="Başvuru bilgisi",
        ),
    )

    result = handle_draft_edit("Gövde metnini düzelt.", current, {})

    assert result["status"] == "rejected"
    assert result["updated_draft"] is None
    assert "birden fazla" in result["sohbet_yaniti"]


def test_handle_draft_edit_never_mutates_current_draft_in_place(monkeypatch):
    current = _current_draft()
    original = deepcopy(current)
    _install_fake_evren(
        monkeypatch,
        payload=_evren_payload(
            target="konu",
            old="Başvuru İncelemesi",
            new="Başvuru Sonucu",
        ),
    )

    result = handle_draft_edit("Konu metnini değiştir.", current, {})

    assert result["status"] == "applied"
    assert current == original
    assert result["updated_draft"] is not current


def test_handle_draft_edit_preserves_old_draft_when_validator_fails(monkeypatch):
    current = _current_draft()
    original = deepcopy(current)
    _install_fake_evren(
        monkeypatch,
        payload=_evren_payload(
            target="konu",
            old="Başvuru İncelemesi",
            new="Başvuru Sonucu.",
        ),
    )

    result = handle_draft_edit("Konu metnini değiştir.", current, {})

    assert result["status"] == "rejected"
    assert result["updated_draft"] is None
    assert current == original
    assert any(
        item["kural_kodu"] == "KONU_FORMAT"
        for item in result["validation_errors"]
    )


def test_handle_draft_edit_preserves_old_draft_when_renderer_raises(
    monkeypatch,
):
    current = _current_draft()
    original = deepcopy(current)
    _install_fake_evren(
        monkeypatch,
        payload=_evren_payload(
            target="govde",
            old="işlem tamamlanmıştır",
            new="işlem uygun şekilde tamamlanmıştır",
        ),
    )
    monkeypatch.setattr(
        "backend.app.agents.chat_agent.render_ust_yazi",
        lambda context: (_ for _ in ()).throw(RuntimeError("render failed")),
    )

    result = handle_draft_edit("Gövde metnini değiştir.", current, {})

    assert result["status"] == "error"
    assert result["updated_draft"] is None
    assert current == original


@pytest.mark.parametrize(
    "raw",
    [
        "geçerli json değil",
        json.dumps({"sohbet_yaniti": "Taslak değişikliği hazırlandı."}),
    ],
)
def test_handle_draft_edit_rejects_invalid_json_or_missing_schema(
    monkeypatch,
    raw,
):
    _install_fake_evren(monkeypatch, raw=raw)

    result = handle_draft_edit("Konu metnini değiştir.", _current_draft(), {})

    assert result["status"] == "error"
    assert result["updated_draft"] is None
    assert result["sohbet_yaniti"] == TASLAK_DUZENLEME_GUVENLI_FALLBACK_MESAJI


@pytest.mark.parametrize("foreign_text", ["你好", "New information text"])
def test_handle_draft_edit_rejects_cjk_or_foreign_content(
    monkeypatch,
    foreign_text,
):
    _install_fake_evren(
        monkeypatch,
        payload=_evren_payload(
            target="konu",
            old="Başvuru İncelemesi",
            new=foreign_text,
        ),
    )

    result = handle_draft_edit("Konu metnini değiştir.", _current_draft(), {})

    assert result["status"] == "error"
    assert result["updated_draft"] is None


def test_handle_draft_edit_hides_api_timeout(monkeypatch):
    _install_fake_evren(
        monkeypatch,
        error=TimeoutError("EVREN timeout"),
    )

    result = handle_draft_edit("Gövde metnini değiştir.", _current_draft(), {})

    assert result["status"] == "error"
    assert result["updated_draft"] is None
    assert result["sohbet_yaniti"] == TASLAK_DUZENLEME_GUVENLI_FALLBACK_MESAJI


def test_handle_draft_edit_rejects_unsupported_draft_type_before_evren(
    monkeypatch,
):
    monkeypatch.setattr(
        "backend.app.agents.chat_agent._get_evren_client",
        lambda: (_ for _ in ()).throw(AssertionError("EVREN çağrılmamalı")),
    )

    result = handle_draft_edit(
        "Taslak gövdesini değiştir.",
        _current_draft(draft_type="diger"),
        {},
    )

    assert result["status"] == "rejected"
    assert result["updated_draft"] is None
    assert "desteklenmiyor" in result["sohbet_yaniti"]


def test_handle_chat_message_prioritizes_mod_c_with_draft_context(monkeypatch):
    current = _current_draft()
    monkeypatch.setattr(
        "backend.app.agents.chat_agent.handle_draft_edit",
        lambda message, current_draft, workflow_context: {
            "status": "applied",
            "sohbet_yaniti": message,
            "updated_draft": current_draft,
            "validation_errors": [],
            "validation_warnings": [],
        },
    )

    result = handle_chat_message(
        "Taslak konusunu değiştir.",
        current_draft=current,
        workflow_context={"routing": {}},
    )

    assert result["status"] == "applied"
    assert result["updated_draft"] is current
