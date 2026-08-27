from abc import ABC, abstractmethod
from typing import Any, Iterator


class LLMClient(ABC):
    """
    Tüm LLM sağlayıcılarının uygulaması gereken
    ortak arayüz.
    """

    @abstractmethod
    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 500,
        json_mode: bool = False,
    ) -> str:
        pass

    def chat_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        history: list[dict] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 800,
    ) -> Iterator[str]:
        """Token-by-token streaming. Varsayılan: non-stream fallback."""
        yield self.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @abstractmethod
    def get_model_name(
        self,
    ) -> str:
        pass

    @abstractmethod
    def get_provider_name(
        self,
    ) -> str:
        pass