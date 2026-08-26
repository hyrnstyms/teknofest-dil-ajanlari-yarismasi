from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.robustness.common import emit_report


def _http_probe(
    name: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 5.0,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        return {
            "name": name,
            "status": "PASS" if response.status_code < 400 else "FAIL",
            "http_status": response.status_code,
            "latency_ms": round((time.perf_counter() - started) * 1000),
        }
    except requests.RequestException as exc:
        return {
            "name": name,
            "status": "BLOCKED",
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "detail": type(exc).__name__,
        }


def build_report(
    backend_url: str,
    frontend_url: str,
) -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
    checks: list[dict[str, Any]] = []

    postgres_configured = any(
        os.getenv(key)
        for key in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_HOST")
    )
    checks.append({
        "name": "postgres",
        "status": "BLOCKED" if postgres_configured else "SKIP",
        "detail": (
            "Configured but this isolated harness does not mutate DB."
            if postgres_configured
            else "Postgres is not active in this project configuration."
        ),
    })

    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    ollama = _http_probe("ollama", f"{ollama_url}/api/tags")
    if ollama["status"] == "PASS":
        try:
            tags = requests.get(f"{ollama_url}/api/tags", timeout=5).json()
            model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct")
            names = {item.get("name") for item in tags.get("models", [])}
            ollama["model"] = model
            ollama["model_status"] = "PASS" if model in names else "BLOCKED"
        except (ValueError, TypeError):
            ollama["model_status"] = "FAIL"
    checks.append(ollama)

    evren_configured = bool(
        os.getenv("EVREN_BASE_URL") and os.getenv("EVREN_API_KEY")
    )
    if evren_configured:
        checks.append(_http_probe(
            "evren",
            f"{os.environ['EVREN_BASE_URL'].rstrip('/')}/models",
            headers={"Authorization": f"Bearer {os.environ['EVREN_API_KEY']}"},
        ))
    else:
        checks.append({
            "name": "evren",
            "status": "BLOCKED",
            "detail": "EVREN BLOCKED BY CONFIG",
        })

    qdrant_started = time.perf_counter()
    try:
        from backend.app.rag.qdrant_store import QdrantStore

        collections = QdrantStore().client.get_collections().collections
        checks.append({
            "name": "qdrant",
            "status": "PASS",
            "latency_ms": round((time.perf_counter() - qdrant_started) * 1000),
            "collection_count": len(collections),
            "access": "read-only",
        })
    except Exception as exc:
        checks.append({
            "name": "qdrant",
            "status": "BLOCKED",
            "latency_ms": round((time.perf_counter() - qdrant_started) * 1000),
            "detail": type(exc).__name__,
        })

    checks.append(_http_probe("backend_health", f"{backend_url.rstrip('/')}/health"))
    checks.append(_http_probe("backend_ready", f"{backend_url.rstrip('/')}/ready", timeout=15))
    frontend_base = frontend_url.rstrip("/")
    checks.append(_http_probe("frontend", frontend_base))
    checks.append(_http_probe(
        "frontend_module",
        f"{frontend_base}/src/App.tsx",
    ))

    selected = next((item for item in checks if item["name"] == provider), None)
    required_names = {
        "qdrant",
        "backend_health",
        "backend_ready",
        "frontend",
        "frontend_module",
    }
    required = [item for item in checks if item["name"] in required_names]
    if selected:
        required.append(selected)
    ready = all(item["status"] == "PASS" for item in required)
    return {
        "gate": "READY" if ready else "BLOCKED",
        "selected_provider": provider,
        "env_file_modified": False,
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    parser.add_argument("--frontend-url", default="http://127.0.0.1:5173")
    parser.add_argument("--output")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    report = build_report(args.backend_url, args.frontend_url)
    emit_report(report, args.output)
    if args.strict and report["gate"] != "READY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
