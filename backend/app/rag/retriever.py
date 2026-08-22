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

    @staticmethod
    def _first_metadata_value(
        *values: Any,
    ) -> Any:
        for value in values:
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return value
        return None

    @classmethod
    def _result_from_point(
        cls,
        point: Any,
    ) -> dict[str, Any]:
        payload = point.payload or {}
        nested_metadata = payload.get("metadata")
        metadata = (
            nested_metadata
            if isinstance(nested_metadata, dict)
            else {}
        )

        source = cls._first_metadata_value(
            payload.get("source"),
            metadata.get("source"),
        )
        law_number = cls._first_metadata_value(
            payload.get("law_number"),
            metadata.get("law_number"),
        )
        document_id = cls._first_metadata_value(
            payload.get("document_id"),
            metadata.get("document_id"),
        )
        madde_no = cls._first_metadata_value(
            payload.get("madde_no"),
            metadata.get("madde_no"),
            metadata.get("article"),
        )
        article = cls._first_metadata_value(
            payload.get("article"),
            metadata.get("article"),
            payload.get("madde_no"),
            metadata.get("madde_no"),
        )

        return {
            "score": float(point.score),
            "chunk_id": payload.get("chunk_id"),
            "title": payload.get("title"),
            "text": payload.get("text"),
            "source": source,
            "rag_domain": payload.get("rag_domain"),
            "law_number": law_number,
            "document_id": document_id,
            "madde_no": madde_no,
            "article": article,
            "trusted_source": payload.get(
                "trusted_source",
                False,
            ),
            "metadata": metadata,
        }

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
            results.append(
                self._result_from_point(point)
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
