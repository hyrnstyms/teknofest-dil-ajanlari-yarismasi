import sys

# Legal Agent ve Writing Agent'i baslatiyoruz.
from backend.app.rag.embedding_service import EmbeddingService
from backend.app.rag.retriever import Retriever

def test_agents():
    print("=== STARTING AGENT INITIALIZATION TEST ===")
    
    print("Initializing Legal Agent and Writing Agent dummy equivalents...")
    # Just checking if they can be initialized without crashing
    
    # In this mock, we just initialize the retriever (which uses EmbeddingService)
    # The prompt said: "Embedding fix sonrası mevcut Legal Agent'i değiştirmeden varsayılan dependency'leri ile initialize etmeyi dene."
    try:
        from backend.app.agents.legal_agent import LegalAgent
        from backend.app.agents.writing_agent import WritingAgent
        
        legal_agent = LegalAgent()
        print("LegalAgent initialized successfully.")
        
        writing_agent = WritingAgent()
        print("WritingAgent initialized successfully.")
        
        # Test legal agent query
        print("Testing legal agent query...")
        legal_res = legal_agent.analyze("Bilgi edinme başvurusunda başvuru sahibinin hangi bilgileri bulunmalıdır?")
        print(f"Legal agent analysis returned: {legal_res.keys()}")
        print(f"Number of retrieved sources: {len(legal_res.get('retrieved_sources', []))}")
        print(f"Legal agent search returned {len(legal_res)} results.")
        
    except ImportError as e:
        print(f"ImportError while loading agents: {e}")
        # Not all files might exist in this mock environment, so just fallback to checking what we have
    
    print("=== AGENT INITIALIZATION TEST FINISHED ===")

if __name__ == "__main__":
    test_agents()
