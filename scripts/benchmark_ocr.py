from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.ocr.ocr_service import OCRService
from scripts.robustness.common import emit_report, p50, short_text


def _samples() -> list[tuple[str, Path]]:
    base = PROJECT_ROOT / "data" / "evaluation" / "ocr"
    clean = [("clean", path) for path in sorted((base / "temiz").glob("*.png"))[:3]]
    difficult = [("difficult", path) for path in sorted((base / "zor").glob("*.png"))[:2]]
    return clean + difficult


def run() -> dict:
    service = OCRService()
    results = []
    for quality, path in _samples():
        started = time.perf_counter()
        try:
            text = service.extract_text_from_image(str(path))
            latency_ms = round((time.perf_counter() - started) * 1000)
            usable = len(text.strip()) >= 50
            results.append({
                "name": path.name,
                "quality": quality,
                "status": "PASS" if usable else "FAIL",
                "runtime_success": True,
                "usable_text": usable,
                "latency_ms": latency_ms,
                "characters": len(text),
                "preview": short_text(text, 160),
            })
        except Exception as exc:
            results.append({
                "name": path.name,
                "quality": quality,
                "status": "FAIL",
                "runtime_success": False,
                "usable_text": False,
                "latency_ms": round((time.perf_counter() - started) * 1000),
                "error": f"{type(exc).__name__}: {short_text(exc)}",
            })
    return {
        "sample_policy": "3 clean + 2 difficult single-page images",
        "full_17_page_pdf_run": False,
        "existing_ocr_options_only": True,
        "p50_ms": p50([item["latency_ms"] for item in results]),
        "passed": sum(item["status"] == "PASS" for item in results),
        "total": len(results),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    report = run()
    emit_report(report, args.output)
    if report["passed"] != report["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
