"""Optional Case creation when an authenticated EVRAK_KAYIT user runs analysis."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from backend.app.auth.dependencies import CurrentUser
from backend.app.auth.tokens import parse_token
from backend.app.cases.enums import ROLE_EVRAK_KAYIT
from backend.app.cases.errors import CaseError
from backend.app.db.case_models import CaseUser


def maybe_create_case_for_analysis(
    request: Request | None,
    analysis_id: str,
    state: dict[str, Any],
) -> dict[str, Any] | None:
    if request is None:
        return None
    authorization = request.headers.get("authorization") or request.headers.get("Authorization")
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    try:
        from backend.app.cases.runtime import get_case_engine

        payload = parse_token(token)
        engine = get_case_engine()
        with engine.session_factory() as session:
            row = session.get(CaseUser, payload["sub"])
            if row is None or not row.is_active:
                return None
            user = CurrentUser(
                id=row.id,
                name=row.name,
                role=row.role,
                institution_id=row.institution_id,
                department_code=row.department_code,
                user_key=row.user_key,
            )
        if user.role != ROLE_EVRAK_KAYIT:
            return None
        analysis_institution = state.get("institution_id") or state.get("kurum_profili_id")
        if analysis_institution and analysis_institution != user.institution_id:
            return None
        created = engine.create_case(
            user,
            {
                "confirmed": True,
                "source_type": "VATANDAS",
                "source_channel": "WEB_FORM",
                "originator_type": "VATANDAS",
                "originator_name": "Analiz kaydı",
                "analysis_id": analysis_id,
            },
        )
        engine.mark_analysis_started(created["id"], user)
        engine.mark_analysis_completed(created["id"], user)
        return {
            "case_id": created["id"],
            "tracking_code": created["tracking_code"],
        }
    except CaseError:
        return None
    except Exception:
        return None
