from typing import Literal

from pydantic import BaseModel, Field


class GeneratedContent(BaseModel):

    document_type: Literal[
        "dilekce",
        "basvuru",
        "sikayet",
    ]

    institution: str = Field(
        min_length=3,
        max_length=200,
    )

    subject: str = Field(
        min_length=5,
        max_length=200,
    )

    request_text: str = Field(
        min_length=30,
        max_length=1500,
    )

    secondary_request_text: str = Field(
        min_length=20,
        max_length=1000,
    )