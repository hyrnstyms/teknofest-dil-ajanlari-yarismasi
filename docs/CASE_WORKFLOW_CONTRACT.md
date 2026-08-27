# EVRAG Case Workflow Contract

**Status:** FROZEN — Wave 0  
**Baseline:** `8898fd46836ef2ad1a4b793a4bcd4184d4cfbc8d` (`main`)  
**Scope:** Case lifecycle, demo authentication, authorization, assignments,
department actions, drafts, clarification, deadlines, public tracking and AI
preview integration.  
**Normative language:** MUST, MUST NOT, SHOULD and MAY are binding in the usual
RFC sense. Enum values and JSON field names in this document are canonical.

## 1. Product and bounded context

EVRAG is an AI-assisted public-sector workflow orchestration and decision-support
layer. It may sit above or beside EBYS; it is not an EBYS replacement, a generic
chatbot or an autonomous public decision maker.

The existing `Analysis` is the immutable-by-identity AI work product and retains
its current state/status vocabulary. A new `Case` is the institutional lifecycle,
ownership and authorization boundary. One Case MAY reference zero or one Analysis
while intake is pending and MUST reference one Analysis after analysis completes.
An Analysis MUST NOT be renamed to or silently migrated into a Case.

```text
Ingress -> Case -> Analysis/workflow -> initial human review
       -> confirmed assignment -> department processing
       -> human DepartmentAction -> grounded draft -> human approval
       -> completed -> closed -> public status projection
```

## 2. Compatibility with current main

### 2.1 Existing and protected

| Current capability | Contract decision |
|---|---|
| `Analysis` ORM/state JSON and existing statuses | Preserve without renaming; add `Case.analysis_id` as a nullable reference |
| `ReviewEvent` | Preserve as analysis review history; Case events are a separate append-only stream |
| Document, Extraction, Legal, MissingField, Summary, Routing, Writing and Quality agents | Extend through adapters/context; do not rewrite |
| LangGraph document workflow | Continues to produce Analysis; Case orchestration wraps it |
| Human Review approve/edit/reject API | Remains backward-compatible for Analysis; new Case actions do not reuse these status names |
| DOCX renderer | Reuse; Case download requires an approved Case draft |
| Qdrant/BGE-M3 retrievers | Reuse; no Case data is indexed by default |
| PostgreSQL | Extend with Case-domain tables/migrations |
| Institution YAML profiles | Sole institution/department directory source of truth |
| Copilot | Add case-aware read/preview/action proposals; LLM never writes persistence directly |

Current `department` and routing fields inside Analysis are recommendations or
legacy presentation fields. They MUST NOT be treated as Case ownership. Current
Analysis `human_review.status` remains independent from `Case.workflow_status`.

### 2.2 New domain layer

The Case layer owns:

- institutional lifecycle and optimistic concurrency;
- originator versus current owner;
- current assignment and assignment history;
- role/institution/department authorization;
- citizen clarification requests and safe public projection;
- human-supplied DepartmentAction;
- Case drafts and approval state;
- verified deadlines;
- append-only Case timeline events.

## 3. Identity, roles and authorization

### 3.1 Canonical internal roles

```text
EVRAK_KAYIT
BIRIM_PERSONELI
```

- `EVRAK_KAYIT`: intake, preliminary review, clarification confirmation and
  routing confirmation for its institution.
- `BIRIM_PERSONELI`: processes Cases assigned to its own configured department.
  This role is not synonymous with `fen_isleri`.
- Citizens are not internal users and never receive an internal access token.

Frozen demo principals:

| user_key | name | role | institution_id | department_code |
|---|---|---|---|---|
| `ayse_kaya` | Ayşe Kaya | `EVRAK_KAYIT` | `belediye` | `yazi_isleri` |
| `mehmet_demir` | Mehmet Demir | `BIRIM_PERSONELI` | `belediye` | `fen_isleri` |

### 3.2 Backend authority

`role`, `institution_id`, `department_code` and user ID MUST be resolved from a
signed/opaque demo token. Values supplied in request bodies or query parameters
MUST NOT override the authenticated principal. Every internal Case query MUST be
institution-scoped before rows are returned.

Department codes MUST be validated against the selected institution's current
YAML profile. A database cache MAY be derived from the profile, but MUST NOT become
an independently edited directory.

