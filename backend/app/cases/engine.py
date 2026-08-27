"""Deterministic Case engine: persistence, RBAC, transitions, events."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.auth.dependencies import CurrentUser
from backend.app.auth.principals import DEMO_USERS
from backend.app.cases.departments import assert_department
from backend.app.cases.enums import (
    ACTOR_CITIZEN,
    ACTOR_SYSTEM,
    ACTOR_USER,
    DEPARTMENT_INBOX_STATUSES,
    DRAFT_STATUS_APPROVED,
    DRAFT_STATUS_DRAFT,
    DRAFT_STATUS_EDITED,
    DRAFT_STATUS_SENT,
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
    CaseUser,
    CitizenRequest,
    DepartmentAction,
)
from backend.app.db.database import create_session_factory


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
            session.execute(delete(CitizenRequest))
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
    ) -> CaseEvent:
        event = CaseEvent(
            id=str(uuid.uuid4()),
            case_id=case.id,
            event_type=event_type,
            actor_type=actor_type,
            actor_user_id=actor_user_id,
            from_status=from_status,
            to_status=to_status,
            payload=payload or {},
            created_at=_now(),
        )
        session.add(event)
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

    def _scoped_case(self, session: Session, user: CurrentUser, case_id: str) -> CaseRecord:
        row = session.get(CaseRecord, case_id)
        if row is None or row.institution_id != user.institution_id:
            raise case_not_found()
        if not self.can_view(user, row):
            raise action_forbidden(case_id=case_id, role=user.role)
        return row

    def can_view(self, user: CurrentUser, case: CaseRecord) -> bool:
        if case.institution_id != user.institution_id:
            return False
        if user.role == ROLE_EVRAK_KAYIT:
            if case.workflow_status in REGISTRY_INBOX_STATUSES:
                return True
            if case.workflow_status == STATUS_CLOSED:
                return True
            return case.current_department_code == user.department_code
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
                actions.extend(["RECORD_DEPARTMENT_ACTION", "SAVE_DRAFT"])
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
            "source_type": case.source_type,
            "source_channel": case.source_channel,
            "originator_type": case.originator_type,
            "originator_name": case.originator_name,
            "originator_email": case.originator_email,
            "originator_phone": case.originator_phone,
            "current_department_code": case.current_department_code,
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
        limit: int = 20,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 100))
        offset = int(cursor) if cursor else 0
        with self.session_factory() as session:
            statement = select(CaseRecord).where(
                CaseRecord.institution_id == user.institution_id
            )
            if user.role == ROLE_EVRAK_KAYIT:
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
                "events": [self._serialize_event(item) for item in events],
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
                aggregate["analysis"] = {
                    "analysis_id": stored.get("analysis_id"),
                    "document_type": (stored.get("document") or {}).get("document_type"),
                    "process_intent": (stored.get("document") or {}).get("process_intent"),
                    "recommended_unit": (stored.get("routing") or {}).get("recommended_unit"),
                    "recommended_department_code": (stored.get("routing") or {}).get(
                        "recommended_department_code"
                    ),
                    "human_review_status": (stored.get("human_review") or {}).get("status"),
                }
        return aggregate

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
        )

    def mark_analysis_started(self, case_id: str, user: CurrentUser | None) -> dict[str, Any]:
        with self.session_factory.begin() as session:
            case = self._load_case(session, case_id) if user is None else self._scoped_case(session, user, case_id)
            if user is not None:
                self._require_role(user, ROLE_EVRAK_KAYIT)
            self._transition(session, case, STATUS_ANALYZING, EVENT_ANALYSIS_STARTED, user, actor_type=ACTOR_USER if user else ACTOR_SYSTEM)
            return self.serialize_case(case)

    def mark_analysis_completed(self, case_id: str, user: CurrentUser | None) -> dict[str, Any]:
        with self.session_factory.begin() as session:
            case = self._load_case(session, case_id) if user is None else self._scoped_case(session, user, case_id)
            if user is not None:
                self._require_role(user, ROLE_EVRAK_KAYIT)
            self._transition(
                session,
                case,
                STATUS_WAITING_INITIAL_REVIEW,
                EVENT_ANALYSIS_COMPLETED,
                user,
                actor_type=ACTOR_USER if user else ACTOR_SYSTEM,
            )
            return self.serialize_case(case)

    def accept_review(self, user: CurrentUser, case_id: str, expected_version: int, confirmed: bool) -> dict[str, Any]:
        self._require_role(user, ROLE_EVRAK_KAYIT)
        self._require_confirmed(confirmed)
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id)
            self._require_version(case, expected_version)
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
        self._require_role(user, ROLE_EVRAK_KAYIT)
        self._require_confirmed(confirmed)
        assert_department(user.institution_id, department_code)
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id)
            self._require_version(case, expected_version)
            self.workflow.assert_transition(case.workflow_status, STATUS_IN_DEPARTMENT)
            active = session.scalars(
                select(CaseAssignment).where(
                    CaseAssignment.case_id == case.id,
                    CaseAssignment.ended_at.is_(None),
                )
            ).all()
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
            from_status = case.workflow_status
            case.current_department_code = department_code
            self._bump(case, STATUS_IN_DEPARTMENT)
            payload = {
                "department_code": department_code,
                "assignment_id": assignment.id,
                "routing_snapshot": routing_snapshot or {},
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
            )
            self.notifications.store(
                session,
                case_id=case.id,
                channel="PORTAL",
                template_key="CASE_ROUTED",
                payload={"department_code": department_code},
            )
            serialized = self.serialize_case(case)
            serialized["assignment_id"] = assignment.id
            return serialized

    def start_case(self, user: CurrentUser, case_id: str, expected_version: int, confirmed: bool) -> dict[str, Any]:
        self._require_confirmed(confirmed)
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id)
            self._require_own_department(user, case)
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
        self._require_confirmed(confirmed)
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id)
            self._require_own_department(user, case)
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
        self._require_role(user, ROLE_EVRAK_KAYIT)
        self._require_confirmed(confirmed)
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id)
            self._require_version(case, expected_version)
            request = CitizenRequest(
                id=str(uuid.uuid4()),
                case_id=case.id,
                status="PENDING",
                blocking=bool(payload.get("blocking", True)),
                requested_fields=list(payload["requested_fields"]),
                question_type=payload.get("question_type") or "free_text",
                question=payload["question"],
                options=list(payload.get("options") or []),
                resume_target=payload.get("resume_target") or STATUS_READY_TO_ROUTE,
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
        self._require_confirmed(confirmed)
        if draft_type not in DRAFT_TYPES:
            raise validation_error("Geçersiz taslak türü.", draft_type=draft_type)
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id)
            self._require_own_department(user, case)
            self._require_version(case, expected_version)
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
            if case.workflow_status == STATUS_IN_PROGRESS:
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
        self._require_confirmed(confirmed)
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id)
            self._require_own_department(user, case)
            self._require_version(case, expected_version)
            draft = session.get(CaseDraft, draft_id)
            if draft is None or draft.case_id != case.id:
                raise validation_error("Taslak bulunamadı.", draft_id=draft_id)
            if draft.draft_type == "OFFICIAL_RESPONSE" and not draft.grounded_action_id:
                raise verified_department_action_required()
            draft.status = DRAFT_STATUS_APPROVED
            draft.approved_by_user_id = user.id
            draft.approved_at = _now()
            if case.workflow_status == STATUS_RESPONSE_DRAFTED:
                self._transition(
                    session,
                    case,
                    STATUS_WAITING_FINAL_APPROVAL,
                    EVENT_DRAFT_SUBMITTED,
                    user,
                    payload={"draft_id": draft.id},
                )
                self._append_event(
                    session,
                    case,
                    EVENT_DRAFT_APPROVED,
                    actor_type=ACTOR_USER,
                    actor_user_id=user.id,
                    from_status=STATUS_WAITING_FINAL_APPROVAL,
                    to_status=STATUS_WAITING_FINAL_APPROVAL,
                    payload={"draft_id": draft.id},
                )
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
        self._require_confirmed(confirmed)
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id)
            self._require_own_department(user, case)
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
            draft.status = DRAFT_STATUS_SENT
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
        self._require_role(user, ROLE_EVRAK_KAYIT)
        self._require_confirmed(confirmed)
        with self.session_factory.begin() as session:
            case = self._scoped_case(session, user, case_id)
            self._require_version(case, expected_version)
            case.closed_at = _now()
            self._transition(session, case, STATUS_CLOSED, EVENT_CASE_CLOSED, user)
            return self.serialize_case(case)

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
                clarification = {
                    "requested_fields": pending.requested_fields or [],
                    "question": pending.question,
                    "question_type": pending.question_type,
                    "options": pending.options or [],
                }
            return {
                "tracking_code": case.tracking_code,
                "public_status": PUBLIC_STATUS_LABELS.get(case.workflow_status, "İşlemde"),
                "workflow_status": case.workflow_status,
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
                select(CaseRecord).where(CaseRecord.tracking_code == tracking_code)
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
            resume = (pending.resume_target or STATUS_READY_TO_ROUTE).upper()
            if resume in {"ANALYZING", "MISSING_FIELD", "MISSING_INFORMATION"}:
                target = STATUS_ANALYZING
            else:
                target = STATUS_READY_TO_ROUTE
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
