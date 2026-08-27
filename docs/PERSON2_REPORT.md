# PERSON 2 REPORT

Base commit: `08cbcf6` (`feat: ground case responses in verified department actions`)  
Frozen contract baseline: `8898fd46836ef2ad1a4b793a4bcd4184d4cfbc8d`  
Branch: `feature/agent-orchestration`

## Old vs new orchestration

The legacy `KamuaiWorkflow` remains the Analysis-producing workflow. The new
`CaseAwareOrchestrator` is an additive, persistence-free service layer that
accepts a `CaseIntelligenceContext`, evaluates missing information, clarification,
routing, operational priority and legal deadline previews, and then yields to the
Case Engine for every durable decision.

The Case-aware flow never assigns a department, changes `workflow_status`, creates
a citizen token, records a DepartmentAction, or persists a draft. Initial intake
cannot produce an `OFFICIAL_RESPONSE`.

## Compatibility strategy

- Existing Analysis models, LangGraph workflow, agents and API mounting remain
  unchanged.
- Person 2 contracts use Pydantic DTOs and dictionaries; they do not import Person
  1 ORM models or database sessions.
- Canonical draft types are adapted to legacy WritingAgent draft type names.
- The preview router remains standalone and is not mounted in `main.py`.
- The default official-response path is deterministic and grounded directly in a
  verified DepartmentAction. A `WritingAgent` may be explicitly injected for a
  stylistic rewrite; quality checks remain mandatory.

## Case orchestrator

`CaseAwareOrchestrator.evaluate_first_stage` returns one of two human wait points:

- blocking minimum information -> `WAIT_FOR_HUMAN_CITIZEN_INFO` with a
  `MISSING_INFORMATION_REQUEST` preview;
- sufficient intake -> `WAIT_FOR_HUMAN_ROUTING_CONFIRMATION` with an interim
  information preview and a routing recommendation.

Returned statuses are recommendations to Person 1's Case Engine. The result
explicitly has `assigns_case=false` and `commits_workflow_status=false`.

## Clarification contract

`ClarificationAgent.preview` returns the frozen flat clarification DTO. It asks
for only the first minimum blocking field. Generic permit requests produce one
single-choice `permit_type` question with institution-allowed options. Preview
generation has no send, token, event, status or persistence behavior.

## Resume contract

`resume_after_citizen_info` accepts structured `CitizenResponse` evidence. Only
requested/allowlisted fields are merged. Contradictions do not overwrite verified
document facts; they become uncertain evidence for human review. Resume reruns
only missing-field, clarification and routing decisions, not document/extraction
analysis, and does not produce a DepartmentAction or official response.

## Routing contract

Routing output is an AI recommendation. It preserves the raw similarity score as
a diagnostic value, sets `requires_human_review=true`, and sets `assigned=false`.
It does not translate a score such as `0.82` into an accuracy percentage and does
not write assignment state.

## Case writing rules

- Intake produces only `MISSING_INFORMATION_REQUEST` or `INTERIM_INFORMATION`.
- `OFFICIAL_RESPONSE` requires a verified DepartmentAction belonging to the same
  Case.
- The deterministic fallback body contains only the action's `result` and
  `decision`.
- All drafts require human approval and no draft is persisted by Person 2.

## DepartmentAction grounding

Missing, unverified, Case-unidentified, or other-Case DepartmentAction input is
rejected with `verified_department_action_required`. A verified action must also
contain a non-empty `result` or `decision`. Routing and initial Analysis content
are not accepted as substitutes for human-supplied institutional truth.

## Quality guard

The Case-aware quality guard rejects unsupported completion claims. For example,
an action stating “Yol deformasyonu tespit edildi; bakım programına alındı” may
support a maintenance-program statement but cannot support “onarım tamamlandı”.
Recipient mismatches, unsupported legal claims and fabricated official references
are also surfaced as failures or human-review warnings. No hidden chain-of-thought
or private reasoning fields are returned.

## Deadline contract

`LegalDeadlineService` is deterministic and has no LLM dependency.

