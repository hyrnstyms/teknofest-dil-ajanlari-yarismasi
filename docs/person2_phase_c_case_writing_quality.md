# Phase P2-C: Case-Aware Writing & Quality Guard

## CaseWritingService Architecture
A new thin service `CaseWritingService` has been introduced at `backend/app/intelligence/case_writing.py` to handle Case lifecycle writing requirements. It acts as an orchestrator for writing tasks, translating safe inputs into a context suitable for the existing `WritingAgent`.

### Why reuse `WritingAgent`?
The existing `WritingAgent` already implements comprehensive format validation (e.g. `validate_format` based on official writing guidelines), dynamic RAG retrieval (for style and templates), context injection (for missing fields and summaries), and LLM generation logic. By wrapping it in `CaseWritingService`, we avoid massive duplication of RAG mechanics, template rendering, and prompt engineering, while injecting precise Case Engine state rules.

## DepartmentAction Guard
The `OFFICIAL_RESPONSE` type now includes a strict deterministic lifecycle guard before any LLM is queried.
- It requires `department_action` to be provided.
- The `department_action` MUST be `verified=True`.
- If a `case_id` is supplied, the `department_action.case_id` MUST match.
If any condition fails, the service returns immediately with:
```json
{
  "allowed": false,
  "draft": null,
  "reason": "verified_department_action_required"
}
```

## Draft Type Mapping
The Case-aware contracts introduce canonical draft types. The `CaseWritingService` maps these back to the legacy internal enums to ensure the existing `WritingAgent` interprets them correctly:
- `MISSING_INFORMATION_REQUEST` -> `eksik_bilgi_talebi`
- `INTERIM_INFORMATION` -> `bilgilendirme_metni`
- `OFFICIAL_RESPONSE` -> `cevap_yazisi`
- `INTERNAL_MEMO` -> `diger`
- `FORWARDING_COVER_LETTER` -> `ust_yazi`

## Grounding Rules & Unsupported Completions
When generating an `OFFICIAL_RESPONSE`, the `DepartmentAction`'s `result` and `decision` fields are deterministically concatenated to form a verified baseline.
The `QualityAgent` has been extended to check for unsupported completion claims. If the LLM generates a phrase like "onarım tamamlandı" or "işlem tamamlanmıştır", the system verifies if these words are explicitly supported by the provided `DepartmentAction`. If they are not (e.g., the action only states "bakım programına alındı"), the `QualityAgent` marks it as `fail` (`unverified_outcome_claim`), effectively blocking it.

## QualityAgent Extension
The `QualityAgent` now includes Case lifecycle evaluation logic.
- It ensures that an `OFFICIAL_RESPONSE` is fully backed by a verified `DepartmentAction`.
- It executes the `unverified_outcome_claim` validation comparing the generated body to the `DepartmentAction`.
- It validates the drafted document's format if the format validator is available.
- It ensures the recipient of the draft matches the original `originator` (`person_name`). Any mismatch is flagged as a warning.

## Compatibility & Integration
- The Case Engine (Person 1) must use `CaseWritingService.draft_official_response` to produce official responses.
- The Case Engine must provide a verified `DepartmentActionContext`.
- No Case state or database mutability is performed in `CaseWritingService`; it is a pure state evaluation.
- All existing Phase A (Orchestration) tests, Copilot Stream tests, and Quality tests continue to PASS unmodified.

## Known Limitations
- The `recipient` matching logic uses exact string equality. In cases of slight normalization differences (e.g., lowercase vs uppercase), it might yield false positive warnings. This acts as a safe fallback for human review rather than an error.
- The format validator relies on the exact `draft_type` mappings.
