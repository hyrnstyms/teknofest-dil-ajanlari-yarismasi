from __future__ import annotations

import json
import statistics
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

import requests


@dataclass
class ScenarioResult:
    name: str
    category: str
    status: str
    latency_ms: int
    http_status: int | None = None
    detail: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def p50(values: list[int | float]) -> float | None:
    if not values:
        return None
    return round(float(statistics.median(values)), 2)


def short_text(value: Any, limit: int = 240) -> str:
    normalized = " ".join(str(value or "").split())
    return normalized[:limit]


def timed_http(
    session: requests.Session,
    method: str,
    url: str,
    *,
    timeout: float,
    expected: Callable[[requests.Response], bool] | None = None,
    **kwargs: Any,
) -> tuple[ScenarioResult, requests.Response | None]:
    started = time.perf_counter()
    try:
        response = session.request(method, url, timeout=timeout, **kwargs)
        latency_ms = round((time.perf_counter() - started) * 1000)
        passed = expected(response) if expected else response.status_code < 500
        result = ScenarioResult(
            name=f"{method.upper()} {url}",
            category="http",
            status="PASS" if passed else "FAIL",
            latency_ms=latency_ms,
            http_status=response.status_code,
            detail="" if passed else short_text(response.text),
        )
        return result, response
    except requests.RequestException as exc:
        latency_ms = round((time.perf_counter() - started) * 1000)
        return (
            ScenarioResult(
                name=f"{method.upper()} {url}",
                category="http",
                status="BLOCKED",
                latency_ms=latency_ms,
                detail=f"{type(exc).__name__}: {short_text(exc)}",
            ),
            None,
        )


def summarize(results: list[ScenarioResult]) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    for result in results:
        statuses[result.status] = statuses.get(result.status, 0) + 1
    return {
        "total": len(results),
        "statuses": statuses,
        "crashes": sum(r.status == "CRASH" for r in results),
        "unexpected_500": sum(
            r.http_status is not None and r.http_status >= 500
            for r in results
        ),
        "p50_ms": p50([r.latency_ms for r in results]),
    }


def emit_report(
    report: dict[str, Any],
    output: str | None = None,
) -> None:
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered + "\n", encoding="utf-8")
