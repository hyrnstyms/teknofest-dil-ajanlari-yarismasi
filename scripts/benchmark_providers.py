from __future__ import annotations

import argparse
import json
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

from scripts.robustness.common import emit_report, p50, short_text


CASES = [
    {
        "name": "document_type",
        "agent": "document_agent",
        "prompt": (
            "Belge: 'Kaymakamlığa sunulan imzalı başvuru dilekçesidir.' "
            "Belge türünü sınıflandır ve çıktıyı tam olarak bu JSON anahtarında "
            "döndür: {\"answer\":\"dilekce\"}."
        ),
        "required": ["answer"],
        "keywords": ["dilekce", "dilekçe"],
    },
    {
        "name": "missing_fields",
        "agent": "extraction_agent",
        "prompt": "Adı ve adresi olmayan başvuru için sadece JSON döndür: {\"missing\":[\"ad_soyad\",\"adres\"]}.",
        "required": ["missing"],
        "keywords": ["adres"],
    },
    {
        "name": "routing",
        "agent": "document_agent",
        "prompt": "Genel ve belirsiz başvuru hangi birime yönlenmeli? Sadece JSON: {\"unit\":\"Yazı İşleri\"}.",
        "required": ["unit"],
        "keywords": ["yazı", "yazi"],
    },
    {
        "name": "summary",
        "agent": "summary_agent",
        "prompt": "'Sokak lambaları iki aydır yanmıyor' metnini sadece JSON özetle: {\"summary\":\"...\"}.",
        "required": ["summary"],
        "keywords": ["lamba", "aydınlat"],
    },
    {
        "name": "legal_citation",
        "agent": "legal_agent",
        "prompt": (
            "Kaynak: 3071 sayılı Kanun Madde 7. Cevap süresi otuz gündür. "
            "Sadece JSON: {\"answer\":\"...\",\"citation\":\"3071 Madde 7\"}."
        ),
        "required": ["answer", "citation"],
        "keywords": ["otuz", "30"],
        "citation": "3071 madde 7",
    },
    {
        "name": "unsupported",
        "agent": "document_agent",
        "prompt": (
            "Hava durumu tahmini isteyen kullanıcıya yetki dışı olduğunu söyle. "
            "Sadece JSON: {\"answer\":\"...\"}."
        ),
        "required": ["answer"],
        "keywords": ["yetki", "yardımcı olam"],
    },
    {
        "name": "schema_stability",
        "agent": "writing_agent",
        "prompt": "Sadece şu şemada JSON döndür: {\"subject\":\"Bilgi Talebi\",\"body\":\"Talep incelenmiştir.\"}.",
        "required": ["subject", "body"],
        "keywords": ["bilgi", "talep"],
    },
]


def _json_object(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _preflight(provider: str) -> tuple[str, str]:
    if provider == "ollama":
        url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
        try:
            response = requests.get(f"{url}/api/tags", timeout=5)
            response.raise_for_status()
            model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct")
            models = {item.get("name") for item in response.json().get("models", [])}
            if model not in models:
                return "BLOCKED", "Configured Ollama model is not installed."
            return "PASS", "Ollama and configured model are available."
        except requests.RequestException:
            return "BLOCKED", "Ollama service is unavailable."
    if not os.getenv("EVREN_BASE_URL") or not os.getenv("EVREN_API_KEY"):
        return "BLOCKED", "EVREN BLOCKED BY CONFIG"
    try:
        response = requests.get(
            f"{os.environ['EVREN_BASE_URL'].rstrip('/')}/models",
            headers={"Authorization": f"Bearer {os.environ['EVREN_API_KEY']}"},
            timeout=5,
        )
        response.raise_for_status()
        return "PASS", "EVREN configuration and model endpoint are available."
    except requests.RequestException:
        return "BLOCKED", "EVREN model endpoint is unavailable."


def run(provider: str) -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    os.environ["LLM_PROVIDER"] = provider
    if provider == "ollama":
        os.environ["OLLAMA_MODEL"] = "qwen2.5:3b-instruct"

    preflight, detail = _preflight(provider)
    if preflight != "PASS":
        return {
            "provider": provider,
            "status": "BLOCKED",
            "detail": detail,
            "env_file_modified": False,
            "results": [],
        }

    from backend.app.llm.factory import create_llm_client

    results = []
    for case in CASES:
        client = create_llm_client(case["agent"])
        started = time.perf_counter()
        try:
            raw = client.chat(
                "Türkçe yanıt ver. Yalnız istenen JSON şemasını döndür.",
                case["prompt"],
                temperature=0.0,
                max_tokens=180,
                json_mode=True,
            )
            latency_ms = round((time.perf_counter() - started) * 1000)
            parsed = _json_object(raw)
            schema_ok = bool(parsed) and all(key in parsed for key in case["required"])
            lowered = raw.lower()
            correctness = any(keyword in lowered for keyword in case["keywords"])
            expected_citation = case.get("citation")
            citation_ok = not expected_citation or expected_citation in lowered
            results.append({
                "name": case["name"],
                "status": "PASS" if schema_ok and correctness and citation_ok else "FAIL",
                "success": True,
                "schema": schema_ok,
                "correctness": correctness,
                "citation": citation_ok,
                "latency_ms": latency_ms,
                "timeout": False,
                "preview": short_text(raw, 180),
            })
        except Exception as exc:
            results.append({
                "name": case["name"],
                "status": "FAIL",
                "success": False,
                "schema": False,
                "correctness": False,
                "citation": False,
                "latency_ms": round((time.perf_counter() - started) * 1000),
                "timeout": "timeout" in type(exc).__name__.lower(),
                "error": f"{type(exc).__name__}: {short_text(exc)}",
            })

    passed = sum(item["status"] == "PASS" for item in results)
    return {
        "provider": provider,
        "status": "PASS" if passed == len(results) else "FAIL",
        "process_environment_override": True,
        "env_file_modified": False,
        "ollama_keep_alive": os.getenv("OLLAMA_KEEP_ALIVE", "30m") if provider == "ollama" else None,
        "passed": passed,
        "total": len(results),
        "p50_ms": p50([item["latency_ms"] for item in results]),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", required=True, choices=("ollama", "evren"))
    parser.add_argument("--output")
    args = parser.parse_args()
    report = run(args.provider)
    emit_report(report, args.output)
    if report["status"] == "FAIL":
        raise SystemExit(1)
    if report["status"] == "BLOCKED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
