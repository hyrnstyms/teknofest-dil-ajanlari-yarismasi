"""Short-lived HMAC demo tokens. Production OAuth/SSO is out of scope."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from backend.app.cases.errors import invalid_token

TOKEN_TTL_SECONDS = 8 * 60 * 60


def _secret() -> bytes:
    return os.getenv("CASE_DEMO_TOKEN_SECRET", "evrag-demo-secret-not-for-production").encode(
        "utf-8"
    )


def issue_token(user_id: str, user_key: str) -> str:
    payload = {
        "sub": user_id,
        "user_key": user_key,
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    body = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    signature = hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"v1.{body}.{signature}"


def parse_token(token: str) -> dict[str, Any]:
    try:
        version, body, signature = token.split(".", 2)
    except ValueError as exc:
        raise invalid_token() from exc
    if version != "v1":
        raise invalid_token()
    expected = hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise invalid_token()
    try:
        payload = json.loads(base64.urlsafe_b64decode(body.encode("ascii")))
    except (ValueError, json.JSONDecodeError) as exc:
        raise invalid_token() from exc
    if int(payload.get("exp") or 0) < int(time.time()):
        raise invalid_token()
    if not payload.get("sub") or not payload.get("user_key"):
        raise invalid_token()
    return payload
