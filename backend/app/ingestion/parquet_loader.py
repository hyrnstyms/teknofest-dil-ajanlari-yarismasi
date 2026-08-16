from pathlib import Path
from typing import List

import pandas as pd

from .document import Document


def load_parquet(path: Path) -> List[Document]:
    """
    Parquet dosyasını Document listesine dönüştürür.
    """

    df = pd.read_parquet(path)

    documents = []

    for index, row in df.iterrows():

        text = ""

        # Muhtemel text alanlarını sırayla kontrol et.
        for column in ["text", "content", "context", "retrieval_text", "question"]:
            if column in df.columns:
                value = row.get(column)

                if pd.notna(value) and str(value).strip():
                    text = str(value).strip()
                    break

        if not text:
            continue

        metadata = {}

        for column in df.columns:
            if column in {
                "text",
                "content",
                "context",
                "retrieval_text",
                "question",
            }:
                continue

            value = row.get(column)

            if pd.notna(value):
                metadata[column] = value

        documents.append(
            Document(
                id=f"{path.stem}_{index}",
                source=str(path),
                source_type="dataset",
                file_type="parquet",
                title=path.stem,
                text=text,
                metadata=metadata,
            )
        )

    return documents