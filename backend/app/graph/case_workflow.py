"""Additive LangGraph wrapper around case-aware intake.

Legacy ``KamuaiWorkflow`` remains the document-analysis pipeline used by
current APIs. This graph is an explicit case-lifecycle entry point.
"""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, StateGraph
from pydantic import Field

from backend.app.graph.state import DocumentState
from backend.app.graph.workflow import KamuaiWorkflow
from backend.app.intelligence.contracts import CaseIntelligenceContext, OriginatorContext
from backend.app.intelligence.orchestration import CaseAwareOrchestrator


class CaseAwareState(DocumentState):
    received_at: str | None = None
    clarification: dict[str, Any] = Field(default_factory=dict)
    case_orchestration: dict[str, Any] = Field(default_factory=dict)
    deadline_evaluation: dict[str, Any] = Field(default_factory=dict)
    wait_for: Literal[
        "",
        "WAIT_FOR_HUMAN_CITIZEN_INFO",
        "WAIT_FOR_HUMAN_ROUTING_CONFIRMATION",
    ] = ""


class CaseAwareWorkflow:
    def __init__(self, institution: str = "belediye"):
        self.institution = institution
        self.legacy = KamuaiWorkflow(institution=institution)
        self.orchestrator = CaseAwareOrchestrator(institution=institution)
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(CaseAwareState)
        workflow.add_node("document_agent", self.legacy.node_document)
        workflow.add_node("extraction_agent", self.legacy.node_extraction)
        workflow.add_node("legal_agent", self.legacy.node_legal)
        workflow.add_node("missing_field_agent", self.legacy.node_missing_field)
        workflow.add_node("intake_gate", self.node_intake_gate)
        workflow.set_entry_point("document_agent")
        workflow.add_edge("document_agent", "extraction_agent")
        workflow.add_edge("extraction_agent", "legal_agent")
        workflow.add_edge("legal_agent", "missing_field_agent")
        workflow.add_edge("missing_field_agent", "intake_gate")
        workflow.add_edge("intake_gate", END)
        return workflow.compile()

    def node_intake_gate(self, state: CaseAwareState) -> dict[str, Any]:
        context = CaseIntelligenceContext(
            institution_id=self.institution,
            raw_text=state.raw_text,
            received_at=state.received_at,
            originator=OriginatorContext(),
            document=state.document,
            extraction=state.extraction,
            legal_analysis=state.legal_analysis,
            missing_fields=state.missing_fields,
        )
        outcome = self.orchestrator.evaluate_first_stage(context)
        return {
            "clarification": outcome.get("clarification") or {},
            "case_orchestration": outcome,
            "deadline_evaluation": outcome.get("deadline_evaluation") or {},
            "wait_for": outcome.get("wait_for") or "",
            "summary": outcome.get("summary") or state.summary,
            "routing": outcome.get("routing") or {},
            "draft": outcome.get("missing_information_request")
            or outcome.get("interim_information")
            or {},
        }

    def run(
        self,
        raw_text: str,
        document_id: str = "case-doc-1",
        received_at: str | None = None,
    ) -> dict[str, Any]:
        initial = CaseAwareState(
            document_id=document_id,
            raw_text=raw_text,
            kurum_profili_id=self.institution,
            received_at=received_at,
        )
        return self.graph.invoke(initial)
