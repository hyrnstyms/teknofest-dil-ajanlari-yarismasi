# Phase P2-B: Active Clarification & Structured Citizen Resume

## Clarification Contract

The `ClarificationAgent` acts as a pure intelligence service. It does not mutate the DB or hold persistent state. It receives a snapshot of the current case analysis state and returns a minimum necessary actionable question to continue safely, adhering strictly to the frozen `ClarificationPreview` contract:

```json
{
  "needs_clarification": true,
  "blocking": true,
  "requested_fields": ["permit_type"],
  "question_type": "choice",
  "question": "Başvurunuz hangi ruhsat türüyle ilgilidir?",
  "options": [
    "YAPI_RUHSATI",
    "ISYERI_ACMA_RUHSATI"
  ],
  "resume_target": "routing"
}
```

## Deterministic-First Decision
Clarification relies on existing extraction metadata and process profile configurations (like `PERMIT_DEPARTMENT_BY_OPTION`). It generates questions deterministically rather than blindly injecting LLM calls, mapping known ambiguity signatures into safe template questions. 

## Minimum-Information Policy
Clarification only requests fields that are genuinely blocking and independent. If only one field is needed to safely route a document, only that field is requested. It avoids overwhelming the citizen with broad, generic information requests.

## Ambiguous Ruhsat Behavior
When the text contains generic phrases like "ruhsat" but lacks specific modifiers, the agent identifies the `permit_ambiguity` blocking state. It subsequently formulates a single-choice question mapped to the institution's allowed permit categories (`YAPI_RUHSATI` vs `ISYERI_ACMA_RUHSATI`) to resolve the process routing securely.

## Resume Contract
The orchestrator implements `resume_after_citizen_info(prior_state, citizen_response)` which takes the prior snapshot and the structured citizen DTO (`CitizenResponse`), and outputs an updated intelligence context (`CaseIntelligenceContext`).
The citizen response acts as evidence. The user text is NEVER concatenated back into an LLM prompt as instructions.

## Safe Merge Behavior
The merging process evaluates incoming citizen responses strictly against the `requested_fields` array.
- **Whitelist Merge**: If a field was not actively requested during the clarification phase, it is rejected/ignored.
- **Contradiction Management**: If the citizen submits a value for an already validated field (e.g. changing the address) and it contradicts the existing evidence, the system does not silently overwrite the validated fact. Instead, it marks the field as `uncertain` and escalates it to human review.

## Selective Reevaluation
Resuming a case post-clarification does not rerun the expensive document analysis pipelines (like `ExtractionAgent` or `DocumentAgent`). It only selectively reruns `MissingFieldAgent`, `ClarificationAgent`, and `RoutingAgent` to deduce the next workflow state.

## Integration Requirements
- The Case Engine (Person 1) must track `requested_fields` and pass them correctly inside `CaseIntelligenceContext` when resuming.
- DB updates are owned purely by the Case Engine. This module produces DTO recommendations that dictate if the state transforms into `WAITING_CITIZEN_INFO` or transitions forward.

## Known Limitations
- If a citizen responds with contradictory information for multiple fields, human review is heavily triggered since automated overwrite is disabled.
- Missing field detection heavily relies on `process_profiles` which currently maps specific predefined schemas. Unmapped document schemas will fallback to LLM evaluation.

## Test Results
All 12 specific testing requirements have been fulfilled and all tests pass (including regression of Phase A and Copilot stream tests):
1. **missing location**: one free-text clarification ✅
2. **missing optional phone**: no blocking clarification ✅
3. **ambiguous "ruhsat"**: one single-choice question ✅
4. **clarification preview causes no persistence/state mutation**: verified lack of save/update methods on the service ✅
5. **citizen supplies YAPI_RUHSATI**: routing reevaluates appropriately ✅
6. **citizen supplies ISYERI_ACMA_RUHSATI**: may change routing ✅
7. **citizen sends unrequested field**: rejected/ignored safely according to contract ✅
8. **contradictory citizen response**: no silent overwrite (marked uncertain) ✅
9. **malicious citizen response**: treated as data only, no prompt injection effect ✅
10. **resume does not rerun unnecessary agents where measurable**: Document/Extraction are completely bypassed ✅
11. **no DepartmentAction or OFFICIAL_RESPONSE produced**: explicitly verified missing from response ✅
12. **existing Phase A and legacy tests remain PASS**: `test_case_orchestration.py` passed successfully ✅
