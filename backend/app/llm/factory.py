from backend.app.llm.base import (
    LLMClient,
)

from backend.app.llm.ollama_client import (
    OllamaClient,
)

from backend.app.llm.settings import (
    LLMSettings,
)


def create_llm_client() -> LLMClient:

    provider = (
        LLMSettings.PROVIDER
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