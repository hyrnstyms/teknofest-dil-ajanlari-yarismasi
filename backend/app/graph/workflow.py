import time
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from backend.app.graph.state import DocumentState

# Import agents
from backend.app.agents.document_agent import DocumentAgent
from backend.app.agents.extraction_agent import ExtractionAgent
from backend.app.agents.legal_agent import LegalAgent
from backend.app.agents.missing_field_agent import MissingFieldAgent
from backend.app.agents.summary_agent import SummaryAgent
from backend.app.agents.routing_agent import RoutingAgent
from backend.app.agents.writing_agent import WritingAgent
from backend.app.agents.quality_agent import QualityAgent

from backend.app.llm.factory import create_llm_client

class KamuaiWorkflow:
    def __init__(self, institution: str = "kaymakamlik"):
        """
        Args:
            institution: Aktif kurum profil id'si.
                         Varsayılan "kaymakamlik"; "belediye" gibi
                         başka kurumlar da desteklenir (Track 3).
        """
        self.institution = institution
        self.llm = create_llm_client()
        self.doc_agent = DocumentAgent(llm=self.llm)
        self.extract_agent = ExtractionAgent(llm=self.llm)
        self.legal_agent = LegalAgent(llm=self.llm)
        self.missing_field_agent = MissingFieldAgent()
        self.summary_agent = SummaryAgent(llm=self.llm)
        self.routing_agent = RoutingAgent(institution=institution)
        self.writing_agent = WritingAgent(llm=self.llm)
        self.quality_agent = QualityAgent()

        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(DocumentState)
        
        # Add nodes
        workflow.add_node("document_agent", self.node_document)
        workflow.add_node("extraction_agent", self.node_extraction)
        workflow.add_node("legal_agent", self.node_legal)
        workflow.add_node("missing_field_agent", self.node_missing_field)
        workflow.add_node("summary_agent", self.node_summary)
        workflow.add_node("routing_agent", self.node_routing)
        workflow.add_node("writing_agent", self.node_writing)
        workflow.add_node("quality_agent", self.node_quality)
        workflow.add_node("human_review_agent", self.node_human_review)
        
        # Build linear edges for MVP V1 raw_text flow
        workflow.set_entry_point("document_agent")
        workflow.add_edge("document_agent", "extraction_agent")
        workflow.add_edge("extraction_agent", "legal_agent")
        workflow.add_edge("legal_agent", "missing_field_agent")
        workflow.add_edge("missing_field_agent", "summary_agent")
        workflow.add_edge("summary_agent", "routing_agent")
        workflow.add_edge("routing_agent", "writing_agent")
        workflow.add_edge("writing_agent", "quality_agent")
        workflow.add_edge("quality_agent", "human_review_agent")
        workflow.add_edge("human_review_agent", END)
        
        return workflow.compile()

    def _measure_time(self, func, state, node_name):
        start = time.time()
        try:
            result = func(state)
            status = "completed"
        except Exception as e:
            result = {"warnings": [f"{node_name} adımında hata: {str(e)}"]}
            status = "failed"
        end = time.time()
        
        duration_ms = int((end - start) * 1000)
        
        # Copy existing node_timings to avoid modifying the current state object directly
        # and to allow LangGraph to replace the field
        node_timings = dict(state.node_timings)
        node_timings[node_name] = {
            "duration_ms": duration_ms,
            "status": status
        }
        result["node_timings"] = node_timings
        
        # update state warnings
        if "warnings" in result:
            current_warnings = list(state.warnings)
            current_warnings.extend(result["warnings"])
            result["warnings"] = current_warnings
                
        return result

    def node_document(self, state: DocumentState):
        def _run(s: DocumentState):
            text = s.raw_text
            res = self.doc_agent.analyze(text)
            return {"document": res}
        return self._measure_time(_run, state, "document_agent")

    def node_extraction(self, state: DocumentState):
        def _run(s: DocumentState):
            text = s.raw_text
            doc_ctx = s.document
            res = self.extract_agent.extract(text, document_context=doc_ctx)
            return {"extraction": res}
        return self._measure_time(_run, state, "extraction_agent")

    def node_legal(self, state: DocumentState):
        def _run(s: DocumentState):
            doc_ctx = s.document
            intent = doc_ctx.get("process_intent", "")
            subject = doc_ctx.get("subject_excerpt", "")
            req = doc_ctx.get("request_excerpt", "")
            
            query = f"{intent} {subject} {req}".strip()
            if not query:
                query = s.raw_text[:500]
                
            try:
                # Assuming top_k parameter can be passed
                res = self.legal_agent.analyze(query=query)
                return {"legal_analysis": res}
            except Exception as e:
                # If legal retrieval fails, we do not crash
                return {
                    "legal_analysis": {"warnings": [str(e)], "evidence": [], "sources": []},
                    "warnings": ["Mevzuat arama adımı tamamlanamadı."]
                }
        return self._measure_time(_run, state, "legal_agent")

    def node_missing_field(self, state: DocumentState):
        def _run(s: DocumentState):
            doc_ctx = s.document
            dtype = doc_ctx.get("document_type", "")
            intent = doc_ctx.get("process_intent", "")
            ext = s.extraction.get("fields", {})
            leg = s.legal_analysis
            
            res = self.missing_field_agent.check_missing_fields(
                document_type=dtype,
                process_intent=intent,
                extracted_fields=ext,
                legal_analysis=leg
            )
            return {"missing_fields": res}
        return self._measure_time(_run, state, "missing_field_agent")

    def node_summary(self, state: DocumentState):
        def _run(s: DocumentState):
            text = s.raw_text
            doc_ctx = s.document
            ext = s.extraction.get("fields", {})
            res = self.summary_agent.summarize(text, doc_ctx, ext)
            return {"summary": res}
        return self._measure_time(_run, state, "summary_agent")

    def node_routing(self, state: DocumentState):
        def _run(s: DocumentState):
            doc_ctx = s.document
            dtype = doc_ctx.get("document_type", "")
            intent = doc_ctx.get("process_intent", "")
            sub = doc_ctx.get("subject_excerpt", "")
            req = doc_ctx.get("request_excerpt", "")
            ext = s.extraction.get("fields", {})
            
            res = self.routing_agent.route(dtype, intent, sub, req, ext)
            return {"routing": res}
        return self._measure_time(_run, state, "routing_agent")

    def node_writing(self, state: DocumentState):
        def _run(s: DocumentState):
            summ = s.summary.get("short_summary", "")
            doc_ctx = s.document
            req_act = doc_ctx.get("process_intent", "")
            mf = s.missing_fields.get("missing_fields", [])
            ext = s.extraction.get("fields", {})
            
            # Extract sender and recipient if available
            sender = s.routing.get("recommended_unit", None)
            recipient = (
                ext.get("recipient", {}).get("value")
                or ext.get("institution", {}).get("value")
                or ext.get("person_name", {}).get("value")
            )
            
            # Gather verified facts
            facts = []
            if req_act:
                facts.append(f"İşlem Türü: {req_act}")
            
            res = self.writing_agent.draft(
                document_summary=summ or "Özet bulunamadı",
                requested_action=req_act,
                missing_fields=mf,
                verified_facts=facts,
                recipient=recipient,
                sender_unit=sender,
                state={
                    "extraction": s.extraction,
                    "routing": s.routing,
                    "kurum_profili_id": s.kurum_profili_id,
                    "muhatap": s.muhatap,
                    "muhatap_turu": s.muhatap_turu,
                }
            )
            return {"draft": res}
        return self._measure_time(_run, state, "writing_agent")

    def node_quality(self, state: DocumentState):
        def _run(s: DocumentState):
            res = self.quality_agent.check_quality(
                document=s.document,
                extraction=s.extraction,
                legal_analysis=s.legal_analysis,
                missing_fields=s.missing_fields,
                summary=s.summary,
                routing=s.routing,
                draft=s.draft
            )
            return {"quality": res}
        return self._measure_time(_run, state, "quality_agent")

    def node_human_review(self, state: DocumentState):
        def _run(s: DocumentState):
            # Evaluate requires_human_review from components
            req = False
            if s.quality.get("requires_human_review"):
                req = True
            if s.missing_fields.get("needs_human_review"):
                req = True
            if s.routing.get("needs_human_review"):
                req = True
            
            # Default fallback: if there's a draft, we usually want approval
            if s.draft.get("draft_text"):
                req = True
                
            return {
                "human_review": {
                    "required": req,
                    "status": "pending_review" if req else "approved_auto"
                }
            }
        return self._measure_time(_run, state, "human_review_agent")

    def run(
        self,
        raw_text: str,
        document_id: str = "test-doc-1",
    ):
        initial_state = DocumentState(
            document_id=document_id,
            raw_text=raw_text,
            kurum_profili_id=self.institution,
        )
        final_state = self.graph.invoke(initial_state)
        return final_state
