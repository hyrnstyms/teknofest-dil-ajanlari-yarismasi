from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select

from backend.app.auth.dependencies import CurrentUser, get_current_user
from backend.app.cases.departments import assert_department
from backend.app.cases.enums import (
    DEPARTMENT_INBOX_STATUSES,
    DURABLE_STATUSES,
    ROLE_BIRIM_PERSONELI,
    ROLE_EVRAK_KAYIT,
    STATUS_CLOSED,
)
from backend.app.cases.errors import (
    CaseError,
    action_forbidden,
    validation_error,
    verified_department_action_required,
    version_conflict,
)
from backend.app.cases.exports import approved_export_context, render_case_pdf
from backend.app.official_writing.docx_renderer import render_to_docx
from backend.app.cases.auto_draft import generate_official_response_after_action
from backend.app.cases.runtime import get_case_engine
from backend.app.cases.schemas import (
    CompleteCaseRequest,
    CreateCaseRequest,
    CitizenRequestCreate,
    DepartmentActionRequest,
    InformationRequestCreate,
    RouteCaseRequest,
    SaveDraftRequest,
    TaskAssignmentRequest,
    TaskStatusRequest,
    VersionedAction,
)
from backend.app.db.case_models import CaseRecord

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


@router.get("")
def list_cases_by_department(
    department_code: str = Query(min_length=1),
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """List an authorized department queue within the caller's institution."""
    try:
        department_code = department_code.strip()
        assert_department(current_user.institution_id, department_code)
        if status is not None and status not in DURABLE_STATUSES:
            raise validation_error("Geçersiz dosya durumu.", status=status)
        try:
            offset = int(cursor) if cursor else 0
        except (TypeError, ValueError) as exc:
            raise validation_error(
                "Geçersiz sayfalama imleci.", cursor=cursor
            ) from exc
        if offset < 0:
            raise validation_error("Geçersiz sayfalama imleci.", cursor=cursor)

        if current_user.role == ROLE_BIRIM_PERSONELI:
            if department_code != current_user.department_code:
                raise action_forbidden(
                    department_code=department_code,
                    user_department_code=current_user.department_code,
                )
        elif current_user.role != ROLE_EVRAK_KAYIT:
            raise action_forbidden(role=current_user.role)

        engine = _engine()
        with engine.session_factory() as session:
            statement = select(CaseRecord).where(
                CaseRecord.institution_id == current_user.institution_id,
                CaseRecord.current_department_code == department_code,
            )
            if current_user.role == ROLE_BIRIM_PERSONELI:
                statement = statement.where(
                    CaseRecord.workflow_status.in_(
                        tuple(DEPARTMENT_INBOX_STATUSES | {STATUS_CLOSED})
                    )
                )
            if status:
                statement = statement.where(CaseRecord.workflow_status == status)
            statement = statement.order_by(
                CaseRecord.received_at.desc(), CaseRecord.id.desc()
            )
            rows = list(
                session.scalars(statement.offset(offset).limit(limit + 1))
            )

        items = [engine.serialize_inbox_item(row) for row in rows[:limit]]
        next_cursor = str(offset + limit) if len(rows) > limit else None
        return {"items": items, "next_cursor": next_cursor}
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.get("/inbox")
def case_inbox(
    status: str | None = Query(default=None),
    scope: str | None = Query(default=None, pattern="^(history)?$"),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        return _engine().list_inbox(current_user, status=status, scope=scope, limit=limit, cursor=cursor)
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.get("/official-writings")
def official_writings(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    try:
        return _engine().list_official_writings(current_user)
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
        return _engine().mark_analysis_started(
            case_id,
            current_user,
            expected_version=body.expected_version,
            confirmed=body.confirmed,
        )
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.post("/{case_id}/analysis/complete")
def complete_analysis(
    case_id: str,
    body: VersionedAction,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        return _engine().mark_analysis_completed(
            case_id,
            current_user,
            expected_version=body.expected_version,
            confirmed=body.confirmed,
        )
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


@router.post("/{case_id}/tasks/{task_id}/assign")
def assign_task(
    case_id: str,
    task_id: str,
    body: TaskAssignmentRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        return _engine().assign_task(
            current_user, case_id, task_id,
            assigned_user_id=body.assigned_user_id,
            expected_version=body.expected_version,
            confirmed=body.confirmed,
            reason=body.reason,
        )
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.post("/{case_id}/tasks/{task_id}/status")
def update_task_status(
    case_id: str,
    task_id: str,
    body: TaskStatusRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        return _engine().update_task_status(
            current_user, case_id, task_id,
            status=body.status,
            expected_version=body.expected_version,
            confirmed=body.confirmed,
            reason=body.reason,
        )
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.post("/{case_id}/information-requests")
def create_information_request(
    case_id: str,
    body: InformationRequestCreate,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    try:
        return _engine().create_information_request(
            current_user, case_id,
            requested_fields=body.requested_fields,
            reason=body.reason,
            expected_version=body.expected_version,
            confirmed=body.confirmed,
            target_type=body.target_type,
            target_name=body.target_name,
            target_department=body.target_department,
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
        engine = _engine()
        result = engine.record_department_action(
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
        result["draft_generation"] = generate_official_response_after_action(engine=engine, user=current_user, case_id=case_id, action_result=result)
        if result["draft_generation"].get("case"):
            # Preserve the legacy response shape while returning the current
            # post-generation version for clients that still save a revision.
            result["case"] = result["draft_generation"]["case"]
        return result
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


@router.post("/{case_id}/drafts/regenerate")
def regenerate_draft(case_id: str, body: VersionedAction, current_user: CurrentUser = Depends(get_current_user)) -> dict:
    try:
        engine = _engine()
        aggregate = engine.get_case_aggregate(current_user, case_id)
        actions = aggregate.get("department_actions") or []
        if not actions:
            raise verified_department_action_required()
        if aggregate["case"]["version"] != body.expected_version:
            raise version_conflict(body.expected_version, aggregate["case"]["version"])
        action = dict(actions[-1]) | {"case": aggregate["case"]}
        return generate_official_response_after_action(engine=engine, user=current_user, case_id=case_id, action_result=action, force_revision=True)
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@router.get("/{case_id}/drafts/{draft_id}/export/{format_name}")
def export_draft(
    case_id: str,
    draft_id: str,
    format_name: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> Response:
    aggregate = _engine().get_case_aggregate(current_user, case_id)
    context, _ = approved_export_context(aggregate, draft_id)
    tracking_code = aggregate["case"]["tracking_code"]
    if format_name == "docx":
        content = render_to_docx(context, evrak_id=tracking_code).getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif format_name == "pdf":
        content = render_case_pdf(context, tracking_code).getvalue()
        media_type = "application/pdf"
    else:
        raise HTTPException(status_code=404, detail={"code": "export_format_not_found", "message": "Dışa aktarma biçimi desteklenmiyor."})
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{tracking_code}.{format_name}"'})


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
