import re
import unicodedata
from datetime import date, datetime
from typing import Any, Literal


PriorityLevel = Literal["HIGH", "MEDIUM", "LOW"]

URGENCY_RE = re.compile(r"\b(acil|ivedi|ivedilikle|derhal|gecikmeksizin)\b")
DATE_VALUE = r"(?:\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{4}-\d{2}-\d{2})"
DEADLINE_AFTER_MARKER_RE = re.compile(
    rf"(?:son\s+(?:başvuru\s+)?tarih(?:i)?|son\s+gün|süre\s+bitimi)\s*[:\-]?\s*({DATE_VALUE})"
)
DEADLINE_BEFORE_MARKER_RE = re.compile(
    rf"({DATE_VALUE})\s+tarihine\s+kadar"
)
DEADLINE_MARKER_RE = re.compile(
    r"son\s+(?:başvuru\s+)?tarih|son\s+gün|süre\s+bitimi|tarihine\s+kadar"
)


class PriorityAgent:
    """Deterministic priority assessment; it never calls an LLM."""

    def __init__(self, near_deadline_days: int = 3):
        self.near_deadline_days = near_deadline_days

    def assess(
        self,
        text: Any,
        deadline: Any = None,
        reference_date: date | None = None,
    ) -> dict[str, Any]:
        normalized_text = self._normalize_text(text)
        as_of = reference_date or date.today()

        if URGENCY_RE.search(normalized_text):
            return self._result(
                "HIGH", "explicit_urgency",
                "Evrak açık bir acil/ivedi işlem ifadesi içeriyor.",
            )

        deadline_value = deadline if deadline not in (None, "") else self._extract_deadline(normalized_text)
        parsed_deadline = self._parse_date(deadline_value)
        if parsed_deadline:
            days_remaining = (parsed_deadline - as_of).days
            if days_remaining < 0:
                return self._result(
                    "HIGH", "deadline_overdue", "İşlem son tarihi geçmiş.",
                    parsed_deadline, days_remaining,
                )
            if days_remaining <= self.near_deadline_days:
                return self._result(
                    "HIGH", "deadline_near", "İşlem son tarihi çok yakın.",
                    parsed_deadline, days_remaining,
                )
            return self._result(
                "MEDIUM", "deadline_future",
                "Belirli bir işlem son tarihi bulunuyor.",
                parsed_deadline, days_remaining,
            )

        has_deadline_signal = deadline not in (None, "") or bool(
            DEADLINE_MARKER_RE.search(normalized_text)
        )
        if has_deadline_signal:
            return self._result(
                "LOW", "invalid_deadline",
                "Son tarih ifadesi güvenli biçimde çözümlenemedi.",
            )

        return self._result(
            "LOW", "no_urgency_or_deadline",
            "Açık bir aciliyet veya son tarih bulunmuyor.",
        )

    @staticmethod
    def _normalize_text(value: Any) -> str:
        text = unicodedata.normalize("NFKC", "" if value is None else str(value))
        text = text.casefold().replace("i̇", "i")
        return " ".join(text.split())

    @staticmethod
    def _extract_deadline(text: str) -> str | None:
        candidates = []
        for pattern in (DEADLINE_AFTER_MARKER_RE, DEADLINE_BEFORE_MARKER_RE):
            candidates.extend(match.group(1) for match in pattern.finditer(text))
        parsed = [(PriorityAgent._parse_date(value), value) for value in candidates]
        valid = [(parsed_date, value) for parsed_date, value in parsed if parsed_date]
        return min(valid, key=lambda item: item[0])[1] if valid else None

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        candidate = str(value or "").strip()
        for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _result(
        priority: PriorityLevel,
        rule: str,
        reason: str,
        deadline: date | None = None,
        days_remaining: int | None = None,
    ) -> dict[str, Any]:
        return {
            "priority": priority,
            "priority_rule": rule,
            "priority_reason": reason,
            "deadline": deadline.isoformat() if deadline else None,
            "days_remaining": days_remaining,
            "decision_source": "rule_based",
        }
