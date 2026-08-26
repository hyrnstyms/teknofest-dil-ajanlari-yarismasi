from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.robustness.common import ScenarioResult, emit_report, p50, short_text, summarize, timed_http


class AcceptanceRunner:
    def __init__(self, api_base: str, timeout: float):
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.results: list[ScenarioResult] = []
        self.analyses: list[dict[str, Any]] = []
        self.node_timings: dict[str, list[int]] = {}

    def _call(
        self,
        name: str,
        category: str,
        method: str,
        path: str,
        *,
        expected=None,
        **kwargs: Any,
    ) -> requests.Response | None:
        result, response = timed_http(
            self.session,
            method,
            f"{self.api_base}{path}",
            timeout=self.timeout,
            expected=expected,
            **kwargs,
        )
        result.name = name
        result.category = category
        self.results.append(result)
        return response

    def _load_text_cases(self) -> list[tuple[str, str]]:
        kaymakamlik_path = (
            PROJECT_ROOT / "data" / "institutions" / "kaymakamlik"
            / "ornek_evraklar" / "curated_scenarios.jsonl"
        )
        kaymakamlik = []
        with kaymakamlik_path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    kaymakamlik.append(json.loads(line)["text"])
                if len(kaymakamlik) == 3:
                    break
        belediye_dir = (
            PROJECT_ROOT / "data" / "institutions" / "belediye" / "ornek_evraklar"
        )
        belediye = [
            (belediye_dir / "01_ruhsat_basvurusu.txt").read_text(encoding="utf-8"),
            (belediye_dir / "13_ambiguous_ruhsat.txt").read_text(encoding="utf-8"),
        ]
        return [
            ("kaymakamlik", text) for text in kaymakamlik
        ] + [("belediye", text) for text in belediye]

    def readiness(self) -> None:
        self._call("ready", "ready", "GET", "/ready", expected=lambda r: r.status_code == 200)

    def text_analyses(self) -> None:
        for index, (institution, text) in enumerate(self._load_text_cases(), start=1):
            response = self._call(
                f"text_analysis_{index}_{institution}",
                "text",
                "POST",
                "/api/documents/analyze-text",
                json={"text": text, "institution": institution},
                expected=lambda r: r.status_code == 200 and "analysis_id" in r.json(),
            )
            if response is None or response.status_code != 200:
                continue
            data = response.json()
            self.analyses.append(data)
            for node, timing in data.get("node_timings", {}).items():
                self.node_timings.setdefault(node, []).append(timing.get("duration_ms", 0))

    def ocr_uploads(self) -> None:
        samples = [
            PROJECT_ROOT / "data" / "evaluation" / "ocr" / "temiz" / "SENT-0003_temiz.png",
            PROJECT_ROOT / "data" / "evaluation" / "ocr" / "zor" / "SENT-0001_zor.png",
        ]
        for index, path in enumerate(samples, start=1):
            with path.open("rb") as handle:
                response = self._call(
                    f"ocr_upload_{index}",
                    "ocr",
                    "POST",
                    "/api/documents/upload",
                    files={"file": (path.name, handle, "image/png")},
                    data={"institution": "kaymakamlik"},
                    expected=lambda r: r.status_code == 200 and "analysis_id" in r.json(),
                )
            if response is not None and response.status_code == 200:
                self.analyses.append(response.json())

    def bad_inputs(self) -> None:
        cases = [
            ("empty", ""),
            ("very_short", "x"),
            ("gibberish", "zxqv 19@@ asdf !!! qqq"),
            ("very_long", "Başvuru metni. " * 5000),
        ]
        for name, text in cases:
            self._call(
                f"bad_input_{name}",
                "bad_input",
                "POST",
                "/api/documents/analyze-text",
                json={"text": text, "institution": "kaymakamlik"},
                expected=lambda r: r.status_code < 500,
            )
        self._call(
            "unsupported_file",
            "bad_input",
            "POST",
            "/api/documents/upload",
            files={"file": ("unsupported.exe", b"not a document", "application/octet-stream")},
            data={"institution": "kaymakamlik"},
            expected=lambda r: 400 <= r.status_code < 500,
        )

    def chats(self) -> None:
        active_id = self.analyses[0].get("analysis_id") if self.analyses else None
        chat_cases = [
            ("active_summary", "Bu evrakı kısaca özetle", active_id, "kaymakamlik"),
            ("missing", "Bu evrakta hangi bilgiler eksik?", active_id, "kaymakamlik"),
            ("routing", "Bu evrak hangi birime yönlendirildi?", active_id, "kaymakamlik"),
            ("legal_3071_madde_7", "3071 sayılı Kanun Madde 7 ne düzenler?", None, "kaymakamlik"),
            ("unsupported", "Yarın hava nasıl olacak?", None, "kaymakamlik"),
            ("institution_kaymakamlik", "Seçili kurumun birimleri nelerdir?", None, "kaymakamlik"),
            ("institution_belediye", "Seçili kurumun birimleri nelerdir?", None, "belediye"),
            ("active_status", "Bu evrakın inceleme durumu nedir?", active_id, "kaymakamlik"),
            ("faq", "Dilekçe nasıl hazırlanır?", None, "kaymakamlik"),
            ("unrelated", "Bana bir oyun öner", None, "belediye"),
        ]
        for name, message, analysis_id, institution in chat_cases:
            payload: dict[str, Any] = {"message": message, "institution": institution}
            if analysis_id:
                payload["analysis_id"] = analysis_id
            self._call(
                f"chat_{name}",
                "chat",
                "POST",
                "/api/chat/message",
                json=payload,
                expected=lambda r: r.status_code < 500 and isinstance(r.json(), dict),
            )

    def review_docx_lists(self) -> None:
        ids = [item.get("analysis_id") for item in self.analyses if item.get("analysis_id")]
        if ids:
            approved = ids[0]
            self._call("approve", "review", "POST", f"/api/analysis/{approved}/approve")
            self._call(
                "docx",
                "docx",
                "GET",
                f"/api/analysis/{approved}/export/docx",
                expected=lambda r: r.status_code == 200 and "wordprocessingml" in r.headers.get("content-type", ""),
            )
        if len(ids) > 1:
            self._call(
                "reject",
                "review",
                "POST",
                f"/api/analysis/{ids[1]}/reject",
                json={"reason": "Final acceptance kontrollü ret testi"},
            )
        self._call("analyses_list", "list", "GET", "/api/analyses")
        self._call("pending_list", "list", "GET", "/api/reviews/pending")

    def report(self) -> dict[str, Any]:
        category_p50 = {}
        for category in sorted({item.category for item in self.results}):
            category_p50[category] = p50([
                item.latency_ms for item in self.results if item.category == category
            ])
        node_p50 = {
            node: p50(values) for node, values in self.node_timings.items()
        }
        slowest = sorted(node_p50.items(), key=lambda item: item[1] or 0, reverse=True)
        summary = summarize(self.results)
        gate_passed = (
            summary["crashes"] == 0
            and summary["unexpected_500"] == 0
            and summary["statuses"].get("FAIL", 0) == 0
        )
        return {
            "gate": "PASS" if gate_passed else "FAIL",
            "summary": summary,
            "category_p50_ms": category_p50,
            "node_p50_ms": node_p50,
            "slowest_nodes": slowest[:5],
            "remote_qdrant_writes": 0,
            "results": [item.as_dict() for item in self.results],
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=240.0)
    parser.add_argument("--skip-ocr", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()

    runner = AcceptanceRunner(args.api_base, args.timeout)
    runner.readiness()
    runner.text_analyses()
    if not args.skip_ocr:
        runner.ocr_uploads()
    runner.bad_inputs()
    runner.chats()
    runner.review_docx_lists()
    report = runner.report()
    emit_report(report, args.output)
    raise SystemExit(0 if report["gate"] == "PASS" else 1)


if __name__ == "__main__":
    main()