### 3.3 Authorization matrix

| Action | EVRAK_KAYIT | BIRIM_PERSONELI |
|---|---:|---:|
| View institution intake Cases | Yes | No |
| View Case assigned to own department | Yes | Yes |
| Confirm route | Yes | No |
| Confirm citizen information request before routing | Yes | No |
| Start Case in department | No | Own department |
| Record DepartmentAction | No | Own department |
| Create/approve department response draft | No | Own department |
| Complete Case | No | Own department |
| Close completed Case | Yes | No |

Cross-institution access MUST return `404 case_not_found`, not reveal existence
through `403`. Same-institution but role/department-forbidden actions return
`403 action_forbidden`.

## 4. Canonical Case model

```json
{
  "id": "case_uuid",
  "tracking_code": "EVR-2026-000001",
  "analysis_id": "analysis_uuid_or_null",
  "institution_id": "belediye",
  "source_type": "VATANDAS",
  "source_channel": "EBYS",
  "originator_type": "VATANDAS",
  "originator_name": "Ali Yılmaz",
  "originator_email": null,
  "originator_phone": null,
  "current_department_code": "yazi_isleri",
  "assigned_user_id": null,
  "workflow_status": "RECEIVED",
  "priority": null,
  "citizen_token": null,
  "received_at": "2026-08-27T09:30:00+03:00",
  "created_at": "2026-08-27T09:31:00+03:00",
  "updated_at": "2026-08-27T09:31:00+03:00",
  "closed_at": null,
  "version": 1
}
```

Canonical enums:

```text
source_type    = VATANDAS | DIS_KURUM | KURUM_ICI
source_channel = WEB_FORM | FIZIKI_EVRAK | EPOSTA | KEP | EBYS | KURUM_ICI
originator_type = VATANDAS | DIS_KURUM | KURUM_ICI
```

Invariants:

1. `tracking_code` is unique, stable and non-secret.
2. `citizen_token` is secret, revocable and MUST be stored hashed where practical;
   it is never returned by internal list endpoints or logged.
3. `originator_*` identifies where the Case came from and never changes during
   routing. `current_department_code` identifies present ownership.
4. `received_at` is explicitly captured process/legal receipt time. `created_at`
   MUST NOT silently substitute for it in deadline calculation.
5. `institution_id` is immutable after creation.
6. `version` increments on every state-changing transaction and is used for
   optimistic concurrency.
7. Personally identifying contact fields MUST NOT appear in public projections.

## 5. Workflow state machine

Canonical durable statuses, and no others:

```text
RECEIVED
ANALYZING
WAITING_INITIAL_REVIEW
WAITING_CITIZEN_INFO
READY_TO_ROUTE
IN_DEPARTMENT
IN_PROGRESS
RESPONSE_DRAFTED
WAITING_FINAL_APPROVAL
COMPLETED
CLOSED
```

`ROUTED` MUST NOT be introduced as a durable status. Confirmed routing is one
atomic transaction: append `CASE_ROUTED`, create/activate `CaseAssignment`, update
`current_department_code`, set `IN_DEPARTMENT`, increment version.

Allowed transitions:

| From | To | Trigger/event |
|---|---|---|
| `RECEIVED` | `ANALYZING` | analysis started / `ANALYSIS_STARTED` |
| `ANALYZING` | `WAITING_INITIAL_REVIEW` | analysis completed / `ANALYSIS_COMPLETED` |
| `ANALYZING` | `WAITING_CITIZEN_INFO` | blocking clarification confirmed / `CITIZEN_INFO_REQUESTED` |
| `WAITING_CITIZEN_INFO` | `ANALYZING` | supplied data requires re-analysis / `CITIZEN_INFO_COMPLETED` |
| `WAITING_CITIZEN_INFO` | `READY_TO_ROUTE` | supplied data is sufficient / `CITIZEN_INFO_COMPLETED` |
| `WAITING_INITIAL_REVIEW` | `WAITING_CITIZEN_INFO` | reviewer confirms clarification request |
| `WAITING_INITIAL_REVIEW` | `READY_TO_ROUTE` | reviewer accepts analysis/routing readiness |
| `READY_TO_ROUTE` | `IN_DEPARTMENT` | human confirms route / `CASE_ROUTED` |
| `IN_DEPARTMENT` | `IN_PROGRESS` | own-department user starts / `CASE_STARTED` |
| `IN_PROGRESS` | `RESPONSE_DRAFTED` | valid draft saved / `DRAFT_SAVED` |
| `RESPONSE_DRAFTED` | `WAITING_FINAL_APPROVAL` | draft submitted / `DRAFT_SUBMITTED` |
| `WAITING_FINAL_APPROVAL` | `RESPONSE_DRAFTED` | draft edited/revision requested / `DRAFT_REVISION_REQUESTED` |
| `WAITING_FINAL_APPROVAL` | `COMPLETED` | approved result finalized / `CASE_COMPLETED` |
| `COMPLETED` | `CLOSED` | registry closure / `CASE_CLOSED` |

