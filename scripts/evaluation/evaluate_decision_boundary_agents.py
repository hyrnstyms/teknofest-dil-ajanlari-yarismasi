"""Evaluate the three intake agents on the locked 120-case boundary set.

The evaluator intentionally runs only the production steps needed by the
requested metrics: document classification, extraction (as input to missing
field checks), missing-field checks, and routing.  It does not call legal,
summary, writing, or quality agents.

The locked dataset was created in Git object
0c62f06bccd8c4ec456cd16f6de58dc7b6813a92.  The working-tree path is used
when present; ``--git-object`` provides a reproducible fallback when it is not.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.agents.document_agent import DocumentAgent
from backend.app.agents.extraction_agent import ExtractionAgent
from backend.app.agents.missing_field_agent import MissingFieldAgent
from backend.app.agents.routing_agent import RoutingAgent
from backend.app.institutions.profile_loader import load_institution_profile
from backend.app.llm.base import LLMClient
from backend.app.llm.factory import create_llm_client


DEFAULT_DATASET = Path("data/evaluation/synthetic/decision_boundary_120.jsonl")
LOCKED_DATASET_OBJECT = "0c62f06bccd8c4ec456cd16f6de58dc7b6813a92"

MISSING_FIELD_ALIASES = {
    "sender_name": "person_name",
    "signature": "signature_present",
}


class CountingLLMClient(LLMClient):
    """Count attempted, successful, and failed calls without changing behavior."""

    def __init__(self, delegate: LLMClient):
        self.delegate = delegate
        self.attempted = 0
        self.successful = 0
        self.failed = 0

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 500,
        json_mode: bool = False,
    ) -> str:
        self.attempted += 1
        try:
            result = self.delegate.chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )
        except Exception:
            self.failed += 1
            raise
        self.successful += 1
        return result

    def get_model_name(self) -> str:
        return self.delegate.get_model_name()

    def get_provider_name(self) -> str:
        return self.delegate.get_provider_name()


_thread_local = threading.local()


def _base_llm() -> LLMClient:
    client = getattr(_thread_local, "llm", None)
    if client is None:
        client = create_llm_client("document_agent")
        _thread_local.llm = client
    return client


def _load_dataset(path: Path, git_object: str | None) -> tuple[list[dict[str, Any]], str, str]:
    if path.exists():
        raw = path.read_bytes()
        source = str(path)
    elif git_object:
        completed = subprocess.run(
            ["git", "cat-file", "-p", git_object],
            check=True,
            capture_output=True,
        )
        raw = completed.stdout
        source = f"git-object:{git_object}"
    else:
        raise FileNotFoundError(
            f"Dataset bulunamadı: {path}. Kilitli nesne için --git-object kullanın."
        )

    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    if len(rows) != 120:
        raise ValueError(f"Kilitli sette 120 yerine {len(rows)} kayıt var.")
    if len({row["id"] for row in rows}) != 120:
        raise ValueError("Dataset ID'leri benzersiz değil.")
    return rows, source, hashlib.sha256(raw).hexdigest()


def _normalize_document_type(value: Any) -> str:
    label = str(value or "").strip().lower()
    if label in {
        "bilgi_edinme",
        "sosyal_yardim_basvuru",
        "tapu_kadastro_basvuru",
        "ihale_itirazi",
    }:
        return "dilekce"
    if label == "kurumlar_arasi_yazi":
        return "resmi_yazi"
    return label


def _canonical_missing_fields(values: list[Any] | None) -> set[str]:
    return {
        MISSING_FIELD_ALIASES.get(str(value), str(value))
        for value in (values or [])
        if str(value).strip()
    }


def _ranked_unit_codes(routing: dict[str, Any]) -> list[str]:
    codes = []
    for item in routing.get("ranked_units") or []:
        if not isinstance(item, dict):
            continue
        code = item.get("department_code") or item.get("unit_id") or item.get("id")
        if code:
            codes.append(str(code))
    return codes


def _evaluate_row(row: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    institution = str(row["institution"])
    profile = load_institution_profile(institution)
    llm = CountingLLMClient(_base_llm())

    document_agent = DocumentAgent(llm=llm, institution_profile=profile)
    extraction_agent = ExtractionAgent(llm=llm)
    missing_field_agent = MissingFieldAgent()
    routing_agent = RoutingAgent(institution=institution)

    text = str(row["text"])
    gold = row["gold"]

    document = document_agent.analyze(text)
    extraction = extraction_agent.extract(text, document_context=document)
    fields = extraction.get("fields") or {}

    # Match KamuaiWorkflow ordering: missing-field runs before routing and thus
    # receives no candidate department.
    missing = missing_field_agent.check_missing_fields(
        document_type=str(document.get("document_type") or ""),
        process_intent=str(document.get("process_intent") or ""),
        extracted_fields=fields,
        document_subtype=document.get("document_subtype"),
        institution_profile=profile,
        institution_id=institution,
        raw_text=text,
        document=document,
    )

    # Match the current production workflow, which does not pass subtype or
    # retrieved evaluation exemplars into the standalone routing rule engine.
    routing = routing_agent.route(
        document_type=str(document.get("document_type") or ""),
        process_intent=str(document.get("process_intent") or ""),
        subject=str(document.get("subject_excerpt") or ""),
        request_text=str(document.get("request_excerpt") or ""),
        extracted_fields=fields,
        retrieved_documents=[],
    )

    gold_doc = _normalize_document_type(gold.get("expected_document_type"))
    predicted_doc = _normalize_document_type(document.get("document_type"))
    accepted_units = {str(unit) for unit in (gold.get("acceptable_units") or [])}
    gold_unit = gold.get("expected_unit")
    predicted_unit = routing.get("recommended_department_code")
    ranked_units = _ranked_unit_codes(routing)

    gold_missing = _canonical_missing_fields(gold.get("expected_missing_fields"))
    predicted_missing = _canonical_missing_fields(missing.get("missing_fields"))

    route_evaluable = gold_unit is not None and bool(accepted_units)
    route_top1_correct = route_evaluable and str(predicted_unit or "") in accepted_units
    route_top3_correct = route_evaluable and bool(accepted_units.intersection(ranked_units[:3]))

    gold_review = bool(gold.get("needs_human_review"))
    predicted_review = bool(routing.get("needs_human_review"))
    if route_evaluable:
        routing_decision_correct = route_top1_correct and not predicted_review
    else:
        routing_decision_correct = gold_review == predicted_review

    return {
        "id": row["id"],
        "bucket": row["bucket"],
        "institution": institution,
        "status": "ok",
        "document": {
            "gold": gold_doc,
            "predicted": predicted_doc,
            "correct": predicted_doc == gold_doc,
            "classification_mode": document.get("classification_mode"),
        },
        "routing": {
            "evaluable": route_evaluable,
            "accepted_units": sorted(accepted_units),
            "predicted": predicted_unit,
            "ranked_top3": ranked_units[:3],
            "top1_correct": route_top1_correct,
            "top3_correct": route_top3_correct,
            "gold_review": gold_review,
            "predicted_review": predicted_review,
            "decision_correct": routing_decision_correct,
        },
        "missing_field": {
            "gold": sorted(gold_missing),
            "predicted": sorted(predicted_missing),
            "exact_match": gold_missing == predicted_missing,
            "any_missing_correct": bool(gold_missing) == bool(predicted_missing),
            "true_positives": len(gold_missing.intersection(predicted_missing)),
            "false_positives": len(predicted_missing - gold_missing),
            "false_negatives": len(gold_missing - predicted_missing),
        },
        "llm": {
            "provider": llm.get_provider_name(),
            "model": llm.get_model_name(),
            "attempted_calls": llm.attempted,
            "successful_calls": llm.successful,
            "failed_calls": llm.failed,
        },
        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
    }


def _safe_evaluate_row(row: dict[str, Any]) -> dict[str, Any]:
    try:
        return _evaluate_row(row)
    except Exception as exc:
        return {
            "id": row.get("id"),
            "bucket": row.get("bucket"),
            "institution": row.get("institution"),
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def _percentage(numerator: int, denominator: int) -> float | None:
    return round(100.0 * numerator / denominator, 2) if denominator else None


def _summarize(
    results: list[dict[str, Any]],
    *,
    dataset_source: str,
    dataset_sha256: str,
    elapsed_seconds: float,
) -> dict[str, Any]:
    ok = [result for result in results if result.get("status") == "ok"]
    failures = [result for result in results if result.get("status") != "ok"]

    document_correct = sum(bool(result["document"]["correct"]) for result in ok)
    route_rows = [result for result in ok if result["routing"]["evaluable"]]
    route_top1 = sum(bool(result["routing"]["top1_correct"]) for result in route_rows)
    route_top3 = sum(bool(result["routing"]["top3_correct"]) for result in route_rows)
    routing_decisions = sum(bool(result["routing"]["decision_correct"]) for result in ok)

    missing_exact = sum(bool(result["missing_field"]["exact_match"]) for result in ok)
    missing_any = sum(bool(result["missing_field"]["any_missing_correct"]) for result in ok)
    missing_tp = sum(result["missing_field"]["true_positives"] for result in ok)
    missing_fp = sum(result["missing_field"]["false_positives"] for result in ok)
    missing_fn = sum(result["missing_field"]["false_negatives"] for result in ok)
    precision = missing_tp / (missing_tp + missing_fp) if missing_tp + missing_fp else 0.0
    recall = missing_tp / (missing_tp + missing_fn) if missing_tp + missing_fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    attempted_calls = sum(result["llm"]["attempted_calls"] for result in ok)
    successful_calls = sum(result["llm"]["successful_calls"] for result in ok)
    failed_calls = sum(result["llm"]["failed_calls"] for result in ok)
    fallback_modes = Counter(result["document"]["classification_mode"] for result in ok)

    return {
        "dataset": {
            "name": "decision_boundary_120",
            "source": dataset_source,
            "sha256": dataset_sha256,
            "total_records": len(results),
            "successful_records": len(ok),
            "failed_records": len(failures),
            "bucket_counts": dict(Counter(result.get("bucket") for result in results)),
        },
        "metrics": {
            "document_agent": {
                "metric": "broad_document_type_exact_accuracy",
                "correct": document_correct,
                "total": len(ok),
                "accuracy_percent": _percentage(document_correct, len(ok)),
                "classification_modes": dict(fallback_modes),
            },
            "routing_agent": {
                "metric": "top1_acceptable_unit_accuracy_on_routable_cases",
                "correct": route_top1,
                "total": len(route_rows),
                "accuracy_percent": _percentage(route_top1, len(route_rows)),
                "top3_correct": route_top3,
                "top3_accuracy_percent": _percentage(route_top3, len(route_rows)),
                "full_set_decision_correct": routing_decisions,
                "full_set_decision_accuracy_percent": _percentage(routing_decisions, len(ok)),
            },
            "missing_field_agent": {
                "primary_metric": "any_missing_field_binary_accuracy",
                "correct": missing_any,
                "total": len(ok),
                "accuracy_percent": _percentage(missing_any, len(ok)),
                "exact_set_correct": missing_exact,
                "exact_set_accuracy_percent": _percentage(missing_exact, len(ok)),
                "field_true_positives": missing_tp,
                "field_false_positives": missing_fp,
                "field_false_negatives": missing_fn,
                "field_precision_percent": round(precision * 100, 2),
                "field_recall_percent": round(recall * 100, 2),
                "field_f1_percent": round(f1 * 100, 2),
            },
        },
        "llm_usage": {
            "attempted_calls": attempted_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "attempted_calls_per_document": round(attempted_calls / len(ok), 3) if ok else None,
            "provider": ok[0]["llm"]["provider"] if ok else None,
            "model": ok[0]["llm"]["model"] if ok else None,
        },
        "runtime": {
            "wall_clock_seconds": round(elapsed_seconds, 2),
            "mean_focused_pipeline_ms": round(
                sum(result["duration_ms"] for result in ok) / len(ok), 1
            ) if ok else None,
        },
        "failures": failures,
        "rows": sorted(results, key=lambda result: str(result.get("id"))),
    }


def _print_table(report: dict[str, Any]) -> None:
    metrics = report["metrics"]
    rows = [
        (
            "document_agent",
            "Belge türü doğruluğu",
            metrics["document_agent"]["correct"],
            metrics["document_agent"]["total"],
            metrics["document_agent"]["accuracy_percent"],
        ),
        (
            "routing_agent",
            "Doğru birim (Top-1, yönlendirilebilir)",
            metrics["routing_agent"]["correct"],
            metrics["routing_agent"]["total"],
            metrics["routing_agent"]["accuracy_percent"],
        ),
        (
            "missing_field_agent",
            "Eksik alan var/yok doğruluğu",
            metrics["missing_field_agent"]["correct"],
            metrics["missing_field_agent"]["total"],
            metrics["missing_field_agent"]["accuracy_percent"],
        ),
    ]
    print("\n| Ajan | Metrik | Doğru | Toplam | Doğruluk |")
    print("|---|---|---:|---:|---:|")
    for agent, metric, correct, total, percent in rows:
        shown = f"%{percent:.2f}" if percent is not None else "N/A"
        print(f"| {agent} | {metric} | {correct} | {total} | {shown} |")

    missing = metrics["missing_field_agent"]
    exact_set = missing["exact_set_accuracy_percent"]
    exact_set_shown = f"%{exact_set:.2f}" if exact_set is not None else "N/A"
    print(
        "\nEksik alan katı kontrolleri: "
        f"exact-set {exact_set_shown}; "
        f"precision %{missing['field_precision_percent']:.2f}; "
        f"recall %{missing['field_recall_percent']:.2f}; "
        f"F1 %{missing['field_f1_percent']:.2f}."
    )
    usage = report["llm_usage"]
    calls_per_document = usage["attempted_calls_per_document"]
    calls_shown = f"{calls_per_document:.3f}" if calls_per_document is not None else "N/A"
    print(
        "LLM kullanımı: "
        f"{usage['attempted_calls']} çağrı / {report['dataset']['successful_records']} evrak = "
        f"{calls_shown} çağrı/evrak "
        f"({usage['failed_calls']} başarısız çağrı)."
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--git-object", default=LOCKED_DATASET_OBJECT)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/evaluation/decision_boundary_agents.json"),
    )
    args = parser.parse_args()

    records, source, sha256 = _load_dataset(args.dataset, args.git_object)
    if args.limit is not None:
        if args.limit <= 0:
            raise ValueError("--limit pozitif olmalı.")
        records = records[: args.limit]

    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(_safe_evaluate_row, row): row["id"] for row in records}
        completed_count = 0
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed_count += 1
            print(
                f"[{completed_count:03d}/{len(records):03d}] {result.get('id')} "
                f"{result.get('status')}",
                flush=True,
            )

    report = _summarize(
        results,
        dataset_source=source,
        dataset_sha256=sha256,
        elapsed_seconds=time.perf_counter() - started,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _print_table(report)
    print(f"\nRapor: {args.output}")
    return 1 if report["dataset"]["failed_records"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
