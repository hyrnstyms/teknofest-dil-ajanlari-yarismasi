from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.app.auth.dependencies import CurrentUser, get_current_user
from backend.app.auth.principals import DEMO_USERS
from backend.app.auth.tokens import issue_token
from backend.app.cases.errors import CaseError, validation_error
from backend.app.cases.runtime import get_case_engine

router = APIRouter(prefix="/api/auth", tags=["auth"])


class DemoLoginRequest(BaseModel):
    user_key: str = Field(min_length=1)


@router.post("/demo-login")
def demo_login(body: DemoLoginRequest) -> dict:
    try:
        principal = DEMO_USERS.get(body.user_key)
        if principal is None:
            raise validation_error("Bilinmeyen demo kullanıcısı.", user_key=body.user_key)
        engine = get_case_engine()
        engine.bootstrap()
        user = engine.get_user(principal.id)
        if user is None:
            raise validation_error("Demo kullanıcısı hazırlanamadı.")
        token = issue_token(user.id, user.user_key)
        public = {
            "id": user.id,
            "name": user.name,
            "role": user.role,
            "institution_id": user.institution_id,
            "department_code": user.department_code,
        }
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": public,
        }
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.get("/me")
def me(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    return current_user.to_public_dict()
