"""Optional Case creation when an authenticated EVRAK_KAYIT user runs analysis."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from sqlalchemy import select

from backend.app.auth.dependencies import CurrentUser
from backend.app.auth.tokens import parse_token
from backend.app.cases.enums import ROLE_EVRAK_KAYIT
from backend.app.cases.errors import CaseError
from backend.app.cases.intelligence_bridge import persist_initial_intelligence
from backend.app.db.case_models import CaseRecord, CaseUser


logger = logging.getLogger(__name__)


def _field_value(state: dict[str, Any], name: str) -> str | None:
    fields = (state.get("extraction") or {}).get("fields") or {}
    value = fields.get(name)
    if isinstance(value, dict):
        value = value.get("value")
    normalized = str(value or "").strip()
    return normalized or None


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
        with engine.session_factory() as session:
            existing = session.scalar(
                select(CaseRecord).where(CaseRecord.analysis_id == analysis_id)
            )
            if existing is not None:
                return {
                    "case_id": existing.id,
                    "tracking_code": existing.tracking_code,
                }
        created = engine.create_case(
            user,
            {
                "confirmed": True,
                "source_type": "VATANDAS",
                "source_channel": "WEB_FORM",
                "originator_type": "VATANDAS",
                "originator_name": _field_value(state, "person_name") or "Analiz kaydı",
                "originator_email": _field_value(state, "email"),
                "originator_phone": _field_value(state, "phone"),
                "analysis_id": analysis_id,
            },
        )
        engine.mark_analysis_started(created["id"], user)
        persist_initial_intelligence(
            engine=engine,
            user=user,
            case=created,
            analysis_id=analysis_id,
            state=state,
        )
        engine.mark_analysis_completed(created["id"], user)
        return {
            "case_id": created["id"],
            "tracking_code": created["tracking_code"],
            "citizen_access_token": created["citizen_access_token"],
        }
    except CaseError:
        logger.exception("Authenticated Analysis could not be linked to a Case.")
        return None
    except Exception:
        logger.exception("Unexpected Analysis-to-Case integration failure.")
        return None
