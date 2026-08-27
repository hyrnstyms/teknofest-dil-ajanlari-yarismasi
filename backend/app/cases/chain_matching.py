"""Deterministic matching of related incoming Cases."""
from __future__ import annotations

import re
import unicodedata
import uuid
from datetime import timedelta
from typing import Any

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.case_models import CaseRecord
from backend.app.db.models import Analysis

ZINCIR_ESLESME_ESIGI = 80
ZINCIR_TARIH_PENCERESI_GUN = 60


def _normalize(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def _value(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("value")
    value = str(value or "").strip()
    return value or None


def analysis_subject(state: dict[str, Any] | None) -> str | None:
    state = state or {}
    fields = ((state.get("extraction") or {}).get("fields") or {})
    structured = ((state.get("summary") or {}).get("structured_summary") or {})
    document = state.get("document") or {}
    candidates = (fields.get("subject"), structured.get("subject"), document.get("subject_excerpt"))
    return next((subject for item in candidates if (subject := _value(item))), None)


def assign_matching_chain(session: Session, new_case: CaseRecord) -> str | None:
    analysis = session.get(Analysis, new_case.analysis_id) if new_case.analysis_id else None
    subject = _normalize(analysis_subject(analysis.state_json if analysis else None))
    originator = _normalize(new_case.originator_name)
    if not subject or not originator:
        return None
    received_at = new_case.received_at
    window_start = received_at - timedelta(days=ZINCIR_TARIH_PENCERESI_GUN)
    rows = session.execute(
        select(CaseRecord, Analysis).join(Analysis).where(
            CaseRecord.id != new_case.id,
            CaseRecord.institution_id == new_case.institution_id,
            CaseRecord.received_at >= window_start,
            CaseRecord.received_at <= received_at,
        )
    ).all()
    matches = []
    for previous, previous_analysis in rows:
        if _normalize(previous.originator_name) != originator:
            continue
        previous_subject = _normalize(analysis_subject(previous_analysis.state_json))
        score = fuzz.token_set_ratio(subject, previous_subject) if previous_subject else 0
        if score >= ZINCIR_ESLESME_ESIGI:
            matches.append((score, previous.received_at, previous))
    if not matches:
        return None
    previous = max(matches, key=lambda item: (item[0], item[1]))[2]
    new_case.zincir_id = previous.zincir_id or str(uuid.uuid4())
    previous.zincir_id = new_case.zincir_id
    return new_case.zincir_id