`CLOSED` is terminal. Invalid transitions return HTTP 409 with
`invalid_case_transition`. Events such as comments, failed authorization-safe
operations, preview generation and notification attempts MAY be recorded without
changing status. State and event writes MUST share one database transaction.

## 6. Assignments and timeline events

### 6.1 CaseAssignment

```json
{
  "id": "assignment_uuid",
  "case_id": "case_uuid",
  "department_code": "fen_isleri",
  "assigned_user_id": null,
  "assigned_by_user_id": "ayse_uuid",
  "assigned_at": "2026-08-27T10:00:00+03:00",
  "ended_at": null,
  "reason": "Yol bakım talebi",
  "routing_snapshot": {}
}
```

Only one active assignment (`ended_at=null`) is allowed. The routing snapshot
preserves the AI recommendation used for human confirmation; it is evidence, not
authority.

### 6.2 CaseEvent

Every event contains `id`, `case_id`, `event_type`, `actor_type`, optional
`actor_user_id`, `created_at`, `from_status`, `to_status`, and a JSON `payload`.
Events are append-only and ordered by `(created_at, id)`. Public responses map
internal events to a strict allowlist of neutral public labels; payloads are never
exposed verbatim.

## 7. AI contracts

### 7.1 Routing recommendation

```json
{
  "recommended_unit": "Fen İşleri Müdürlüğü",
  "recommended_department_code": "fen_isleri",
  "score": 0.82,
  "reason": "Yol bakım ve onarım talebi.",
  "evidence": [],
  "alternatives": [],
  "requires_human_review": true
}
```

The normal UI says “AI Önerisi”, “Gerekçe” and “Alternatifler”. It MUST NOT
render `0.82` as “%82 accuracy”. Diagnostic views MAY show the raw score.
Recommendation never changes assignment without a confirmed Case Engine action.

### 7.2 Clarification preview

```json
{
  "needs_clarification": true,
  "blocking": true,
  "requested_fields": ["location"],
  "question_type": "free_text",
  "question": "Bakım talep edilen yolun açık adresini belirtir misiniz?",
  "options": [],
  "resume_target": "missing_field"
}
```

Only minimum information necessary to proceed may be requested. A preview does
not send a request or change status. Human confirmation creates the request.

### 7.3 Deadline evaluation

```json
{
  "applicable": true,
  "deadline_days": 30,
  "deadline_type": "CALENDAR_DAY",
  "legal_basis": {
    "verified": true,
    "law_number": "3071",
    "article": "7",
    "citation": "3071 sayılı Kanun, Madde 7"
  },
  "received_at": "2026-08-27T09:30:00+03:00",
  "due_at": "2026-09-26T09:30:00+03:00",
  "remaining_days": 12,
  "risk_level": "NORMAL"
}
```

`risk_level = NORMAL | APPROACHING | CRITICAL | OVERDUE | UNKNOWN`.
`due_at` MUST be null and risk MUST be `UNKNOWN` if verified legal duration or
reliable `received_at` is absent. Calendar/business-day computation policy must be
explicit in `deadline_type`; an LLM must not perform authoritative date arithmetic.

### 7.4 DepartmentAction

DepartmentAction is human-supplied institutional truth:

```json
{
  "id": "action_uuid",
  "case_id": "case_uuid",
  "action_type": "SAHA_INCELEMESI",
  "result": "Yol deformasyonu tespit edildi.",
  "decision": "Bakım programına alındı.",
  "planned_date": "2026-08-29",
  "notes": "",
  "verified": true,
  "recorded_by_user_id": "mehmet_uuid",
  "created_at": "2026-08-27T11:00:00+03:00"
}
```

