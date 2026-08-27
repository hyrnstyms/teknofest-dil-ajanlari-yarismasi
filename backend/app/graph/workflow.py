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
from backend.app.agents.transfer_agent import TransferAgent

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
        self.llm = create_llm_client(
            "document_agent"
        )
        self.legal_llm = create_llm_client(
            "legal_agent"
        )
        self.doc_agent = DocumentAgent(llm=self.llm)
        self.extract_agent = ExtractionAgent(llm=self.llm)
        self.legal_agent = LegalAgent(llm=self.legal_llm)
        self.document_retriever = self.legal_agent.retriever
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

            document_legal_references = self._extract_document_legal_references(
                s.raw_text
            )
            query = " ".join(
                part
                for part in (
                    intent,
                    subject,
                    req,
                    s.raw_text[:1000],
                    *document_legal_references,
                )
                if part
            )
            if not query:
                query = s.raw_text[:500]
                
            try:
                res = self.legal_agent.analyze(
                    query=query,
                    strict_explicit_law=bool(document_legal_references),
                )
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

            query = f"{dtype} {intent} {sub} {req}".strip()
            retrieved_documents = []
            retrieval_warning = None
            if query:
                try:
                    retrieved_documents = self.document_retriever.search_documents(
                        query=query,
                        limit=8,
                        institution=self.institution,
                    )
                except Exception as exc:
                    retrieval_warning = (
                        "Belge bilgi tabanı araması tamamlanamadı: "
                        f"{exc}"
                    )

            res = self.routing_agent.route(
                dtype,
                intent,
                sub,
                req,
                ext,
                retrieved_documents=retrieved_documents,
            )
            if retrieval_warning:
                res.setdefault("warnings", []).append(retrieval_warning)

            # Transfer tespiti: iletim intent'i veya kurumlar arası evrak türü
            transfer_routing: dict = {}
            if intent == "iletim" or dtype == "kurumlar_arasi_yazi":
                hedef = _detect_target_institution(s.raw_text)
                try:
                    transfer_routing = TransferAgent().transfer(
                        kaynak_kurum=self.institution,
                        hedef_kurum=hedef,
                        konu=sub or dtype or "Bilinmiyor",
                        evrak_ozeti=req or sub or dtype or "Bilinmiyor",
                        process_intent=intent or "iletim",
                    )
                except Exception as exc:
                    transfer_routing = {
                        "transfer_required": False,
                        "warnings": [f"Transfer ajanı hatası: {exc}"],
                    }

            if transfer_routing:
                return {"routing": res, "transfer_routing": transfer_routing}
            return {"routing": res}
        return self._measure_time(_run, state, "routing_agent")

    def node_writing(self, state: DocumentState):
        def _run(s: DocumentState):
            summ = s.summary.get("short_summary", "")
            doc_ctx = s.document
            req_act = doc_ctx.get("process_intent", "")
            requested_action = {
                "cevap": "başvuru sahibine cevap verilmesi",
                "iletim": "ilgili birime iletilmesi",
                "bildirim": "bilgi verilmesi",
                "bilgi_talebi": "bilgi verilmesi",
            }.get(req_act, req_act)
            mf = s.missing_fields.get("missing_fields", [])
            ext = s.extraction.get("fields", {})
            
            # Cevap yazısının muhatabı, evrakın hitap ettiği kurum değil,
            # başvuru sahibidir. Kurum muhatabı yalnızca başvuru sahibi
            # çıkarılamayan durumlar için fallback olarak kalır.
            sender = s.routing.get("recommended_unit", None)
            recipient = (
                ext.get("person_name", {}).get("value")
                or ext.get("sender_unit", {}).get("value")
                or ext.get("recipient", {}).get("value")
                or ext.get("institution", {}).get("value")
            )
            
            # Gather verified facts
            facts = []
            if req_act:
                facts.append(f"İşlem Türü: {req_act}")

            legal_context = self._build_legal_context(s.legal_analysis)
            document_legal_references = self._extract_document_legal_references(
                s.raw_text
            )
            
            res = self.writing_agent.draft(
                document_summary=summ or "Özet bulunamadı",
                requested_action=requested_action,
                missing_fields=mf,
                verified_facts=facts,
                legal_context=legal_context,
                document_legal_references=document_legal_references,
                recipient=recipient,
                sender_unit=sender,
                state={
                    "extraction": s.extraction,
                    "routing": s.routing,
                    "legal_analysis": s.legal_analysis,
                    "legal_context": legal_context,
                    "document_legal_references": document_legal_references,
                    "kurum_profili_id": s.kurum_profili_id,
                    "muhatap": s.muhatap,
                    "muhatap_turu": s.muhatap_turu,
                }
            )
            return {"draft": res}
        return self._measure_time(_run, state, "writing_agent")

    @staticmethod
    def _build_legal_context(legal_analysis: Dict[str, Any]) -> str:
        """Format only source-verified legal evidence for the writing prompt."""

        analysis = legal_analysis if isinstance(legal_analysis, dict) else {}
        sources = analysis.get("sources") or []
        source_map = {
            f"K{index}": source
            for index, source in enumerate(sources, start=1)
            if isinstance(source, dict)
        }
        context = []
        for item in analysis.get("evidence") or []:
            if not isinstance(item, dict):
                continue
            evidence = str(item.get("evidence") or "").strip()
            source = source_map.get(str(item.get("source") or ""), {})
            if not evidence or not source:
                continue
            citation = []
            if source.get("law_number"):
                citation.append(f"{source['law_number']} sayılı Kanun")
            if source.get("madde_no"):
                citation.append(f"Madde {source['madde_no']}")
            if not citation:
                citation.append(str(source.get("title") or source.get("source") or "Mevzuat kaynağı"))
            context.append(f"- {evidence} [{' — '.join(citation)}]")
        return "\n".join(context) if context else "Doğrulanmış hukuki kanıt bulunamadı."

    @staticmethod
    def _extract_document_legal_references(raw_text: str) -> list[str]:
        """Return only statute references explicitly written in the document."""

        return [
            f"{law_number} sayılı Kanun"
            for law_number in dict.fromkeys(
                __import__("re").findall(r"\b(\d{3,6})\s+sayılı\b", raw_text, __import__("re").IGNORECASE)
            )
        ]

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


# ---------------------------------------------------------------------------
# Modül düzeyinde yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

def _detect_target_institution(raw_text: str) -> str:
    """
    Evrak metninden hedef kurumu deterministik olarak tespit eder.
    Kural tabanlıdır — LLM kullanmaz.

    Tanınan örüntüler (büyük/küçük harf duyarsız):
      - "belediye" → "belediye"
      - "il özel idaresi" / "il_ozel_idare" → "il_ozel_idare"
      - Aksi halde varsayılan: "belediye"
    """
    text_lower = raw_text.lower()
    if "belediye" in text_lower:
        return "belediye"
    if "il özel idaresi" in text_lower or "il özel idare" in text_lower:
        return "il_ozel_idare"
    # Varsayılan: kaymakamlıktan gelen iletim yazıları çoğunlukla belediyeye
    return "belediye"
