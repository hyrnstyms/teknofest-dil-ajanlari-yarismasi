"""Legal deadline from verified evidence only. No model-invented durations."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.app.intelligence.contracts import DeadlineEvaluation, LegalBasis

_DAY_WORDS = {
    "on": 10,
    "on beş": 15,
    "onbes": 15,
    "onbeş": 15,
    "yirmi": 20,
    "otuz": 30,
    "kırk": 40,
    "kirk": 40,
    "altmış": 60,
    "altmis": 60,
    "doksan": 90,
}

_NUMERIC_DURATION = re.compile(
    r"(\d+)\s*(?:takvim\s*)?(iş\s*)?g[uü]n",
    re.IGNORECASE,
)
_WORD_DURATION = re.compile(
    r"\b(on\s*be[sş]|onbe[sş]|otuz|yirmi|kırk|kirk|altmış|altmis|doksan|on)\s+"
    r"(?:takvim\s*)?(iş\s*)?g[uü]n",
    re.IGNORECASE,
)


def _parse_received_at(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _parse_as_of(value: str | None, fallback: datetime) -> datetime:
    parsed = _parse_received_at(value)
    return parsed or fallback


def _iter_evidence_texts(legal_analysis: dict[str, Any]) -> list[tuple[str, dict[str, Any] | None]]:
    analysis = legal_analysis if isinstance(legal_analysis, dict) else {}
    sources = [s for s in (analysis.get("sources") or []) if isinstance(s, dict)]
    source_map = {
        f"K{index}": source for index, source in enumerate(sources, start=1)
    }
    items: list[tuple[str, dict[str, Any] | None]] = []
    for item in analysis.get("evidence") or []:
        if isinstance(item, str) and item.strip():
            items.append((item.strip(), sources[0] if sources else None))
            continue
        if not isinstance(item, dict):
            continue
        text = str(item.get("evidence") or item.get("text") or "").strip()
        if not text:
            continue
        source = source_map.get(str(item.get("source") or ""), None)
        if source is None and sources:
            source = sources[0]
        items.append((text, source))
    return items


def _extract_duration(text: str) -> tuple[int, str] | None:
    numeric = _NUMERIC_DURATION.search(text)
    if numeric:
        days = int(numeric.group(1))
        deadline_type = "BUSINESS_DAY" if numeric.group(2) else "CALENDAR_DAY"
        return days, deadline_type
    word = _WORD_DURATION.search(text)
    if word:
        token = re.sub(r"\s+", " ", word.group(1).casefold().replace("ı", "i"))
        token = token.replace("ş", "s")
        days = _DAY_WORDS.get(word.group(1).casefold()) or _DAY_WORDS.get(token)
        if days:
            deadline_type = "BUSINESS_DAY" if word.group(2) else "CALENDAR_DAY"
            return days, deadline_type
    return None


def _risk(remaining_days: int | None) -> str:
    if remaining_days is None:
        return "UNKNOWN"
    if remaining_days < 0:
        return "OVERDUE"
    if remaining_days <= 3:
        return "CRITICAL"
    if remaining_days <= 7:
        return "APPROACHING"
    return "NORMAL"


def _citation(source: dict[str, Any] | None) -> LegalBasis:
    if not source:
        return LegalBasis(verified=False)
    law_number = str(source.get("law_number") or source.get("kanun_no") or "") or None
    article = str(source.get("article") or source.get("madde_no") or "") or None
    parts = []
    if law_number:
        parts.append(f"{law_number} sayılı Kanun")
    if article:
        parts.append(f"Madde {article}")
    return LegalBasis(
        verified=True,
        law_number=law_number,
        article=article,
        citation=", ".join(parts) if parts else str(source.get("title") or "") or None,
    )


class LegalDeadlineService:
    """Deadline arithmetic is deterministic. LLM knowledge is never used."""

    def evaluate(
        self,
        *,
        legal_analysis: dict[str, Any] | None,
        received_at: str | None,
        created_at: str | None = None,
        as_of: str | None = None,
    ) -> dict[str, Any]:
        del created_at  # never a substitute for received_at
        empty = DeadlineEvaluation(
            applicable=False,
            deadline_days=None,
            deadline_type=None,
            legal_basis=LegalBasis(verified=False),
            received_at=received_at,
            due_at=None,
            remaining_days=None,
            risk_level="UNKNOWN",
        )
        evidence_items = _iter_evidence_texts(legal_analysis or {})
        duration = None
        basis_source = None
        evidence_text = None
        for text, source in evidence_items:
            found = _extract_duration(text)
            if found:
                duration = found
                basis_source = source
                evidence_text = text
                break

        if duration is None:
            return empty.model_dump()

        days, deadline_type = duration
        received = _parse_received_at(received_at)
        legal_basis = _citation(basis_source)
        legal_basis.verified = True
        if evidence_text and not legal_basis.citation:
            legal_basis.citation = evidence_text[:180]

        if received is None:
            return DeadlineEvaluation(
                applicable=True,
                deadline_days=days,
                deadline_type=deadline_type,  # type: ignore[arg-type]
                legal_basis=legal_basis,
                received_at=received_at,
                due_at=None,
                remaining_days=None,
                risk_level="UNKNOWN",
            ).model_dump()

        due = received + timedelta(days=days)
        now = _parse_as_of(as_of, received)
        remaining = (due.date() - now.date()).days
        return DeadlineEvaluation(
            applicable=True,
            deadline_days=days,
            deadline_type=deadline_type,  # type: ignore[arg-type]
            legal_basis=legal_basis,
            received_at=received_at,
            due_at=due.isoformat(),
            remaining_days=remaining,
            risk_level=_risk(remaining),  # type: ignore[arg-type]
        ).model_dump()
