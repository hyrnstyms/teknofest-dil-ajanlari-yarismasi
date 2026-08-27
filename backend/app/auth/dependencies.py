"""FastAPI auth dependencies. Principal is resolved only from the Bearer token."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header

from backend.app.auth.tokens import parse_token
from backend.app.cases.errors import (
    CaseError,
    authentication_required,
    invalid_token,
)
from backend.app.db.case_models import CaseUser


@dataclass
class CurrentUser:
    id: str
    name: str
    role: str
    institution_id: str
    department_code: str
    user_key: str

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "institution_id": self.institution_id,
            "department_code": self.department_code,
        }


def _extract_bearer(authorization: str | None) -> str:
    if not authorization:
        raise authentication_required()
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        raise authentication_required()
    return value.strip()


def get_current_user(
    authorization: str | None = Header(default=None),
) -> CurrentUser:
    from backend.app.cases.runtime import get_case_engine

    try:
        raw = _extract_bearer(authorization)
        payload = parse_token(raw)
        engine = get_case_engine()
        with engine.session_factory() as session:
            row = session.get(CaseUser, payload["sub"])
            if row is None or not row.is_active or row.user_key != payload["user_key"]:
                raise invalid_token()
            return CurrentUser(
                id=row.id,
                name=row.name,
                role=row.role,
                institution_id=row.institution_id,
                department_code=row.department_code,
                user_key=row.user_key,
            )
    except CaseError as exc:
        raise exc.to_http_exception() from exc
