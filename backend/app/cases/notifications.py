"""Notification storage. No external SMS/email provider is invoked."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.cases.enums import EVENT_NOTIFICATION_STORED, NOTIFICATION_CHANNELS
from backend.app.cases.errors import validation_error
from backend.app.db.case_models import CaseNotification, CaseRecord


logger = logging.getLogger(__name__)


class NotificationService:
    def store(
        self,
        session: Session,
        *,
        case_id: str,
        channel: str,
        template_key: str,
        payload: dict[str, Any] | None = None,
    ) -> CaseNotification:
        if channel not in NOTIFICATION_CHANNELS:
            raise validation_error("Geçersiz bildirim kanalı.", channel=channel)
        safe_payload = dict(payload or {})
        safe_payload.pop("citizen_token", None)
        safe_payload.pop("token", None)
        row = CaseNotification(
            id=str(uuid.uuid4()),
            case_id=case_id,
            channel=channel,
            template_key=template_key,
            payload=safe_payload,
            delivery_status="STORED_NOT_SENT",
        )
        session.add(row)
        logger.info(
            "Citizen notification queued: case_id=%s template=%s channel=%s",
            case_id,
            template_key,
            channel,
        )
        return row

    def queue_analysis_rejected(
        self,
        *,
        analysis_id: str,
        reason: str | None = None,
    ) -> CaseNotification | None:
        """Queue a portal notification when a linked analysis is rejected.

        Legacy analyses can exist without a Case record.  In that situation we
        only emit an audit-friendly log and never invent a recipient or call an
        external provider.
        """

        try:
            from backend.app.cases.runtime import get_case_engine

            engine = get_case_engine()
            with engine.session_factory.begin() as session:
                case = session.scalar(
                    select(CaseRecord).where(CaseRecord.analysis_id == analysis_id)
                )
                if case is None:
                    logger.info(
                        "Citizen notification not queued: rejected analysis has no linked case: analysis_id=%s",
                        analysis_id,
                    )
                    return None
                return self.store(
                    session,
                    case_id=case.id,
                    channel="PORTAL",
                    template_key="ANALYSIS_REJECTED",
                    payload={
                        "tracking_code": case.tracking_code,
                        "reason_provided": bool(reason),
                    },
                )
        except Exception:
            # Rejection remains durable even if best-effort notification
            # queueing is unavailable.  There is deliberately no SMS/e-mail
            # provider call in this scope.
            logger.exception(
                "Citizen notification queueing failed for rejected analysis: analysis_id=%s",
                analysis_id,
            )
            return None

    @staticmethod
    def event_payload(notification: CaseNotification) -> dict[str, Any]:
        return {
            "event_type": EVENT_NOTIFICATION_STORED,
            "notification_id": notification.id,
            "channel": notification.channel,
            "template_key": notification.template_key,
            "delivery_status": notification.delivery_status,
        }
