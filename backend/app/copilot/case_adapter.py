from typing import Protocol

class InboxAdapter(Protocol):
    def get_inbox_summary(self, user_context: dict) -> str:
        ...

class MockInboxAdapter:
    def get_inbox_summary(self, user_context: dict) -> str:
        if not user_context:
            return "Gelen kutunuza erişmek için giriş yapmalısınız."
            
        role = user_context.get("role", "Bilinmeyen Rol")
        department = user_context.get("department", "Genel")
        
        return f"{department} birimi ({role}) gelen kutunuzda 3 yeni görev bulunmaktadır. (Not: Case Engine API tam entegre edildiğinde gerçek veriler listelenecektir.)"

def get_inbox_adapter() -> InboxAdapter:
    return MockInboxAdapter()
