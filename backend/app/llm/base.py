from abc import ABC, abstractmethod
from typing import Any


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