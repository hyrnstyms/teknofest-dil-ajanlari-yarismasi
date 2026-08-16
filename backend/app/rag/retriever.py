from typing import Any

from qdrant_client import models

from backend.app.rag.embedding_service import (
    EmbeddingService,
)

from backend.app.rag.qdrant_store import (
    QdrantStore,
    LEGAL_COLLECTION,
    DOCUMENT_COLLECTION,
)


class Retriever:

    def __init__(self):
        self.embedding_service = (
            EmbeddingService()
        )

        self.store = QdrantStore()

    def search(
        self,
        query: str,
        collection_name: str,
        limit: int = 5,
        rag_domain: str | None = None,
        law_number: str | None = None,
    ) -> list[dict[str, Any]]:

        query_vector = (
            self.embedding_service.encode_query(
                query
            )
        )

        conditions = []

        if rag_domain:
            conditions.append(
                models.FieldCondition(
                    key="rag_domain",
                    match=models.MatchValue(
                        value=rag_domain
                    ),
                )
            )

        if law_number:
            conditions.append(
                models.FieldCondition(
                    key="law_number",
                    match=models.MatchValue(
                        value=str(law_number)
                    ),
                )
            )

        query_filter = None

        if conditions:
            query_filter = models.Filter(
                must=conditions
            )

        response = (
            self.store.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
        )

        results = []

        for point in response.points:

            payload = point.payload or {}

            results.append(
                {
                    "score": float(
                        point.score
                    ),

                    "chunk_id": payload.get(
                        "chunk_id"
                    ),

                    "title": payload.get(
                        "title"
                    ),

                    "text": payload.get(
                        "text"
                    ),

                    "source": payload.get(
                        "source"
                    ),

                    "rag_domain": payload.get(
                        "rag_domain"
                    ),

                    "law_number": payload.get(
                        "law_number"
                    ),

                    "madde_no": payload.get(
                        "madde_no"
                    ),

                    "trusted_source": payload.get(
                        "trusted_source",
                        False,
                    ),
                }
            )

        return results

    def search_legal(
        self,
        query: str,
        limit: int = 5,
        law_number: str | None = None,
    ) -> list[dict[str, Any]]:

        return self.search(
            query=query,
            collection_name=(
                LEGAL_COLLECTION
            ),
            limit=limit,
            rag_domain="legal",
            law_number=law_number,
        )

    def search_official_writing(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:

        return self.search(
            query=query,
            collection_name=(
                LEGAL_COLLECTION
            ),
            limit=limit,
            rag_domain="official_writing",
        )

    def search_documents(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:

        return self.search(
            query=query,
            collection_name=(
                DOCUMENT_COLLECTION
            ),
            limit=limit,
            rag_domain="document",
        )