"""Idempotently repair canonical metadata on existing 3071 Qdrant points.

Dry-run is the default. Pass ``--apply`` to update payloads in place. The
operation never creates points, changes vectors, or touches another source.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.rag.qdrant_store import LEGAL_COLLECTION, QdrantStore

EXPECTED_POINT_COUNT = 12
CANONICAL_SOURCE = "3071"
SOURCE_DOCUMENT_ID = "3071kanun"
ARTICLE_HEADING_RE = re.compile(r"(?i)^\s*MADDE\s+(\d+)\b")


@dataclass(frozen=True)
class Repair:
    point_id: str
    article: str
    payload: dict[str, Any]
    changed: bool


def infer_article(text: Any) -> str:
    match = ARTICLE_HEADING_RE.search("" if text is None else str(text))
    return match.group(1) if match else ""


def is_3071_payload(payload: dict[str, Any]) -> bool:
    return (
        str(payload.get("document_id") or "").strip() == SOURCE_DOCUMENT_ID
        and str(payload.get("rag_domain") or "").strip() == "legal"
    )


def repaired_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    article = infer_article(payload.get("text"))
    metadata = dict(payload.get("metadata") or {})
    metadata["law_number"] = CANONICAL_SOURCE
    if article:
        metadata["madde_no"] = article
        metadata["article"] = article
    update: dict[str, Any] = {"law_number": CANONICAL_SOURCE, "metadata": metadata}
    if article:
        update["madde_no"] = article
        update["article"] = article
    return update, article


def plan_repairs(points: list[Any]) -> list[Repair]:
    selected = [point for point in points if is_3071_payload(point.payload or {})]
    if len(selected) != EXPECTED_POINT_COUNT:
        raise RuntimeError(
            f"Expected exactly {EXPECTED_POINT_COUNT} existing 3071 points; "
            f"found {len(selected)}. Refusing to continue."
        )
    repairs = []
    for point in selected:
        current = point.payload or {}
        update, article = repaired_payload(current)
        changed = any(current.get(key) != value for key, value in update.items())
        repairs.append(Repair(str(point.id), article, update, changed))
    return repairs


def load_all_points(store: QdrantStore) -> list[Any]:
    points: list[Any] = []
    offset = None
    while True:
        batch, offset = store.client.scroll(
            collection_name=LEGAL_COLLECTION, limit=256, offset=offset,
            with_payload=True, with_vectors=False,
        )
        points.extend(batch)
        if offset is None:
            return points


def run(apply: bool = False) -> list[Repair]:
    store = QdrantStore()
    repairs = plan_repairs(load_all_points(store))
    if apply:
        for repair in repairs:
            if repair.changed:
                store.client.set_payload(
                    collection_name=LEGAL_COLLECTION,
                    points=[repair.point_id], payload=repair.payload, wait=True,
                )
    return repairs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    repairs = run(apply=args.apply)
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"{mode}: selected={len(repairs)} changed={sum(r.changed for r in repairs)}")
    for repair in repairs:
        print(
            f"point={repair.point_id} article={repair.article or '-'} "
            f"status={'UPDATE' if repair.changed else 'UNCHANGED'}"
        )


if __name__ == "__main__":
    main()
