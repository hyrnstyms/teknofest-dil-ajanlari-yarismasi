from sentence_transformers import SentenceTransformer


MODEL_NAME = "BAAI/bge-m3"


class EmbeddingService:

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        device: str = "cpu",
    ):
        print(
            f"Embedding modeli yükleniyor: "
            f"{model_name}"
        )

        self.model = SentenceTransformer(
            model_name,
            device=device,
        )

        dimension = (
            self.model.get_embedding_dimension()
        )

        print(
            "Embedding modeli hazır."
        )

        print(
            f"Embedding dimension: "
            f"{dimension}"
        )

        self._validate_qdrant_schema(dimension)

    def _validate_qdrant_schema(self, dimension: int) -> None:
        try:
            from backend.app.rag.qdrant_store import QdrantStore, LEGAL_COLLECTION, DOCUMENT_COLLECTION
            from qdrant_client.http.exceptions import UnexpectedResponse
            
            store = QdrantStore()
            collections_to_check = [LEGAL_COLLECTION, DOCUMENT_COLLECTION]
            
            for coll in collections_to_check:
                try:
                    info = store.client.get_collection(coll)
                    # Check vector size (assuming default unnamed vector config)
                    config = info.config.params.vectors
                    if hasattr(config, 'size'):
                        qdrant_dim = config.size
                        if qdrant_dim != dimension:
                            raise ValueError(
                                f"Qdrant collection '{coll}' has vector size {qdrant_dim}, "
                                f"but embedding model dimension is {dimension}. "
                                f"Please recreate the collection or use the correct model."
                            )
                except UnexpectedResponse as e:
                    if e.status_code == 404:
                        print(f"Collection {coll} does not exist yet. Skipping validation.")
                    else:
                        raise e
            print("Qdrant schema validation passed.")
        except ValueError:
            raise
        except ImportError:
            print("QdrantStore not found, skipping schema validation.")
        except Exception as e:
            print(f"Qdrant connection failed during schema validation: {e}. Skipping validation.")

    def encode_documents(
        self,
        texts: list[str],
        batch_size: int = 8,
    ) -> list[list[float]]:

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=True,
        )

        return embeddings.tolist()

    def encode_query(
        self,
        query: str,
    ) -> list[float]:

        embedding = self.model.encode(
            query,
            normalize_embeddings=True,
        )

        return embedding.tolist()