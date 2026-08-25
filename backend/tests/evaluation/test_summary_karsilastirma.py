import json

from scripts.evaluation import summary_karsilastirma as comparison


def test_select_records_is_reproducible_and_unique():
    records = [
        {"id": f"SENT-{index:04d}", "metin": f"Metin {index}"}
        for index in range(20)
    ]

    first = comparison.select_records(records, sample_size=10, seed=7)
    second = comparison.select_records(
        records,
        sample_size=10,
        seed=7,
    )

    assert [record["id"] for record in first] == [
        record["id"] for record in second
    ]
    assert len({record["id"] for record in first}) == 10


def test_build_agents_uses_summary_model_for_both_providers(
    monkeypatch,
):
    clients = {}

    class FakeAgent:
        def __init__(self, llm):
            self.llm = llm

    def fake_create(agent_name):
        provider = comparison.os.environ["LLM_PROVIDER"]
        clients[provider] = {
            "agent_name": agent_name,
            "client": object(),
        }
        return clients[provider]["client"]

    monkeypatch.setattr(comparison, "SummaryAgent", FakeAgent)
    monkeypatch.setattr(comparison, "create_llm_client", fake_create)

    agents = comparison.build_agents()

    assert set(agents) == {"ollama", "evren"}
    assert clients["ollama"]["agent_name"] == "summary_agent"
    assert clients["evren"]["agent_name"] == "summary_agent"
    assert agents["ollama"].llm is clients["ollama"]["client"]
    assert agents["evren"].llm is clients["evren"]["client"]


def test_compare_records_forces_same_llm_fallback_for_both_agents():
    calls = []

    class FakeAgent:
        def __init__(self, provider):
            self.provider = provider

        def summarize(
            self,
            raw_text,
            document_analysis,
            extracted_fields,
        ):
            calls.append(
                (
                    self.provider,
                    raw_text,
                    document_analysis,
                    extracted_fields,
                )
            )
            return {
                "short_summary": f"{self.provider} özeti",
                "summary_mode": "llm_grounded",
                "warnings": [],
                "llm": {
                    "provider": self.provider,
                    "model": "model",
                    "status": "success",
                },
            }

    records = [
        {
            "id": "SENT-0001",
            "metin": "Evrak metni",
            "evrak_turu_dogru": "dilekce",
            "zorluk": "kolay",
            "beklenen_alanlar": {
                "konu": "Konu",
                "talep_metni": "Talep",
            },
        }
    ]
    agents = {
        "ollama": FakeAgent("ollama"),
        "evren": FakeAgent("evren"),
    }

    results = comparison.compare_records(records, agents)

    assert calls == [
        (
            "ollama",
            "Evrak metni",
            {"document_type": "dilekce"},
            {},
        ),
        (
            "evren",
            "Evrak metni",
            {"document_type": "dilekce"},
            {},
        ),
    ]
    assert results[0]["results"]["ollama"]["summary"] == (
        "ollama özeti"
    )
    assert results[0]["results"]["evren"]["summary"] == (
        "evren özeti"
    )
    assert results[0]["expected_subject"] == "Konu"


def test_write_comparisons_uses_utf8_and_records_seed(tmp_path):
    output_path = tmp_path / "summary.json"
    comparisons = [
        {
            "id": "SENT-0001",
            "results": {
                "evren": {"summary": "Türkçe özet"}
            },
        }
    ]

    comparison.write_comparisons(
        comparisons,
        output_path,
        seed=20260825,
    )

    payload = json.loads(
        output_path.read_text(encoding="utf-8")
    )
    assert payload["seed"] == 20260825
    assert payload["sample_size"] == 1
    assert payload["automatic_score"] is None
    assert payload["manual_review_required"] is True
    assert payload["comparisons"] == comparisons
