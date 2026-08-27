"""Deterministic legal deadlines derived from verified evidence only."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
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
    r"(?<!\d)(\d{1,5})(?!\d)\s*(?:takvim\s*)?(iş\s*)?g[uü]n",
    re.IGNORECASE,
)
_WORD_DURATION = re.compile(
    r"\b(on\s*be[sş]|onbe[sş]|otuz|yirmi|kırk|kirk|altmış|altmis|doksan|on)\s+"
    r"(?:takvim\s*)?(iş\s*)?g[uü]n",
    re.IGNORECASE,
)
_ALLOWED_TYPES = {"CALENDAR_DAY", "BUSINESS_DAY"}
_MAX_DEADLINE_DAYS = 36_500


def _parse_timestamp(value: str | datetime | None) -> datetime | None:
    """Accept only explicit, timezone-aware receipt timestamps."""

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        if text.endswith(("Z", "z")):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _source_map(analysis: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(analysis.get("sources") or [], start=1):
        if not isinstance(source, dict):
            continue
        result[f"K{index}"] = source
        for key in ("id", "source_id", "key"):
            if source.get(key) is not None:
                result[str(source[key])] = source
    return result


def _verified_evidence(
    analysis: dict[str, Any],
) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
    """Return evidence with explicit verification or LegalAgent source linkage.

    ``LegalAgent`` puts only Python-validated excerpts in ``evidence`` and keeps
    unvalidated retrieval results in ``retrieved_sources``. Therefore a normal
    evidence item is trusted only when its source reference resolves to the
    selected ``sources`` collection. Callers may alternatively pass an explicit
    ``verified_legal_evidence`` item with ``verified=true``.
    """

    sources = _source_map(analysis)
    verified: list[tuple[dict[str, Any], dict[str, Any] | None]] = []

    for item in analysis.get("evidence") or []:
        if not isinstance(item, dict) or item.get("verified") is False:
            continue
        source_ref = item.get("source") or item.get("source_id")
        source = sources.get(str(source_ref)) if source_ref is not None else None
        if source is None or source.get("verified") is False:
            continue
        verified.append((item, source))

    explicit = analysis.get("verified_legal_evidence") or []
    if isinstance(explicit, dict):
        explicit = [explicit]
    for item in explicit:
        if not isinstance(item, dict) or item.get("verified") is not True:
            continue
        inline_source = item.get("legal_basis") or item.get("source")
        source = inline_source if isinstance(inline_source, dict) else None
        if source is None and inline_source is not None:
            source = sources.get(str(inline_source))
        if source is not None and source.get("verified") is False:
            continue
        verified.append((item, source))

    # A fully structured integration DTO is also supported, but it must carry
    # its own explicit verification marker.
    if analysis.get("verified") is True and analysis.get("deadline_days") is not None:
        basis = analysis.get("legal_basis")
        if not isinstance(basis, dict) or basis.get("verified") is not False:
            verified.append((analysis, basis if isinstance(basis, dict) else None))
    return verified


def _structured_duration(item: dict[str, Any]) -> tuple[int, str] | None:
    days = item.get("deadline_days")
    deadline_type = item.get("deadline_type")
    if (
        isinstance(days, bool)
        or not isinstance(days, int)
        or not 0 < days <= _MAX_DEADLINE_DAYS
    ):
        return None
    if deadline_type not in _ALLOWED_TYPES:
        return None
    return days, deadline_type


def _extract_duration(text: str) -> tuple[int, str] | None:
    numeric = _NUMERIC_DURATION.search(text)
    if numeric:
        days = int(numeric.group(1))
        if not 0 < days <= _MAX_DEADLINE_DAYS:
            return None
        return days, "BUSINESS_DAY" if numeric.group(2) else "CALENDAR_DAY"
    word = _WORD_DURATION.search(text)
    if not word:
        return None
    days = _DAY_WORDS.get(word.group(1).casefold())
    if not days:
        return None
    return days, "BUSINESS_DAY" if word.group(2) else "CALENDAR_DAY"


def _evidence_text(item: dict[str, Any]) -> str:
    return str(item.get("evidence") or item.get("text") or "").strip()


def _legal_basis(
    item: dict[str, Any], source: dict[str, Any] | None, evidence_text: str
) -> LegalBasis:
    inline = item.get("legal_basis") if isinstance(item.get("legal_basis"), dict) else {}
    source = source or inline
    law_number = str(source.get("law_number") or source.get("kanun_no") or "") or None
    article = str(source.get("article") or source.get("madde_no") or "") or None
    citation = str(source.get("citation") or "").strip() or None
    if not citation:
        parts = []
        if law_number:
            parts.append(f"{law_number} sayılı Kanun")
        if article:
            parts.append(f"Madde {article}")
        citation = ", ".join(parts) or str(source.get("title") or "").strip() or None
    if not citation and evidence_text:
        citation = evidence_text[:180]
    return LegalBasis(
        verified=True,
        law_number=law_number,
        article=article,
        citation=citation,
    )


def _risk(remaining_days: int) -> str:
    if remaining_days < 0:
        return "OVERDUE"
    if remaining_days <= 3:
        return "CRITICAL"
    if remaining_days <= 7:
        return "APPROACHING"
    return "NORMAL"


def _unknown(received_at: str | datetime | None) -> dict[str, Any]:
    return DeadlineEvaluation(
        applicable=False,
        deadline_days=None,
        deadline_type=None,
        legal_basis=LegalBasis(verified=False),
        received_at=received_at.isoformat() if isinstance(received_at, datetime) else received_at,
        due_at=None,
        remaining_days=None,
        risk_level="UNKNOWN",
    ).model_dump()


class LegalDeadlineService:
    """Calculate deadlines without an LLM, persistence, or priority coupling."""

    def evaluate(
        self,
        *,
        received_at: str | datetime | None,
        legal_analysis: dict[str, Any] | None = None,
        verified_legal_evidence: dict[str, Any] | list[dict[str, Any]] | None = None,
        created_at: str | datetime | None = None,
        as_of: str | datetime | None = None,
    ) -> dict[str, Any]:
        del created_at  # created_at is never receipt evidence.
        analysis = dict(legal_analysis) if isinstance(legal_analysis, dict) else {}
        if verified_legal_evidence is not None:
            analysis["verified_legal_evidence"] = verified_legal_evidence

        evidence_items = _verified_evidence(analysis)
        duration: tuple[int, str] | None = None
        basis_source: dict[str, Any] | None = None
        basis_item: dict[str, Any] | None = None
        evidence_text = ""
        # Structured evidence is authoritative over free-text parsing even when
        # it appears later in the evidence collection.
        for item, source in evidence_items:
            evidence_text = _evidence_text(item)
            duration = _structured_duration(item)
            if duration is not None:
                basis_item, basis_source = item, source
                break
        if duration is None:
            for item, source in evidence_items:
                evidence_text = _evidence_text(item)
                duration = _extract_duration(evidence_text)
                if duration is not None:
                    basis_item, basis_source = item, source
                    break

        if duration is None or basis_item is None:
            return _unknown(received_at)

        days, deadline_type = duration
        basis = _legal_basis(basis_item, basis_source, evidence_text)
        received = _parse_timestamp(received_at)
        received_text = received.isoformat() if received is not None else (
            received_at.isoformat() if isinstance(received_at, datetime) else received_at
        )

        # The project has no authoritative holiday/business-day policy. Preserve
        # the verified duration but refuse to invent a due date.
        if received is None or deadline_type == "BUSINESS_DAY":
            return DeadlineEvaluation(
                applicable=True,
                deadline_days=days,
                deadline_type=deadline_type,
                legal_basis=basis,
                received_at=received_text,
                due_at=None,
                remaining_days=None,
                risk_level="UNKNOWN",
            ).model_dump()

        try:
            due = received + timedelta(days=days)
        except OverflowError:
            return DeadlineEvaluation(
                applicable=True,
                deadline_days=days,
                deadline_type=deadline_type,
                legal_basis=basis,
                received_at=received_text,
                due_at=None,
                remaining_days=None,
                risk_level="UNKNOWN",
            ).model_dump()
        current = datetime.now(received.tzinfo) if as_of is None else _parse_timestamp(as_of)
        remaining = None if current is None else (due.date() - current.date()).days
        return DeadlineEvaluation(
            applicable=True,
            deadline_days=days,
            deadline_type=deadline_type,
            legal_basis=basis,
            received_at=received_text,
            due_at=due.isoformat(),
            remaining_days=remaining,
            risk_level="UNKNOWN" if remaining is None else _risk(remaining),
        ).model_dump()
