from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.app.auth.dependencies import CurrentUser, get_current_user
from backend.app.cases.departments import list_departments
from backend.app.cases.errors import CaseError, case_not_found, validation_error

router = APIRouter(prefix="/api/institutions", tags=["institutions-case"])


@router.get("/{institution_id}/departments")
def institution_departments(
    institution_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        if current_user.institution_id != institution_id:
            raise case_not_found()
        departments = list_departments(institution_id)
        return {"institution_id": institution_id, "departments": departments}
    except FileNotFoundError as exc:
        raise validation_error(
            "Kurum profili bulunamadı.", institution_id=institution_id
        ).to_http_exception() from exc
    except CaseError as exc:
        raise exc.to_http_exception() from exc
    except HTTPException:
        raise
