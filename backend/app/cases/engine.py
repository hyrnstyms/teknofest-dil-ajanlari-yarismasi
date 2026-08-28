"""Deterministic Case engine: persistence, RBAC, transitions, events."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.auth.dependencies import CurrentUser
from backend.app.auth.principals import DEMO_USERS
from backend.app.cases.departments import assert_department, list_departments
from backend.app.cases.enums import (
    ACTOR_CITIZEN,
    ACTOR_SYSTEM,
    ACTOR_USER,
    DEPARTMENT_INBOX_STATUSES,
    DURABLE_STATUSES,
    DRAFT_STATUS_APPROVED,
    DRAFT_STATUS_DRAFT,
    DRAFT_STATUS_EDITED,
    DRAFT_TYPES,
    EVENT_ANALYSIS_COMPLETED,
    EVENT_ANALYSIS_STARTED,
    EVENT_CASE_CLOSED,
    EVENT_CASE_COMPLETED,
    EVENT_CASE_RECEIVED,
    EVENT_CASE_ROUTED,
    EVENT_CASE_STARTED,
    EVENT_CITIZEN_INFO_COMPLETED,
    EVENT_CITIZEN_INFO_REQUESTED,
    EVENT_DEPARTMENT_ACTION_RECORDED,
    EVENT_DRAFT_APPROVED,
    EVENT_DRAFT_SAVED,
    EVENT_DRAFT_SUBMITTED,
    EVENT_ROUTING_CONFIRMED,
    EVENT_TASK_ASSIGNED,
    EVENT_TASK_CREATED,
    EVENT_TASK_STATUS_CHANGED,
    EVENT_INTERNAL_INFORMATION_REQUESTED,
    EVENT_EXTERNAL_INFORMATION_REQUESTED,
    PUBLIC_EVENT_LABELS,
    PUBLIC_STATUS_LABELS,
    REGISTRY_INBOX_STATUSES,
    ROLE_BIRIM_PERSONELI,
    ROLE_EVRAK_KAYIT,
    STATUS_ANALYZING,
    STATUS_CLOSED,
    STATUS_COMPLETED,
    STATUS_IN_DEPARTMENT,
    STATUS_IN_PROGRESS,
    STATUS_READY_TO_ROUTE,
    STATUS_RECEIVED,
    STATUS_RESPONSE_DRAFTED,
    STATUS_WAITING_CITIZEN_INFO,
    STATUS_WAITING_FINAL_APPROVAL,
    STATUS_WAITING_INITIAL_REVIEW,
    TASK_ASSIGNED,
    TASK_ASSIGNMENT_PENDING,
    TASK_DONE,
    TASK_IN_PROGRESS,
    TASK_STATUSES,
    TASK_WAITING_INFO,
)
from backend.app.cases.errors import (
    action_forbidden,
    approved_draft_required,
    case_not_found,
    citizen_token_invalid,
    clarification_not_active,
    confirmation_required,
    invalid_case_transition,
    validation_error,
    verified_department_action_required,
    version_conflict,
)
from backend.app.cases.chain_matching import assign_matching_chain
from backend.app.cases.notifications import NotificationService
from backend.app.cases.workflow import CaseWorkflowService
from backend.app.db.case_models import (
    CaseAssignment,
    CaseDraft,
    CaseEvent,
    CaseIdempotencyKey,
    CaseNotification,
    CaseRecord,
    CaseTrackingCounter,
    CaseTask,
    CaseInformationRequest,
    CaseUser,
    CitizenRequest,
    DepartmentAction,
)
from backend.app.db.database import create_session_factory
from backend.app.db.models import Analysis


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def hash_citizen_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def tokens_match(raw: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    return hmac.compare_digest(hash_citizen_token(raw), stored_hash)


def _department_name(institution_id: str, department_code: str) -> str:
    try:
        match = next(
            item
            for item in list_departments(institution_id)
            if item["code"] == department_code
        )
        return str(match["name"])
    except (StopIteration, FileNotFoundError):
        return department_code


class CaseEngine:
    def __init__(self, engine: Engine, session_factory: sessionmaker[Session] | None = None):
        self.engine = engine
        self.session_factory = session_factory or create_session_factory(engine)
        self.workflow = CaseWorkflowService()
        self.notifications = NotificationService()

    def bootstrap(self) -> None:
        with self.session_factory.begin() as session:
            for principal in DEMO_USERS.values():
                row = session.get(CaseUser, principal.id)
                if row is None:
                    session.add(
                        CaseUser(
                            id=principal.id,
                            user_key=principal.user_key,
                            name=principal.name,
                            role=principal.role,
                            institution_id=principal.institution_id,
                            department_code=principal.department_code,
                            is_active=True,
                        )
                    )
                else:
                    row.user_key = principal.user_key
                    row.name = principal.name
                    row.role = principal.role
                    row.institution_id = principal.institution_id
                    row.department_code = principal.department_code
                    row.is_active = True

    def get_user(self, user_id: str) -> CaseUser | None:
        with self.session_factory() as session:
            return session.get(CaseUser, user_id)

    def clear_domain(self) -> None:
        with self.session_factory.begin() as session:
            session.execute(delete(CaseIdempotencyKey))
            session.execute(delete(CaseNotification))
            session.execute(delete(CaseDraft))
            session.execute(delete(DepartmentAction))
            session.execute(delete(CaseInformationRequest))
            session.execute(delete(CitizenRequest))
            session.execute(delete(CaseTask))
            session.execute(delete(CaseEvent))
            session.execute(delete(CaseAssignment))
            session.execute(delete(CaseRecord))
            session.execute(delete(CaseTrackingCounter))
        self.bootstrap()

    def _next_tracking_code(self, session: Session, received_at: datetime) -> str:
        year = received_at.year
        counter = session.get(CaseTrackingCounter, year)
        if counter is None:
            counter = CaseTrackingCounter(year=year, last_value=0)
            session.add(counter)
            session.flush()
        counter.last_value += 1
        return f"EVR-{year}-{counter.last_value:06d}"

    def _append_event(
        self,
        session: Session,
        case: CaseRecord,
        event_type: str,
        *,
        actor_type: str,
        actor_user_id: str | None,
        from_status: str | None,
        to_status: str | None,
        payload: dict[str, Any] | None = None,
        before_value: dict[str, Any] | None = None,
        after_value: dict[str, Any] | None = None,
    ) -> CaseEvent:
        created_at = _now()
        latest_created_at = session.scalar(
            select(CaseEvent.created_at)
            .where(CaseEvent.case_id == case.id)
            .order_by(CaseEvent.created_at.desc(), CaseEvent.id.desc())
            .limit(1)
        )
        if latest_created_at is not None:
            if latest_created_at.tzinfo is None:
                latest_created_at = latest_created_at.replace(tzinfo=timezone.utc)
            if created_at <= latest_created_at:
                created_at = latest_created_at + timedelta(microseconds=1)
        event = CaseEvent(
            id=str(uuid.uuid4()),
            case_id=case.id,
            event_type=event_type,
            actor_type=actor_type,
            actor_user_id=actor_user_id,
            from_status=from_status,
            to_status=to_status,
            payload=payload or {},
            created_at=created_at,
            before_value=before_value,
            after_value=after_value,
        )
        session.add(event)
        # Make the event visible to the next append in the same transaction so
        # monotonic ordering never depends on autoflush timing.
        session.flush()
        return event

    def _bump(self, case: CaseRecord, new_status: str | None = None) -> None:
        case.updated_at = _now()
        case.version += 1
        if new_status is not None:
            case.workflow_status = new_status

    def _require_confirmed(self, confirmed: bool) -> None:
        if not confirmed:
            raise confirmation_required()

    def _require_version(self, case: CaseRecord, expected_version: int) -> None:
        if expected_version != case.version:
            raise version_conflict(expected_version, case.version)

    def _load_case(self, session: Session, case_id: str) -> CaseRecord:
        row = session.get(CaseRecord, case_id)
        if row is None:
            raise case_not_found()
        return row

    def _scoped_case(
        self,
        session: Session,
        user: CurrentUser,
        case_id: str,
        *,
        for_update: bool = False,
    ) -> CaseRecord:
        statement = select(CaseRecord).where(CaseRecord.id == case_id)
        if for_update:
            statement = statement.with_for_update()
        row = session.scalar(statement)
        if row is None or row.institution_id != user.institution_id:
            raise case_not_found()
        if not self.can_view(user, row):
            raise action_forbidden(case_id=case_id, role=user.role)
        return row

    def can_view(self, user: CurrentUser, case: CaseRecord) -> bool:
        if case.institution_id != user.institution_id:
            return False
        if user.role == ROLE_EVRAK_KAYIT:
            # The institution registry may inspect the lifecycle it originated,
            # while its actionable inbox remains restricted in ``list_inbox``.
            return True
        if user.role == ROLE_BIRIM_PERSONELI:
            return (
                case.current_department_code == user.department_code
                and case.workflow_status in DEPARTMENT_INBOX_STATUSES | {STATUS_CLOSED}
            )
        return False

    def _require_role(self, user: CurrentUser, role: str) -> None:
        if user.role != role:
            raise action_forbidden(required_role=role, actual_role=user.role)

    def _require_own_department(self, user: CurrentUser, case: CaseRecord) -> None:
        if user.role != ROLE_BIRIM_PERSONELI:
            raise action_forbidden(required_role=ROLE_BIRIM_PERSONELI)
        if case.current_department_code != user.department_code:
            raise action_forbidden(department_code=user.department_code)

    def allowed_actions(self, user: CurrentUser, case: CaseRecord) -> list[str]:
        actions: list[str] = []
        if not self.can_view(user, case) or case.workflow_status == STATUS_CLOSED:
            return actions
        if user.role == ROLE_EVRAK_KAYIT:
            if case.workflow_status == STATUS_RECEIVED:
                actions.append("START_ANALYSIS")
            if case.workflow_status == STATUS_ANALYZING:
                actions.extend(["COMPLETE_ANALYSIS", "REQUEST_CITIZEN_INFO"])
            if case.workflow_status == STATUS_WAITING_INITIAL_REVIEW:
                actions.extend(["ACCEPT_REVIEW", "REQUEST_CITIZEN_INFO"])
            if case.workflow_status == STATUS_READY_TO_ROUTE:
                actions.append("ROUTE_CASE")
            if case.workflow_status == STATUS_COMPLETED:
                actions.append("CLOSE_CASE")
        if user.role == ROLE_BIRIM_PERSONELI and case.current_department_code == user.department_code:
            if case.workflow_status == STATUS_IN_DEPARTMENT:
                actions.append("START_CASE")
            if case.workflow_status == STATUS_IN_PROGRESS:
                actions.extend(["RECORD_DEPARTMENT_ACTION", "SAVE_DRAFT", "APPROVE_DRAFT"])
            if case.workflow_status == STATUS_RESPONSE_DRAFTED:
                actions.extend(["SAVE_DRAFT", "APPROVE_DRAFT"])
            if case.workflow_status == STATUS_WAITING_FINAL_APPROVAL:
                actions.extend(["APPROVE_DRAFT", "FINALIZE_CASE"])
        return actions

    def serialize_case(self, case: CaseRecord) -> dict[str, Any]:
        return {
            "id": case.id,
            "tracking_code": case.tracking_code,
            "analysis_id": case.analysis_id,
            "institution_id": case.institution_id,
            "zincir_id": case.zincir_id,
            "source_type": case.source_type,
            "source_channel": case.source_channel,
            "originator_type": case.originator_type,
            "originator_name": case.originator_name,
            "originator_email": case.originator_email,
            "originator_phone": case.originator_phone,
            "current_department_code": case.current_department_code,
            "current_department": case.current_department_code,
            "assigned_user_id": case.assigned_user_id,
            "workflow_status": case.workflow_status,
            "priority": case.priority,
            "received_at": _iso(case.received_at),
            "created_at": _iso(case.created_at),
            "updated_at": _iso(case.updated_at),
            "closed_at": _iso(case.closed_at),
            "version": case.version,
        }

    def serialize_inbox_item(self, case: CaseRecord) -> dict[str, Any]:
        data = self.serialize_case(case)
        data.pop("originator_email", None)
        data.pop("originator_phone", None)
        return data

    def create_case(
        self,
        user: CurrentUser,
        payload: dict[str, Any],
        *,
        raw_citizen_token: str | None = None,
    ) -> dict[str, Any]:
        self._require_role(user, ROLE_EVRAK_KAYIT)
        self._require_confirmed(bool(payload.get("confirmed")))
        assert_department(user.institution_id, user.department_code)
        received_at = payload.get("received_at") or _now()
        if received_at.tzinfo is None:
            received_at = received_at.replace(tzinfo=timezone.utc)
        raw_token = raw_citizen_token or secrets.token_urlsafe(32)
        with self.session_factory.begin() as session:
            case = CaseRecord(
                id=str(uuid.uuid4()),
                tracking_code=self._next_tracking_code(session, received_at),
                analysis_id=payload.get("analysis_id"),
                institution_id=user.institution_id,
                source_type=payload["source_type"],
                source_channel=payload["source_channel"],
                originator_type=payload["originator_type"],
                originator_name=payload["originator_name"],
                originator_email=payload.get("originator_email"),
                originator_phone=payload.get("originator_phone"),
                current_department_code=user.department_code,
                assigned_user_id=None,
                workflow_status=STATUS_RECEIVED,
                priority=payload.get("priority"),
                citizen_token_hash=hash_citizen_token(raw_token),
                received_at=received_at,
                created_at=_now(),
                updated_at=_now(),
                version=1,
            )
            session.add(case)
            session.flush()
            assign_matching_chain(session, case)
            self._append_event(
                session,
                case,
                EVENT_CASE_RECEIVED,
                actor_type=ACTOR_USER,
                actor_user_id=user.id,
                from_status=None,
                to_status=STATUS_RECEIVED,
                payload={"source_channel": case.source_channel},
            )
            self.notifications.store(
                session,
                case_id=case.id,
                channel="PORTAL",
                template_key="CASE_RECEIVED",
                payload={"tracking_code": case.tracking_code},
            )
            serialized = self.serialize_case(case)
        serialized["citizen_access_token"] = raw_token
        return serialized

    def list_inbox(
        self,
        user: CurrentUser,
        *,
        status: str | None = None,
        scope: str | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 100))
        if status is not None and status not in DURABLE_STATUSES:
            raise validation_error("Geçersiz dosya durumu.", status=status)
        try:
            offset = int(cursor) if cursor else 0
        except (TypeError, ValueError) as exc:
            raise validation_error("Geçersiz sayfalama imleci.", cursor=cursor) from exc
        if offset < 0:
            raise validation_error("Geçersiz sayfalama imleci.", cursor=cursor)
        with self.session_factory() as session:
            statement = select(CaseRecord).where(
                CaseRecord.institution_id == user.institution_id
            )
            if user.role == ROLE_EVRAK_KAYIT and scope == "history":
                # Registry staff retain a read-only audit/history view after a
                # case is handed to a department.  It must not be mistaken for
                # the actionable inbox, whose ownership rules remain below.
                pass
            elif user.role == ROLE_EVRAK_KAYIT:
                statement = statement.where(
                    (CaseRecord.workflow_status.in_(tuple(REGISTRY_INBOX_STATUSES)))
                    | (CaseRecord.current_department_code == user.department_code)
                )
            elif user.role == ROLE_BIRIM_PERSONELI:
                statement = statement.where(
                    CaseRecord.current_department_code == user.department_code,
                    CaseRecord.workflow_status.in_(tuple(DEPARTMENT_INBOX_STATUSES)),
                )
            else:
                raise action_forbidden(role=user.role)
            if status:
                statement = statement.where(CaseRecord.workflow_status == status)
            statement = statement.order_by(
                CaseRecord.received_at.desc(), CaseRecord.id.desc()
            )
            rows = list(session.scalars(statement.offset(offset).limit(limit + 1)))
        items = [self.serialize_inbox_item(row) for row in rows[:limit]]
        next_cursor = str(offset + limit) if len(rows) > limit else None
        return {"items": items, "next_cursor": next_cursor}

    def get_case_aggregate(self, user: CurrentUser, case_id: str) -> dict[str, Any]:
        from backend.app.db.repository import AnalysisRepository

        with self.session_factory() as session:
            case = self._scoped_case(session, user, case_id)
            assignments = list(
                session.scalars(
                    select(CaseAssignment)
                    .where(CaseAssignment.case_id == case.id)
                    .order_by(CaseAssignment.assigned_at.asc(), CaseAssignment.id.asc())
                )
            )
            tasks = list(
                session.scalars(
                    select(CaseTask)
                    .where(CaseTask.case_id == case.id)
                    .order_by(CaseTask.created_at.asc(), CaseTask.id.asc())
                )
            )
            information_requests = list(
                session.scalars(
                    select(CaseInformationRequest)
                    .where(CaseInformationRequest.case_id == case.id)
                    .order_by(CaseInformationRequest.created_at.asc(), CaseInformationRequest.id.asc())
                )
            )
            events = list(
                session.scalars(
                    select(CaseEvent)
                    .where(CaseEvent.case_id == case.id)
                    .order_by(CaseEvent.created_at.asc(), CaseEvent.id.asc())
                )
            )
            requests = list(
                session.scalars(
                    select(CitizenRequest)
                    .where(CitizenRequest.case_id == case.id)
                    .order_by(CitizenRequest.created_at.asc())
                )
            )
            actions = list(
                session.scalars(
                    select(DepartmentAction)
                    .where(DepartmentAction.case_id == case.id)
                    .order_by(DepartmentAction.created_at.asc())
                )
            )
            drafts = list(
                session.scalars(
                    select(CaseDraft)
                    .where(CaseDraft.case_id == case.id)
                    .order_by(CaseDraft.created_at.asc())
                )
            )
            notes = list(
                session.scalars(
                    select(CaseNotification)
                    .where(CaseNotification.case_id == case.id)
                    .order_by(CaseNotification.created_at.asc())
                )
            )
            analysis_id = case.analysis_id
            aggregate = {
                "case": self.serialize_case(case),
                "permissions": self.allowed_actions(user, case),
                "assignments": [self._serialize_assignment(item) for item in assignments],
                "tasks": [self._serialize_task(item) for item in tasks],
                "assignment": self._serialize_task(tasks[-1]) if tasks else None,
                "information_requests": [self._serialize_information_request(item) for item in information_requests],
                "events": [self._serialize_event(item) for item in events],
                "timeline": [self._serialize_event(item) for item in events],
                "ai_operation": {},
                "clarification": {},
                "priority_assessment": {},
                "citizen_requests": [self._serialize_citizen_request(item) for item in requests],
                "department_actions": [self._serialize_action(item) for item in actions],
                "drafts": [self._serialize_draft(item) for item in drafts],
                "notifications": [self._serialize_notification(item) for item in notes],
                "analysis": None,
                "deadline": {
                    "applicable": False,
                    "due_at": None,
                    "risk_level": "UNKNOWN",
                },
            }
        if analysis_id:
            try:
                stored = AnalysisRepository(engine=self.engine).get_analysis(analysis_id)
            except Exception:
                stored = None
            if stored:
                routing = dict(stored.get("routing") or {})
                clarification = dict(stored.get("clarification") or {})
                summary = dict(stored.get("summary") or {})
                deadline = stored.get("deadline_evaluation")
                if not isinstance(deadline, dict) or not deadline:
                    from backend.app.intelligence.deadline import LegalDeadlineService

                    deadline = LegalDeadlineService().evaluate(
                        legal_analysis=dict(stored.get("legal_analysis") or {}),
                        received_at=aggregate["case"]["received_at"],
                    )
                aggregate["deadline"] = deadline
                aggregate["clarification"] = clarification
                aggregate["ai_operation"] = dict((stored.get("case_orchestration") or {}).get("ai_operation") or {})
                aggregate["priority_assessment"] = dict((stored.get("case_orchestration") or {}).get("operational_priority") or {})
                aggregate["analysis"] = {
                    "analysis_id": stored.get("analysis_id"),
                    "document_type": (stored.get("document") or {}).get("document_type"),
                    "process_intent": (stored.get("document") or {}).get("process_intent"),
                    "summary": summary,
                    "routing": routing,
                    "clarification": clarification,
                    "ai_operation": dict((stored.get("case_orchestration") or {}).get("ai_operation") or {}),
                    "operational_priority": dict((stored.get("case_orchestration") or {}).get("operational_priority") or {}),
                    "recommended_unit": routing.get("recommended_unit"),
                    "recommended_department_code": routing.get("recommended_department_code"),
                    "human_review_status": (stored.get("human_review") or {}).get("status"),
                    "document": dict(stored.get("document") or {}),
                    "extraction": dict(stored.get("extraction") or {}),
                    "missing_fields": dict(stored.get("missing_fields") or {}),
                    "legal_analysis": dict(stored.get("legal_analysis") or {}),
                    "raw_text": stored.get("raw_text"),
                }
        aggregate["case"]["current_department_name"] = _department_name(
            aggregate["case"]["institution_id"],
            aggregate["case"]["current_department_code"],
        )
        return aggregate

    def list_official_writings(self, user: CurrentUser) -> dict[str, Any]:
        """Return drafts only for Cases visible to the caller's role scope."""
        with self.session_factory() as session:
            cases = list(session.scalars(select(CaseRecord).where(CaseRecord.institution_id == user.institution_id)))
            visible: list[CaseRecord] = []
            for case in cases:
                if user.role == ROLE_BIRIM_PERSONELI:
                    if case.current_department_code == user.department_code:
                        visible.append(case)
                elif case.current_department_code == user.department_code:
                    visible.append(case)
                else:
                    routed_by_user = session.scalar(select(CaseAssignment.id).where(CaseAssignment.case_id == case.id, CaseAssignment.assigned_by_user_id == user.id).limit(1))
                    if routed_by_user:
                        visible.append(case)
            case_map = {case.id: case for case in visible}
            drafts = list(session.scalars(select(CaseDraft).where(CaseDraft.case_id.in_(case_map)).order_by(CaseDraft.updated_at.desc()))) if case_map else []
            items = []
            for draft in drafts:
                case = case_map[draft.case_id]
                items.append(self._serialize_draft(draft) | {
                    "tracking_code": case.tracking_code,
                    "institution_id": case.institution_id,
                    "originator_name": case.originator_name,
                    "current_department_code": case.current_department_code,
                    "current_department_name": _department_name(case.institution_id, case.current_department_code),
                    "case_status": case.workflow_status,
                    "case_version": case.version,
                })
            return {"items": items, "count": len(items)}

    def _serialize_assignment(self, row: CaseAssignment) -> dict[str, Any]:
        return {
            "id": row.id,
            "case_id": row.case_id,
            "department_code": row.department_code,
            "assigned_user_id": row.assigned_user_id,
            "assigned_by_user_id": row.assigned_by_user_id,
            "assigned_at": _iso(row.assigned_at),
            "ended_at": _iso(row.ended_at),
            "reason": row.reason,
            "routing_snapshot": row.routing_snapshot or {},
        }

    def _serialize_task(self, row: CaseTask) -> dict[str, Any]:
        return {
            "id": row.id,
            "case_id": row.case_id,
            "source_case_id": row.source_case_id,
            "task_type": row.task_type,
            "department_code": row.department_code,
            "team_code": row.team_code,
            "recommended_role": row.recommended_role,
            "assigned_user_id": row.assigned_user_id,
            "status": row.status,
            "reason": row.reason,
            "ai_recommendation": row.ai_recommendation or {},
            "created_by_user_id": row.created_by_user_id,
            "approved_by_user_id": row.approved_by_user_id,
            "created_at": _iso(row.created_at),
            "updated_at": _iso(row.updated_at),
        }

    def _serialize_information_request(self, row: CaseInformationRequest) -> dict[str, Any]:
        return {
            "id": row.id,
            "case_id": row.case_id,
            "target_type": row.target_type,
            "target_name": row.target_name,
            "target_department": row.target_department,
            "requested_fields": row.requested_fields or [],
            "reason": row.reason,
            "recommended_action": row.recommended_action,
            "status": row.status,
            "created_by_user_id": row.created_by_user_id,
            "created_at": _iso(row.created_at),
        }

    def _serialize_event(self, row: CaseEvent) -> dict[str, Any]:
        return {
            "id": row.id,
            "case_id": row.case_id,
            "event_type": row.event_type,
            "actor_type": row.actor_type,
            "actor_user_id": row.actor_user_id,
            "created_at": _iso(row.created_at),
            "from_status": row.from_status,
            "to_status": row.to_status,
            "payload": row.payload or {},
            "before_value": row.before_value,
            "after_value": row.after_value,
        }

    def _serialize_citizen_request(self, row: CitizenRequest) -> dict[str, Any]:
        return {
            "id": row.id,
            "case_id": row.case_id,
            "status": row.status,
            "blocking": row.blocking,
            "requested_fields": row.requested_fields or [],
            "question_type": row.question_type,
            "question": row.question,
            "options": row.options or [],
            "resume_target": row.resume_target,
            "created_by_user_id": row.created_by_user_id,
            "created_at": _iso(row.created_at),
            "completed_at": _iso(row.completed_at),
        }

    def _serialize_action(self, row: DepartmentAction) -> dict[str, Any]:
        return {
            "id": row.id,
            "case_id": row.case_id,
            "action_type": row.action_type,
            "result": row.result,
            "decision": row.decision,
            "planned_date": row.planned_date.isoformat() if row.planned_date else None,
            "notes": row.notes,
            "verified": row.verified,
            "recorded_by_user_id": row.recorded_by_user_id,
            "created_at": _iso(row.created_at),
        }

    def _serialize_draft(self, row: CaseDraft) -> dict[str, Any]:
        return {
            "id": row.id,
            "case_id": row.case_id,
            "draft_type": row.draft_type,
            "status": row.status,
            "revision": row.revision,
            "content": row.content or {},
            "grounded_action_id": row.grounded_action_id,
            "created_by_user_id": row.created_by_user_id,
            "approved_by_user_id": row.approved_by_user_id,
            "approved_at": _iso(row.approved_at),
            "created_at": _iso(row.created_at),
            "updated_at": _iso(row.updated_at),
        }

    def _serialize_notification(self, row: CaseNotification) -> dict[str, Any]:
        return {
            "id": row.id,
            "case_id": row.case_id,
            "channel": row.channel,
            "template_key": row.template_key,
            "payload": row.payload or {},
            "delivery_status": row.delivery_status,
            "created_at": _iso(row.created_at),
        }

    def _transition(
        self,
        session: Session,
        case: CaseRecord,
        target: str,
        event_type: str,
        user: CurrentUser | None,
        payload: dict[str, Any] | None = None,
        actor_type: str = ACTOR_USER,
    ) -> None:
        self.workflow.assert_transition(case.workflow_status, target)
        from_status = case.workflow_status
        self._bump(case, target)
        self._append_event(
            session,
            case,
            event_type,
            actor_type=actor_type,
            actor_user_id=user.id if user else None,
            from_status=from_status,
            to_status=target,
            payload=payload or {},
            before_value={"workflow_status": from_status},
            after_value={"workflow_status": target},
        )

    def mark_analysis_started(
        self,
        case_id: str,
        user: CurrentUser | None,
        *,
        expected_version: int | None = None,
        confirmed: bool | None = None,
    ) -> dict[str, Any]:
        with self.session_factory.begin() as session:
            case = (
                self._load_case(session, case_id)
                if user is None
                else self._scoped_case(session, user, case_id, for_update=True)
            )
            if user is not None:
                self._require_role(user, ROLE_EVRAK_KAYIT)
            if confirmed is not None:
                self._require_confirmed(confirmed)
            if expected_version is not None:
                self._require_version(case, expected_version)
            self._transition(session, case, STATUS_ANALYZING, EVENT_ANALYSIS_STARTED, user, actor_type=ACTOR_USER if user else ACTOR_SYSTEM)
            return self.serialize_case(case)

    def mark_analysis_completed(
        self,
        case_id: str,
        user: CurrentUser | None,
        *,
        expected_version: int | None = None,
        confirmed: bool | None = None,
        ready_to_route: bool = False,
    ) -> dict[str, Any]:
        with self.session_factory.begin() as session:
            case = (
                self._load_case(session, case_id)
                if user is None
                else self._scoped_case(session, user, case_id, for_update=True)
            )
            if user is not None:
                self._require_role(user, ROLE_EVRAK_KAYIT)
            if confirmed is not None:
                self._require_confirmed(confirmed)
            if expected_version is not None:
                self._require_version(case, expected_version)
            self._transition(
                session,
                case,
                STATUS_READY_TO_ROUTE if ready_to_route else STATUS_WAITING_INITIAL_REVIEW,
                EVENT_ANALYSIS_COMPLETED,
                user,
                actor_type=ACTOR_USER if user else ACTOR_SYSTEM,
            )
            return self.serialize_case(case)

    def accept_review(self, user: CurrentUser, case_id: str, expected_version: int, confirmed: bool) -> dict[str, Any]:
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id, for_update=True)
            self._require_role(user, ROLE_EVRAK_KAYIT)
            self._require_confirmed(confirmed)
            self._require_version(case, expected_version)
            analysis = session.get(Analysis, case.analysis_id) if case.analysis_id else None
            analysis_state = dict(analysis.state_json or {}) if analysis is not None else {}
            orchestration = analysis_state.get("case_orchestration") or {}
            clarification = analysis_state.get("clarification") or {}
            if orchestration.get("blocking_missing") or clarification.get("blocking"):
                raise invalid_case_transition(
                    case.workflow_status,
                    STATUS_WAITING_CITIZEN_INFO,
                )
            self._transition(session, case, STATUS_READY_TO_ROUTE, "REVIEW_ACCEPTED", user)
            return self.serialize_case(case)

    def route_case(
        self,
        user: CurrentUser,
        case_id: str,
        *,
        department_code: str,
        expected_version: int,
        confirmed: bool,
        reason: str | None,
        routing_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id, for_update=True)
            self._require_role(user, ROLE_EVRAK_KAYIT)
            self._require_confirmed(confirmed)
            self._require_version(case, expected_version)
            assert_department(case.institution_id, department_code)
            self.workflow.assert_transition(case.workflow_status, STATUS_IN_DEPARTMENT)
            active = session.scalars(
                select(CaseAssignment).where(
                    CaseAssignment.case_id == case.id,
                    CaseAssignment.ended_at.is_(None),
                )
            ).all()
            before_routing = {
                "department_code": case.current_department_code,
                "workflow_status": case.workflow_status,
                "active_assignment_ids": [item.id for item in active],
            }
            now = _now()
            for item in active:
                item.ended_at = now
            assignment = CaseAssignment(
                id=str(uuid.uuid4()),
                case_id=case.id,
                department_code=department_code,
                assigned_user_id=None,
                assigned_by_user_id=user.id,
                assigned_at=now,
                ended_at=None,
                reason=reason,
                routing_snapshot=routing_snapshot or {},
            )
            session.add(assignment)
            operation = dict((routing_snapshot or {}).get("ai_operation") or {})
            if not operation and case.analysis_id:
                analysis = session.get(Analysis, case.analysis_id)
                if analysis is not None:
                    operation = dict(
                        (dict(analysis.state_json or {}).get("case_orchestration") or {}).get("ai_operation")
                        or {}
                    )
            # A human may select a different Level-1 department than the AI.
            # Preserve the recommendation for audit, but never carry its team
            # into a department where it does not belong.
            operation_department = str(operation.get("department_code") or "")
            if operation_department and operation_department != department_code:
                task_team_code = None
                task_role = None
            else:
                task_team_code = operation.get("team_code")
                task_role = operation.get("recommended_role")
            task = CaseTask(
                id=str(uuid.uuid4()),
                case_id=case.id,
                source_case_id=case.id,
                task_type=str(operation.get("task_type") or "GENEL_INCELEME"),
                department_code=department_code,
                team_code=str(task_team_code) if task_team_code else None,
                recommended_role=str(task_role) if task_role else "BIRIM_PERSONELI",
                assigned_user_id=None,
                status=TASK_ASSIGNMENT_PENDING,
                reason=reason or operation.get("reason"),
                ai_recommendation=operation,
                created_by_user_id=user.id,
                created_at=now,
                updated_at=now,
            )
            session.add(task)
            from_status = case.workflow_status
            case.current_department_code = department_code
            self._bump(case, STATUS_IN_DEPARTMENT)
            payload = {
                "from_department": before_routing["department_code"],
                "to_department": department_code,
                "department_code": department_code,
                "assignment_id": assignment.id,
                "task_id": task.id,
                "routing_snapshot": routing_snapshot or {},
                "ai_recommendation": operation,
                "human_decision": {"actor_user_id": user.id, "reason": reason},
            }
            after_routing = {
                "department_code": department_code,
                "workflow_status": STATUS_IN_DEPARTMENT,
                "active_assignment_ids": [assignment.id],
            }
            self._append_event(
                session,
                case,
                EVENT_ROUTING_CONFIRMED,
                actor_type=ACTOR_USER,
                actor_user_id=user.id,
                from_status=from_status,
                to_status=STATUS_IN_DEPARTMENT,
                payload=payload,
                before_value=before_routing,
                after_value=after_routing,
            )
            self._append_event(
                session,
                case,
                EVENT_TASK_CREATED,
                actor_type=ACTOR_SYSTEM,
                actor_user_id=None,
                from_status=STATUS_IN_DEPARTMENT,
                to_status=STATUS_IN_DEPARTMENT,
                payload={"task_id": task.id, "status": task.status, "ai_recommendation": operation},
            )
            self._append_event(
                session,
                case,
                EVENT_CASE_ROUTED,
                actor_type=ACTOR_USER,
                actor_user_id=user.id,
                from_status=from_status,
                to_status=STATUS_IN_DEPARTMENT,
                payload=payload,
                before_value=before_routing,
                after_value=after_routing,
            )
            self.notifications.store(
                session,
                case_id=case.id,
                channel="PORTAL",
                template_key="CASE_ROUTED",
                payload={"department_code": department_code},
            )
            forwarding = CaseDraft(
                id=str(uuid.uuid4()), case_id=case.id,
                draft_type="FORWARDING_COVER_LETTER", status=DRAFT_STATUS_DRAFT,
                revision=1,
                content={
                    "subject": "Dosyanın İlgili Birime Yönlendirilmesi",
                    "recipient": _department_name(case.institution_id, department_code),
                    "sender_unit": _department_name(case.institution_id, user.department_code),
                    "recipient_kind": "INTERNAL_DEPARTMENT",
                    "body": f"{case.tracking_code} takip numaralı başvuru, görev alanınız kapsamında değerlendirilmek ve gerekli işlemler yapılmak üzere biriminize yönlendirilmiştir.",
                },
                grounded_action_id=None, created_by_user_id=user.id,
                created_at=_now(), updated_at=_now(),
            )
            session.add(forwarding)
            self._append_event(session, case, EVENT_DRAFT_SAVED, actor_type=ACTOR_USER, actor_user_id=user.id, from_status=case.workflow_status, to_status=case.workflow_status, payload={"draft_id": forwarding.id, "draft_type": forwarding.draft_type})
            serialized = self.serialize_case(case)
            serialized["assignment_id"] = assignment.id
            serialized["task"] = self._serialize_task(task)
            return serialized

    def assign_task(
        self,
        user: CurrentUser,
        case_id: str,
        task_id: str,
        *,
        assigned_user_id: str,
        expected_version: int,
        confirmed: bool,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Manager-approved task assignment within the receiving department.

        The demo permission model has no separate manager principal.  A
        ``BIRIM_PERSONELI`` in the receiving department is the deliberately
        narrow approval authority; named personnel are never chosen by AI.
        """
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id, for_update=True)
            self._require_own_department(user, case)
            self._require_confirmed(confirmed)
            self._require_version(case, expected_version)
            task = session.scalar(
                select(CaseTask).where(CaseTask.id == task_id, CaseTask.case_id == case.id)
            )
            if task is None:
                raise validation_error("Görev bulunamadı.", task_id=task_id)
            if task.department_code != user.department_code:
                raise action_forbidden(department_code=user.department_code)
            if task.status != TASK_ASSIGNMENT_PENDING:
                raise validation_error("Görev atama onayı beklemiyor.", task_status=task.status)
            assignee = session.get(CaseUser, assigned_user_id)
            if assignee is None or not assignee.is_active or assignee.institution_id != case.institution_id:
                raise validation_error("Atanacak kullanıcı bulunamadı veya aktif değil.")
            if assignee.department_code != task.department_code:
                raise validation_error("Kullanıcı hedef birimde değil.", department_code=task.department_code)
            task.assigned_user_id = assignee.id
            task.approved_by_user_id = user.id
            task.status = TASK_ASSIGNED
            task.reason = reason or task.reason
            task.updated_at = _now()
            self._bump(case)
            self._append_event(
                session, case, EVENT_TASK_ASSIGNED,
                actor_type=ACTOR_USER, actor_user_id=user.id,
                from_status=case.workflow_status, to_status=case.workflow_status,
                payload={"task_id": task.id, "assigned_user_id": assignee.id, "reason": reason},
            )
            return {"case": self.serialize_case(case), "task": self._serialize_task(task)}

    def update_task_status(
        self,
        user: CurrentUser,
        case_id: str,
        task_id: str,
        *,
        status: str,
        expected_version: int,
        confirmed: bool,
        reason: str | None = None,
    ) -> dict[str, Any]:
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id, for_update=True)
            self._require_own_department(user, case)
            self._require_confirmed(confirmed)
            self._require_version(case, expected_version)
            task = session.scalar(select(CaseTask).where(CaseTask.id == task_id, CaseTask.case_id == case.id))
            if task is None:
                raise validation_error("Görev bulunamadı.", task_id=task_id)
            if task.department_code != user.department_code or task.status == TASK_ASSIGNMENT_PENDING:
                raise validation_error("Atama onayı olmayan görev ilerletilemez.")
            if status not in TASK_STATUSES or status == TASK_ASSIGNMENT_PENDING:
                raise validation_error("Geçersiz görev durumu.", status=status)
            before = task.status
            task.status = status
            task.reason = reason or task.reason
            task.updated_at = _now()
            self._bump(case)
            self._append_event(
                session, case, EVENT_TASK_STATUS_CHANGED,
                actor_type=ACTOR_USER, actor_user_id=user.id,
                from_status=case.workflow_status, to_status=case.workflow_status,
                payload={"task_id": task.id, "from_status": before, "to_status": status, "reason": reason},
            )
            return {"case": self.serialize_case(case), "task": self._serialize_task(task)}

    def create_information_request(
        self,
        user: CurrentUser,
        case_id: str,
        *,
        requested_fields: list[str],
        reason: str,
        expected_version: int,
        confirmed: bool,
        target_type: str | None = None,
        target_name: str | None = None,
        target_department: str | None = None,
    ) -> dict[str, Any]:
        from backend.app.intelligence.municipal_workflow import ClarificationTargetResolver

        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id, for_update=True)
            if user.role == ROLE_BIRIM_PERSONELI:
                self._require_own_department(user, case)
            else:
                self._require_role(user, ROLE_EVRAK_KAYIT)
            self._require_confirmed(confirmed)
            self._require_version(case, expected_version)
            target = ClarificationTargetResolver().resolve(
                originator={
                    "originator_type": target_type or case.originator_type,
                    "originator_name": target_name or case.originator_name,
                    "current_department_code": target_department,
                },
                document={"source_type": case.source_type, "source_department_code": target_department},
                reason=reason,
            )
            request = CaseInformationRequest(
                id=str(uuid.uuid4()), case_id=case.id,
                target_type=target["target_type"], target_name=target["target_name"],
                target_department=target["target_department"],
                requested_fields=list(dict.fromkeys(requested_fields)), reason=target["reason"],
                recommended_action=target["recommended_action"], status="PENDING",
                created_by_user_id=user.id, created_at=_now(),
            )
            session.add(request)
            self._bump(case)
            event_type = (
                EVENT_INTERNAL_INFORMATION_REQUESTED
                if request.target_type == "INTERNAL_DEPARTMENT"
                else EVENT_EXTERNAL_INFORMATION_REQUESTED
            )
            self._append_event(
                session, case, event_type, actor_type=ACTOR_USER, actor_user_id=user.id,
                from_status=case.workflow_status, to_status=case.workflow_status,
                payload={"information_request_id": request.id, "target": target, "requested_fields": request.requested_fields},
            )
            return {"case": self.serialize_case(case), "information_request": self._serialize_information_request(request)}

    def start_case(self, user: CurrentUser, case_id: str, expected_version: int, confirmed: bool) -> dict[str, Any]:
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id, for_update=True)
            self._require_own_department(user, case)
            self._require_confirmed(confirmed)
            self._require_version(case, expected_version)
            case.assigned_user_id = user.id
            self._transition(session, case, STATUS_IN_PROGRESS, EVENT_CASE_STARTED, user)
            return self.serialize_case(case)

    def record_department_action(
        self,
        user: CurrentUser,
        case_id: str,
        payload: dict[str, Any],
        expected_version: int,
        confirmed: bool,
    ) -> dict[str, Any]:
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id, for_update=True)
            self._require_own_department(user, case)
            self._require_confirmed(confirmed)
            self._require_version(case, expected_version)
            if case.workflow_status != STATUS_IN_PROGRESS:
                raise invalid_case_transition(case.workflow_status, STATUS_IN_PROGRESS)
            action = DepartmentAction(
                id=str(uuid.uuid4()),
                case_id=case.id,
                action_type=payload["action_type"],
                result=payload["result"],
                decision=payload["decision"],
                planned_date=payload.get("planned_date"),
                notes=payload.get("notes") or "",
                verified=True,
                recorded_by_user_id=user.id,
                created_at=_now(),
            )
            session.add(action)
            self._bump(case)
            self._append_event(
                session,
                case,
                EVENT_DEPARTMENT_ACTION_RECORDED,
                actor_type=ACTOR_USER,
                actor_user_id=user.id,
                from_status=case.workflow_status,
                to_status=case.workflow_status,
                payload={"action_id": action.id, "action_type": action.action_type},
            )
            return self._serialize_action(action) | {"case": self.serialize_case(case)}

    def create_citizen_request(
        self,
        user: CurrentUser,
        case_id: str,
        payload: dict[str, Any],
        expected_version: int,
        confirmed: bool,
    ) -> dict[str, Any]:
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id, for_update=True)
            self._require_role(user, ROLE_EVRAK_KAYIT)
            self._require_confirmed(confirmed)
            self._require_version(case, expected_version)
            requested_fields = [
                field.strip()
                for field in payload["requested_fields"]
                if isinstance(field, str) and field.strip()
            ]
            if not requested_fields or len(requested_fields) != len(
                set(requested_fields)
            ):
                raise validation_error(
                    "İstenen alanlar boş veya tekrarlı olamaz."
                )
            resume_target = str(
                payload.get("resume_target") or STATUS_READY_TO_ROUTE
            ).upper()
            if resume_target not in {
                STATUS_ANALYZING,
                STATUS_READY_TO_ROUTE,
                "MISSING_FIELD",
                "MISSING_INFORMATION",
                "ROUTING",
            }:
                raise validation_error(
                    "Geçersiz devam hedefi.", resume_target=resume_target
                )
            request = CitizenRequest(
                id=str(uuid.uuid4()),
                case_id=case.id,
                status="PENDING",
                blocking=bool(payload.get("blocking", True)),
                requested_fields=requested_fields,
                question_type=payload.get("question_type") or "free_text",
                question=payload["question"],
                options=list(payload.get("options") or []),
                resume_target=resume_target,
                created_by_user_id=user.id,
                created_at=_now(),
            )
            session.add(request)
            self._transition(
                session,
                case,
                STATUS_WAITING_CITIZEN_INFO,
                EVENT_CITIZEN_INFO_REQUESTED,
                user,
                payload={"citizen_request_id": request.id, "requested_fields": request.requested_fields},
            )
            self.notifications.store(
                session,
                case_id=case.id,
                channel="PORTAL",
                template_key="CITIZEN_INFO_REQUESTED",
                payload={"tracking_code": case.tracking_code},
            )
            return {
                "citizen_request": self._serialize_citizen_request(request),
                "case": self.serialize_case(case),
            }

    def save_draft(
        self,
        user: CurrentUser,
        case_id: str,
        *,
        draft_type: str,
        content: dict[str, Any],
        grounded_action_id: str | None,
        expected_version: int,
        confirmed: bool,
    ) -> dict[str, Any]:
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id, for_update=True)
            self._require_own_department(user, case)
            self._require_confirmed(confirmed)
            self._require_version(case, expected_version)
            if draft_type not in DRAFT_TYPES:
                raise validation_error("Geçersiz taslak türü.", draft_type=draft_type)
            if case.workflow_status not in {STATUS_IN_PROGRESS, STATUS_RESPONSE_DRAFTED, STATUS_WAITING_FINAL_APPROVAL}:
                raise invalid_case_transition(case.workflow_status)
            verified_actions = list(
                session.scalars(
                    select(DepartmentAction).where(
                        DepartmentAction.case_id == case.id,
                        DepartmentAction.verified.is_(True),
                    )
                )
            )
            action_id = grounded_action_id
            if draft_type == "OFFICIAL_RESPONSE":
                if action_id:
                    match = next((item for item in verified_actions if item.id == action_id), None)
                    if match is None:
                        raise verified_department_action_required()
                elif len(verified_actions) == 1:
                    action_id = verified_actions[0].id
                else:
                    raise verified_department_action_required()
            existing = session.scalars(
                select(CaseDraft)
                .where(CaseDraft.case_id == case.id, CaseDraft.draft_type == draft_type)
                .order_by(CaseDraft.revision.desc())
            ).first()
            revision = (existing.revision + 1) if existing else 1
            status = DRAFT_STATUS_EDITED if existing else DRAFT_STATUS_DRAFT
            draft = CaseDraft(
                id=str(uuid.uuid4()),
                case_id=case.id,
                draft_type=draft_type,
                status=status,
                revision=revision,
                content=content or {},
                grounded_action_id=action_id,
                created_by_user_id=user.id,
                created_at=_now(),
                updated_at=_now(),
            )
            session.add(draft)
            if case.workflow_status == STATUS_IN_PROGRESS and draft_type == "OFFICIAL_RESPONSE":
                self._transition(session, case, STATUS_RESPONSE_DRAFTED, EVENT_DRAFT_SAVED, user, payload={"draft_id": draft.id})
            elif case.workflow_status == STATUS_WAITING_FINAL_APPROVAL:
                self._transition(
                    session,
                    case,
                    STATUS_RESPONSE_DRAFTED,
                    "DRAFT_REVISION_REQUESTED",
                    user,
                    payload={"draft_id": draft.id},
                )
            else:
                self._bump(case)
                self._append_event(
                    session,
                    case,
                    EVENT_DRAFT_SAVED,
                    actor_type=ACTOR_USER,
                    actor_user_id=user.id,
                    from_status=case.workflow_status,
                    to_status=case.workflow_status,
                    payload={"draft_id": draft.id},
                )
            return {"draft": self._serialize_draft(draft), "case": self.serialize_case(case)}

    def approve_draft(
        self,
        user: CurrentUser,
        case_id: str,
        draft_id: str,
        expected_version: int,
        confirmed: bool,
    ) -> dict[str, Any]:
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id, for_update=True)
            self._require_own_department(user, case)
            self._require_confirmed(confirmed)
            self._require_version(case, expected_version)
            draft = session.get(CaseDraft, draft_id)
            if draft is None or draft.case_id != case.id:
                raise validation_error("Taslak bulunamadı.", draft_id=draft_id)
            if draft.status not in {DRAFT_STATUS_DRAFT, DRAFT_STATUS_EDITED}:
                raise invalid_case_transition(case.workflow_status)
            if draft.draft_type == "OFFICIAL_RESPONSE":
                if case.workflow_status != STATUS_RESPONSE_DRAFTED:
                    raise invalid_case_transition(case.workflow_status, STATUS_WAITING_FINAL_APPROVAL)
                grounded_action = (
                    session.get(DepartmentAction, draft.grounded_action_id)
                    if draft.grounded_action_id
                    else None
                )
                if (
                    grounded_action is None
                    or grounded_action.case_id != case.id
                    or not grounded_action.verified
                ):
                    raise verified_department_action_required()
            before_draft = {
                "status": draft.status,
                "approved_by_user_id": draft.approved_by_user_id,
                "approved_at": _iso(draft.approved_at),
            }
            draft.status = DRAFT_STATUS_APPROVED
            draft.approved_by_user_id = user.id
            draft.approved_at = _now()
            after_draft = {
                "status": draft.status,
                "approved_by_user_id": draft.approved_by_user_id,
                "approved_at": _iso(draft.approved_at),
            }
            if draft.draft_type == "OFFICIAL_RESPONSE":
                self._transition(session, case, STATUS_WAITING_FINAL_APPROVAL, EVENT_DRAFT_SUBMITTED, user, payload={"draft_id": draft.id})
            else:
                self._bump(case)
            self._append_event(
                session,
                case,
                EVENT_DRAFT_APPROVED,
                actor_type=ACTOR_USER,
                actor_user_id=user.id,
                from_status=case.workflow_status,
                to_status=case.workflow_status,
                payload={"draft_id": draft.id},
                before_value=before_draft,
                after_value=after_draft,
            )
            return {"draft": self._serialize_draft(draft), "case": self.serialize_case(case)}

    def complete_case(
        self,
        user: CurrentUser,
        case_id: str,
        draft_id: str,
        expected_version: int,
        confirmed: bool,
    ) -> dict[str, Any]:
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id, for_update=True)
            self._require_own_department(user, case)
            self._require_confirmed(confirmed)
            self._require_version(case, expected_version)
            draft = session.get(CaseDraft, draft_id)
            if draft is None or draft.case_id != case.id or draft.status != DRAFT_STATUS_APPROVED:
                raise approved_draft_required()
            recipient = {
                "originator_type": case.originator_type,
                "originator_name": case.originator_name,
                "originator_email": case.originator_email,
                "originator_phone": case.originator_phone,
            }
            self._transition(
                session,
                case,
                STATUS_COMPLETED,
                EVENT_CASE_COMPLETED,
                user,
                payload={"draft_id": draft.id, "recipient": recipient},
            )
            self.notifications.store(
                session,
                case_id=case.id,
                channel="PORTAL",
                template_key="CASE_COMPLETED",
                payload={"tracking_code": case.tracking_code, "recipient_name": case.originator_name},
            )
            return {"case": self.serialize_case(case), "recipient": recipient}

    def close_case(self, user: CurrentUser, case_id: str, expected_version: int, confirmed: bool) -> dict[str, Any]:
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id, for_update=True)
            self._require_role(user, ROLE_EVRAK_KAYIT)
            self._require_confirmed(confirmed)
            self._require_version(case, expected_version)
            case.closed_at = _now()
            self._transition(session, case, STATUS_CLOSED, EVENT_CASE_CLOSED, user)
            return self.serialize_case(case)

    def issue_citizen_access(self, user: CurrentUser, case_id: str) -> dict[str, str]:
        """Issue a fresh public link without exposing its token in the Case DTO."""
        raw_token = secrets.token_urlsafe(32)
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id, for_update=True)
            case.citizen_token_hash = hash_citizen_token(raw_token)
            case.updated_at = _now()
            return {
                "tracking_code": case.tracking_code,
                "citizen_url": f"/takip/{case.tracking_code}?token={raw_token}",
            }

    def public_projection(self, tracking_code: str, token: str) -> dict[str, Any]:
        with self.session_factory() as session:
            case = session.scalar(
                select(CaseRecord).where(CaseRecord.tracking_code == tracking_code)
            )
            if case is None or not tokens_match(token, case.citizen_token_hash):
                raise citizen_token_invalid()
            events = list(
                session.scalars(
                    select(CaseEvent)
                    .where(CaseEvent.case_id == case.id)
                    .order_by(CaseEvent.created_at.asc(), CaseEvent.id.asc())
                )
            )
            pending = session.scalar(
                select(CitizenRequest)
                .where(
                    CitizenRequest.case_id == case.id,
                    CitizenRequest.status == "PENDING",
                )
                .order_by(CitizenRequest.created_at.desc())
            )
            timeline = []
            for event in events:
                label = PUBLIC_EVENT_LABELS.get(event.event_type)
                if not label:
                    continue
                timeline.append(
                    {
                        "event": event.event_type,
                        "label": label,
                        "created_at": _iso(event.created_at),
                    }
                )
            clarification = None
            if pending is not None:
                options = []
                for option in pending.options or []:
                    if isinstance(option, dict):
                        options.append(option)
                    else:
                        value = str(option)
                        options.append({"value": value, "label": value.replace("_", " ")})
                clarification = {
                    "requested_fields": pending.requested_fields or [],
                    "question": pending.question,
                    "question_type": "choice" if pending.question_type in {"choice", "single_choice"} else "free_text",
                    "options": options,
                }
            return {
                "tracking_code": case.tracking_code,
                "public_status": PUBLIC_STATUS_LABELS.get(case.workflow_status, "İşlemde"),
                "received_at": _iso(case.received_at),
                "updated_at": _iso(case.updated_at),
                "timeline": timeline,
                "clarification": clarification,
            }

    def complete_citizen_info(
        self,
        tracking_code: str,
        token: str,
        answers: dict[str, Any],
    ) -> dict[str, Any]:
        from backend.app.cases.hooks import emit_citizen_info_received

        with self.session_factory.begin() as session:
            case = session.scalar(
                select(CaseRecord)
                .where(CaseRecord.tracking_code == tracking_code)
                .with_for_update()
            )
            if case is None or not tokens_match(token, case.citizen_token_hash):
                raise citizen_token_invalid()
            pending = session.scalar(
                select(CitizenRequest)
                .where(
                    CitizenRequest.case_id == case.id,
                    CitizenRequest.status == "PENDING",
                )
                .order_by(CitizenRequest.created_at.desc())
            )
            if pending is None or case.workflow_status != STATUS_WAITING_CITIZEN_INFO:
                raise clarification_not_active()
            allowlist = list(pending.requested_fields or [])
            extra = set(answers) - set(allowlist)
            if extra:
                raise validation_error(
                    "Talep edilmeyen alanlar gönderilemez.",
                    extra_fields=sorted(extra),
                )
            missing = [field for field in allowlist if field not in answers]
            if missing:
                raise validation_error("İstenen alanlar eksik.", missing_fields=missing)
            pending.status = "COMPLETED"
            pending.completed_at = _now()
            pending.submitted_payload = {field: answers[field] for field in allowlist}
            # Every citizen answer becomes structured evidence and returns to
            # focused AI reevaluation. The registered bridge decides whether
            # the safe result is READY_TO_ROUTE or human review.
            target = STATUS_ANALYZING if case.analysis_id else STATUS_READY_TO_ROUTE
            self._transition(
                session,
                case,
                target,
                EVENT_CITIZEN_INFO_COMPLETED,
                user=None,
                payload={"citizen_request_id": pending.id, "resume_target": target},
                actor_type=ACTOR_CITIZEN,
            )
            case_id = case.id
            submitted = dict(pending.submitted_payload)
            target_status = target
        emit_citizen_info_received(
            case_id,
            {"answers": submitted, "resume_target": target_status},
        )
        return self.public_projection(tracking_code, token)
