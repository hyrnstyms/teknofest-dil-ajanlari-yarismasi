"""ClarificationAgent: minimum actionable question to continue safely."""

from __future__ import annotations

from typing import Any

from backend.app.intelligence.contracts import ClarificationPreview
from backend.app.intelligence.process_profiles import (
    detect_permit_ambiguity,
    field_label,
    matching_profiles,
    unresolved_blocking_groups,
)


class ClarificationAgent:
    """Produces one minimum question. Does not invent legal requirements."""

    def preview(
        self,
        *,
        missing_fields: dict[str, Any] | None = None,
        institution_id: str | None = None,
        document_type: str = "",
        process_intent: str = "",
        candidate_department: str | None = None,
        raw_text: str = "",
        document: dict[str, Any] | None = None,
        extracted_fields: dict[str, Any] | None = None,
        routing: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        missing_fields = missing_fields or {}
        document = document or {}
        extracted_fields = extracted_fields or missing_fields.get("extracted_fields") or {}
        routing = routing or {}

        permit = missing_fields.get("permit_ambiguity") or detect_permit_ambiguity(
            institution_id=institution_id,
            raw_text=raw_text,
            document=document,
            extracted_fields=extracted_fields,
        )
        if permit:
            preview = ClarificationPreview(
                needs_clarification=True,
                blocking=True,
                requested_fields=[permit["field"]],
                question_type="choice",
                question=permit["question"],
                options=list(permit.get("options") or []),
                resume_target="routing",
                reason="Ruhsat türü farklı birim/süreçlere güvenli biçimde ayrılmalıdır.",
            )
            return preview.model_dump()

        profiles = matching_profiles(
            institution_id=institution_id,
            document_type=document_type,
            process_intent=process_intent,
            candidate_department=candidate_department
            or routing.get("recommended_department_code"),
            raw_text=raw_text,
            document=document,
            extracted_fields=extracted_fields,
        )
        groups = unresolved_blocking_groups(profiles, extracted_fields)
        if groups:
            group = groups[0]
            field = group["fields"][0]
            preview = ClarificationPreview(
                needs_clarification=True,
                blocking=True,
                requested_fields=[field],
                question_type="free_text",
                question=group.get("question")
                or f"{field_label(field)} bilgisini paylaşınız.",
                options=[],
                resume_target="missing_field",
                reason=group.get("reason"),
            )
            return preview.model_dump()

        blocking = list(missing_fields.get("blocking_fields") or [])
        details = {
            item.get("field"): item
            for item in (missing_fields.get("missing_field_details") or [])
            if isinstance(item, dict)
        }
        citizen_blocking = [
            field
            for field in blocking
            if field != "permit_type" and (details.get(field) or {}).get("blocking", True)
        ]
        if citizen_blocking:
            field = citizen_blocking[0]
            label = (details.get(field) or {}).get("label") or field_label(field)
            reason = (details.get(field) or {}).get("reason") or "Süreç için gerekli bilgi eksik."
            preview = ClarificationPreview(
                needs_clarification=True,
                blocking=True,
                requested_fields=[field],
                question_type="free_text",
                question=f"{label} bilgisini paylaşınız.",
                options=[],
                resume_target="missing_field",
                reason=reason,
            )
            return preview.model_dump()

        return ClarificationPreview(
            needs_clarification=False,
            blocking=False,
            requested_fields=[],
            question_type="free_text",
            question="",
            options=[],
            resume_target="missing_field",
        ).model_dump()
