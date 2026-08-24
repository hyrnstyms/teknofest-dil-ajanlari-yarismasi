from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import os
import shutil
from copy import deepcopy
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from backend.app.graph.workflow import KamuaiWorkflow
from backend.app.telemetry.service import telemetry_service
from backend.app.telemetry.roi import calculate_roi_summary
from backend.app.ingestion.document_loader import load_file
from backend.app.agents.chat_agent import handle_draft_edit

# Initialize FastAPI app
app = FastAPI(title="KAMUAI MVP API")

# Setup CORS
origins = [
    "http://localhost:5173"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory Analysis Store
analysis_store: Dict[str, Any] = {}

# Lazy initialization for workflow and other services
workflow = None
def get_workflow():
    global workflow
    if workflow is None:
        workflow = KamuaiWorkflow()
    return workflow

ocr_svc = None
def get_ocr_service():
    global ocr_svc
    if ocr_svc is None:
        from backend.app.ocr.ocr_service import OCRService
        ocr_svc = OCRService()
    return ocr_svc


# Schemas
class AnalyzeRequest(BaseModel):
    text: str
    document_id: Optional[str] = None

class RejectRequest(BaseModel):
    reason: Optional[str] = None

class EditRequest(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None

class ChatDraftEditRequest(BaseModel):
    message: str


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "KAMUAI API çalışıyor."}


@app.get("/ready")
def readiness_check():
    # Check services (Ollama, Qdrant, Embedding) safely
    ready = True
    services = {
        "ollama": {"status": "unknown"},
        "qdrant": {"status": "unknown"},
        "embedding": {"status": "unknown"}
    }
    
    # Try Ollama (just a ping or check settings)
    try:
        from backend.app.llm.settings import LLMSettings
        import requests
        resp = requests.get(LLMSettings.OLLAMA_URL)
        if resp.status_code == 200:
            services["ollama"]["status"] = "ok"
        else:
            services["ollama"]["status"] = "error"
            ready = False
    except Exception:
        services["ollama"]["status"] = "unreachable"
        ready = False
        
    # Try Qdrant and Embedding via RAG system
    try:
        from backend.app.rag.embedding_service import EmbeddingService
        from backend.app.rag.qdrant_store import QdrantStore
        
        try:
            emb = EmbeddingService()
            if emb.model:
                services["embedding"]["status"] = "ok"
            else:
                services["embedding"]["status"] = "error"
                ready = False
        except Exception as e:
            logger.error(f"Embedding service check failed: {e}", exc_info=True)
            services["embedding"]["status"] = "unreachable"
            ready = False
            
        try:
            store = QdrantStore()
            # Try to fetch collections to verify connection
            store.client.get_collections()
            services["qdrant"]["status"] = "ok"
        except Exception as e:
            logger.error(f"Qdrant connection failed: {e}", exc_info=True)
            services["qdrant"]["status"] = "unavailable"
            ready = False
            
    except Exception as e:
        logger.error(f"RAG dependencies check failed: {e}", exc_info=True)
        if services["embedding"]["status"] == "unknown":
            services["embedding"]["status"] = "error"
        if services["qdrant"]["status"] == "unknown":
            services["qdrant"]["status"] = "error"
        ready = False

    return {
        "ready": ready,
        "services": services,
        "message": "Sistem servise hazır." if ready else "Bazı servisler hazır değil."
    }


@app.post("/api/documents/analyze-text")
def analyze_text(req: AnalyzeRequest):
    try:
        doc_id = req.document_id or str(uuid.uuid4())
        wf = get_workflow()
        
        final_state = wf.run(req.text, document_id=doc_id)
        
        analysis_id = str(uuid.uuid4())
        
        # Add basic audit history
        audit_history = [
            {"event": "analysis_completed", "timestamp": datetime.utcnow().isoformat(), "message": "Analiz tamamlandı."}
        ]
        
        final_state["analysis_id"] = analysis_id
        final_state["audit_history"] = audit_history
        final_state["created_at"] = datetime.utcnow().isoformat()
        
        # Telemetry extraction
        telemetry_service.extract_from_state(analysis_id, final_state)
        
        analysis_store[analysis_id] = final_state
        return final_state
        
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "analysis_error", "message": f"Analiz sırasında bir hata oluştu: {str(e)}"})


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    file_path = None
    try:
        temp_dir = Path("temp_uploads")
        temp_dir.mkdir(exist_ok=True)
        file_path = temp_dir / file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1. Try standard extraction first
        docs = load_file(file_path, "upload")
        raw_text = docs[0].text if docs else ""
        
        # 2. Check if we need OCR
        is_pdf = file_path.suffix.lower() == ".pdf"
        is_image = file_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]
        needs_ocr = False
        
        if is_image:
            needs_ocr = True
        elif is_pdf and len(raw_text.strip()) < 50:
            needs_ocr = True
            
        if needs_ocr:
            try:
                ocr = get_ocr_service()
                if is_pdf:
                    ocr_text = ocr.extract_text_from_pdf(str(file_path))
                else:
                    ocr_text = ocr.extract_text_from_image(str(file_path))
                    
                if ocr_text and ocr_text.strip():
                    raw_text = ocr_text
            except Exception as e:
                logger.error(f"OCR işlemi başarısız oldu: {str(e)}", exc_info=True)
                # If we already have some text, continue. If not, raise.
                if not raw_text.strip():
                    if file_path.exists():
                        os.remove(file_path)
                    raise HTTPException(
                        status_code=500, 
                        detail={"code": "ocr_error", "message": "Belge OCR ile okunamadı. Lütfen dosyayı kontrol edip tekrar deneyin."}
                    )
                
        if not raw_text.strip():
            if file_path.exists():
                os.remove(file_path)
            raise HTTPException(status_code=400, detail={"code": "empty_document", "message": "Belgeden okunabilir metin çıkarılamadı."})
            
        # Clean up
        if file_path.exists():
            os.remove(file_path)
        
        # Run analysis
        req = AnalyzeRequest(text=raw_text, document_id=file.filename)
        return analyze_text(req)
        
    except HTTPException:
        raise
    except Exception as e:
        if file_path and file_path.exists():
            os.remove(file_path)
        raise HTTPException(status_code=500, detail={"code": "upload_error", "message": f"Dosya işlenirken hata oluştu: {str(e)}"})


