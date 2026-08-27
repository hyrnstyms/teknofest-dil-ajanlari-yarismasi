"""Case-aware first-stage orchestration. Additive; does not replace KamuaiWorkflow."""

from __future__ import annotations

from typing import Any

from backend.app.agents.missing_field_agent import MissingFieldAgent
from backend.app.agents.priority_agent import PriorityAgent
from backend.app.agents.routing_agent import RoutingAgent
from backend.app.agents.summary_agent import SummaryAgent
from backend.app.intelligence.case_writing import CaseWritingService
from backend.app.intelligence.clarification import ClarificationAgent
from backend.app.intelligence.contracts import CaseIntelligenceContext, IntakeOrchestrationResult
from backend.app.intelligence.deadline import LegalDeadlineService
from backend.app.intelligence.municipal_workflow import MunicipalOperationResolver
from backend.app.institutions.profile_loader import load_institution_profile


class CaseAwareOrchestrator:
    """Document → extraction → legal → missing → conditional intake path.

    Agents recommend. They do not commit routing or write Case state.
    First intake never produces OFFICIAL_RESPONSE.
    """

    def __init__(self, institution: str = "belediye"):
        self.institution = institution
        try:
            self.institution_profile = load_institution_profile(institution)
        except Exception:
            self.institution_profile = None
        self.missing_field_agent = MissingFieldAgent()
        self.clarification_agent = ClarificationAgent()
        self.routing_agent = RoutingAgent(institution=institution)
        self.writing = CaseWritingService()
        self.deadline_service = LegalDeadlineService()
        self.priority_agent = PriorityAgent()
        self.summary_agent: SummaryAgent | None = None
        self.operation_resolver = MunicipalOperationResolver(institution)

    def evaluate_first_stage(
        self,
        context: CaseIntelligenceContext | dict[str, Any],
        *,
        summary_fn=None,
    ) -> dict[str, Any]:
        ctx = (
            context
            if isinstance(context, CaseIntelligenceContext)
            else CaseIntelligenceContext.model_validate(context)
        )
        document = ctx.document or {}
        extracted_fields = (ctx.extraction or {}).get("fields") or {}
        document_type = document.get("document_type") or ""
        process_intent = document.get("process_intent") or ""

        missing = ctx.missing_fields or self.missing_field_agent.check_missing_fields(
            document_type=document_type,
            process_intent=process_intent,
            extracted_fields=extracted_fields,
            legal_analysis=ctx.legal_analysis,
            document_subtype=document.get("document_subtype"),
            institution_profile=self.institution_profile,
            institution_id=ctx.institution_id,
            raw_text=ctx.raw_text,
            document=document,
        )

        clarification = self.clarification_agent.preview(
            missing_fields=missing,
            institution_id=ctx.institution_id,
            document_type=document_type,
            process_intent=process_intent,
            raw_text=ctx.raw_text,
            document=document,
            extracted_fields=extracted_fields,
            routing=ctx.routing,
            originator=ctx.originator,
        )
        blocking = bool(clarification.get("blocking") or missing.get("has_blocking_missing"))

        deadline = self.deadline_service.evaluate(
            legal_analysis=ctx.legal_analysis,
            received_at=ctx.received_at,
            created_at=ctx.created_at,
            as_of=ctx.as_of,
        )
        priority = self.priority_agent.assess(ctx.raw_text)

        if blocking:
            request_preview = self.writing.draft_for_intake(
                clarification=clarification,
                missing_fields=missing,
                originator=ctx.originator,
                extraction=ctx.extraction,
            )
            result = IntakeOrchestrationResult(
                wait_for="WAIT_FOR_HUMAN_CITIZEN_INFO",
                recommended_workflow_status="WAITING_CITIZEN_INFO",
                blocking_missing=True,
                clarification=clarification,
                missing_information_request=request_preview,
                summary=None,
                routing=None,
                official_response=None,
                operational_priority=priority,
                deadline_evaluation=deadline,
            )
            payload = result.model_dump()
            payload["missing_fields"] = missing
            payload["document"] = document
            payload["extraction"] = ctx.extraction
            return payload

        summary = ctx.summary
        if summary_fn is not None and not summary:
            summary = summary_fn(ctx)
        routing = ctx.routing or self.routing_agent.route(
            document_type,
            process_intent,
            document.get("subject_excerpt") or "",
            document.get("request_excerpt") or "",
            extracted_fields,
            document_subtype=document.get("document_subtype"),
        )
        routing = dict(routing)
        routing["assigned"] = False
        routing["requires_human_review"] = bool(
            routing.get("requires_human_review", routing.get("needs_human_review", True))
        )
        operation = self.operation_resolver.recommend(
            document=document,
            extracted_fields=extracted_fields,
            raw_text=ctx.raw_text,
            routing=routing,
        )

        interim = self.writing.draft_for_intake(
            clarification=clarification,
            missing_fields=missing,
            routing=routing,
            originator=ctx.originator,
            extraction=ctx.extraction,
        )
        result = IntakeOrchestrationResult(
            wait_for="WAIT_FOR_HUMAN_ROUTING_CONFIRMATION",
            recommended_workflow_status="WAITING_INITIAL_REVIEW",
            blocking_missing=False,
            clarification=clarification,
            missing_information_request=None,
            summary=summary or None,
            routing=routing,
            official_response=None,
            operational_priority=priority,
            deadline_evaluation=deadline,
        )
        payload = result.model_dump()
        payload["missing_fields"] = missing
        payload["document"] = document
        payload["extraction"] = ctx.extraction
        payload["interim_information"] = interim
        payload["ai_operation"] = operation
        return payload
