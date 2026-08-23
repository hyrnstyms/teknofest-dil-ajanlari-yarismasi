import json

from backend.app.agents.legal_agent import LegalAgent
from backend.app.llm.base import LLMClient


class FakeLLM(LLMClient):
    def __init__(self, response):
        self.response = response
        self.calls = []

    def chat(self, system_prompt, user_prompt, temperature=0.0, max_tokens=500, json_mode=False):
        self.calls.append({
            "system": system_prompt, "user": user_prompt,
            "temperature": temperature, "json_mode": json_mode,
        })
        return json.dumps(self.response, ensure_ascii=False)

    def get_model_name(self):
        return "fake"

    def get_provider_name(self):
        return "test"


SOURCE = {
    "title": "Dilekçe Hakkının Kullanılmasına Dair Kanun",
    "source_type": "Kanun",
    "law_number": "3071",
    "madde_no": "7",
    "text": "Başvurunun sonucu en geç otuz gün içinde bildirilir.",
}


def agent_with(response):
    llm = FakeLLM(response)
    return LegalAgent(llm=llm, retriever=object()), llm


def test_grounded_item_is_validated_and_real_metadata_is_rendered():
    evidence = "Başvurunun sonucu en geç otuz gün içinde bildirilir."
    agent, llm = agent_with({"items": [{"evidence": evidence, "source": "K1"}]})
    answer, items = agent._generate_grounded_answer("Kaç gün içinde?", [SOURCE])
    assert items == [{"evidence": evidence, "source": "K1"}]
    assert "[Dilekçe Hakkının Kullanılmasına Dair Kanun, 3071, Madde 7]" in answer
    assert llm.calls[0]["temperature"] == 0.0
    assert llm.calls[0]["json_mode"] is True


def test_empty_items_uses_safe_fallback_without_hallucination():
    agent, _ = agent_with({"items": []})
    answer, items = agent._generate_grounded_answer("Ücret ne kadar?", [SOURCE])
    assert items == []
    assert "doğrulanabilir bir bilgi çıkarılamadı" in answer


def test_missing_metadata_is_not_invented_and_does_not_crash():
    source = {"text": "Kısa doğrulanabilir ifade."}
    agent, llm = agent_with({"items": [{"evidence": source["text"], "source": "K1"}]})
    answer, _ = agent._generate_grounded_answer("Do\u011frulanabilir ifade nedir?", [source])
    assert "[K1]" in answer
    assert "Bilinmiyor" not in llm.calls[0]["user"]
    assert "Kaynak Adı:" not in llm.calls[0]["user"]


def test_hallucinated_evidence_is_still_rejected():
    agent, _ = agent_with({"items": [{"evidence": "Kaynakta olmayan hüküm.", "source": "K1"}]})
    answer, items = agent._generate_grounded_answer("Soru", [SOURCE])
    assert items == []
    assert "doğrulanabilir bir bilgi çıkarılamadı" in answer


def test_prompt_contains_two_short_examples_and_structured_context():
    agent, llm = agent_with({"items": []})
    agent._generate_grounded_answer("Soru", [SOURCE])
    call = llm.calls[0]
    assert "ÖRNEK 1" in call["system"] and "ÖRNEK 2" in call["system"]
    assert '{"items":[]}' in call["system"]
    assert "Kaynak Adı:" in call["user"]
    assert "Kaynak Türü:" in call["user"]
    assert "Kanun/Yönetmelik No: 3071" in call["user"]
    assert "Madde: 7" in call["user"]
    assert "Metin:" in call["user"]


def test_supported_3071_evidence_passes_relevance_guard():
    evidence = "Ba\u015fvurunun sonucu en ge\u00e7 otuz g\u00fcn i\u00e7inde bildirilir."
    agent, _ = agent_with({"items": [{"evidence": evidence, "source": "K1"}]})
    query = (
        "Yetkili makamlara yap\u0131lan dilek\u00e7e ba\u015fvurular\u0131n\u0131n sonucu "
        "en ge\u00e7 ka\u00e7 g\u00fcn i\u00e7inde cevaplan\u0131r?"
    )
    answer, items = agent._generate_grounded_answer(query, [SOURCE])
    assert items == [{"evidence": evidence, "source": "K1"}]
    assert "Madde 7" in answer


def test_supported_4982_evidence_passes_relevance_guard():
    source = {
        "title": "Bilgi Edinme Kanunu",
        "law_number": "4982",
        "madde_no": "11",
        "text": (
            "Kurum ve kurulu\u015flar, ba\u015fvuru \u00fczerine istenen bilgi veya belgeye "
            "eri\u015fimi onbe\u015f i\u015f g\u00fcn\u00fc i\u00e7inde sa\u011flarlar."
        ),
    }
    evidence = "onbe\u015f i\u015f g\u00fcn\u00fc i\u00e7inde sa\u011flarlar."
    agent, _ = agent_with({"items": [{"evidence": evidence, "source": "K1"}]})
    answer, items = agent._generate_grounded_answer(
        "Bilgi veya belgeye eri\u015fim s\u00fcresi ne kadard\u0131r?", [source]
    )
    assert items == [{"evidence": evidence, "source": "K1"}]
    assert "4982, Madde 11" in answer


def test_wrong_context_evidence_is_rejected_even_when_it_exists_in_source():
    evidence = "Ba\u015fvurunun sonucu en ge\u00e7 otuz g\u00fcn i\u00e7inde bildirilir."
    agent, _ = agent_with({"items": [{"evidence": evidence, "source": "K1"}]})
    answer, items = agent._generate_grounded_answer(
        "Bo\u015fanma davas\u0131nda yetkili mahkeme hangisidir?", [SOURCE]
    )
    assert items == []
    assert "do\u011frulanabilir bir bilgi \u00e7\u0131kar\u0131lamad\u0131" in answer