Only an authorized human/API action can create it. AI MAY summarize it but MUST
NOT synthesize or mark a real-world operation as completed.

### 7.5 Draft

```text
draft_type = MISSING_INFORMATION_REQUEST | INTERIM_INFORMATION |
             OFFICIAL_RESPONSE | INTERNAL_MEMO | FORWARDING_COVER_LETTER
draft_status = DRAFT | EDITED | APPROVED | SENT | CANCELLED
```

An `OFFICIAL_RESPONSE` MUST cite at least one verified DepartmentAction belonging
to the same Case. Initial Analysis may only create appropriate non-final types.
Approval records approver and time. Draft text edits create a new revision or
preserve the prior content in audit history. DOCX/export uses the approved revision.

## 8. Read versus write actions

Reads require no confirmation: summary, missing fields, legal evidence, routing
explanation, Case status/timeline/inbox and previews.

State-changing actions require an explicit pending action and confirmation:

```json
{
  "type": "ROUTE_CASE",
  "case_id": "case_uuid",
  "payload": {"department_code": "fen_isleri"},
  "confirmation_required": true,
  "confirmation_text": "Dosya Fen İşleri Müdürlüğüne yönlendirilecek. Onaylıyor musunuz?"
}
```

Canonical action types include `ROUTE_CASE`, `START_CASE`,
`REQUEST_CITIZEN_INFO`, `SAVE_DRAFT`, `APPROVE_DRAFT` and `FINALIZE_CASE`.
The UI or Copilot confirms through a deterministic API call. The LLM only proposes
the payload; it never updates the database or manufactures authorization context.

## 9. Canonical API

All internal endpoints require `Authorization: Bearer <token>`. JSON responses use
ISO-8601 timestamps with offsets. State-changing requests SHOULD carry
`expected_version`; mismatch returns `409 version_conflict`. An `Idempotency-Key`
header SHOULD be supported for create/action POSTs.

### 9.1 Authentication

#### `POST /api/auth/demo-login`

Request: `{"user_key":"ayse_kaya"}`

Response 200:

```json
{
  "access_token": "opaque_or_signed_token",
  "token_type": "bearer",
  "user": {
    "id": "ayse_uuid",
    "name": "Ayşe Kaya",
    "role": "EVRAK_KAYIT",
    "institution_id": "belediye",
    "department_code": "yazi_isleri"
  }
}
```

#### `GET /api/auth/me`

Returns the same `user` object resolved exclusively from the token.

### 9.2 Case reads

#### `GET /api/cases/inbox`

Optional filters: `status`, `limit`, `cursor`. Scope is backend-derived:
EVRAK_KAYIT receives its institution's registry queue; BIRIM_PERSONELI receives
only active Cases assigned to its own department. Response:

```json
{"items": [], "next_cursor": null}
```

#### `GET /api/cases/{case_id}`

Returns Case, safe Analysis projection, active assignment, actions, drafts,
deadline and internal timeline according to authorization.

### 9.3 Case actions

| Endpoint | Request essentials | Success/transition |
|---|---|---|
| `POST /api/cases/{id}/route` | `department_code`, `expected_version`, `confirmed:true` | assignment + `IN_DEPARTMENT` |
| `POST /api/cases/{id}/start` | `expected_version`, `confirmed:true` | `IN_PROGRESS` |
| `POST /api/cases/{id}/department-action` | action fields, `expected_version`, `confirmed:true` | action created; status unchanged |
| `POST /api/cases/{id}/citizen-requests` | clarification fields, `expected_version`, `confirmed:true` | `WAITING_CITIZEN_INFO` |
| `POST /api/cases/{id}/drafts` | `draft_type`, content or approved preview, `expected_version`, `confirmed:true` | draft saved; applicable draft transition |
| `POST /api/cases/{id}/drafts/{draft_id}/approve` | `expected_version`, `confirmed:true` | draft `APPROVED`; Case may become `COMPLETED` only through complete endpoint |
| `POST /api/cases/{id}/complete` | approved draft ID, `expected_version`, `confirmed:true` | `COMPLETED` |
| `POST /api/cases/{id}/close` | `expected_version`, `confirmed:true` | `CLOSED` |

