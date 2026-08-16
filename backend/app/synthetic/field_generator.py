import json
import re
from typing import Any

import requests

from backend.app.synthetic.anonymizer import (
    anonymize_basic_pii,
)
from backend.app.synthetic.schemas import (
    GeneratedContent,
)


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5:3b-instruct"


class FieldGenerator:

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        ollama_url: str = OLLAMA_URL,
    ):
        self.model_name = model_name
        self.ollama_url = ollama_url

    def generate(
        self,
        source_document: dict[str, Any],
    ) -> GeneratedContent:

        source_text = str(
            source_document.get(
                "text",
                "",
            )
        )

        source_text = anonymize_basic_pii(
            source_text
        )

        source_text = source_text[:3500]

        system_prompt = """
Türkiye'deki kamu kurumlarına yapılan başvurular için
sentetik veri üretimine yardımcı oluyorsun.

Sadece belgenin anlamsal içeriğini üret.

KURALLAR:

- Kaynak belgeyi kopyalama.
- Yeni bir olay ve yeni bir başvuru oluştur.
- Kişi adı üretme.
- Adres üretme.
- Telefon üretme.
- E-posta üretme.
- Tarih üretme.
- İmza üretme.
- T.C. kimlik numarası üretme.

- Kanun numarası üretme.
- Yönetmelik üretme.
- Madde numarası üretme.
- Hukuki dayanak uydurma.

- Gerçekçi bir kamu kurumu/birimi seç.
- Anlamsız kurum adı oluşturma.
- Başvurunun konusu açık olsun.

document_type yalnızca:
dilekce
basvuru
sikayet

değerlerinden biri olabilir.

secondary_request_text ana talepten farklı fakat aynı
başvuru bağlamında kullanılabilecek ikinci bir talep olsun.

SADECE JSON döndür:

{
  "document_type": "dilekce",
  "institution": "kurum veya birim",
  "subject": "başvurunun konusu",
  "request_text": "esas talep",
  "secondary_request_text": "ikinci farklı talep"
}
"""

        user_prompt = f"""
Aşağıdaki belge yalnızca konu ve yapı açısından örnektir.

KAYNAK:
{source_text}

Kaynak metni kopyalamadan tamamen yeni bir kamu başvurusu
için anlamsal alanları üret.
"""

        response = requests.post(
            self.ollama_url,
            json={
                "model": self.model_name,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.55,
                },
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
            },
            timeout=180,
        )

        response.raise_for_status()

        content = response.json()[
            "message"
        ][
            "content"
        ]

        result = GeneratedContent(
            **json.loads(content)
        )

        self._validate(result)

        return result

    def _validate(
        self,
        result: GeneratedContent,
    ) -> None:

        combined = (
            result.subject
            + " "
            + result.request_text
            + " "
            + result.secondary_request_text
        ).lower()

        forbidden = [
            r"\b\d+\s*sayılı\b",
            r"\bmadde\s*\d+",
            r"\bkanunun\b",
            r"\byönetmeliğin\b",
            r"\byönetmelik'in\b",
        ]

        for pattern in forbidden:
            if re.search(
                pattern,
                combined,
                flags=re.IGNORECASE,
            ):
                raise ValueError(
                    "Model mevzuat/hukuki "
                    "dayanak üretmeye çalıştı."
                )

        bad_words = [
            "null kurumu",
            "eksik tarih",
            "eksik adres",
            "çelişkili bilgi",
            "yanlış kuruma yönlendirme",
        ]

        for word in bad_words:
            if word in combined:
                raise ValueError(
                    f"Model senaryo/meta ifade üretti: {word}"
                )
            