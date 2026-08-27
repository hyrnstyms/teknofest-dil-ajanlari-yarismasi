import os
from typing import Any

import requests

from backend.app.llm.base import (
    LLMClient,
)


class OllamaClient(LLMClient):

    def __init__(
        self,
        model_name: str,
        base_url: str,
    ):
        self.model_name = model_name

        self.base_url = (
            base_url.rstrip("/")
        )

        self.chat_url = (
            f"{self.base_url}/api/chat"
        )

    def _build_messages(
        self,
        system_prompt: str,
        user_prompt: str,
        history: list[dict] | None = None,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        if history:
            for turn in history:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_prompt})
        return messages

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 500,
        json_mode: bool = False,
    ) -> str:

        payload: dict[str, Any] = {
            "model": self.model_name,
            "stream": False,
            "keep_alive": os.getenv("OLLAMA_KEEP_ALIVE", "30m"),

            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],

            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        if json_mode:
            payload["format"] = "json"

        response = requests.post(
            self.chat_url,
            json=payload,
            timeout=180,
        )

        response.raise_for_status()

        data = response.json()

        message = data.get(
            "message",
            {},
        )

        content = message.get(
            "content",
            "",
        )

        if not content:
            raise RuntimeError(
                "LLM boş cevap döndürdü."
            )

        return content.strip()

    def chat_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        history: list[dict] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 800,
    ):
        """Ollama native streaming — yields text deltas token by token."""
        import json as _json

        payload: dict[str, Any] = {
            "model": self.model_name,
            "stream": True,
            "keep_alive": os.getenv("OLLAMA_KEEP_ALIVE", "30m"),
            "messages": self._build_messages(system_prompt, user_prompt, history),
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        with requests.post(
            self.chat_url,
            json=payload,
            timeout=180,
            stream=True,
        ) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines():
                if not raw_line:
                    continue
                try:
                    chunk = _json.loads(raw_line)
                except (ValueError, TypeError):
                    continue
                delta = chunk.get("message", {}).get("content", "")
                if delta:
                    yield delta
                if chunk.get("done"):
                    break

    def get_model_name(
        self,
    ) -> str:
        return self.model_name

    def get_provider_name(
        self,
    ) -> str:
        return "ollama"