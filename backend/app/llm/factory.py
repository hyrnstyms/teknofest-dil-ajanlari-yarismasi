from backend.app.llm.base import (
    LLMClient,
)

from backend.app.llm.ollama_client import (
    OllamaClient,
)

from backend.app.llm.evren_client import (
    EvrenClient,
)

from backend.app.llm.settings import (
    LLMSettings,
)


_EVREN_AGENT_MODEL_TIERS = {
    "document_agent": "fast",
    "extraction_agent": "fast",
    "summary_agent": "fast",
    "writing_agent": "fast",
    "legal_agent": "large",
}


def _get_evren_model(agent_name: str | None) -> str:
    if not agent_name:
        raise ValueError(
            "EVREN istemcisi için agent_name zorunludur."
        )

    tier = _EVREN_AGENT_MODEL_TIERS.get(agent_name)
    if tier is None:
        raise ValueError(
            f"EVREN model eşlemesi bulunmayan ajan: {agent_name}"
        )

    if tier == "large":
        return LLMSettings.EVREN_MODEL_LARGE
    return LLMSettings.EVREN_MODEL_FAST


def create_llm_client(
    agent_name: str | None = None,
) -> LLMClient:

    provider = (
        LLMSettings.get_provider()
    )

    if provider == "evren":

        return EvrenClient(
            model_name=(
                _get_evren_model(agent_name)
            ),
            base_url=(
                LLMSettings.EVREN_BASE_URL
            ),
            api_key=(
                LLMSettings.EVREN_API_KEY
            ),
            timeout=(
                LLMSettings.EVREN_TIMEOUT_SECONDS
            ),
        )

    if provider == "ollama":

        return OllamaClient(
            model_name=(
                LLMSettings.OLLAMA_MODEL
            ),
            base_url=(
                LLMSettings.OLLAMA_URL
            ),
        )

    raise ValueError(
        f"Desteklenmeyen LLM provider: "
        f"{provider}"
    )
