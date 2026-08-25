import json

from scripts.evaluation import llm_cevap_karsilastirma as comparison


def test_load_cases_adds_45_dataset_rows_and_4982_case(tmp_path):
    dataset = tmp_path / "cases.jsonl"
    rows = [
        {
            "id": f"RAG-{index:03d}",
            "soru": f"Soru {index}",
            "dogru_madde_no": f"Madde {index}",
            "dogru_metin_ozeti": f"Özet {index}",
        }
        for index in range(1, 46)
    ]
    dataset.write_text(
        "\n".join(
            json.dumps(row, ensure_ascii=False)
            for row in rows
        ),
        encoding="utf-8",
    )

    cases = comparison.load_cases(dataset)

    assert len(cases) == 46
    assert cases[:45] == rows
    assert cases[-1]["id"] == "EK-4982-M11"
    assert cases[-1]["dogru_madde_no"] == "Madde 11"


def test_build_agents_uses_both_providers_and_shared_retriever(
    monkeypatch,
):
    clients = {}
    created_agents = []
    shared_retriever = object()

    class FakeAgent:
        def __init__(self, llm, retriever):
            self.llm = llm
            self.retriever = retriever
            created_agents.append(self)

    def fake_create(agent_name):
        provider = comparison.os.environ["LLM_PROVIDER"]
        clients[provider] = {
            "agent_name": agent_name,
            "client": object(),
        }
        return clients[provider]["client"]

    monkeypatch.setattr(
        comparison,
        "Retriever",
        lambda: shared_retriever,
    )
    monkeypatch.setattr(comparison, "LegalAgent", FakeAgent)
    monkeypatch.setattr(comparison, "create_llm_client", fake_create)

    agents = comparison.build_agents()

    assert set(agents) == {"ollama", "evren"}
    assert clients["ollama"]["agent_name"] == "legal_agent"
    assert clients["evren"]["agent_name"] == "legal_agent"
    assert agents["ollama"].llm is clients["ollama"]["client"]
    assert agents["evren"].llm is clients["evren"]["client"]
    assert all(
        agent.retriever is shared_retriever
        for agent in created_agents
    )


def test_compare_cases_uses_validated_answer_and_evidence_from_both_agents():
    calls = []

    class FakeAgent:
        def __init__(self, provider):
            self.provider = provider

        def analyze(self, query, top_k):
            calls.append((self.provider, query, top_k))
            return {
                "answer": f"{self.provider} doğrulanmış cevap",
                "evidence": [
                    {
                        "evidence": f"{self.provider} kanıt",
                        "source": "K1",
                    }
                ],
                "sources": [
                    {
                        "source": "Kaynak",
                        "law_number": "3071",
                        "madde_no": "4",
                        "score": 0.9,
                    }
                ],
                "retrieved_sources": [
                    {"madde_no": "istenmeyen-retriever-alanı"}
                ],
                "retrieval_score": 0.9,
                "llm": {
                    "provider": self.provider,
                    "model": "model",
                },
            }

    cases = [
        {
            "id": "RAG-001",
            "soru": "Soru",
            "dogru_madde_no": "Madde 4",
            "dogru_metin_ozeti": "Beklenen cevap",
        }
    ]
    agents = {
        "ollama": FakeAgent("ollama"),
        "evren": FakeAgent("evren"),
    }

    results = comparison.compare_cases(cases, agents)

    assert calls == [
        ("ollama", "Soru", 5),
        ("evren", "Soru", 5),
    ]
    assert results[0]["results"]["ollama"]["answer"] == (
        "ollama doğrulanmış cevap"
    )
    assert results[0]["results"]["evren"]["evidence"][0]["source"] == "K1"
    assert "retrieved_sources" not in results[0]["results"]["ollama"]


def test_write_comparisons_uses_utf8_json(tmp_path):
    output_path = tmp_path / "nested" / "comparison.json"
    payload = [{"answer": "Doğrulanmış Türkçe yanıt"}]

    comparison.write_comparisons(payload, output_path)

    assert json.loads(
        output_path.read_text(encoding="utf-8")
    ) == payload
