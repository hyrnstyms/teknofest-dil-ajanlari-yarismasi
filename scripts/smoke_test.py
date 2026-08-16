import math
from backend.app.rag.embedding_service import EmbeddingService
from backend.app.rag.retriever import Retriever

def run_tests():
    print("=== STARTING SMOKE TEST ===")
    
    # 1. Initialize EmbeddingService
    print("\n--- Testing EmbeddingService ---")
    emb_service = EmbeddingService()
    
    query = "Bilgi edinme başvurusunda gerekli bilgiler nelerdir?"
    vector = emb_service.encode_query(query)
    
    print(f"Query: {query}")
    print(f"Vector Length: {len(vector)}")
    assert len(vector) == 1024, "Vector length is not 1024"
    
    # Check if finite and no NaN/inf
    is_finite = all(math.isfinite(x) for x in vector)
    print(f"All elements finite (no NaN/Inf): {is_finite}")
    assert is_finite, "Vector contains non-finite values"
    
    # Check L2 norm
    l2_norm = math.sqrt(sum(x*x for x in vector))
    print(f"L2 Norm: {l2_norm:.4f}")
    assert abs(l2_norm - 1.0) < 1e-4, f"L2 norm is not approx 1.0 (got {l2_norm})"
    
    # Check batch encoding
    batch = emb_service.encode_documents(["Doc 1", "Doc 2"])
    print(f"Batch embedding dimension: {len(batch)}x{len(batch[0])}")
    assert len(batch) == 2 and len(batch[0]) == 1024, "Batch embedding failed"
    
    # 2. Initialize Retriever and test
    print("\n--- Testing Retriever ---")
    retriever = Retriever()
    
    test_query = "Bilgi edinme başvurusunda başvuru sahibinin hangi bilgileri bulunmalıdır?"
    
    print("\n[Legal Search]")
    legal_results = retriever.search_legal(test_query)
    print(f"Legal results found: {len(legal_results)}")
    for i, r in enumerate(legal_results):
        print(f"  {i+1}: Score={r['score']:.4f}, chunk_id={r['chunk_id']}")
        
    print("\n[Official Writing Search]")
    writing_results = retriever.search_official_writing(test_query)
    print(f"Official Writing results found: {len(writing_results)}")
    for i, r in enumerate(writing_results):
        print(f"  {i+1}: Score={r['score']:.4f}, chunk_id={r['chunk_id']}")
        
    print("\n[Document Search]")
    doc_results = retriever.search_documents(test_query)
    print(f"Document results found: {len(doc_results)}")
    for i, r in enumerate(doc_results):
        print(f"  {i+1}: Score={r['score']:.4f}, chunk_id={r['chunk_id']}")
        
    print("\n=== SMOKE TEST PASSED ===")

if __name__ == "__main__":
    run_tests()
