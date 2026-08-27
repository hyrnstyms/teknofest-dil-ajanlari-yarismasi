"""Read-only Copilot adapter backed by the real Case Engine."""

from __future__ import annotations

from typing import Protocol

class InboxAdapter(Protocol):
    def get_inbox_summary(self, user_context: dict) -> str:
        ...

class CaseEngineInboxAdapter:
    def get_inbox_summary(self, user_context: dict) -> str:
        current_user = user_context.get("_current_user") if user_context else None
        if current_user is None:
            return "Gelen kutunuza erişmek için giriş yapmalısınız."

        from backend.app.cases.runtime import get_case_engine

        result = get_case_engine().list_inbox(current_user, limit=20)
        items = result.get("items") or []
        role = user_context.get("role", "Bilinmeyen Rol")
        department = user_context.get("department_name") or user_context.get(
            "department_code", "Birim"
        )
        if not items:
            return f"{department} birimi ({role}) gelen kutunuzda bekleyen dosya yok."
        codes = ", ".join(str(item.get("tracking_code")) for item in items[:5])
        suffix = "" if len(items) <= 5 else " ve diğerleri"
        return (
            f"{department} birimi ({role}) gelen kutunuzda {len(items)} dosya var: "
            f"{codes}{suffix}."
        )


_ADAPTER = CaseEngineInboxAdapter()

def get_inbox_adapter() -> InboxAdapter:
    return _ADAPTER
