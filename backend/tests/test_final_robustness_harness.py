from __future__ import annotations

import json
from types import SimpleNamespace

from scripts.benchmark_providers import _json_object
from scripts.final_failure_harness import run as run_failure_harness
from scripts.robustness.common import ScenarioResult, p50, summarize, timed_http


def test_p50_handles_even_odd_and_empty_values():
    assert p50([]) is None
    assert p50([1, 3, 2]) == 2.0
    assert p50([1, 3]) == 2.0


def test_summary_counts_crashes_and_unexpected_500():
    results = [
        ScenarioResult("ok", "api", "PASS", 10, 200),
        ScenarioResult("bad", "api", "FAIL", 20, 500),
        ScenarioResult("crash", "api", "CRASH", 30),
    ]
    result = summarize(results)
    assert result["total"] == 3
    assert result["crashes"] == 1
    assert result["unexpected_500"] == 1
    assert result["p50_ms"] == 20.0


def test_provider_json_parser_accepts_plain_and_fenced_json():
    assert _json_object('{"ok": true}') == {"ok": True}
    assert _json_object('```json\n{"ok": true}\n```') == {"ok": True}
    assert _json_object("not-json") is None


def test_timed_http_marks_500_as_failure(monkeypatch):
    response = SimpleNamespace(status_code=500, text="safe error")
    session = SimpleNamespace(request=lambda *args, **kwargs: response)
    result, returned = timed_http(
        session,
        "GET",
        "http://example.invalid",
        timeout=1,
    )
    assert returned is response
    assert result.status == "FAIL"
    assert result.http_status == 500


def test_failure_harness_returns_safe_unhealthy_contracts():
    report = run_failure_harness()
    assert report["gate"] == "PASS"
    assert report["stacktrace_success_response"] is False
    assert [item["status"] for item in report["results"]] == ["PASS", "PASS"]
