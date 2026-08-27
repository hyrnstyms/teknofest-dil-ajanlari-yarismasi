"""Deterministic municipal Level-2 and clarification-target recommendations.

This module only recommends an organizational role/team.  It deliberately
does not resolve or assign a named employee; that remains a manager action in
the Case workflow.
"""

from __future__ import annotations

from typing import Any

from backend.app.intelligence.process_profiles import matching_profiles
from backend.app.institutions.profile_loader import load_institution_profile


def _value(fields: dict[str, Any], key: str) -> str | None:
    item = fields.get(key)
    if isinstance(item, dict):
        item = item.get("value")
    value = str(item or "").strip()
    return value or None


class MunicipalOperationResolver:
    """Maps a confirmed Level-1 department recommendation to a team/role."""

    def __init__(self, institution_id: str = "belediye"):
        self.institution_id = institution_id
        try:
            self.profile = load_institution_profile(institution_id)
        except (FileNotFoundError, ValueError):
            self.profile = None

    def recommend(
        self,
        *,
        document: dict[str, Any],
        extracted_fields: dict[str, Any],
        raw_text: str,
        routing: dict[str, Any],
    ) -> dict[str, Any]:
        department_code = str(routing.get("recommended_department_code") or "").strip()
        profiles = matching_profiles(
            institution_id=self.institution_id,
            document_type=str(document.get("document_type") or ""),
            process_intent=str(document.get("process_intent") or ""),
            candidate_department=department_code or None,
            raw_text=raw_text,
            document=document,
            extracted_fields=extracted_fields,
        )
        profile = next((item for item in profiles if item.get("task_type")), None)
        if profile and not department_code:
            department_code = str((profile.get("department_codes") or [""])[0])

        team_code = str(profile.get("team_code") or "") if profile else ""
        role = str(profile.get("recommended_role") or "") if profile else ""
        team_name = None
        if self.profile and department_code:
            unit = next(
                (item for item in self.profile.birimler if item.get("id") == department_code),
                {},
            )
            teams = list(unit.get("teams") or []) if isinstance(unit, dict) else []
            team = next((item for item in teams if item.get("code") == team_code), None)
            if team is None and teams:
                team = teams[0]
                team_code = str(team.get("code") or "")
            if isinstance(team, dict):
                team_name = team.get("name")
                if not role:
                    roles = team.get("roles") or []
                    role = str(roles[0]) if roles else "BIRIM_PERSONELI"

        return {
            "profile_id": profile.get("id") if profile else None,
            "task_type": profile.get("task_type") if profile else "GENEL_INCELEME",
            "department_code": department_code or None,
            "team_code": team_code or None,
            "team_name": team_name,
            "recommended_role": role or "BIRIM_PERSONELI",
            "requires_field_visit": bool(profile and profile.get("requires_field_visit")),
            "reason": (
                f"{profile.get('id')} süreç profiliyle eşleşti."
                if profile else "Birim içinde insan onayı bekleyen genel inceleme önerisi."
            ),
            "assigned_user_id": None,
            # Stable names for the Case API; code-oriented values above are
            # retained for Task persistence and compatibility.
            "recommended_department": department_code or None,
            "alternatives": list(routing.get("alternatives") or []),
            "recommended_task_type": profile.get("task_type") if profile else "GENEL_INCELEME",
            "recommended_team": team_code or None,
            "field_visit_required": bool(profile and profile.get("requires_field_visit")),
            "next_action": "MANAGER_ASSIGNMENT_REQUIRED",
        }


class ClarificationTargetResolver:
    """Selects the proper information-request recipient from source metadata."""

    def resolve(
        self,
        *,
        originator: Any = None,
        document: dict[str, Any] | None = None,
        extracted_fields: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        document = document or {}
        fields = extracted_fields or {}
        if hasattr(originator, "model_dump"):
            originator = originator.model_dump()
        originator = originator or {}
        source_type = str(
            originator.get("originator_type")
            or document.get("originator_type")
            or document.get("source_type")
            or "VATANDAS"
        ).upper()
        name = str(originator.get("originator_name") or "").strip() or _value(fields, "sender_unit")

        if source_type == "KURUM_ICI":
            department = str(
                document.get("sender_department_code")
                or document.get("source_department_code")
                or originator.get("current_department_code")
                or "yazi_isleri"
            )
            return {
                "target_type": "INTERNAL_DEPARTMENT",
                "target_name": name or department,
                "target_department": department,
                "reason": reason or "Eksik bilgi gönderici birimden tamamlanmalıdır.",
                "recommended_action": "INTERNAL_INFORMATION_REQUESTED",
            }
        if source_type == "DIS_KURUM":
            return {
                "target_type": "DIS_KURUM",
                "target_name": name or "Gönderen kurum",
                "target_department": _value(fields, "sender_unit"),
                "reason": reason or "Eksik bilgi gönderen kurumdan istenmelidir.",
                "recommended_action": "EXTERNAL_INFORMATION_REQUESTED",
            }
        return {
            "target_type": "VATANDAS",
            "target_name": name or _value(fields, "person_name") or "Başvuru sahibi",
            "target_department": None,
            "reason": reason or "Eksik bilgi başvuru sahibinden istenmelidir.",
            "recommended_action": "CITIZEN_INFORMATION_REQUESTED",
        }