- It accepts structured `verified_legal_evidence`, or source-linked `evidence`
  that has already passed `LegalAgent`'s Python validation. Raw strings,
  `retrieved_sources`, unresolved source references and `verified=false` evidence
  cannot establish a deadline.
- Structured `deadline_days` and `deadline_type` are preferred. Otherwise a small
  deterministic Turkish duration parser is used only on verified evidence.
- `CALENDAR_DAY` computes `due_at = received_at + deadline_days` in Python.
- There is no verified business-day/holiday calendar policy, so `BUSINESS_DAY`
  preserves the applicable duration but returns `due_at=null`,
  `remaining_days=null`, and `risk_level=UNKNOWN`.
- Missing, invalid or timezone-naive `received_at` never falls back to
  `created_at`; the due date and risk remain unknown.
- Risk values are limited to `NORMAL`, `APPROACHING`, `CRITICAL`, `OVERDUE`, and
  `UNKNOWN`. Operational priority remains a separate result key and never changes
  legal deadline risk.

## AI preview contracts

Standalone router: `backend/app/intelligence/preview_router.py`

- `POST /api/cases/{id}/ai/clarification-preview`
- `POST /api/cases/{id}/ai/deadline-evaluation`
- `POST /api/cases/{id}/ai/official-response-preview`

The router accepts a Person 1-supplied Case snapshot because it has no repository
or database access. All successful responses are previews and carry
`persisted=false`. Official-response guard failures use HTTP 409 with the frozen
error envelope. Invalid inner Case DTO input uses HTTP 422 with
`validation_error`. Authorization, Case lookup and outer request validation remain
integration responsibilities.

## Tests

Focused Person 2 suite after final changes:

```text
46 passed
```

Covered scenarios include yol bakım/onarım grounding, ambiguous ruhsat
clarification, verified and unknown deadlines, structured durations, deterministic
calendar arithmetic, unsupported business-day arithmetic, all DepartmentAction
negative cases, non-mutating previews, no assignment, no raw-score accuracy
conversion, no private reasoning output and no DB imports.

## Regression

- Required agent/workflow/writing/quality/routing selection: `128 passed`.
- Existing `test_chat_agent.py`: `135 passed`.
- Full backend initially: `507 passed, 1 skipped, 1 failed, 12 errors`. All 12
  errors were pytest `tmp_path` access failures under the user Temp directory.
- Final re-run with a workspace-local `--basetemp`, excluding the independently
  reproduced Copilot failure: `525 passed, 1 skipped, 1 deselected`.
- The deselected test is
  `test_copilot_stream.py::test_copilot_legal_rag_and_no_evidence`. It classifies
  “3071 kapsamında cevap süresi nedir?” as `out_of_domain`. It reproduces in
  isolation and no `chat_agent.py` or `main.py` changes exist in Person 2 scope.
- `git diff --check` passes.

## Integration requirements

Person 1 must wire:

- Case objects -> `CaseIntelligenceContext` DTOs;
- confirmed structured citizen responses -> `resume_after_citizen_info`;
- the same Case's verified DepartmentAction -> `CaseWritingService`;
- explicit `received_at` and verified legal evidence -> `LegalDeadlineService`;
- standalone `preview_router.router` mounting under the application, if these
  preview endpoints are enabled;
- authentication, authorization, Case lookup, persistence, optimistic locking,
  events and all confirmed workflow transitions outside Person 2 services.

Suggested mount owned by the integration branch:

```python
from backend.app.intelligence.preview_router import router as ai_preview_router

app.include_router(ai_preview_router)
```

## Known risks

- No authoritative Turkish business-day/holiday calendar source is configured;
  business-day due dates intentionally remain unknown.
- The preview router trusts Person 1 to supply an authorized, institution-scoped
  Case snapshot and verified legal evidence provenance.
- An injected generative WritingAgent can still produce wording beyond the
  deterministic baseline; the quality guard and human approval must remain in the
  integration path.
- One pre-existing/out-of-scope Copilot legal routing regression remains, as
  documented above. The task explicitly excludes `chat_agent.py` changes.

## Merge-ready

YES — Person 2 focused tests and the required legacy agent/workflow regressions
pass. The unrelated Copilot regression is isolated and recorded for its owner.
