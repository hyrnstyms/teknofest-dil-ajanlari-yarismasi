import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from backend.app.synthetic.generator import (
    SyntheticGenerator,
)
from backend.app.synthetic.scenarios import (
    SCENARIOS,
)


INPUT_FILE = Path(
    "data/processed/documents.jsonl"
)

OUTPUT_FILE = Path(
    "data/synthetic/synthetic_documents.jsonl"
)


def load_source_documents():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"{INPUT_FILE} bulunamadı."
        )

    documents = []

    with INPUT_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line in file:

            if not line.strip():
                continue

            item = json.loads(line)

            if (
                item.get("source_type")
                != "raw"
            ):
                continue

            text = str(
                item.get(
                    "text",
                    "",
                )
            ).strip()

            source = str(
                item.get(
                    "source",
                    "",
                )
            ).lower()

            # Çok kısa / çok uzun kaynak alma.
            if not (
                150 <= len(text) <= 3500
            ):
                continue

            text_lower = text.lower()

            # Şimdilik sadece dilekçe benzeri
            # belgeleri seed olarak kullan.
            is_petition = (
                "dilekce" in source
                or "dilekçe" in source
                or "gereğini arz ederim"
                in text_lower
                or "gereğini bilgilerinize arz ederim"
                in text_lower
            )

            if not is_petition:
                continue

            documents.append(
                item
            )

    return documents

def main(
    target_count: int,
    seed: int,
) -> None:

    random.seed(seed)

    source_documents = (
        load_source_documents()
    )

    if not source_documents:
        raise RuntimeError(
            "Uygun kaynak belge bulunamadı."
        )

    generator = (
        SyntheticGenerator()
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    generated_documents = []

    attempts = 0

    max_attempts = (
        target_count * 5
    )

    print(
        f"Kaynak belge sayısı: "
        f"{len(source_documents)}"
    )

    print(
        f"Hedef sentetik belge: "
        f"{target_count}"
    )

    print(
        f"Seed: {seed}"
    )

    while (
        len(generated_documents)
        < target_count
        and attempts < max_attempts
    ):

        attempts += 1

        source_document = random.choice(
            source_documents
        )

        # Dengeli scenario dağılımı.
        scenario = SCENARIOS[
            len(generated_documents)
            % len(SCENARIOS)
        ]

        current_index = (
            len(generated_documents)
            + 1
        )

        print()
        print(
            f"[{current_index}/"
            f"{target_count}]"
        )

        print(
            "Kaynak:",
            source_document.get(
                "title"
            ),
        )

        print(
            "Senaryo:",
            scenario,
        )

        try:

            document = (
                generator.generate(
                    source_document=(
                        source_document
                    ),
                    scenario=scenario,
                    index=current_index,
                )
            )

            generated_documents.append(
                document
            )

            print(
                "[OK]",
                document.title,
            )

        except Exception as exc:

            print(
                "[REDDİ]",
                exc,
            )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        for document in (
            generated_documents
        ):

            file.write(
                json.dumps(
                    document.model_dump(),
                    ensure_ascii=False,
                )
                + "\n"
            )

    print()
    print(
        "=============================="
    )

    print(
        "SENTETİK ÜRETİM TAMAMLANDI"
    )

    print(
        "=============================="
    )

    print(
        f"Deneme sayısı: {attempts}"
    )

    print(
        f"Başarılı: "
        f"{len(generated_documents)}"
    )

    print(
        f"Çıktı: {OUTPUT_FILE}"
    )


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--count",
        type=int,
        default=10,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    args = parser.parse_args()

    main(
        target_count=args.count,
        seed=args.seed,
    )