from qdrant_client import QdrantClient
from qdrant_client import models

import os

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

VECTOR_SIZE = 1024

LEGAL_COLLECTION = "legal_knowledge_v2"
DOCUMENT_COLLECTION = "document_knowledge"


class QdrantStore:

    def __init__(
        self,
        url: str = QDRANT_URL,
    ):
        self.client = QdrantClient(
            url=url
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
        ]

        for field in fields:

            self.client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=(
                    models.PayloadSchemaType.KEYWORD
                ),
            )

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