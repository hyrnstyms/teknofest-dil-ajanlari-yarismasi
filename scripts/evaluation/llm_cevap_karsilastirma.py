"""Ollama ve EVREN LegalAgent kanıt çıktılarını elle karşılaştırır.

Bu script otomatik doğruluk yüzdesi üretmez. Aynı Retriever örneğini
iki sağlayıcıyla paylaşır ve doğrulanmış answer/evidence çıktılarını
yan yana incelenmek üzere yazdırır.
"""

import argparse
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env", override=False)

from backend.app.agents.legal_agent import LegalAgent
from backend.app.llm.factory import create_llm_client
from backend.app.rag.retriever import Retriever


DATASET_PATH = (
    PROJECT_ROOT
    / "data"
    / "evaluation"
    / "legal"
    / "rag_test_seti.jsonl"
)

EXTRA_4982_CASE = {
    "id": "EK-4982-M11",
    "soru": (
        "4982 sayılı kanunda bilgi edinme başvurusuna kaç günde "
        "cevap verilir?"
    ),
    "dogru_madde_no": "Madde 11",
    "dogru_metin_ozeti": (
        "Kurum ve kuruluşlar başvuruya 15 iş günü içinde cevap verir."
    ),
    "kaynak_dokuman": "4982_bilgi_edinme_kanunu.pdf",
    "zorluk": "kontrol",
}

PROVIDERS = ("ollama", "evren")


@contextmanager
def selected_provider(provider: str) -> Iterator[None]:
    """Factory çağrısı boyunca LLM_PROVIDER değerini geçici değiştirir."""

    previous = os.environ.get("LLM_PROVIDER")
    os.environ["LLM_PROVIDER"] = provider
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("LLM_PROVIDER", None)
        else:
            os.environ["LLM_PROVIDER"] = previous


def load_cases(
    dataset_path: Path = DATASET_PATH,
) -> list[dict[str, Any]]:
    cases = []
    with dataset_path.open("r", encoding="utf-8") as dataset:
        for line in dataset:
            if line.strip():
                cases.append(json.loads(line))

    cases.append(dict(EXTRA_4982_CASE))
    return cases


def build_agents() -> dict[str, LegalAgent]:
    """İki sağlayıcı için aynı Retriever'ı paylaşan ajanları kurar."""

    shared_retriever = Retriever()
    agents = {}
    for provider in PROVIDERS:
        with selected_provider(provider):
            llm = create_llm_client("legal_agent")
        agents[provider] = LegalAgent(
            llm=llm,
            retriever=shared_retriever,
        )
    return agents


def _source_summary(
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "source_id": f"K{index}",
            "source": source.get("title") or source.get("source"),
            "law_number": source.get("law_number"),
            "article": source.get("madde_no") or source.get("article"),
            "score": source.get("score"),
        }
        for index, source in enumerate(sources, start=1)
    ]


def compare_cases(
    cases: list[dict[str, Any]],
    agents: dict[str, LegalAgent],
) -> list[dict[str, Any]]:
    comparisons = []
    for case_index, case in enumerate(cases, start=1):
        print(
            f"[{case_index}/{len(cases)}] {case.get('id')}",
            flush=True,
        )
        provider_results = {}
        for provider in PROVIDERS:
            print(f"  - {provider}", flush=True)
            agent = agents[provider]
            try:
                result = agent.analyze(
                    query=case["soru"],
                    top_k=5,
                )
                provider_results[provider] = {
                    "status": "ok",
                    "provider": result.get("llm", {}).get("provider"),
                    "model": result.get("llm", {}).get("model"),
                    "answer": result.get("answer"),
                    "evidence": result.get("evidence", []),
                    "sources": _source_summary(
                        result.get("sources", [])
                    ),
                    "retrieval_score": result.get("retrieval_score"),
                }
            except Exception as exc:
                provider_results[provider] = {
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }

        comparisons.append(
            {
                "id": case.get("id"),
                "question": case.get("soru"),
                "expected_article": case.get("dogru_madde_no"),
                "expected_answer_summary": case.get("dogru_metin_ozeti"),
                "results": provider_results,
            }
        )
    return comparisons


def write_comparisons(
    comparisons: list[dict[str, Any]],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            comparisons,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def print_comparisons(
    comparisons: list[dict[str, Any]],
) -> None:
    for comparison in comparisons:
        print("=" * 88)
        print(f"VAKA: {comparison['id']}")
        print(f"SORU: {comparison['question']}")
        print(f"BEKLENEN MADDE: {comparison['expected_article']}")
        print(
            "BEKLENEN CEVAP ÖZETİ: "
            f"{comparison['expected_answer_summary']}"
        )

        for provider in PROVIDERS:
            result = comparison["results"][provider]
            print("-" * 88)
            print(f"SAĞLAYICI: {provider.upper()}")
            if result["status"] == "error":
                print(
                    f"HATA: {result['error_type']}: {result['error']}"
                )
                continue

            print(
                "MODEL: "
                f"{result.get('provider')}/{result.get('model')}"
            )
            print(f"ANSWER:\n{result.get('answer')}")
            print(
                "EVIDENCE:\n"
                + json.dumps(
                    result.get("evidence", []),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            print(
                "LLM'E VERİLEN KAYNAKLAR:\n"
                + json.dumps(
                    result.get("sources", []),
                    ensure_ascii=False,
                    indent=2,
                )
            )

    print("=" * 88)
    print(
        "NOT: Otomatik doğruluk yüzdesi hesaplanmadı. Her vaka; kanıtın "
        "soruyu doğrudan yanıtlaması, beklenen maddeye dayanması ve kaynak "
        "dışı iddia içermemesi açısından elle değerlendirilmelidir."
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description=(
            "Ollama ve EVREN LegalAgent kanıtlarını yan yana karşılaştırır."
        )
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Yapılandırılmış sonuçların yazılacağı isteğe bağlı JSON yolu.",
    )
    args = parser.parse_args()

    cases = load_cases()
    agents = build_agents()
    comparisons = compare_cases(cases, agents)
    if args.json_output:
        write_comparisons(comparisons, args.json_output)
        print(f"JSON ÇIKTISI: {args.json_output}", flush=True)
    print_comparisons(comparisons)


if __name__ == "__main__":
    main()
