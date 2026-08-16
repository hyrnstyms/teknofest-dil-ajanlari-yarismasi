from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Document(BaseModel):
    """
    Sistemdeki bütün dokümanların ortak veri modeli.

    Gerçek belgeler ve ileride üretilecek sentetik belgeler
    aynı şemayı kullanacaktır.
    """

    id: str

    source: str

    source_type: str

    file_type: str

    title: Optional[str] = None

    text: str

    metadata: Dict[str, Any] = Field(default_factory=dict)

    evaluation: Optional[Dict[str, Any]] = None