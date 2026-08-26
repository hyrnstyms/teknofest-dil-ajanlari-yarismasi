"""Evaluation-only smoke test for newly indexed high-value legal sources."""

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

from backend.app.rag.retriever import Retriever


DATASET = Path("data/evaluation/legal/high_value_regression.jsonl")


def _normalize(value: object) -> str:
    return " ".join(str(value or "").casefold().split())


def main() -> int:
    rows = [
        json.loads(line)
        for line in DATASET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    retriever = Retriever()
    failures: list[dict[str, object]] = []

    for row in rows:
        if row["rag_domain"] == "official_writing":
            results = retriever.search_official_writing(row["soru"], limit=5)
        else:
            results = retriever.search_legal(row["soru"], limit=5)

        expected_source = _normalize(row["expected_source"])
        expected_article = _normalize(row["expected_article"])
        expected_evidence = _normalize(row["verified_evidence"])
        rank = next(
            (
                index
                for index, result in enumerate(results, start=1)
                if _normalize(result.get("source")) == expected_source
                and _normalize(result.get("madde_no")) == expected_article
                and expected_evidence in _normalize(result.get("text"))
                and result.get("trusted_source") is True
                and result.get("title")
            ),
            None,
        )
        status = "PASS" if rank is not None else "FAIL"
        print(
            f"{status} {row['id']} "
            f"expected={expected_source}|{expected_article} rank={rank}"
        )
        if rank is None:
            failures.append(
                {
                    "id": row["id"],
                    "expected": f"{expected_source}|{expected_article}",
                    "retrieved": [
                        f"{result.get('source')}|{result.get('madde_no')}"
                        for result in results
                    ],
                }
            )

    print(
        f"SUMMARY total={len(rows)} "
        f"passed={len(rows) - len(failures)} failed={len(failures)}"
    )
    if failures:
        print(json.dumps(failures, ensure_ascii=False, indent=2))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
