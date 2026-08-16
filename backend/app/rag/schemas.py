from typing import Any, Dict

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    id: str

    document_id: str

    source: str

    source_type: str

    corpus_type: str

    chunk_index: int

    text: str

    content_hash: str

    metadata: Dict[str, Any] = Field(
        default_factory=dict
    )