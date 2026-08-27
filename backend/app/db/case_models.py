"""ORM models for the Case workflow domain.

Kept separate from Analysis/ReviewEvent so the existing analysis schema remains
untouched. Tables are registered on the shared Base metadata.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.models import Base, JsonType


class CaseUser(Base):
    """Internal demo/staff principal. Table name avoids colliding with Analysis."""

    __tablename__ = "case_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    institution_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    department_code: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CaseRecord(Base):
    """Institutional Case lifecycle record. Analysis remains a separate work product."""

    __tablename__ = "cases"
    __table_args__ = (UniqueConstraint("tracking_code", name="uq_cases_tracking_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tracking_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    analysis_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("analyses.analysis_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    institution_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_channel: Mapped[str] = mapped_column(String(32), nullable=False)
    originator_type: Mapped[str] = mapped_column(String(32), nullable=False)
    originator_name: Mapped[str] = mapped_column(String(256), nullable=False)
    originator_email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    originator_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_department_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    assigned_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("case_users.id", ondelete="SET NULL"), nullable=True
    )
    workflow_status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    priority: Mapped[str | None] = mapped_column(String(32), nullable=True)
    citizen_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class CaseTrackingCounter(Base):
    __tablename__ = "case_tracking_counters"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class CaseAssignment(Base):
    __tablename__ = "case_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    department_code: Mapped[str] = mapped_column(String(128), nullable=False)
    assigned_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    assigned_by_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    routing_snapshot: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)


class CaseEvent(Base):
    __tablename__ = "case_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)


class CitizenRequest(Base):
    __tablename__ = "citizen_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requested_fields: Mapped[list] = mapped_column(JsonType, nullable=False, default=list)
    question_type: Mapped[str] = mapped_column(String(32), nullable=False, default="free_text")
    question: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list] = mapped_column(JsonType, nullable=False, default=list)
    resume_target: Mapped[str] = mapped_column(String(64), nullable=False, default="READY_TO_ROUTE")
    created_by_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_payload: Mapped[dict | None] = mapped_column(JsonType, nullable=True)


class DepartmentAction(Base):
    __tablename__ = "department_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    planned_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    recorded_by_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CaseDraft(Base):
    __tablename__ = "case_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    draft_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    grounded_action_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("department_actions.id", ondelete="SET NULL"), nullable=True
    )
    created_by_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    approved_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CaseNotification(Base):
    __tablename__ = "case_notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    template_key: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    delivery_status: Mapped[str] = mapped_column(String(32), nullable=False, default="STORED_NOT_SENT")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CaseIdempotencyKey(Base):
    __tablename__ = "case_idempotency_keys"
    __table_args__ = (
        UniqueConstraint("actor_user_id", "key", name="uq_case_idempotency_actor_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    response_json: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