@app.get("/api/analysis/{analysis_id}")
def get_analysis(analysis_id: str):
    if analysis_id not in analysis_store:
        raise HTTPException(status_code=404, detail={"code": "analysis_not_found", "message": "İstenen analiz kaydı bulunamadı."})
    return analysis_store[analysis_id]


@app.post("/api/analysis/{analysis_id}/approve")
def approve_analysis(analysis_id: str):
    if analysis_id not in analysis_store:
        raise HTTPException(status_code=404, detail={"code": "analysis_not_found", "message": "İstenen analiz kaydı bulunamadı."})
        
    state = analysis_store[analysis_id]
    
    if "human_review" not in state:
        state["human_review"] = {}
        
    state["human_review"]["status"] = "approved"
    
    # Audit log
    state.get("audit_history", []).append({
        "event": "approved",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Analiz ve taslak personel tarafından onaylandı."
    })
    
    telemetry_service.update_human_review(analysis_id, "approved")
    
    return {"status": "success", "message": "Analiz ve taslak personel tarafından onaylandı."}


@app.get("/api/analysis/{analysis_id}/export/docx")
def export_docx(analysis_id: str):
    """Onaylı taslağı biçimlendirilmiş .docx dosyası olarak dışa aktarır."""
    if analysis_id not in analysis_store:
        raise HTTPException(
            status_code=404,
            detail={"code": "analysis_not_found", "message": "İstenen analiz kaydı bulunamadı."},
        )

    state = analysis_store[analysis_id]

    # Draft ve draft_type bilgisini çıkar
    draft_data = state.get("draft", {})
    draft = draft_data.get("draft", draft_data)
    draft_type = (
        draft_data.get("draft_type")
        or draft.get("draft_type")
        or state.get("draft_type")
        or "ust_yazi"
    )

    # Mod C tarafından doğrulanmış context varsa yeniden adapter çalıştırma.
    from backend.app.official_writing.docx_renderer import render_to_docx

    validated_context = draft_data.get("mod_c_validated_context")
    if isinstance(validated_context, dict) and validated_context:
        context = deepcopy(validated_context)
    else:
        from backend.app.official_writing.context_adapter import (
            build_official_writing_context,
        )

        try:
            adapter_res = build_official_writing_context(draft, state, draft_type)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail={"code": "context_error", "message": f"Context oluşturulurken hata: {str(exc)}"},
            )

        context = adapter_res.get("context", {})

    try:
        docx_buffer = render_to_docx(context, evrak_id=analysis_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "docx_render_error", "message": f"DOCX üretilirken hata: {str(exc)}"},
        )

    return Response(
        content=docx_buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=resmi_yazi_taslak.docx"},
    )


