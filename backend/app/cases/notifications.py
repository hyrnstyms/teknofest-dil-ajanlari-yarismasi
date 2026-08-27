"""Notification storage. No external SMS/email provider is invoked."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from backend.app.cases.enums import EVENT_NOTIFICATION_STORED, NOTIFICATION_CHANNELS
from backend.app.cases.errors import validation_error
from backend.app.db.case_models import CaseNotification


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
        return row

    @staticmethod
    def event_payload(notification: CaseNotification) -> dict[str, Any]:
        return {
            "event_type": EVENT_NOTIFICATION_STORED,
            "notification_id": notification.id,
            "channel": notification.channel,
            "template_key": notification.template_key,
            "delivery_status": notification.delivery_status,
        }
