from types import SimpleNamespace

import pytest

from backend.app.agents.quality_agent import QualityAgent
from backend.app.llm.evren_client import EvrenClient
from backend.app.llm.factory import create_llm_client
from backend.app.llm.ollama_client import OllamaClient
from backend.app.llm.settings import LLMSettings


@pytest.fixture
def evren_settings(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "evren")
    monkeypatch.setattr(
        LLMSettings,
        "EVREN_BASE_URL",
        "https://example.invalid/v1",
    )
    monkeypatch.setattr(LLMSettings, "EVREN_API_KEY", "test-key")
    monkeypatch.setattr(LLMSettings, "EVREN_MODEL_FAST", "llm-fast")
    monkeypatch.setattr(LLMSettings, "EVREN_MODEL_LARGE", "llm-large")
    monkeypatch.setattr(LLMSettings, "EVREN_TIMEOUT_SECONDS", 60.0)


@pytest.mark.parametrize(
    ("agent_name", "expected_model"),
    [
        ("document_agent", "llm-fast"),
        ("extraction_agent", "llm-fast"),
        ("summary_agent", "llm-fast"),
        ("writing_agent", "llm-fast"),
        ("legal_agent", "llm-large"),
    ],
)
def test_factory_selects_evren_model_for_each_llm_agent(
    evren_settings,
    agent_name,
    expected_model,
):
    client = create_llm_client(agent_name)

    assert isinstance(client, EvrenClient)
    assert client.get_provider_name() == "evren"
    assert client.get_model_name() == expected_model


def test_factory_requires_known_agent_for_evren(evren_settings):
    with pytest.raises(ValueError, match="agent_name"):
        create_llm_client()

    with pytest.raises(ValueError, match="model eşlemesi"):
        create_llm_client("unknown_agent")


def test_factory_preserves_ollama_behavior(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setattr(
        LLMSettings,
        "OLLAMA_URL",
        "http://ollama.invalid",
    )
    monkeypatch.setattr(LLMSettings, "OLLAMA_MODEL", "legacy-model")

    client = create_llm_client("legal_agent")

    assert isinstance(client, OllamaClient)
    assert client.get_provider_name() == "ollama"
    assert client.get_model_name() == "legacy-model"


def test_factory_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "unknown")

    with pytest.raises(ValueError, match="Desteklenmeyen LLM provider"):
        create_llm_client("document_agent")


def test_evren_client_sends_required_parameters(monkeypatch):
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=' {"ok": true} '),
                    )
                ]
            )

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(
        "backend.app.llm.evren_client.OpenAI",
        FakeOpenAI,
    )
    client = EvrenClient(
        model_name="llm-large",
        base_url="https://example.invalid/v1/",
        api_key="test-key",
        timeout=42.0,
    )

    result = client.chat(
        system_prompt="system",
        user_prompt="user",
        temperature=0.8,
        max_tokens=450,
        json_mode=True,
    )

    assert result == '{"ok": true}'
    assert captured["client"] == {
        "base_url": "https://example.invalid/v1",
        "api_key": "test-key",
    }
    assert captured["model"] == "llm-large"
    assert captured["temperature"] == 0.0
    assert captured["max_tokens"] == 450
    assert captured["response_format"] == {"type": "json_object"}
    assert captured["extra_body"] == {"enable_thinking": False}
    assert captured["timeout"] == 42.0
    assert captured["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "user"},
    ]


def test_evren_client_omits_json_mode_when_not_requested(monkeypatch):
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="yanıt"),
                    )
                ]
            )

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(
        "backend.app.llm.evren_client.OpenAI",
        FakeOpenAI,
    )
    client = EvrenClient(
        model_name="llm-fast",
        base_url="https://example.invalid/v1",
        api_key="test-key",
    )

    assert client.chat("system", "user") == "yanıt"
    assert "response_format" not in captured


def test_evren_client_rejects_empty_response(monkeypatch):
    class FakeCompletions:
        def create(self, **kwargs):
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=""),
                    )
                ]
            )

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(
        "backend.app.llm.evren_client.OpenAI",
        FakeOpenAI,
    )
    client = EvrenClient(
        model_name="llm-fast",
        base_url="https://example.invalid/v1",
        api_key="test-key",
    )

    with pytest.raises(RuntimeError, match="boş cevap"):
        client.chat("system", "user")


def test_quality_agent_remains_deterministic_without_llm():
    agent = QualityAgent()

    assert not hasattr(agent, "llm")


def test_direct_agent_constructors_request_their_own_model(monkeypatch):
    from backend.app.agents import document_agent
    from backend.app.agents import extraction_agent
    from backend.app.agents import legal_agent
    from backend.app.agents import writing_agent

    calls = []
    fake_client = SimpleNamespace()

    def fake_create(agent_name):
        calls.append(agent_name)
        return fake_client

    monkeypatch.setattr(document_agent, "create_llm_client", fake_create)
    monkeypatch.setattr(extraction_agent, "create_llm_client", fake_create)
    monkeypatch.setattr(legal_agent, "create_llm_client", fake_create)
    monkeypatch.setattr(writing_agent, "create_llm_client", fake_create)

    assert document_agent.DocumentAgent().llm is fake_client
    assert extraction_agent.ExtractionAgent().llm is fake_client
    assert legal_agent.LegalAgent(retriever=object()).llm is fake_client
    assert writing_agent.WritingAgent(retriever=object()).llm is fake_client
    assert calls == [
        "document_agent",
        "extraction_agent",
        "legal_agent",
        "writing_agent",
    ]


def test_ollama_client_sends_configurable_keep_alive(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": "yanıt"}}

    def fake_post(url, json, timeout):
        captured.update({"url": url, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setenv("OLLAMA_KEEP_ALIVE", "45m")
    monkeypatch.setattr("backend.app.llm.ollama_client.requests.post", fake_post)
    client = OllamaClient("demo-model", "http://ollama.invalid")

    assert client.chat("system", "user") == "yanıt"
    assert captured["json"]["keep_alive"] == "45m"
    assert captured["json"]["stream"] is False