import json
from backend.app.agents.document_agent import DocumentAgent
from backend.app.llm.factory import create_llm_client

def main():
    llm = create_llm_client()
    original_chat = llm.chat
    
    def chat_with_logging(*args, **kwargs):
        print("\n\n=== LLM CHAT CALL ===")
        # print("Messages:", kwargs.get("messages", args[0] if args else []))
        response = original_chat(*args, **kwargs)
        print("\n=== RAW LLM RESPONSE ===")
        print(response)
        print("========================\n\n")
        return response
        
    llm.chat = chat_with_logging
    
    agent = DocumentAgent(llm=llm)
    
    with open("data/evaluation/synthetic/evraklar.jsonl", "r", encoding="utf-8") as f:
        line = f.readline()
        record = json.loads(line)
        text = record.get("metin", "")
        
    print("Running analyze...")
    result = agent.analyze(text)
    print(f"\nResult: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
if __name__ == "__main__":
    main()
