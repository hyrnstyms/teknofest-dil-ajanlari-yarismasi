"""Live department directory from institution YAML profiles."""

from __future__ import annotations

from typing import Any

from backend.app.cases.errors import invalid_department, validation_error
from backend.app.institutions.profile_loader import load_institution_profile


def list_departments(institution_id: str) -> list[dict[str, Any]]:
    try:
        profile = load_institution_profile(institution_id)
    except FileNotFoundError as exc:
        raise validation_error(
            "Kurum profili bulunamadı.",
            institution_id=institution_id,
        ) from exc
    departments: list[dict[str, Any]] = []
    for unit in profile.birimler:
        if not isinstance(unit, dict):
            continue
        code = str(unit.get("id") or unit.get("code") or "").strip()
        if not code:
            continue
        departments.append(
            {
                "code": code,
                "name": str(unit.get("ad") or unit.get("name") or code),
                "description": unit.get("aciklama") or unit.get("description"),
                "scope": unit.get("supported_intents") or unit.get("kapsam"),
            }
        )
    return departments


def department_codes(institution_id: str) -> set[str]:
    return {item["code"] for item in list_departments(institution_id)}


def assert_department(institution_id: str, department_code: str) -> dict[str, Any]:
    for item in list_departments(institution_id):
        if item["code"] == department_code:
            return item
    raise invalid_department(department_code)