@app.post("/api/analysis/{analysis_id}/reject")
def reject_analysis(analysis_id: str, req: RejectRequest):
    if analysis_id not in analysis_store:
        raise HTTPException(status_code=404, detail={"code": "analysis_not_found", "message": "İstenen analiz kaydı bulunamadı."})
        
    state = analysis_store[analysis_id]
    
    if "human_review" not in state:
        state["human_review"] = {}
        
    state["human_review"]["status"] = "rejected"
    state["human_review"]["reject_reason"] = req.reason
    
    # Audit log
    state.get("audit_history", []).append({
        "event": "rejected",
        "timestamp": datetime.utcnow().isoformat(),
        "message": f"Analiz reddedildi. Sebep: {req.reason or 'Belirtilmedi'}"
    })
    
    telemetry_service.update_human_review(analysis_id, "rejected")
    
    return {"status": "success", "message": "Analiz reddedildi."}


@app.post("/api/analysis/{analysis_id}/edit")
def edit_analysis(analysis_id: str, req: EditRequest):
    if analysis_id not in analysis_store:
        raise HTTPException(status_code=404, detail={"code": "analysis_not_found", "message": "İstenen analiz kaydı bulunamadı."})
        
    state = analysis_store[analysis_id]
    
    if "draft" not in state:
        state["draft"] = {}
        
    if "human_review" not in state:
        state["human_review"] = {}
        
    # Backup original draft if not already backed up
    if "original_draft" not in state["human_review"]:
        state["human_review"]["original_draft"] = {
            "draft_text": state["draft"].get("draft_text"),
            "subject": state["draft"].get("subject", "")
        }
        
    # Apply edits to the draft structure (we create edited_draft inside draft)
    state["draft"]["edited_draft"] = {
        "subject": req.subject or state["draft"].get("subject", ""),
        "body": req.body or state["draft"].get("draft_text", "")
    }
    
    state["human_review"]["status"] = "edited"
    
    # Audit log
    state.get("audit_history", []).append({
        "event": "draft_edited",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Taslak metin üzerinde manuel düzenleme yapıldı."
    })
    
    telemetry_service.update_human_review(analysis_id, "edited")
    
    return {"status": "success", "message": "Taslak güncellendi."}


@app.post("/api/analysis/{analysis_id}/chat/edit-draft")
def chat_edit_draft(analysis_id: str, req: ChatDraftEditRequest):
    if analysis_id not in analysis_store:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "analysis_not_found",
                "message": "İstenen analiz kaydı bulunamadı.",
            },
        )

    current_state = analysis_store[analysis_id]
    current_draft = current_state.get("draft")
    workflow_context = {
        "extraction": current_state.get("extraction", {}),
        "routing": current_state.get("routing", {}),
        "kurum_profili_id": current_state.get(
            "kurum_profili_id",
            "kaymakamlik_v1",
        ),
        "muhatap": current_state.get("muhatap"),
        "muhatap_turu": current_state.get("muhatap_turu"),
    }

    result = handle_draft_edit(
        req.message,
        current_draft,
        workflow_context,
    )

    updated_draft = result.get("updated_draft")
    if result.get("status") == "applied" and isinstance(updated_draft, dict):
        candidate_state = deepcopy(current_state)
        human_review = candidate_state.setdefault("human_review", {})
        if "mod_c_original_draft" not in human_review:
            human_review["mod_c_original_draft"] = deepcopy(
                candidate_state.get("draft", {})
            )
        human_review["status"] = "edited"

        candidate_state["draft"] = deepcopy(updated_draft)
        candidate_state.setdefault("audit_history", []).append({
            "event": "draft_edited_via_chat",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Taslak, doğrulanmış sohbet düzenlemesiyle güncellendi.",
        })

        analysis_store[analysis_id] = candidate_state

    return result


@app.get("/api/system/status")
def system_status():
    from backend.app.llm.settings import LLMSettings
    
    # Default values
    qdrant_total = 0
    qdrant_legal = 0
    qdrant_docs = 0
    
    try:
        from backend.app.rag.qdrant_store import QdrantStore
        store = QdrantStore()
        
        # Try getting collections point count
        collections = store.client.get_collections().collections
        for c in collections:
            info = store.client.get_collection(c.name)
            if c.name == "legal_knowledge_v2" or c.name == "legal_knowledge":
                qdrant_legal = info.points_count
            elif c.name == "document_knowledge":
                qdrant_docs = info.points_count
            qdrant_total += info.points_count
    except Exception as e:
        logger.error(f"System status Qdrant check failed: {e}", exc_info=True)
        pass
        
    # Full index isn't done
    index_status = "partial" if qdrant_legal > 0 else "empty"
    index_msg = "Mevzuat indeksi kısmi." if index_status == "partial" else "Mevzuat indeksi oluşturulmadı."
    
    return {
        "api": "online",
        "ollama": LLMSettings.OLLAMA_URL,
        "llm_model": LLMSettings.OLLAMA_MODEL,
        "embedding_model": "BAAI/bge-m3",
        "embedding_dimension": 1024,
        "qdrant": {
            "total_points": qdrant_total,
            "legal_points": qdrant_legal,
            "document_points": qdrant_docs,
            "index_status": index_status,
            "message": index_msg
        }
    }


