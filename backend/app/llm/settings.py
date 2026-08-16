import os

from dotenv import load_dotenv


load_dotenv()


class LLMSettings:

    PROVIDER = os.getenv(
        "LLM_PROVIDER",
        "ollama",
    ).lower()

    OLLAMA_URL = os.getenv(
        "OLLAMA_URL",
        "http://localhost:11434",
    )

    OLLAMA_MODEL = os.getenv(
        "OLLAMA_MODEL",
        "qwen2.5:3b-instruct",
    )