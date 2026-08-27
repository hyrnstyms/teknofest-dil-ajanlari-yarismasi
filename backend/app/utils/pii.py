"""PII masking helpers for outbound API representations.

The helpers in this module deliberately return new values.  Callers can mask
an API response without altering the analysis state that is persisted in the
database.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


EMAIL_PATTERN = re.compile(
    r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])",
    flags=re.IGNORECASE,
)
# Eleven digit Turkish national IDs are intentionally matched before phone
# numbers, so a formatted ID is never partly treated as a phone number.
NATIONAL_ID_PATTERN = re.compile(r"(?<!\d)(?:\d[\s-]?){10}\d(?!\d)")
# Turkish mobile and landline numbers, with common local and +90 formats.
PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:(?:\+90|0090)[\s.-]?)?(?:0[\s.-]?)?"
    r"(?:\(?[2-5]\d{2}\)?[\s.-]?)\d{3}[\s.-]?\d{2}[\s.-]?\d{2}(?!\d)"
)


def mask_pii(value: Any) -> Any:
    """Return ``value`` with Turkish TC IDs, phones, and e-mails redacted.

    Dictionaries, lists, and tuples are traversed so the same rule applies to
    extraction ``value`` fields as well as their evidence snippets.
    """

    if isinstance(value, str):
        masked = EMAIL_PATTERN.sub("[E_POSTA]", value)
        masked = NATIONAL_ID_PATTERN.sub("[TC_KIMLIK_NO]", masked)
        return PHONE_PATTERN.sub("[TELEFON]", masked)
    if isinstance(value, dict):
        return {key: mask_pii(item) for key, item in value.items()}
    if isinstance(value, list):
        return [mask_pii(item) for item in value]
    if isinstance(value, tuple):
        return tuple(mask_pii(item) for item in value)
    return value


def mask_extraction(extraction: dict[str, Any] | None) -> dict[str, Any]:
    """Return a masked deep copy of an extraction payload."""

    return mask_pii(deepcopy(extraction or {}))
