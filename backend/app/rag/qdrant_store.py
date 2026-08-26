from qdrant_client import QdrantClient
from qdrant_client import models

import os

from dotenv import load_dotenv


load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_TIMEOUT_SECONDS = int(os.getenv("QDRANT_TIMEOUT_SECONDS", "60"))

VECTOR_SIZE = 1024

LEGAL_COLLECTION = "legal_knowledge_v2"
DOCUMENT_COLLECTION = "document_knowledge"

# Production demos should not be reported as fully covered merely because the
# collection contains at least one point. These are the minimum sources used
# by the supported municipality/kaymakamlik scenarios.
REQUIRED_LEGAL_SOURCES = frozenset({
    "3071",
    "3194",
    "3294",
    "4734",
    "4982",
    "5393",
    "5442",
    "isyeri_acma_calisma_ruhsatlari_yonetmeligi",
    "valilik_kaymakamlik_birimleri_yonetmeligi",
})


class QdrantStore:

    def __init__(
        self,
        url: str = QDRANT_URL,
        api_key: str | None = QDRANT_API_KEY,
        timeout: int = QDRANT_TIMEOUT_SECONDS,
    ):
        self.client = QdrantClient(
            url=url,
            port=None,
            api_key=api_key or None,
            prefer_grpc=False,
            timeout=timeout,
        )

    def health_check(
        self,
    ) -> None:

        collections = (
            self.client.get_collections()
        )

        print(
            "Qdrant bağlantısı başarılı."
        )

        print(
            "Collection sayısı:",
            len(collections.collections),
        )

    def ensure_collection(
        self,
        collection_name: str,
    ) -> None:

        existing = {
            collection.name
            for collection
            in self.client.get_collections().collections
        }

        if collection_name in existing:
            print(
                f"[VAR] {collection_name}"
            )
            # Payload indexes can evolve after the vector collection is first
            # created. Reconcile them on every startup/indexing run.
            self._create_indexes(collection_name)
            return

        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=VECTOR_SIZE,
                distance=models.Distance.COSINE,
            ),
        )

        print(
            f"[OLUŞTURULDU] "
            f"{collection_name}"
        )

        self._create_indexes(
            collection_name
        )

    def _create_indexes(
        self,
        collection_name: str,
    ) -> None:

        fields = [
            "rag_domain",
            "source_type",
            "document_id",
            "law_number",
            "institution",
            "expected_unit",
        ]

        for field in fields:

            self.client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=(
                    models.PayloadSchemaType.KEYWORD
                ),
            )

    def legal_coverage(self) -> dict[str, object]:
        """Return a one-request coverage report for required legal sources."""
        response = self.client.facet(
            collection_name=LEGAL_COLLECTION,
            key="law_number",
            limit=100,
            exact=True,
        )
        available = {
            str(hit.value)
            for hit in response.hits
            if hit.count > 0
        }
        missing = sorted(REQUIRED_LEGAL_SOURCES - available)
        return {
            "required_sources": sorted(REQUIRED_LEGAL_SOURCES),
            "available_sources": sorted(REQUIRED_LEGAL_SOURCES & available),
            "missing_sources": missing,
            "complete": not missing,
        }

    def ensure_all_collections(
        self,
    ) -> None:

        self.ensure_collection(
            LEGAL_COLLECTION
        )

        self.ensure_collection(
            DOCUMENT_COLLECTION
        )

    def upsert_batch(
        self,
        collection_name: str,
        ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict],
    ) -> None:

        self.client.upsert(
            collection_name=collection_name,
            points=models.Batch(
                ids=ids,
                vectors=vectors,
                payloads=payloads,
            ),
            wait=True,
        )

    def count_points(
        self,
        collection_name: str,
    ) -> int:

        info = self.client.get_collection(
            collection_name=collection_name
        )

        return info.points_count or 0
