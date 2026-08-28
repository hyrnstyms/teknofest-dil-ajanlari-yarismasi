"""Measure all Section 9 metrics on the locked decision-boundary dataset.

This evaluator does not change agent behavior.  It runs the production
``KamuaiWorkflow`` and derives:

* subject coverage of ``summary_agent.short_summary`` for all 120 records,
* official-writing format and unverified-outcome-claim metrics for all drafts,
* sequential wall-clock end-to-end latency on a deterministic, stratified
  20-record sample.

The first three metrics are copied without reinterpretation from
``reports/evaluation/decision_boundary_agents.json`` and are combined with the
new measurements in ``docs/METRIK_RAPORU.md``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import subprocess
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.graph.workflow import KamuaiWorkflow
from backend.app.official_writing.format_validator import validate_format


DEFAULT_DATASET = Path("data/evaluation/synthetic/decision_boundary_120.jsonl")
LOCKED_DATASET_OBJECT = "0c62f06bccd8c4ec456cd16f6de58dc7b6813a92"
DEFAULT_EXISTING_METRICS = Path("reports/evaluation/decision_boundary_agents.json")
DEFAULT_OUTPUT = Path("reports/evaluation/section9_metrics.json")
DEFAULT_REPORT = Path("docs/METRIK_RAPORU.md")
TIMING_SAMPLE_SEED = 20260828

OFFICIAL_DRAFT_TYPES = {
    "ust_yazi": "ust_yazi",
    "bilgilendirme_metni": "ust_yazi",
    "cevap_yazisi": "cevap_yazisi",
    "tekit_yazisi": "tekit_yazisi",
    "eksik_bilgi_talebi": "eksik_bilgi_talebi",
}

# Generic Turkish words do not prove that a summary preserved the actual topic.
TOPIC_STOPWORDS = {
    "aciklama",
    "basvuru",
    "basvurusu",
    "belge",
    "belgeleri",
    "bilgi",
    "icin",
    "ile",
    "islem",
    "islemi",
    "islemleri",
    "konu",
    "talep",
    "talebi",
    "yazi",
}

_thread_local = threading.local()


def _load_dataset(path: Path, git_object: str | None) -> tuple[list[dict[str, Any]], str, str]:
    if path.exists():
        raw = path.read_bytes()
        source = str(path)
    elif git_object:
        completed = subprocess.run(
            ["git", "cat-file", "-p", git_object],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        raw = completed.stdout
        source = f"git-object:{git_object}"
    else:
        raise FileNotFoundError(f"Dataset bulunamadı: {path}")

    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    if len(rows) != 120:
        raise ValueError(f"Kilitli sette 120 yerine {len(rows)} kayıt var.")
    if len({row.get("id") for row in rows}) != len(rows):
        raise ValueError("Dataset ID'leri benzersiz değil.")
    return rows, source, hashlib.sha256(raw).hexdigest()


def _workflow(institution: str, *, timing: bool = False) -> KamuaiWorkflow:
    cache_name = "timing_workflows" if timing else "quality_workflows"
    cache = getattr(_thread_local, cache_name, None)
    if cache is None:
        cache = {}
        setattr(_thread_local, cache_name, cache)
    if institution not in cache:
        cache[institution] = KamuaiWorkflow(institution=institution)
    return cache[institution]


def _normalize_text(value: Any) -> str:
    import re
    import unicodedata

    text = str(value or "").replace("I", "ı").replace("İ", "i")
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _topic_match(title: str, summary: str) -> dict[str, Any]:
    normalized_title = _normalize_text(title)
    normalized_summary = _normalize_text(summary)
    title_tokens = normalized_title.split()
    informative = [
        token for token in title_tokens
        if len(token) >= 3 and token not in TOPIC_STOPWORDS
    ]
    if not informative:
        informative = [token for token in title_tokens if len(token) >= 3]

    summary_tokens = set(normalized_summary.split())
    matched = [token for token in informative if token in summary_tokens]
    coverage = len(matched) / len(informative) if informative else 0.0
    required = math.ceil(len(informative) * 0.60) if informative else 1
    token_set = fuzz.token_set_ratio(normalized_title, normalized_summary)
    partial = fuzz.partial_ratio(normalized_title, normalized_summary)

    exact_phrase = bool(normalized_title and normalized_title in normalized_summary)
    keyword_pass = bool(informative and len(matched) >= required)
    fuzzy_pass = bool(token_set >= 75.0 and partial >= 80.0)
    passed = bool(normalized_summary and (exact_phrase or keyword_pass or fuzzy_pass))

    if exact_phrase:
        reason = "exact_normalized_phrase"
    elif keyword_pass:
        reason = "informative_keyword_coverage"
    elif fuzzy_pass:
        reason = "rapidfuzz_similarity"
    elif not normalized_summary:
        reason = "missing_summary"
    else:
        reason = "topic_not_preserved"

    return {
        "passed": passed,
        "reason": reason,
        "title": title,
        "summary": summary,
        "informative_keywords": informative,
        "matched_keywords": matched,
        "keyword_coverage_percent": round(coverage * 100, 2),
        "token_set_ratio": round(token_set, 2),
        "partial_ratio": round(partial, 2),
    }


def _format_result(draft: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(draft, dict) or not draft:
        return {
            "category": "Hata",
            "reason": "writing_agent çıktısı yok",
            "draft_type": None,
            "validator_applied": False,
            "errors": ["Taslak çıktısı bulunamadı."],
            "warnings": [],
        }

    draft_type = str(draft.get("draft_type") or "")
    payload = draft.get("draft")
    if not isinstance(payload, dict) or not payload:
        return {
            "category": "Hata",
            "reason": "taslak metni üretilemedi",
            "draft_type": draft_type or None,
            "validator_applied": False,
            "errors": [str(draft.get("error") or draft.get("warning") or "Taslak payload'u yok.")],
            "warnings": [],
        }

    validator_type = OFFICIAL_DRAFT_TYPES.get(draft_type)
    if not validator_type:
        return {
            "category": "Kontrol Gerekli",
            "reason": "format_validator kapsamı dışındaki taslak türü",
            "draft_type": draft_type or None,
            "validator_applied": False,
            "errors": [],
        "warnings": [
            f"'{draft_type or 'belirsiz'}' türü resmî yazı format_validator kapsamındaki "
            "ust_yazi/cevap_yazisi/tekit_yazisi/eksik_bilgi_talebi türlerinden biri değil."
        ],
        }

    official_render = draft.get("official_render") or {}
    context = official_render.get("context") if isinstance(official_render, dict) else None
    if not isinstance(context, dict) or not context:
        return {
            "category": "Kontrol Gerekli",
            "reason": "resmî şablon doğrulama bağlamı yok",
            "draft_type": draft_type,
            "validator_applied": False,
            "errors": [],
            "warnings": ["Format doğrulaması için official_render.context üretilemedi."],
        }

    try:
        result = validate_format(
            taslak=context,
            yazi_turu=validator_type,
            missing_fields=official_render.get("missing_fields") or [],
        )
    except Exception as exc:
        return {
            "category": "Hata",
            "reason": "format_validator çalıştırma hatası",
            "draft_type": draft_type,
            "validator_applied": True,
            "errors": [f"{type(exc).__name__}: {exc}"],
            "warnings": [],
        }

    errors = [item.mesaj for item in result.hatalar]
    warnings = [item.mesaj for item in result.uyarilar]
    if not result.gecerli:
        category = "Hata"
    elif warnings:
        category = "Kontrol Gerekli"
    else:
        category = "Uygun"
    return {
        "category": category,
        "reason": "format_validator sonucu",
        "draft_type": draft_type,
        "validator_applied": True,
        "errors": errors,
        "warnings": warnings,
    }


def _state_dict(state: Any) -> dict[str, Any]:
    if isinstance(state, dict):
        return state
    if hasattr(state, "model_dump"):
        return state.model_dump()
    raise TypeError(f"Beklenmeyen workflow çıktısı: {type(state).__name__}")


def _run_quality_row(row: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        state = _state_dict(
            _workflow(str(row["institution"])).run(
                raw_text=str(row["text"]),
                document_id=str(row["id"]),
            )
        )
        elapsed = time.perf_counter() - started
        summary = state.get("summary") or {}
        draft = state.get("draft") or {}
        quality = state.get("quality") or {}
        topic = _topic_match(str(row.get("title") or ""), str(summary.get("short_summary") or ""))
        format_evaluation = _format_result(draft)
        claim_check = (quality.get("checks") or {}).get("unverified_outcome_claim") or {}
        claim_detected = claim_check.get("status") == "fail"
        node_failures = [
            name for name, timing in (state.get("node_timings") or {}).items()
            if isinstance(timing, dict) and timing.get("status") == "failed"
        ]
        return {
            "id": row["id"],
            "bucket": row.get("bucket"),
            "institution": row["institution"],
            "status": "ok" if not node_failures else "node_failure",
            "workflow_seconds": round(elapsed, 3),
            "node_failures": node_failures,
            "workflow_warnings": state.get("warnings") or [],
            "summary": topic,
            "draft": {
                **format_evaluation,
                "generation_mode": draft.get("draft_generation_mode"),
                "unverified_outcome_claim_detected": claim_detected,
                "unverified_outcome_claim_check": claim_check or None,
            },
        }
    except Exception as exc:
        elapsed = time.perf_counter() - started
        return {
            "id": row.get("id"),
            "bucket": row.get("bucket"),
            "institution": row.get("institution"),
            "status": "workflow_error",
            "workflow_seconds": round(elapsed, 3),
            "error": f"{type(exc).__name__}: {exc}",
            "node_failures": [],
            "workflow_warnings": [],
            "summary": _topic_match(str(row.get("title") or ""), ""),
            "draft": {
                **_format_result({}),
                "generation_mode": None,
                # Conservative denominator: an unevaluated record is not counted
                # as demonstrably claim-free.
                "unverified_outcome_claim_detected": None,
                "unverified_outcome_claim_check": None,
            },
        }


def _timing_sample(rows: list[dict[str, Any]], size: int = 20) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("bucket") or "unknown")].append(row)
    if size != 20 or len(grouped) != 4:
        rng = random.Random(TIMING_SAMPLE_SEED)
        return sorted(rng.sample(rows, size), key=lambda item: item["id"])

    rng = random.Random(TIMING_SAMPLE_SEED)
    chosen = []
    for bucket in sorted(grouped):
        chosen.extend(rng.sample(grouped[bucket], 5))
    return sorted(chosen, key=lambda item: item["id"])


def _run_timing_row(row: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        state = _state_dict(
            _workflow(str(row["institution"]), timing=True).run(
                raw_text=str(row["text"]),
                document_id=f"timing-{row['id']}",
            )
        )
        elapsed = time.perf_counter() - started
        timings = state.get("node_timings") or {}
        node_failures = [
            name for name, timing in timings.items()
            if isinstance(timing, dict) and timing.get("status") == "failed"
        ]
        return {
            "id": row["id"],
            "bucket": row.get("bucket"),
            "institution": row["institution"],
            "seconds": round(elapsed, 3),
            "status": "ok" if not node_failures else "node_failure",
            "node_failures": node_failures,
            "node_timings": timings,
            "workflow_warnings": state.get("warnings") or [],
        }
    except Exception as exc:
        return {
            "id": row["id"],
            "bucket": row.get("bucket"),
            "institution": row["institution"],
            "seconds": round(time.perf_counter() - started, 3),
            "status": "workflow_error",
            "node_failures": [],
            "error": f"{type(exc).__name__}: {exc}",
            "node_timings": {},
            "workflow_warnings": [],
        }


def _pct(numerator: int, denominator: int) -> float:
    return round(100.0 * numerator / denominator, 2) if denominator else 0.0


def _aggregate_writing(quality_rows: list[dict[str, Any]], total: int) -> dict[str, Any]:
    categories = Counter(item["draft"]["category"] for item in quality_rows)
    claim_detected = sum(
        item["draft"]["unverified_outcome_claim_detected"] is True
        for item in quality_rows
    )
    claim_evaluable = sum(
        item["draft"]["unverified_outcome_claim_detected"] is not None
        for item in quality_rows
    )
    claim_free = sum(
        item["draft"]["unverified_outcome_claim_detected"] is False
        for item in quality_rows
    )
    validator_applied = sum(bool(item["draft"]["validator_applied"]) for item in quality_rows)
    # ``gecerli=True`` means no format error. Warnings still keep the public
    # category at "Kontrol Gerekli", so this is separate from "Uygun".
    format_error_free = sum(
        bool(item["draft"]["validator_applied"])
        and item["draft"]["category"] != "Hata"
        for item in quality_rows
    )
    draft_type_counts = Counter(str(item["draft"].get("draft_type") or "none") for item in quality_rows)

    return {
        "total": total,
        "format_categories": {
            category: {
                "count": categories.get(category, 0),
                "percent": _pct(categories.get(category, 0), total),
            }
            for category in ("Uygun", "Kontrol Gerekli", "Hata")
        },
        "format_pass_definition": "validator_applied_and_gecerli_true_including_warnings",
        "format_pass_count": format_error_free,
        "format_pass_percent": _pct(format_error_free, total),
        "warning_free_uygun_count": categories.get("Uygun", 0),
        "warning_free_uygun_percent": _pct(categories.get("Uygun", 0), total),
        "validator_applied_count": validator_applied,
        "validator_applied_percent": _pct(validator_applied, total),
        "validator_error_count": validator_applied - format_error_free,
        "draft_type_counts": dict(draft_type_counts),
        "unverified_outcome_claim_detected_count": claim_detected,
        "unverified_outcome_claim_detected_percent": _pct(claim_detected, total),
        "unverified_outcome_claim_free_count": claim_free,
        "unverified_outcome_claim_free_percent": _pct(claim_free, total),
        "unverified_outcome_claim_evaluable_count": claim_evaluable,
    }


def _aggregate(
    rows: list[dict[str, Any]],
    quality_rows: list[dict[str, Any]],
    timing_rows: list[dict[str, Any]],
    source: str,
    sha256: str,
    existing: dict[str, Any],
) -> dict[str, Any]:
    total = len(rows)
    summary_correct = sum(bool(item["summary"]["passed"]) for item in quality_rows)
    successful_timings = [item for item in timing_rows if item.get("status") == "ok"]
    measured_seconds = [float(item["seconds"]) for item in successful_timings]
    fastest = min(successful_timings, key=lambda item: item["seconds"]) if successful_timings else None
    slowest = max(successful_timings, key=lambda item: item["seconds"]) if successful_timings else None

    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True
            ).stdout.strip()
        )
    except Exception:
        head, dirty = "unknown", None

    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "code": {"git_head": head, "worktree_dirty": dirty},
        "dataset": {
            "name": "decision_boundary_120",
            "source": source,
            "sha256": sha256,
            "total_records": total,
            "bucket_counts": dict(Counter(str(row.get("bucket")) for row in rows)),
        },
        "existing_metrics_source": str(DEFAULT_EXISTING_METRICS),
        "metrics": {
            "document_agent": existing["metrics"]["document_agent"],
            "routing_agent": existing["metrics"]["routing_agent"],
            "missing_field_agent": existing["metrics"]["missing_field_agent"],
            "summary_agent": {
                "metric": "gold_title_topic_preserved_in_short_summary",
                "correct": summary_correct,
                "total": total,
                "accuracy_percent": _pct(summary_correct, total),
                "failed_or_missing_summaries": sum(
                    item["summary"]["reason"] == "missing_summary" for item in quality_rows
                ),
                "match_reason_counts": dict(Counter(item["summary"]["reason"] for item in quality_rows)),
            },
            "writing_quality": _aggregate_writing(quality_rows, total),
            "end_to_end_runtime": {
                "sample_size_requested": len(timing_rows),
                "successful_runs": len(successful_timings),
                "failed_runs": len(timing_rows) - len(successful_timings),
                "sample_seed": TIMING_SAMPLE_SEED,
                "sample_ids": [item["id"] for item in timing_rows],
                "mean_seconds": round(statistics.mean(measured_seconds), 3) if measured_seconds else None,
                "median_seconds": round(statistics.median(measured_seconds), 3) if measured_seconds else None,
                "fastest": {"id": fastest["id"], "seconds": fastest["seconds"]} if fastest else None,
                "slowest": {"id": slowest["id"], "seconds": slowest["seconds"]} if slowest else None,
                "execution_mode": "sequential_wall_clock_full_production_workflow",
                "included_nodes": [
                    "document_agent",
                    "extraction_agent",
                    "legal_agent",
                    "missing_field_agent",
                    "summary_agent",
                    "routing_agent",
                    "writing_agent",
                    "quality_agent",
                    "human_review_agent",
                ],
            },
        },
        "quality_run": {
            "total": len(quality_rows),
            "workflow_errors": sum(item["status"] == "workflow_error" for item in quality_rows),
            "node_failure_records": sum(item["status"] == "node_failure" for item in quality_rows),
            "workers": None,
        },
        "rows": quality_rows,
        "timing_rows": timing_rows,
    }


def _render_report(result: dict[str, Any], output_json: Path) -> str:
    metrics = result["metrics"]
    doc = metrics["document_agent"]
    routing = metrics["routing_agent"]
    missing = metrics["missing_field_agent"]
    summary = metrics["summary_agent"]
    writing = metrics["writing_quality"]
    runtime = metrics["end_to_end_runtime"]
    cats = writing["format_categories"]
    rows = result["rows"]
    warned_after_validation = sum(
        item["draft"]["category"] == "Kontrol Gerekli"
        and bool(item["draft"]["validator_applied"])
        for item in rows
    )
    outside_validator_scope = sum(
        item["draft"]["category"] == "Kontrol Gerekli"
        and not bool(item["draft"]["validator_applied"])
        for item in rows
    )
    format_error_ids = [
        item["id"]
        for item in rows
        if item["draft"]["category"] == "Hata"
        and bool(item["draft"]["validator_applied"])
    ]
    missing_draft_ids = [
        item["id"]
        for item in rows
        if item["draft"]["category"] == "Hata"
        and not bool(item["draft"]["validator_applied"])
    ]
    claim_ids = [
        item["id"]
        for item in rows
        if item["draft"]["unverified_outcome_claim_detected"] is True
    ]

    timing_result = (
        f"Ort. {runtime['mean_seconds']:.3f} sn; medyan {runtime['median_seconds']:.3f} sn; "
        f"en hızlı {runtime['fastest']['id']} ({runtime['fastest']['seconds']:.3f} sn); "
        f"en yavaş {runtime['slowest']['id']} ({runtime['slowest']['seconds']:.3f} sn)"
        if runtime["successful_runs"]
        else "Başarılı süre ölçümü yok"
    )

    lines = [
        "# Şartname Bölüm 9 — Metrik Raporu",
        "",
        f"> Ölçüm tarihi: {result['generated_at']}  ",
        f"> Veri seti: `decision_boundary_120` — SHA-256 `{result['dataset']['sha256']}`  ",
        f"> Kod durumu: Git `{result['code']['git_head']}`; çalışma ağacı "
        f"{'değişiklik içeriyor' if result['code']['worktree_dirty'] else 'temiz'}.",
        "",
        "## Sunuma hazır sonuç tablosu",
        "",
        "| Şartname Kriteri | Metrik | Sonuç |",
        "|---|---|---|",
        f"| Sınıflandırma doğruluğu | `document_agent` geniş evrak türü exact accuracy | **{doc['correct']}/{doc['total']} — %{doc['accuracy_percent']:.2f}** |",
        f"| Yönlendirme başarımı | `routing_agent` Top-1 / Top-3 (yönlendirilebilir {routing['total']} vaka) | **Top-1 {routing['correct']}/{routing['total']} — %{routing['accuracy_percent']:.2f}; Top-3 {routing['top3_correct']}/{routing['total']} — %{routing['top3_accuracy_percent']:.2f}** |",
        f"| Eksik bilgi tespiti | `missing_field_agent` herhangi bir eksik alan var/yok doğruluğu | **{missing['correct']}/{missing['total']} — %{missing['accuracy_percent']:.2f}** (alan bazlı F1: **%{missing['field_f1_percent']:.2f}**) |",
        f"| Özetleme kalitesi | Altın konu/başlığın `short_summary` içinde korunması | **{summary['correct']}/{summary['total']} — %{summary['accuracy_percent']:.2f}** |",
        f"| Taslak/format kalitesi | `format_validator` hatasız (`gecerli=True`, uyarı olabilir) / doğrulanmamış sonuç iddiası yok | **{writing['format_pass_count']}/{writing['total']} — %{writing['format_pass_percent']:.2f}** format hatasız; **{writing['unverified_outcome_claim_free_count']}/{writing['total']} — %{writing['unverified_outcome_claim_free_percent']:.2f}** iddiasız |",
        f"| Gerçek zamana yakınlık | Tam workflow, 20 kayıt, sıralı duvar saati | **{timing_result}** |",
        "",
        "## Taslak kalitesi dağılımı",
        "",
        "| Format sonucu | Adet | Oran |",
        "|---|---:|---:|",
        f"| Uygun | {cats['Uygun']['count']} | %{cats['Uygun']['percent']:.2f} |",
        f"| Kontrol Gerekli | {cats['Kontrol Gerekli']['count']} | %{cats['Kontrol Gerekli']['percent']:.2f} |",
        f"| Hata | {cats['Hata']['count']} | %{cats['Hata']['percent']:.2f} |",
        f"| **Toplam** | **{writing['total']}** | **%100,00** |",
        "",
        f"Tamamen uyarısız `Uygun` sonucu **{writing['warning_free_uygun_count']}/{writing['total']} "
        f"(%{writing['warning_free_uygun_percent']:.2f})** düzeyindedir. Doğrulayıcı {writing['validator_applied_count']}/{writing['total']} "
        f"taslağa uygulanabildi; bunların {writing['format_pass_count']} tanesi format hatası üretmedi, "
        f"{writing['validator_error_count']} tanesi hata üretti. Uyarılı fakat `gecerli=True` sonuçlar "
        "üçlü dağılımda `Kontrol Gerekli`, hatasız-geçiş metriğinde ise hatasız sayılmıştır.",
        "",
        f"`Kontrol Gerekli` sınıfındaki {cats['Kontrol Gerekli']['count']} kaydın "
        f"{warned_after_validation} tanesi doğrulayıcıdan hatasız fakat EBYS/personel alanı uyarılarıyla geçti; "
        f"{outside_validator_scope} tanesi desteklenen resmî yazı türlerinin dışında kaldığı için doğrulayıcı "
        "kapsamı dışındaydı. `Hata` vakaları: "
        f"format hatası {', '.join(format_error_ids) or 'yok'}; üretilemeyen taslak "
        f"{', '.join(missing_draft_ids) or 'yok'}.",
        "",
        f"Doğrulanmamış sonuç iddiası **{writing['unverified_outcome_claim_detected_count']}/{writing['total']} "
        f"(%{writing['unverified_outcome_claim_detected_percent']:.2f})** taslakta tespit edildi. "
        f"Dolayısıyla **{writing['unverified_outcome_claim_free_count']}/{writing['total']} "
        f"(%{writing['unverified_outcome_claim_free_percent']:.2f})** taslakta bu uyarı yoktu. "
        f"Kontrolün değerlendirilebilir olduğu kayıt sayısı {writing['unverified_outcome_claim_evaluable_count']}/{writing['total']}; "
        f"uyarı üreten vakalar: {', '.join(claim_ids) or 'yok'}.",
        "",
        "## Hesaplama yöntemi ve kapsam",
        "",
        "- **İlk üç metrik yeniden üretilmiştir.** Sınıflandırma, yönlendirme ve eksik bilgi sonuçları bu birleşik "
        "koşudan hemen önce yeniden oluşturulan `reports/evaluation/decision_boundary_agents.json` dosyasından "
        "aynen alınmıştır; bu raporda yeniden yorumlanmamıştır.",
        "- **Özetleme:** Her kaydın altın `title` alanı normalize edilip `short_summary` ile karşılaştırıldı. "
        "Başlık ifadesinin aynen bulunması, bilgilendirici başlık sözcüklerinin en az %60'ının bulunması veya "
        "RapidFuzz `token_set_ratio >= 75` ve `partial_ratio >= 80` koşullarının birlikte sağlanması başarıdır. "
        "Boş/üretilemeyen özet başarısız sayılır.",
        "- **Format:** Resmî yazı türlerinde `official_render.context`, üretimde kullanılan deterministik "
        "`validate_format` fonksiyonuna verildi. Hatasız ve uyarısız sonuç `Uygun`; yalnız uyarı bulunan ya da "
        "doğrulayıcı kapsamı dışında kalan taslak `Kontrol Gerekli`; doğrulama hatası veya üretilemeyen taslak "
        "`Hata` sayıldı. Kapsam dışı taslaklar başarı hanesine yazılmadı. `gecerli=True` olup yalnız uyarı "
        "taşıyan taslaklar hatasız-geçiş metriğine dahil edildi, ancak `Uygun` kategorisine geçirilmedi.",
        "- **Doğrulanmamış sonuç iddiası:** `quality_agent.checks.unverified_outcome_claim.status == fail` "
        "tespit olarak sayıldı. Workflow hatası olan kayıtlar korumacı biçimde 'iddiasız' sayılmadı.",
        "- **Uçtan uca süre:** Dört veri kovasının her birinden sabit tohumla beşer kayıt seçildi. Kayıtlar "
        "paralel değil, sırayla çalıştırıldı. Duvar saati document, extraction, legal, missing-field, summary, "
        "routing, writing, quality ve workflow'un son human-review karar adımını kapsar.",
        "",
        "## Ölçüm bütünlüğü",
        "",
        f"- 120 kayıtlık kalite koşusu: {result['quality_run']['workflow_errors']} workflow hatası, "
        f"{result['quality_run']['node_failure_records']} düğüm-hatası içeren kayıt.",
        f"- 20 kayıtlık süre koşusu: {runtime['successful_runs']} başarılı, {runtime['failed_runs']} başarısız.",
        f"- Süre örneklemi: `{', '.join(runtime['sample_ids'])}`.",
        f"- Ham ve kayıt-bazlı sonuçlar: `{output_json.as_posix()}`.",
        "",
        "## Yeniden üretme",
        "",
        "```powershell",
        ".venv\\Scripts\\python.exe scripts\\evaluation\\evaluate_decision_boundary_agents.py --workers 4",
        ".venv\\Scripts\\python.exe scripts\\evaluation\\evaluate_section9_metrics.py",
        "```",
        "",
        "Script yolu: `scripts/evaluation/evaluate_section9_metrics.py`. Mevcut üç metriğin scripti: "
        "`scripts/evaluation/evaluate_decision_boundary_agents.py`.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--git-object", default=LOCKED_DATASET_OBJECT)
    parser.add_argument("--existing-metrics", type=Path, default=DEFAULT_EXISTING_METRICS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timing-size", type=int, default=20)
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Mevcut JSON satırlarından türetilen taslak metriklerini ve Markdown raporu yenile.",
    )
    args = parser.parse_args()

    output = ROOT / args.output
    report = ROOT / args.report
    if args.report_only:
        aggregated = json.loads(output.read_text(encoding="utf-8"))
        aggregated["metrics"]["writing_quality"] = _aggregate_writing(
            aggregated["rows"], aggregated["dataset"]["total_records"]
        )
        output.write_text(json.dumps(aggregated, ensure_ascii=False, indent=2), encoding="utf-8")
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(_render_report(aggregated, args.output), encoding="utf-8")
        print(json.dumps(aggregated["metrics"], ensure_ascii=False, indent=2), flush=True)
        print(f"JSON: {output}", flush=True)
        print(f"Rapor: {report}", flush=True)
        return 0

    rows, source, sha256 = _load_dataset(args.dataset, args.git_object)
    existing = json.loads((ROOT / args.existing_metrics).read_text(encoding="utf-8"))

    print(f"Kalite koşusu başlıyor: {len(rows)} kayıt, {args.workers} worker", flush=True)
    quality_rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_map = {executor.submit(_run_quality_row, row): row for row in rows}
        for index, future in enumerate(as_completed(future_map), start=1):
            result = future.result()
            quality_rows.append(result)
            print(f"[{index:03d}/{len(rows)}] {result['id']}: {result['status']}", flush=True)
    quality_rows.sort(key=lambda item: item["id"])

    sample = _timing_sample(rows, args.timing_size)
    timing_rows = []
    print(f"Sıralı uçtan uca süre koşusu başlıyor: {len(sample)} kayıt", flush=True)
    for index, row in enumerate(sample, start=1):
        result = _run_timing_row(row)
        timing_rows.append(result)
        print(
            f"[{index:02d}/{len(sample)}] {result['id']}: "
            f"{result['seconds']:.3f} sn ({result['status']})",
            flush=True,
        )

    aggregated = _aggregate(rows, quality_rows, timing_rows, source, sha256, existing)
    aggregated["quality_run"]["workers"] = args.workers

    output.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(aggregated, ensure_ascii=False, indent=2), encoding="utf-8")
    report.write_text(_render_report(aggregated, args.output), encoding="utf-8")

    print(json.dumps(aggregated["metrics"], ensure_ascii=False, indent=2), flush=True)
    print(f"JSON: {output}", flush=True)
    print(f"Rapor: {report}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
