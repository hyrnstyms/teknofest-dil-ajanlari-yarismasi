import argparse
import sys
from pathlib import Path

from qdrant_client import models


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from backend.app.rag.point_ids import legacy_eval_point_id
from backend.app.rag.qdrant_store import LEGAL_COLLECTION, QdrantStore


def find_verified_legacy_ids(store: QdrantStore) -> list[str]:
    legacy_ids: list[str] = []
    offset = None

    while True:
        points, offset = store.client.scroll(
            collection_name=LEGAL_COLLECTION,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in points:
            payload = point.payload or {}
            source = str(payload.get("source") or "").strip()
            madde_no = str(payload.get("madde_no") or "").strip()
            if not source or not madde_no:
                continue
            expected = legacy_eval_point_id(source, madde_no)
            if str(point.id) == expected:
                legacy_ids.append(str(point.id))
        if offset is None:
            break

    return legacy_ids


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    store = QdrantStore()
    before = store.count_points(LEGAL_COLLECTION)
    legacy_ids = find_verified_legacy_ids(store)

    print(f"Point count: {before}")
    print(f"Doğrulanmış legacy ID: {len(legacy_ids)}")

    if not args.apply:
        print("Dry-run: silme yapılmadı.")
        return

    for start in range(0, len(legacy_ids), 256):
        store.client.delete(
            collection_name=LEGAL_COLLECTION,
            points_selector=models.PointIdsList(
                points=legacy_ids[start:start + 256]
            ),
            wait=True,
        )

    after = store.count_points(LEGAL_COLLECTION)
    print(f"Silinen legacy ID: {len(legacy_ids)}")
    print(f"Point count after: {after}")


if __name__ == "__main__":
    main()
