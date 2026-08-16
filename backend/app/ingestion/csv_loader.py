from pathlib import Path
from typing import List

import pandas as pd

from .document import Document


def load_csv(path: Path) -> List[Document]:
    """
    CSV dosyasını Document listesine dönüştürür.

    Özellikle statute_chunks.csv gibi mevzuat veri setlerinde
    mevcut metadata korunur.
    """

    df = pd.read_csv(path)

    documents = []

    for index, row in df.iterrows():

        # Öncelikli olarak retrieval_text kullan.
        text = ""

        if "retrieval_text" in df.columns:
            value = row.get("retrieval_text")

            if pd.notna(value):
                text = str(value).strip()

        # retrieval_text yoksa context kullan.
        if not text and "context" in df.columns:
            value = row.get("context")

            if pd.notna(value):
                text = str(value).strip()

        # Son çare olarak soru/cevap
        if not text:
            soru = row.get("soru", "")
            cevap = row.get("cevap", "")

            if pd.notna(soru):
                text += str(soru)

            if pd.notna(cevap):
                text += "\n" + str(cevap)

        if not text:
            continue

        kaynak = row.get("kaynak", path.stem)

        if pd.isna(kaynak):
            kaynak = path.stem

        madde_no = row.get("madde_no")

        if pd.isna(madde_no):
            madde_no = None

        kanun_no = row.get("kanun_no")

        if pd.isna(kanun_no):
            kanun_no = None

        url = row.get("url")

        if pd.isna(url):
            url = None

        metadata = {
            "category": "mevzuat",
            "kaynak": str(kaynak),
            "madde_no": str(madde_no) if madde_no is not None else None,
            "kanun_no": str(kanun_no) if kanun_no is not None else None,
            "url": str(url) if url is not None else None,
            "chunk_strategy": (
                str(row["chunk_strategy"])
                if "chunk_strategy" in df.columns
                and pd.notna(row["chunk_strategy"])
                else None
            ),
        }

        document = Document(
            id=f"{path.stem}_{index}",
            source=str(path),
            source_type="mevzuat",
            file_type="csv",
            title=str(kaynak),
            text=text,
            metadata=metadata,
        )

        documents.append(document)

    return documents