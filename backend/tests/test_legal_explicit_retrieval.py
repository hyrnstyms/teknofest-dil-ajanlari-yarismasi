import json

from backend.app.agents.legal_agent import LegalAgent
from backend.app.llm.base import LLMClient


class EmptyLLM(LLMClient):
    def chat(
        self,
        system_prompt,
        user_prompt,
        temperature=0.0,
        max_tokens=500,
        json_mode=False,
    ):
        return json.dumps({"items": []})

    def get_model_name(self):
        return "fake"

    def get_provider_name(self):
        return "test"


class RecordingRetriever:
    def __init__(self, by_law):
        self.by_law = by_law
        self.calls = []

    def search_legal(self, query, limit=5, law_number=None):
        self.calls.append({
            "query": query,
            "limit": limit,
            "law_number": law_number,
        })
        return list(self.by_law.get(law_number, []))[:limit]


def source(law, article, score=0.7):
    return {
        "title": f"Kanun {law}",
        "law_number": law,
        "madde_no": article,
        "article": article,
        "text": f"{law} sayili Kanun Madde {article} metni.",
        "score": score,
    }


def analyze(query, by_law, **kwargs):
    retriever = RecordingRetriever(by_law)
    agent = LegalAgent(llm=EmptyLLM(), retriever=retriever)
    return agent.analyze(query, **kwargs), retriever


def test_3071_article_7_is_prioritized():
    result, retriever = analyze(
        "3071 say\u0131l\u0131 Kanun Madde 7 kapsam\u0131nda dilek\u00e7eye ka\u00e7 g\u00fcn "
        "i\u00e7inde cevap verilir?",
        {"3071": [source("3071", "8", 0.9), source("3071", "7", 0.7)]},
    )
    assert result["retrieved_sources"][0]["article"] == "7"
    assert retriever.calls == [{
        "query": retriever.calls[0]["query"],
        "limit": 20,
        "law_number": "3071",
    }]


def test_4982_article_11_is_prioritized():
    result, retriever = analyze(
        "4982 say\u0131l\u0131 Kanun Madde 11 kapsam\u0131nda bilgiye eri\u015fim s\u00fcresi nedir?",
        {"4982": [source("4982", "10", 0.9), source("4982", "11", 0.8)]},
    )
    assert result["retrieved_sources"][0]["article"] == "11"
    assert retriever.calls[0]["law_number"] == "4982"


def test_explicit_law_without_article_filters_to_that_law():
    result, retriever = analyze(
        "3071 say\u0131l\u0131 Kanuna g\u00f6re dilek\u00e7e hakk\u0131 nedir?",
        {"3071": [source("3071", "3"), source("3071", "4")]},
    )
    assert {item["law_number"] for item in result["retrieved_sources"]} == {"3071"}
    assert retriever.calls[0]["limit"] == 5


def test_query_without_explicit_reference_preserves_semantic_retrieval():
    baseline = [source("6100", "127", 0.9), source("3071", "7", 0.7)]
    result, retriever = analyze(
        "Dilek\u00e7eye ka\u00e7 g\u00fcn i\u00e7inde cevap verilir?",
        {None: baseline},
    )
    assert result["retrieved_sources"] == baseline
    assert retriever.calls == [{
        "query": retriever.calls[0]["query"],
        "limit": 5,
        "law_number": None,
    }]


def test_missing_explicit_law_falls_back_to_semantic_retrieval():
    fallback = [source("3071", "7")]
    result, retriever = analyze(
        "9999 say\u0131l\u0131 Kanun Madde 2 ne d\u00fczenler?",
        {"9999": [], None: fallback},
    )
    assert result["retrieved_sources"] == fallback
    assert [call["law_number"] for call in retriever.calls] == ["9999", None]
    assert [call["limit"] for call in retriever.calls] == [20, 5]


def test_strict_explicit_law_never_uses_an_unrelated_semantic_fallback():
    result, retriever = analyze(
        "4734 sayılı Kanun kapsamında ihale itirazı",
        {"4734": [], None: [source("4982", "19")]},
        strict_explicit_law=True,
    )

    assert result["evidence"] == []
    assert result["sources"] == []
    assert "4734 sayılı Kanun" in result["answer"]
    assert [call["law_number"] for call in retriever.calls] == ["4734"]


def test_temporary_article_identity_is_not_guessed():
    law, article = LegalAgent._extract_explicit_reference(
        "3071 say\u0131l\u0131 Kanun Ge\u00e7ici Madde 1"
    )
    assert law == "3071"
    assert article is None
