from pathlib import Path
from typing import List

import pandas as pd

from .document import Document


def load_excel(
    path: Path,
    source_type: str,
) -> List[Document]:

    sheets = pd.read_excel(
        path,
        sheet_name=None,
        header=None,
    )

    documents = []

    for sheet_name, df in sheets.items():

        df = df.dropna(how="all")

        if df.empty:
            continue

        lines = []

        for _, row in df.iterrows():

            values = [
                str(value).strip()
                for value in row.tolist()
                if pd.notna(value)
                and str(value).strip()
            ]

            if values:
                lines.append(
                    " | ".join(values)
                )

        text = "\n".join(lines).strip()

        if not text:
            continue

        documents.append(
            Document(
                id=f"{path.stem}_{sheet_name}",
                source=str(path),
                source_type=source_type,
                file_type=path.suffix.lower().lstrip("."),
                title=f"{path.stem} - {sheet_name}",
                text=text,
                metadata={
                    "filename": path.name,
                    "sheet": str(sheet_name),
                },
            )
        )

    return documents