@app.get("/api/roi/summary")
def roi_summary():
    records = telemetry_service.get_all_records()
    summary = calculate_roi_summary(records)
    
    if not records:
        return {
            "processed_documents": 0,
            "average_processing_seconds": 0.0,
            "human_review_required_rate": 0.0,
            "approved_count": 0,
            "edited_count": 0,
            "rejected_count": 0,
            "estimated_saved_seconds": 0,
            "message": "Henüz işlenmiş belge bulunmuyor."
        }
        
    return summary.model_dump()


@app.get("/api/analyses")
def get_analyses(
    limit: int = 20, 
    offset: int = 0, 
    status: Optional[str] = None, 
    document_type: Optional[str] = None, 
    process_intent: Optional[str] = None
):
    items = []
    for analysis_id, state in analysis_store.items():
        doc = state.get("document", {})
        hr = state.get("human_review", {})
        q = state.get("quality", {})
        r = state.get("routing", {})
        t = state.get("telemetry", {})
        
        # Filtering
        if status and hr.get("status") != status:
            continue
        if document_type and doc.get("document_type") != document_type:
            continue
        if process_intent and doc.get("process_intent") != process_intent:
            continue
            
        items.append({
            "analysis_id": analysis_id,
            "document_id": state.get("document_id", ""),
            "document_type": doc.get("document_type"),
            "process_intent": doc.get("process_intent"),
            "subject": state.get("draft", {}).get("draft", {}).get("subject") or state.get("draft", {}).get("subject", ""),
            "recommended_unit": r.get("recommended_unit"),
            "human_review_status": hr.get("status"),
            "quality_status": q.get("status"),
            "created_at": state.get("created_at"),
            "total_processing_ms": t.get("total_processing_ms", 0)
        })
        
    items.sort(key=lambda x: x["created_at"] or "", reverse=True)
    total = len(items)
    
    return {
        "items": items[offset:offset+limit],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.get("/api/reviews/pending")
def get_pending_reviews(limit: int = 20, offset: int = 0):
    items = []
    for analysis_id, state in analysis_store.items():
        hr = state.get("human_review", {})
        
        # The key in state is requires_human_approval or human_review.required
        is_pending = hr.get("status") == "pending_review"
        is_required = (hr.get("required") is True) or (state.get("requires_human_approval") is True) or (state.get("requires_human_review") is True)
        
        if is_required and is_pending:
            reasons = []
            mf = state.get("missing_fields", {})
            if mf.get("missing_fields"):
                reasons.append("Eksik bilgi tespit edildi.")
            
            r = state.get("routing", {})
            if r.get("needs_human_review"):
                reasons.append("Birim yönlendirmesi personel incelemesi gerektiriyor.")
                
            q = state.get("quality", {})
            if q.get("status") in ["fail", "warning"]:
                if state.get("warnings"):
                    reasons.extend(state["warnings"])
                else:
                    reasons.append("Kalite kontrol kriterleri tam olarak sağlanamadı.")
            
            doc = state.get("document", {})
            
            items.append({
                "analysis_id": analysis_id,
                "document_type": doc.get("document_type"),
                "process_intent": doc.get("process_intent"),
                "subject": state.get("draft", {}).get("draft", {}).get("subject") or state.get("draft", {}).get("subject", ""),
                "recommended_unit": r.get("recommended_unit"),
                "quality_status": q.get("status"),
                "review_reasons": reasons,
                "created_at": state.get("created_at")
            })
            
    items.sort(key=lambda x: x["created_at"] or "", reverse=True)
    total = len(items)
    
    return {
        "items": items[offset:offset+limit],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.get("/api/integrations/ebys/status")
def ebys_status():
    from backend.app.integrations.ebys import MockEBYSAdapter
    adapter = MockEBYSAdapter()
    return adapter.get_status()
