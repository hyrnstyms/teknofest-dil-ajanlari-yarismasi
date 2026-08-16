import json
from pathlib import Path
from typing import Iterable

from .document import Document


def write_jsonl(
    documents: Iterable[Document],
    output_path: str,
) -> None:

    path = Path(output_path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    count = 0

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        for document in documents:

            file.write(
                json.dumps(
                    document.model_dump(),
                    ensure_ascii=False,
                )
                + "\n"
            )

            count += 1

    print()
    print("================================")
    print("INGESTION TAMAMLANDI")
    print("================================")
    print(f"Document sayısı: {count}")
    print(f"Çıktı: {path}")