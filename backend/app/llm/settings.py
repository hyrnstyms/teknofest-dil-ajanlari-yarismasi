import os

from dotenv import load_dotenv


load_dotenv()


class LLMSettings:

    PROVIDER = os.getenv(
        "LLM_PROVIDER",
        "ollama",
    ).lower()

    EVREN_BASE_URL = os.getenv(
        "EVREN_BASE_URL",
        "",
    )

    EVREN_API_KEY = os.getenv(
        "EVREN_API_KEY",
        "",
    )

    EVREN_MODEL_FAST = os.getenv(
        "EVREN_MODEL_FAST",
        "llm-fast",
    )

    EVREN_MODEL_LARGE = os.getenv(
        "EVREN_MODEL_LARGE",
        "llm-large",
    )

    EVREN_TIMEOUT_SECONDS = float(
        os.getenv(
            "EVREN_TIMEOUT_SECONDS",
            "60",
        )
    )

    OLLAMA_URL = os.getenv(
        "OLLAMA_URL",
        "http://localhost:11434",
    )

    OLLAMA_MODEL = os.getenv(
        "OLLAMA_MODEL",
        "qwen2.5:3b-instruct",
    )

    @classmethod
    def get_provider(cls) -> str:
        """Çalışma anındaki provider seçimini döndürür."""

        return os.getenv(
            "LLM_PROVIDER",
            cls.PROVIDER,
        ).strip().lower()
