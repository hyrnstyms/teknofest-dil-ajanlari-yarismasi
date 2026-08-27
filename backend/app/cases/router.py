from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend.app.auth.dependencies import CurrentUser, get_current_user
from backend.app.cases.errors import CaseError
from backend.app.cases.runtime import get_case_engine
from backend.app.cases.schemas import (
    CompleteCaseRequest,
    CreateCaseRequest,
    CitizenRequestCreate,
    DepartmentActionRequest,
    RouteCaseRequest,
    SaveDraftRequest,
    VersionedAction,
)

router = APIRouter(prefix="/api/cases", tags=["cases"])


def _engine():
    return get_case_engine()


@router.post("")
def create_case(
    body: CreateCaseRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        return _engine().create_case(current_user, body.model_dump())
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.get("/inbox")
def case_inbox(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        return _engine().list_inbox(current_user, status=status, limit=limit, cursor=cursor)
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.get("/{case_id}")
def get_case(case_id: str, current_user: CurrentUser = Depends(get_current_user)) -> dict:
    try:
        return _engine().get_case_aggregate(current_user, case_id)
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.post("/{case_id}/analysis/start")
def start_analysis(
    case_id: str,
    body: VersionedAction,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        if not body.confirmed:
            from backend.app.cases.errors import confirmation_required

            raise confirmation_required()
        engine = _engine()
        with engine.session_factory() as session:
            case = engine._scoped_case(session, current_user, case_id)
            engine._require_version(case, body.expected_version)
        return engine.mark_analysis_started(case_id, current_user)
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.post("/{case_id}/analysis/complete")
def complete_analysis(
    case_id: str,
    body: VersionedAction,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        if not body.confirmed:
            from backend.app.cases.errors import confirmation_required

            raise confirmation_required()
        engine = _engine()
        with engine.session_factory() as session:
            case = engine._scoped_case(session, current_user, case_id)
            engine._require_version(case, body.expected_version)
        return engine.mark_analysis_completed(case_id, current_user)
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.post("/{case_id}/accept-review")
def accept_review(
    case_id: str,
    body: VersionedAction,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        return _engine().accept_review(
            current_user, case_id, body.expected_version, body.confirmed
        )
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.post("/{case_id}/route")
def route_case(
    case_id: str,
    body: RouteCaseRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        return _engine().route_case(
            current_user,
            case_id,
            department_code=body.department_code or "",
            expected_version=body.expected_version,
            confirmed=body.confirmed,
            reason=body.reason,
            routing_snapshot=body.routing_snapshot,
        )
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.post("/{case_id}/start")
def start_case(
    case_id: str,
    body: VersionedAction,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        return _engine().start_case(
            current_user, case_id, body.expected_version, body.confirmed
        )
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.post("/{case_id}/department-action")
def department_action(
    case_id: str,
    body: DepartmentActionRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        return _engine().record_department_action(
            current_user,
            case_id,
            {
                "action_type": body.action_type,
                "result": body.result,
                "decision": body.decision,
                "planned_date": body.planned_date,
                "notes": body.notes,
            },
            body.expected_version,
            body.confirmed,
        )
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.post("/{case_id}/citizen-requests")
def citizen_requests(
    case_id: str,
    body: CitizenRequestCreate,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        return _engine().create_citizen_request(
            current_user,
            case_id,
            body.model_dump(),
            body.expected_version,
            body.confirmed,
        )
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.post("/{case_id}/drafts")
def save_draft(
    case_id: str,
    body: SaveDraftRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        return _engine().save_draft(
            current_user,
            case_id,
            draft_type=body.draft_type,
            content=body.content,
            grounded_action_id=body.grounded_action_id,
            expected_version=body.expected_version,
            confirmed=body.confirmed,
        )
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.post("/{case_id}/drafts/{draft_id}/approve")
def approve_draft(
    case_id: str,
    draft_id: str,
    body: VersionedAction,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        return _engine().approve_draft(
            current_user, case_id, draft_id, body.expected_version, body.confirmed
        )
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.post("/{case_id}/complete")
def complete_case(
    case_id: str,
    body: CompleteCaseRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        return _engine().complete_case(
            current_user, case_id, body.draft_id, body.expected_version, body.confirmed
        )
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.post("/{case_id}/close")
def close_case(
    case_id: str,
    body: VersionedAction,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        return _engine().close_case(
            current_user, case_id, body.expected_version, body.confirmed
        )
    except CaseError as exc:
        raise exc.to_http_exception() from exc
