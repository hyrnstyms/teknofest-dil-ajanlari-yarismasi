from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app


class _HealthyResponse:
    status_code = 200


class _HealthyEmbedding:
    model = object()


class _HealthyQdrant:
    class Client:
        @staticmethod
        def get_collections():
            return []

    client = Client()


def _safe_body(response) -> bool:
    body = json.dumps(response.json(), ensure_ascii=False).lower()
    return "traceback" not in body and "traceback (most recent call last)" not in body


def run() -> dict:
    client = TestClient(app)
    results = []

    with (
        patch.dict(os.environ, {"LLM_PROVIDER": "evren"}),
        patch("requests.get", return_value=_HealthyResponse()),
        patch(
            "backend.app.main._get_embedding_service_singleton",
            return_value=_HealthyEmbedding(),
        ),
        patch(
            "backend.app.main._get_qdrant_store_singleton",
            side_effect=ConnectionError("qdrant unavailable"),
        ),
        patch("backend.app.main.logger"),
    ):
        response = client.get("/ready")
        body = response.json()
        passed = (
            response.status_code == 200
            and body["ready"] is False
            and body["services"]["qdrant"]["status"] == "unavailable"
            and _safe_body(response)
        )
        results.append({"name": "qdrant_unavailable", "status": "PASS" if passed else "FAIL"})

    with (
        patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}),
        patch("requests.get", side_effect=ConnectionError("ollama unavailable")),
        patch(
            "backend.app.main._get_embedding_service_singleton",
            return_value=_HealthyEmbedding(),
        ),
        patch(
            "backend.app.main._get_qdrant_store_singleton",
            return_value=_HealthyQdrant(),
        ),
        patch("backend.app.main.logger"),
    ):
        response = client.get("/ready")
        body = response.json()
        passed = (
            response.status_code == 200
            and body["ready"] is False
            and body["services"]["llm"]["status"] == "unreachable"
            and _safe_body(response)
        )
        results.append({"name": "ollama_unavailable", "status": "PASS" if passed else "FAIL"})

    return {
        "gate": "PASS" if all(item["status"] == "PASS" for item in results) else "FAIL",
        "results": results,
        "stacktrace_success_response": False,
    }


if __name__ == "__main__":
    report = run()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["gate"] == "PASS" else 1)
