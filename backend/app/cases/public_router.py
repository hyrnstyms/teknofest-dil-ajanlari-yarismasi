from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.cases.errors import CaseError
from backend.app.cases.runtime import get_case_engine
from backend.app.cases.schemas import CompleteInfoRequest

router = APIRouter(prefix="/api/public/cases", tags=["public-cases"])


@router.get("/{tracking_code}")
def public_case(tracking_code: str, token: str = Query(...)) -> dict:
    try:
        return get_case_engine().public_projection(tracking_code, token)
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.post("/{tracking_code}/complete-info")
def complete_info(
    tracking_code: str,
    body: CompleteInfoRequest,
    token: str = Query(...),
) -> dict:
    try:
        return get_case_engine().complete_citizen_info(tracking_code, token, body.answers)
    except CaseError as exc:
        raise exc.to_http_exception() from exc