No endpoint accepts role, institution or acting department in its request body.

### 9.4 Public endpoints

#### `GET /api/public/cases/{tracking_code}?token=...`

Returns only tracking code, public status label, received/updated timestamps,
safe timeline entries and an outstanding clarification schema. It MUST NOT return
Analysis internals, legal/routing debug, scores, prompts, internal notes, user IDs,
assignments, department actions or other contact data.

#### `POST /api/public/cases/{tracking_code}/complete-info?token=...`

Accepts only fields allowlisted by the active clarification request. It appends an
event and marks the request supplied; Case Engine selects `ANALYZING` or
`READY_TO_ROUTE`. Token and tracking code must both match.

### 9.5 Institution directory

#### `GET /api/institutions/{institution_id}/departments`

Returns a read-only projection derived live/cached from the YAML profile:

```json
{"institution_id":"belediye","departments":[{"code":"fen_isleri","name":"Fen İşleri Müdürlüğü"}]}
```

### 9.6 AI preview/intelligence endpoints

These are side-effect-free service contracts and MAY be mounted under an
integration router:

```text
POST /api/cases/{id}/ai/clarification-preview
POST /api/cases/{id}/ai/deadline-evaluation
POST /api/cases/{id}/ai/official-response-preview
```

They return the schemas in section 7 and MUST NOT update Case, Draft,
DepartmentAction or assignment tables. Official-response preview returns
`409 verified_department_action_required` without a verified action.

### 9.7 Error envelope

```json
{
  "detail": {
    "code": "invalid_case_transition",
    "message": "İşlem mevcut dosya durumunda gerçekleştirilemez.",
    "context": {"current_status":"READY_TO_ROUTE"}
  }
}
```

Canonical codes: `authentication_required`, `invalid_token`, `case_not_found`,
`action_forbidden`, `invalid_department`, `invalid_case_transition`,
`confirmation_required`, `version_conflict`, `validation_error`,
`verified_department_action_required`, `approved_draft_required`,
`citizen_token_invalid`, `clarification_not_active`.

## 10. Frontend contract

Person 3 owns general app routing, login, inbox, Case workspace and citizen UI.
Person 4 owns Chat/Copilot components. Both consume the same authenticated user
and selected Case from shared application state; neither derives authorization
from locally selected role/department.

Required views:

- demo login/persona selection;
- role-scoped inbox;
- Case workspace with Analysis, current owner, timeline and status;
- EVRAK_KAYIT route/clarification confirmation;
- BIRIM_PERSONELI start, DepartmentAction and draft/approval flow;
- public tracking and minimum-information form;
- pending-action confirmation UI for every mutation.

UI invariants:

1. Originator and current department are labeled separately.
2. AI output is labeled recommendation/preview, not institutional fact.
3. Raw routing scores are absent from normal workflow UI.
4. Buttons are enabled from server-provided permissions/current status, then the
   backend rechecks authorization.
5. Refresh restores Case from the API, not an optimistic local-only state.
6. Public UI renders only the public projection.

## 11. File ownership and integration boundaries

| Owner | Scope | Likely files | Must not own |
|---|---|---|---|
| Person 1 | DB models/migrations, repositories, auth, Case Engine and Case APIs | `backend/app/db/*`, new `backend/app/cases/*`, auth/case routers, tests | Agent prompts/Chat UI |
| Person 2 | Case-aware agent adapters, intelligence previews, deadline engine | `backend/app/agents/*` adapters, `backend/app/graph/*` adapter, new intelligence router/tests | Case persistence writes, general `main.py` |
| Person 3 | Login, role inbox, Case workspace, public citizen flow | general frontend pages/routes/services/types/styles | Chat components, backend auth decisions |
| Person 4 | Case-aware Copilot backend and chat frontend/process intelligence | `chat_agent.py`, Copilot router, `frontend/src/components/chat/*`, chat tests | General App routing, Case repository |

During feature development `backend/app/main.py` belongs to Person 1 and general
frontend App/router belongs to Person 3. Person 2/4 provide standalone routers or
service functions; mounts are added only during integration/final-e2e. Shared API
types follow this document; developers MUST NOT create divergent enums.

## 12. Priorities and acceptance gates

### P0

