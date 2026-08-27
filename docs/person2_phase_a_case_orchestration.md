# PERSON 2 REPORT: Phase P2-A Case Orchestration

## 1. Architecture Decision & Legacy Workflow Compatibility
**Decision**: A pure service orchestration layer (`CaseAwareOrchestrator`) was chosen over a second large `LangGraph` graph.
**Why Service Orchestration**: The Case Engine (owned by Person 1) is already responsible for persistence, suspension (WAIT_FOR_HUMAN), optimistic locking, and state transitions. A heavy LangGraph graph would duplicate state management and complicate boundaries. A pure Python service cleanly returns AI intelligence previews and yields control back to the API/Case Engine.
**Legacy Compatibility**: `KamuaiWorkflow` remains fully intact and backward-compatible. Legacy tests and legacy API endpoints will continue to function exactly as before. The new `CaseAwareOrchestrator` merely reuses the underlying agents in a new sequential/conditional flow.

## 2. Case DTO
**Contract**: `CaseIntelligenceContext`
Defined in `backend.app.intelligence.contracts`. It provides a clean, persistence-free structured context containing fields like `institution_id`, `received_at`, `originator`, `raw_text`, and nested structures for `document`, `extraction`, `legal_analysis`, `routing`, etc. This decouples AI intelligence from the DB models.

## 3. analyze_case_intake Contract
**Flow**: `evaluate_first_stage`
1. Runs `MissingFieldAgent` (if missing fields not already provided in context).
2. Runs `ClarificationAgent` to evaluate if blocking info exists.
3. If **blocking**: Generates a clarification request preview (e.g., `WAITING_CITIZEN_INFO`) and halts before routing.
4. If **not blocking**: Proceeds to `RoutingAgent` and generates an interim information preview (e.g., `WAITING_INITIAL_REVIEW`).
*No `OFFICIAL_RESPONSE` is generated during initial intake.*

## 4. Blocking Semantics
Missing fields are evaluated contextually based on the institution profile (e.g., location might be blocking for `fen_isleri` disambiguation, but optional email is not).
The orchestrator checks `has_blocking_missing` or `blocking` flags returned by `ClarificationAgent` to halt processing safely.

## 5. Routing Recommendation Semantics
The `RoutingAgent` output within the Case Orchestrator has been explicitly isolated as a *recommendation*. It does not commit assignment or change ownership. The API returns it with `requires_human_review=True`.

## 6. Tests
Added `backend/tests/test_case_orchestration.py` to cover:
- `test_orchestration_complete_belediye_request`: Ensures non-blocking flow reaches routing and requests `WAIT_FOR_HUMAN_ROUTING_CONFIRMATION`.
- `test_orchestration_blocking_missing_location`: Ensures blocking flow halts at clarification and requests `WAIT_FOR_HUMAN_CITIZEN_INFO`.
- `test_orchestration_institution_isolation`: Verifies institution profiles load correctly.
- All legacy tests (`pytest backend/tests/`) remain passing to ensure no regressions.

## 7. Files Changed
- `backend/tests/test_case_orchestration.py` (added)
*(Note: Core intelligence files such as `orchestration.py`, `clarification.py`, `case_state.py`, and `deadline.py` were already present in `backend/app/intelligence/` and verified to meet requirements).*

## 8. Integration Requirements for Person 1
1. **Case Engine State Machine**: Integrate the `CaseAwareOrchestrator` into the Case intake endpoints.
2. **Suspension**: When the orchestrator returns `wait_for="WAIT_FOR_HUMAN_CITIZEN_INFO"`, transition the Case state to `WAITING_CITIZEN_INFO` and persist the `clarification` schema.
3. **No LLM Writes**: The DB should only mutate after explicit human confirmation of the AI previews returned by this layer.

## 9. Known Limitations
- The `CaseWritingService` relies heavily on structured extraction contexts; if extraction quality degrades, the clarification previews will be less accurate.
- `LegalDeadlineService` relies on explicit `received_at`; if the caller provides generic `created_at`, deadline tracking might be inaccurate for backdated documents.
