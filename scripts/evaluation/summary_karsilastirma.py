"""Ollama ve EVREN SummaryAgent çıktılarını gözle karşılaştırır.

Aynı rastgele örneklem iki sağlayıcıya da verilir. Script otomatik
doğruluk puanı üretmez; özetleri evrak metni ve beklenen alanlarla
yan yana göstererek manuel inceleme için JSON raporu oluşturabilir.
"""

import argparse
import json
import os
import random
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env", override=False)

from backend.app.agents.summary_agent import SummaryAgent
from backend.app.llm.factory import create_llm_client


DATASET_PATH = (
    PROJECT_ROOT
    / "data"
    / "evaluation"
    / "synthetic"
    / "evraklar.jsonl"
)
DEFAULT_SEED = 20260825
DEFAULT_SAMPLE_SIZE = 10
PROVIDERS = ("ollama", "evren")


@contextmanager
def selected_provider(provider: str) -> Iterator[None]:
    """Factory çağrısı sırasında sağlayıcıyı geçici olarak seçer."""

    previous = os.environ.get("LLM_PROVIDER")
    os.environ["LLM_PROVIDER"] = provider
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("LLM_PROVIDER", None)
        else:
            os.environ["LLM_PROVIDER"] = previous


def load_records(
    dataset_path: Path = DATASET_PATH,
) -> list[dict[str, Any]]:
    records = []
    with dataset_path.open("r", encoding="utf-8") as dataset:
        for line_number, line in enumerate(dataset, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(
                    f"Satır {line_number} JSON nesnesi değil."
                )
            if not str(record.get("id") or "").strip():
                raise ValueError(
                    f"Satır {line_number} id alanı içermiyor."
                )
            if not str(record.get("metin") or "").strip():
                raise ValueError(
                    f"Satır {line_number} metin alanı içermiyor."
                )
            records.append(record)
    return records


def select_records(
    records: list[dict[str, Any]],
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    seed: int = DEFAULT_SEED,
) -> list[dict[str, Any]]:
    if sample_size < 1:
        raise ValueError("Örnek sayısı en az 1 olmalıdır.")
    if sample_size > len(records):
        raise ValueError(
            "Örnek sayısı mevcut kayıt sayısını aşamaz."
        )

    rng = random.Random(seed)
    return rng.sample(records, sample_size)


def build_agents() -> dict[str, SummaryAgent]:
    agents = {}
    for provider in PROVIDERS:
        with selected_provider(provider):
            llm = create_llm_client("summary_agent")
        agents[provider] = SummaryAgent(llm=llm)
    return agents


def compare_records(
    records: list[dict[str, Any]],
    agents: dict[str, SummaryAgent],
) -> list[dict[str, Any]]:
    comparisons = []
    for record_index, record in enumerate(records, start=1):
        print(
            f"[{record_index}/{len(records)}] {record['id']}",
            flush=True,
        )
        provider_results = {}
        for provider in PROVIDERS:
            print(f"  - {provider}", flush=True)
            try:
                result = agents[provider].summarize(
                    raw_text=record["metin"],
                    document_analysis={
                        "document_type": record.get(
                            "evrak_turu_dogru"
                        )
                    },
                    # Doğrulanmış alanlar verilirse SummaryAgent
                    # deterministik yola gider. Model karşılaştırması
                    # için iki sağlayıcıda da aynı LLM fallback'i zorlanır.
                    extracted_fields={},
                )
                provider_results[provider] = {
                    "status": "ok",
                    "provider": result.get("llm", {}).get(
                        "provider"
                    ),
                    "model": result.get("llm", {}).get("model"),
                    "summary": result.get("short_summary"),
                    "summary_mode": result.get("summary_mode"),
                    "llm_status": result.get("llm", {}).get(
                        "status"
                    ),
                    "warnings": result.get("warnings", []),
                }
            except Exception as exc:
                provider_results[provider] = {
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }

        expected_fields = (
            record.get("beklenen_alanlar")
            or record.get("beklened_alanlar")
            or {}
        )
        comparisons.append(
            {
                "id": record["id"],
                "document_type": record.get("evrak_turu_dogru"),
                "difficulty": record.get("zorluk"),
                "expected_subject": expected_fields.get("konu"),
                "expected_request": expected_fields.get(
                    "talep_metni"
                ),
                "document_text": record["metin"],
                "results": provider_results,
            }
        )
    return comparisons


def write_comparisons(
    comparisons: list[dict[str, Any]],
    output_path: Path,
    seed: int,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "seed": seed,
        "sample_size": len(comparisons),
        "automatic_score": None,
        "manual_review_required": True,
        "comparisons": comparisons,
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def print_comparisons(
    comparisons: list[dict[str, Any]],
) -> None:
    for comparison in comparisons:
        print("=" * 88)
        print(f"EVRAK: {comparison['id']}")
        print(f"TÜR: {comparison['document_type']}")
        print(f"ZORLUK: {comparison['difficulty']}")
        print(
            f"BEKLENEN KONU: {comparison['expected_subject']}"
        )
        print(
            f"BEKLENEN TALEP: {comparison['expected_request']}"
        )
        print("EVRAK METNİ:")
        print(comparison["document_text"])

        for provider in PROVIDERS:
            result = comparison["results"][provider]
            print("-" * 88)
            print(f"SAĞLAYICI: {provider.upper()}")
            if result["status"] == "error":
                print(
                    f"HATA: {result['error_type']}: "
                    f"{result['error']}"
                )
                continue
            print(
                "MODEL: "
                f"{result.get('provider')}/{result.get('model')}"
            )
            print(f"ÖZET: {result.get('summary')}")
            print(
                "MOD/DURUM: "
                f"{result.get('summary_mode')}/"
                f"{result.get('llm_status')}"
            )

    print("=" * 88)
    print(
        "NOT: Otomatik doğruluk puanı hesaplanmadı. Her özetin "
        "evraktaki gerçek konu ve taleple ilişkisi gözle "
        "değerlendirilmelidir."
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description=(
            "Ollama ve EVREN SummaryAgent çıktılarını karşılaştırır."
        )
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DATASET_PATH,
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=DEFAULT_SAMPLE_SIZE,
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Sonuçların yazılacağı isteğe bağlı JSON yolu.",
    )
    args = parser.parse_args()

    records = load_records(args.dataset)
    selected = select_records(
        records,
        sample_size=args.sample_size,
        seed=args.seed,
    )
    agents = build_agents()
    comparisons = compare_records(selected, agents)

    if args.json_output:
        write_comparisons(
            comparisons,
            args.json_output,
            seed=args.seed,
        )
        print(f"JSON ÇIKTISI: {args.json_output}", flush=True)

    print_comparisons(comparisons)


if __name__ == "__main__":
    main()