- Case engine and transition validation
- two backend-authoritative roles and demo auth
- institution/department inbox isolation
- confirmed routing and assignment
- human DepartmentAction
- case-aware Copilot reads/proposals
- confirmation for every mutation
- official response grounded in verified DepartmentAction
- append-only timeline

P0 acceptance requires cross-institution and cross-department negative tests,
transition tests, LLM-no-write tests and the complete Scenario 1 flow.

### P1

- active minimum clarification flow
- citizen information completion
- verified legal deadline
- public citizen tracking portal

### P2

- QR presentation polish
- notification history UI
- process intelligence dashboard
- ROI and human-feedback analytics

No branch spends significant effort on P2 while its P0 tests fail.

## 13. Frozen E2E scenarios

### Scenario 1 — Yol Onarım Talebi

1. Ayşe logs in as EVRAK_KAYIT and sees a received Belediye Case.
2. Analysis runs; routing recommends `fen_isleri` with reason/evidence.
3. Ayşe explicitly confirms `ROUTE_CASE`.
4. One assignment is created; Case becomes `IN_DEPARTMENT`.
5. Mehmet logs in as BIRIM_PERSONELI and sees it in the Fen İşleri inbox.
6. Mehmet starts the Case, records a real verified DepartmentAction.
7. AI previews an OFFICIAL_RESPONSE grounded only in that action/evidence.
8. Mehmet saves, reviews and approves the draft, then completes the Case.
9. Ayşe closes it. The citizen public projection shows the safe lifecycle.

Acceptance additionally verifies that Ayşe cannot record the department action,
Mehmet cannot route/close, another department cannot view the Case, and an
OFFICIAL_RESPONSE cannot be generated before DepartmentAction.

### Scenario 2 — Ambiguous Ruhsat

1. Analysis cannot safely determine permit type.
2. AI returns one minimum blocking clarification preview.
3. Ayşe confirms the citizen request; status becomes `WAITING_CITIZEN_INFO`.
4. Citizen supplies only allowlisted information using tracking code + token.
5. Workflow resumes; status moves through analysis to `READY_TO_ROUTE`.
6. AI provides a new recommendation; Ayşe confirms the route.

Acceptance verifies that preview alone does not mutate state and the public API
cannot expose internal reasoning or accept unrequested fields.

## 14. Compatibility risks

| Risk | Required mitigation |
|---|---|
| Conflating Analysis review status with Case status | Separate enums, models, endpoints and UI labels |
| Treating Analysis routing output as assignment | Only Case Engine route transaction changes ownership |
| Duplicate unit directory | Validate/serve codes from institution YAML only |
| Frontend-forged role/department | Resolve all scope from token and enforce in repository query |
| LLM writes or fabricated DepartmentAction | Preview/action split; deterministic service performs confirmed write |
| Final response before real work | Verified same-Case DepartmentAction is mandatory |
| Originator overwritten during routing | Immutable originator fields; separate current department |
| Deadline hallucination | Verified evidence + explicit received_at + deterministic date engine |
| Lost concurrent updates | Case version/optimistic locking and transactional events |
| Public information leakage | Dedicated public DTO/event allowlist, token hash and negative tests |
| Breaking existing Analysis clients | Keep existing routes/statuses and add new `/api/cases` surface |
| `main.py` merge conflicts | Standalone routers; integration owner mounts once |

## 15. Questions requiring human decision

These are deliberately not encoded as conflicting implementation choices. Product
owners must decide them before their dependent P1/P2 work is merged:

1. Demo token mechanism and expiry: signed JWT versus server-side opaque session.
   Either must preserve the response contract and backend authority.
2. Citizen token delivery, expiry, rotation and recovery policy.
3. Whether `COMPLETED -> CLOSED` is always EVRAK_KAYIT-only or may be automated
   after outbound EBYS delivery in a future integration.
4. Official calendar/business-day and public-holiday source for deadline arithmetic.
5. Required versus optional DepartmentAction fields per action type.
6. Whether final draft approval and Case completion require distinct people in
   production; MVP permits the same authorized department user.
7. Retention/redaction periods for citizen contact data, Case events and drafts.
8. Mapping rules from future EBYS identities/channels to the canonical ingress
   fields and idempotency key.

Until decided, implementations MUST choose the safer behavior: short-lived demo
credentials, no automatic closure, `UNKNOWN` deadlines, minimum stored PII and
explicit human confirmation.
