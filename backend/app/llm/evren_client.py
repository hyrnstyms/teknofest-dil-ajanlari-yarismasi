from typing import Any

from openai import OpenAI

from backend.app.llm.base import LLMClient


class EvrenClient(LLMClient):
    """OpenAI uyumlu EVREN çıkarım servisi istemcisi."""

    def __init__(
        self,
        model_name: str,
        base_url: str,
        api_key: str,
        timeout: float = 60.0,
    ):
        if not str(model_name or "").strip():
            raise ValueError("EVREN model adı boş olamaz.")
        if not str(base_url or "").strip():
            raise ValueError("EVREN temel URL ayarı bulunamadı.")
        if not str(api_key or "").strip():
            raise ValueError("EVREN API anahtarı bulunamadı.")

        self.model_name = model_name.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=api_key,
        )

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 500,
        json_mode: bool = False,
    ) -> str:
        # EVREN ajan çağrıları deterministik olmalıdır. Ortak LLMClient
        # sözleşmesindeki temperature parametresi uyumluluk için korunur;
        # sağlayıcıya bilinçli olarak daima sıfır gönderilir.
        _ = temperature
        request: dict[str, Any] = {
            "model": self.model_name,
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
            "temperature": 0.0,
            "max_tokens": max_tokens,
            "extra_body": {
                "enable_thinking": False,
            },
            "timeout": self.timeout,
        }

        if json_mode:
            request["response_format"] = {
                "type": "json_object",
            }

        response = self.client.chat.completions.create(
            **request,
        )
        content = response.choices[0].message.content

        if not content or not str(content).strip():
            raise RuntimeError("LLM boş cevap döndürdü.")

        return str(content).strip()

    def get_model_name(self) -> str:
        return self.model_name

    def get_provider_name(self) -> str:
        return "evren"
