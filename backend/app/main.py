from fastapi import Depends, FastAPI, HTTPException, UploadFile, File, Form, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal
from collections.abc import Iterator, MutableMapping
import uuid
import os
import shutil
from copy import deepcopy
from pathlib import Path
from datetime import datetime
from functools import lru_cache
import logging
import json

logger = logging.getLogger(__name__)

from backend.app.graph.workflow import KamuaiWorkflow
from backend.app.graph.state import build_legacy_state_view
from backend.app.telemetry.service import telemetry_service
from backend.app.telemetry.roi import calculate_roi_summary
from backend.app.ingestion.document_loader import load_file
from backend.app.agents.chat_agent import handle_draft_edit
from backend.app.agents.chat_agent import (
    handle_chat_message,
    resolve_chat_mode,
    stream_copilot_response,
)
from backend.app.institutions.profile_loader import (
    list_available_profiles,
    load_institution_profile,
)
from backend.app.agents.transfer_agent import TransferAgent
from backend.app.db.repository import AnalysisRepository
from backend.app.auth.router import router as auth_router
from backend.app.auth.dependencies import (
    CurrentUser,
    get_current_user,
    get_optional_current_user,
)
from backend.app.cases.institution_router import router as case_institution_router
from backend.app.cases.intelligence_bridge import register_intelligence_hooks
from backend.app.cases.intake import maybe_create_case_for_analysis
from backend.app.cases.public_router import router as public_case_router
from backend.app.cases.router import router as case_router
from backend.app.intelligence.preview_router import router as ai_preview_router
from backend.app.demo.router import router as demo_router


# Initialize FastAPI app
app = FastAPI(title="KAMUAI MVP API")

# Setup CORS
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# The Case domain is additive: existing Analysis routes below keep their
# original paths and response fields, while these routers expose the frozen
# workflow contract.
app.include_router(auth_router)
app.include_router(case_router)
app.include_router(public_case_router)
app.include_router(case_institution_router)
app.include_router(ai_preview_router, dependencies=[Depends(get_current_user)])
app.include_router(demo_router)
register_intelligence_hooks()

analysis_repository: AnalysisRepository | None = None


def get_analysis_repository() -> AnalysisRepository:
    """Lazily initialize persistence so non-DB endpoints remain importable."""
    global analysis_repository
    if analysis_repository is None:
        analysis_repository = AnalysisRepository()
    return analysis_repository


def _get_stored_analysis(analysis_id: str) -> dict[str, Any]:
    state = get_analysis_repository().get_analysis(analysis_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "analysis_not_found", "message": "İstenen analiz kaydı bulunamadı."},
        )
    return state


class _PersistentAnalysisStore(MutableMapping[str, dict[str, Any]]):
    """Legacy dict facade backed entirely by PostgreSQL.

    A few existing internal tests import ``analysis_store`` directly. Keeping
    this facade preserves that test seam without retaining any in-memory state;
    runtime endpoints use ``AnalysisRepository`` explicitly below.
    """

    def __getitem__(self, analysis_id: str) -> dict[str, Any]:
        state = get_analysis_repository().get_analysis(analysis_id)
        if state is None:
            raise KeyError(analysis_id)
        return state

    def __setitem__(self, analysis_id: str, state: dict[str, Any]) -> None:
        get_analysis_repository().save_analysis(analysis_id, state)

    def __delitem__(self, analysis_id: str) -> None:
        get_analysis_repository().delete_analysis(analysis_id)

    def __iter__(self) -> Iterator[str]:
        return iter(
            state["analysis_id"]
            for state in get_analysis_repository().list_analyses()
        )

    def __len__(self) -> int:
        return len(get_analysis_repository().list_analyses())

    def clear(self) -> None:
        get_analysis_repository().clear()


analysis_store: MutableMapping[str, dict[str, Any]] = _PersistentAnalysisStore()

TASLAK_BAGLAMI_GEREKLI_MESAJI = (
    "Önce bir evrak analiz edin, sonra taslak düzenleme özelliğini "
    "kullanabilirsiniz."
)

# Lazy initialization for workflow and other services
@lru_cache(maxsize=None)
def get_workflow(institution: str = "kaymakamlik"):
    return KamuaiWorkflow(institution=institution)


from backend.app.rag.retriever import (
    get_shared_embedding_service as _get_embedding_service_singleton,
    get_shared_qdrant_store as _get_qdrant_store_singleton,
)

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
    institution: Optional[str] = None

class RejectRequest(BaseModel):
    reason: Optional[str] = None

class EditRequest(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None

class ChatDraftEditRequest(BaseModel):
    message: str

class ChatMessageRequest(BaseModel):
    message: str
    analysis_id: Optional[str] = None
    institution: Optional[str] = None

class ChatStreamRequest(BaseModel):
    message: str
    analysis_id: Optional[str] = None
    case_id: Optional[str] = None
    institution: Optional[str] = None
    history: Optional[list[dict]] = None


class CopilotActionConfirmRequest(BaseModel):
    action_id: str
    type: Literal[
        "ROUTE_CASE",
        "START_CASE",
        "REQUEST_CITIZEN_INFO",
        "CREATE_OFFICIAL_DRAFT",
        "APPROVE_DRAFT",
        "FINALIZE_CASE",
    ]
    case_id: str
    payload: dict[str, Any]


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "KAMUAI API çalışıyor."}


@app.get("/ready")
def readiness_check():
    # Check services (selected LLM, Qdrant, Embedding) safely
    from backend.app.llm.settings import LLMSettings
    import requests

    ready = True
    provider = LLMSettings.get_provider()
    services = {
        "llm": {
            "provider": provider,
            "status": "unknown",
        },
        # Frontend geriye uyumluluğu: Header bu alanı genel LLM durumu
        # olarak okuyor. Gerçek sağlayıcı services.llm.provider alanındadır.
        "ollama": {"status": "unknown"},
        "qdrant": {"status": "unknown"},
        "embedding": {"status": "unknown"},
        "postgres": {"status": "unknown"},
    }
    
    # Check only the selected provider. EVREN check lists models and never
    # creates an inference request.
    try:
        if provider == "evren":
            if not LLMSettings.EVREN_BASE_URL or not LLMSettings.EVREN_API_KEY:
                raise RuntimeError("EVREN bağlantı ayarları eksik.")
            resp = requests.get(
                f"{LLMSettings.EVREN_BASE_URL.rstrip('/')}/models",
                headers={
                    "Authorization": (
                        f"Bearer {LLMSettings.EVREN_API_KEY}"
                    ),
                },
                timeout=5,
            )
        elif provider == "ollama":
            resp = requests.get(
                LLMSettings.OLLAMA_URL,
                timeout=5,
            )
        else:
            raise ValueError(
                f"Desteklenmeyen LLM provider: {provider}"
            )

        if resp.status_code == 200:
            llm_status = "ok"
        else:
            llm_status = "error"
            ready = False
    except Exception:
        llm_status = "unreachable"
        ready = False

    services["llm"]["status"] = llm_status
    services["ollama"]["status"] = llm_status
        
    # Try Qdrant and Embedding via RAG system
    try:
        from backend.app.rag.embedding_service import EmbeddingService
        from backend.app.rag.qdrant_store import QdrantStore
        
        try:
            emb = _get_embedding_service_singleton()
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
            store = _get_qdrant_store_singleton()
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

    try:
        get_analysis_repository().health_check()
        services["postgres"]["status"] = "ok"
    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {e}", exc_info=True)
        services["postgres"]["status"] = "unavailable"
        ready = False

    response_data = {
        "ready": ready,
        "services": services,
        "message": "Sistem servise hazır." if ready else "Bazı servisler hazır değil."
    }
    return JSONResponse(
        status_code=200,
        content=response_data
    )


@app.post("/api/documents/analyze-text")
def analyze_text(req: AnalyzeRequest, request: Request):
    try:
        doc_id = req.document_id or str(uuid.uuid4())
        wf = (
            get_workflow(req.institution)
            if req.institution
            else get_workflow()
        )
        
        final_state = wf.run(req.text, document_id=doc_id)
        
        analysis_id = str(uuid.uuid4())
        
        # Add basic audit history
        audit_history = [
            {"event": "analysis_completed", "timestamp": datetime.utcnow().isoformat(), "message": "Analiz tamamlandı."}
        ]
        
        final_state["analysis_id"] = analysis_id
        if req.institution:
            final_state.setdefault("institution_id", req.institution)
            final_state.setdefault("kurum_profili_id", req.institution)
        final_state["audit_history"] = audit_history
        final_state["created_at"] = datetime.utcnow().isoformat()
        
        final_state = build_legacy_state_view(final_state)
        
        # Telemetry extraction
        telemetry_service.extract_from_state(analysis_id, final_state)
        
        get_analysis_repository().save_analysis(analysis_id, final_state)
        case_link = maybe_create_case_for_analysis(request, analysis_id, final_state)
        if case_link:
            # Backward compatible additive fields for authenticated demo intake.
            # The persisted Analysis remains the AI work product; Case owns the
            # institutional lifecycle.
            final_state.update(case_link)
        return final_state
        
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "analysis_error", "message": f"Analiz sırasında bir hata oluştu: {str(e)}"})


@app.post("/api/documents/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    institution: Optional[str] = Form(None),
):
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
        req = AnalyzeRequest(
            text=raw_text,
            document_id=file.filename,
            institution=institution,
        )
        return analyze_text(req, request)
        
    except HTTPException:
        raise
    except Exception as e:
        if file_path and file_path.exists():
            os.remove(file_path)
        raise HTTPException(status_code=500, detail={"code": "upload_error", "message": f"Dosya işlenirken hata oluştu: {str(e)}"})


@app.get("/api/analysis/{analysis_id}")
def get_analysis(analysis_id: str):
    return _get_stored_analysis(analysis_id)


@app.post("/api/analysis/{analysis_id}/approve")
def approve_analysis(analysis_id: str):
    state = _get_stored_analysis(analysis_id)
    
    if "human_review" not in state:
        state["human_review"] = {}
        
    state["human_review"]["status"] = "approved"
    
    # Audit log
    state.setdefault("audit_history", []).append({
        "event": "approved",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Analiz ve taslak personel tarafından onaylandı."
    })
    
    telemetry_service.update_human_review(analysis_id, "approved")
    get_analysis_repository().update_analysis_with_event(
        analysis_id, state, "approve", {}
    )
    
    return {"status": "success", "message": "Analiz ve taslak personel tarafından onaylandı."}


@app.get("/api/analysis/{analysis_id}/export/docx")
def export_docx(analysis_id: str):
    """Onaylı taslağı biçimlendirilmiş .docx dosyası olarak dışa aktarır."""
    state = _get_stored_analysis(analysis_id)

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
    state = _get_stored_analysis(analysis_id)
    
    if "human_review" not in state:
        state["human_review"] = {}
        
    state["human_review"]["status"] = "rejected"
    state["human_review"]["reject_reason"] = req.reason
    
    # Audit log
    state.setdefault("audit_history", []).append({
        "event": "rejected",
        "timestamp": datetime.utcnow().isoformat(),
        "message": f"Analiz reddedildi. Sebep: {req.reason or 'Belirtilmedi'}"
    })
    
    telemetry_service.update_human_review(analysis_id, "rejected")
    get_analysis_repository().update_analysis_with_event(
        analysis_id, state, "reject", {"reason": req.reason}
    )
    
    return {"status": "success", "message": "Analiz reddedildi."}


@app.post("/api/analysis/{analysis_id}/edit")
def edit_analysis(analysis_id: str, req: EditRequest):
    state = _get_stored_analysis(analysis_id)
    
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
    state.setdefault("audit_history", []).append({
        "event": "draft_edited",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Taslak metin üzerinde manuel düzenleme yapıldı."
    })
    
    telemetry_service.update_human_review(analysis_id, "edited")
    get_analysis_repository().update_analysis_with_event(
        analysis_id, state, "edit", req.model_dump(exclude_none=True)
    )
    
    return {"status": "success", "message": "Taslak güncellendi."}


@app.post("/api/analysis/{analysis_id}/chat/edit-draft")
def chat_edit_draft(analysis_id: str, req: ChatDraftEditRequest):
    current_state = _get_stored_analysis(analysis_id)
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

        get_analysis_repository().update_analysis_with_event(
            analysis_id,
            candidate_state,
            "chat_edit",
            {"message": req.message, "updated_draft": updated_draft},
        )

    return result


@app.post("/api/chat/message")
def chat_message(req: ChatMessageRequest):
    """Mod A/B/C/D mesajlarını tek ve kararlı bir yanıt sözleşmesiyle işler."""

    current_state = None
    current_draft = None
    workflow_context: Dict[str, Any] = {}
    if req.institution:
        workflow_context["institution"] = req.institution

    if req.analysis_id is not None:
        stored_state = _get_stored_analysis(req.analysis_id)
        state_institution = stored_state.get("kurum_profili_id")
        context_matches = not req.institution or state_institution == req.institution
        if context_matches:
            current_state = stored_state
            current_draft = stored_state.get("draft")
            workflow_context.update({
                "analysis_state": stored_state,
                "extraction": stored_state.get("extraction", {}),
                "routing": stored_state.get("routing", {}),
                "kurum_profili_id": state_institution or "kaymakamlik_v1",
                "muhatap": stored_state.get("muhatap"),
                "muhatap_turu": stored_state.get("muhatap_turu"),
            })

    mode = resolve_chat_mode(req.message)
    draft_edit_requested = mode == "taslak_duzenleme"

    if draft_edit_requested and (
        req.analysis_id is None
        or not isinstance(current_draft, dict)
        or not current_draft
    ):
        return {
            "mode": mode,
            "status": "rejected",
            "sohbet_yaniti": TASLAK_BAGLAMI_GEREKLI_MESAJI,
            "updated_draft": None,
            "validation_errors": [],
            "validation_warnings": [],
        }

    result = handle_chat_message(
        req.message,
        current_draft=current_draft,
        workflow_context=workflow_context,
        resolved_mode=mode,
    )

    if isinstance(result, dict):
        response_data = {"mode": mode, **result}
    else:
        response_data = {
            "mode": mode,
            "status": "answered",
            "sohbet_yaniti": result,
            "updated_draft": None,
            "validation_errors": [],
            "validation_warnings": [],
        }

    updated_draft = response_data.get("updated_draft")
    if (
        mode == "taslak_duzenleme"
        and response_data.get("status") == "applied"
        and isinstance(updated_draft, dict)
        and current_state is not None
        and req.analysis_id is not None
    ):
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
        get_analysis_repository().update_analysis_with_event(
            req.analysis_id,
            candidate_state,
            "chat_edit",
            {"message": req.message, "updated_draft": updated_draft},
        )

    return response_data


@app.post("/api/copilot/stream")
def copilot_stream(
    req: ChatStreamRequest,
    current_user: CurrentUser | None = Depends(get_optional_current_user),
):
    """Copilot streaming endpoint with history and true SSE."""
    current_state = None
    current_draft = None
    if req.case_id is not None:
        if current_user is None:
            raise HTTPException(
                status_code=401,
                detail={"code": "authentication_required", "message": "Case erişimi için giriş yapın."},
            )
        from backend.app.copilot.service import load_case_state

        current_state = load_case_state(current_user, req.case_id)
        current_draft = current_state.get("draft")
        if not current_draft and current_state.get("drafts"):
            current_draft = current_state["drafts"][-1].get("content")
    elif req.analysis_id is not None:
        try:
            stored_state = _get_stored_analysis(req.analysis_id)
            state_institution = stored_state.get("institution_id") or stored_state.get("kurum_profili_id")
            requested_institution = current_user.institution_id if current_user else req.institution
            if not requested_institution or state_institution == requested_institution:
                current_state = stored_state
                current_draft = stored_state.get("draft")
        except HTTPException:
            pass

    user_context = None
    institution_id = req.institution
    if current_user is not None:
        from backend.app.copilot.service import user_context as build_user_context

        user_context = build_user_context(current_user)
        institution_id = current_user.institution_id

    return StreamingResponse(
        stream_copilot_response(
            message=req.message,
            history=req.history or [],
            analysis_state=current_state,
            institution_id=institution_id,
            current_draft=current_draft,
            user_context=user_context,
        ),
        media_type="text/event-stream"
    )


@app.post("/api/copilot/actions/confirm")
def confirm_copilot_action(
    req: CopilotActionConfirmRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    from backend.app.cases.errors import CaseError
    from backend.app.copilot.service import execute_confirmed_action

    try:
        return execute_confirmed_action(
            current_user,
            action_id=req.action_id,
            action_type=req.type,
            case_id=req.case_id,
            payload=req.payload,
        )
    except CaseError as exc:
        raise exc.to_http_exception() from exc


@app.get("/api/system/status")
def system_status():
    from backend.app.llm.settings import LLMSettings

    provider = LLMSettings.get_provider()
    if provider == "evren":
        llm_model = LLMSettings.EVREN_MODEL_FAST
        llm_models = {
            "fast": LLMSettings.EVREN_MODEL_FAST,
            "legal": LLMSettings.EVREN_MODEL_LARGE,
        }
    else:
        llm_model = LLMSettings.OLLAMA_MODEL
        llm_models = {
            "default": LLMSettings.OLLAMA_MODEL,
        }
    
    # Default values
    qdrant_total = 0
    qdrant_legal = 0
    qdrant_docs = 0
    legal_coverage = None
    
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
        if qdrant_legal > 0:
            legal_coverage = store.legal_coverage()
    except Exception as e:
        logger.error(f"System status Qdrant check failed: {e}", exc_info=True)
        pass
        
    if not qdrant_legal:
        index_status = "empty"
        index_msg = "Mevzuat indeksi oluşturulmadı."
    elif legal_coverage and legal_coverage["complete"]:
        index_status = "complete"
        index_msg = "Zorunlu mevzuat kaynakları indekslendi."
    elif legal_coverage is None:
        index_status = "unknown"
        index_msg = "Mevzuat kapsamı doğrulanamadı."
    else:
        index_status = "partial"
        missing = legal_coverage.get("missing_sources", [])
        index_msg = "Eksik mevzuat kaynakları: " + ", ".join(missing)
    
    return {
        "api": "online",
        "llm_provider": provider,
        "ollama": LLMSettings.OLLAMA_URL,
        "llm_model": llm_model,
        "llm_models": llm_models,
        "embedding_model": "BAAI/bge-m3",
        "embedding_dimension": 1024,
        "qdrant": {
            "total_points": qdrant_total,
            "legal_points": qdrant_legal,
            "document_points": qdrant_docs,
            "index_status": index_status,
            "message": index_msg,
            "coverage": legal_coverage,
        }
    }


@app.get("/api/evaluation/summary")
def get_evaluation_summary():
    """Son tamamlanmış offline evaluation artifact'ını model çağrısı yapmadan döndürür."""
    report_path = Path("reports/evaluation/final_evaluation.json")
    if not report_path.exists():
        return {
            "available": False,
            "message": "Tamamlanmış final offline değerlendirme raporu bulunmuyor.",
        }
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("Evaluation summary okunamadı: %s", exc)
        return {"available": False, "message": "Offline değerlendirme raporu okunamadı."}
    return {"available": True, "report": payload}

@app.get("/api/roi/summary")
def roi_summary(institution_id: Optional[str] = None):
    if institution_id:
        states = get_analysis_repository().list_analyses(
            institution_id=institution_id,
        )
        records = [
            telemetry_service.build_record_from_state(
                state["analysis_id"],
                state,
            )
            for state in states
        ]
    else:
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


def _analysis_list_subject(state: Dict[str, Any]) -> str:
    draft_state = state.get("draft")
    if isinstance(draft_state, dict):
        structured_draft = draft_state.get("draft")
        if isinstance(structured_draft, dict) and structured_draft.get("subject"):
            return str(structured_draft["subject"])
        if draft_state.get("subject"):
            return str(draft_state["subject"])

    extraction = state.get("extraction")
    if isinstance(extraction, dict):
        fields = extraction.get("fields")
        if isinstance(fields, dict):
            subject_field = fields.get("subject")
            if isinstance(subject_field, dict) and subject_field.get("value"):
                return str(subject_field["value"])

    summary = state.get("summary")
    if isinstance(summary, dict):
        structured_summary = summary.get("structured_summary")
        if isinstance(structured_summary, dict) and structured_summary.get("subject"):
            return str(structured_summary["subject"])

    document = state.get("document")
    if isinstance(document, dict) and document.get("subject_excerpt"):
        return str(document["subject_excerpt"])

    return ""



# ── QR DOĞRULAMA ENDPOINTİ (tokensiz, kişisel veri YOK) ─────────────────
@app.get("/api/verify/{evrak_id}")
def verify_document(evrak_id: str):
    """
    DOCX içindeki QR kodundan taranan endpoint.
    Tokensiz — sadece evrak türü, tarih ve durum etiket bilgisi döndürür.
    Kişisel veri (isim, TC, ham metin) YOK.

    evrak_id: analysis UUID veya EVRAG-XXXX tracking_code olabilir.
    """
    # 1. Case DB'de tracking_code olarak ara (EVRAG-XXXX format)
    try:
        from backend.app.cases.runtime import get_case_engine
        from backend.app.cases.enums import PUBLIC_STATUS_LABELS
        from sqlalchemy import select
        from backend.app.db.case_models import CaseRecord

        engine_obj = get_case_engine()
        with engine_obj.session_factory() as session:
            stmt = select(CaseRecord).where(CaseRecord.tracking_code == evrak_id)
            row = session.scalars(stmt).first()
            if row is not None:
                return {
                    "found": True,
                    "evrak_id": evrak_id,
                    "source": "case",
                    "document_type": row.source_type,
                    "received_at": row.received_at.strftime("%d.%m.%Y") if row.received_at else None,
                    "status": row.workflow_status,
                    "status_label": PUBLIC_STATUS_LABELS.get(row.workflow_status, row.workflow_status),
                    "institution_id": row.institution_id,
                }
    except Exception:
        pass  # Case DB erişilemiyorsa Analysis DB'e düş

    # 2. Analysis UUID olarak ara
    state = get_analysis_repository().get_analysis(evrak_id)
    if state is not None:
        doc = state.get("document", {})
        return {
            "found": True,
            "evrak_id": evrak_id,
            "source": "analysis",
            "document_type": doc.get("document_type"),
            "received_at": state.get("created_at"),
            "status": state.get("status"),
            "status_label": state.get("status"),
            "institution_id": state.get("institution_id") or state.get("kurum_profili_id"),
        }

    raise HTTPException(
        status_code=404,
        detail={
            "code": "evrak_not_found",
            "message": f"'{evrak_id}' kimlikli evrak bulunamadı.",
        },
    )

@app.get("/api/admin/stats")
def get_admin_stats(institution_id: Optional[str] = None):
    """
    Yönetici paneli için istatistikleri döndürür.
    """
    from backend.app.cases.runtime import get_case_engine
    from backend.app.db.case_models import CaseRecord, CaseEvent, CaseDraft
    from sqlalchemy import select, func
    from datetime import datetime, timezone

    engine_obj = get_case_engine()
    with engine_obj.session_factory() as session:
        # Tüm case'leri (veya kuruma ait olanları) al
        base_query = select(CaseRecord)
        if institution_id:
            base_query = base_query.where(CaseRecord.institution_id == institution_id)
        
        all_cases = session.scalars(base_query).all()
        total_cases = len(all_cases)
        
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_cases = sum(1 for c in all_cases if c.created_at >= today_start)
        
        # Dağılım hesapla
        dist = {}
        for c in all_cases:
            key = (c.institution_id, c.current_department_code)
            dist[key] = dist.get(key, 0) + 1
            
        department_distribution = [
            {"institution_id": inst, "department_code": dept, "count": count}
            for (inst, dept), count in dist.items()
        ]
        
        # Ortalama işlem süresi
        completed = [c for c in all_cases if c.workflow_status in ("COMPLETED", "CLOSED")]
        total_seconds = 0
        valid_times = 0
        for c in completed:
            end_time = c.closed_at or c.updated_at
            if end_time and c.created_at:
                diff = (end_time - c.created_at).total_seconds()
                if diff > 0:
                    total_seconds += diff
                    valid_times += 1
        
        average_processing_hours = (total_seconds / 3600.0) / valid_times if valid_times > 0 else 0.0
        
        # Human review oranı (İnsan müdahalesi gören evraklar)
        human_review_ratio = 0.0
        if total_cases > 0:
            current_case_ids = {c.id for c in all_cases}
            user_events_query = select(CaseEvent.case_id).where(CaseEvent.actor_type == "USER").where(CaseEvent.case_id.in_(current_case_ids)).distinct()
            user_case_ids = set(session.scalars(user_events_query).all())
            human_reviewed_cases = len(user_case_ids)
            human_review_ratio = human_reviewed_cases / total_cases
            
        # Taslak metrikleri
        drafts_query = select(CaseDraft)
        if institution_id:
            case_ids_subquery = select(CaseRecord.id).where(CaseRecord.institution_id == institution_id)
            drafts_query = drafts_query.where(CaseDraft.case_id.in_(case_ids_subquery))
            
        drafts = session.scalars(drafts_query).all()
        approved_drafts = sum(1 for d in drafts if d.status == "APPROVED")
        
        # Reddedilen / Revizyon İstenen taslak olayları
        rejected_query = select(func.count(CaseEvent.id)).where(CaseEvent.event_type == "DRAFT_REVISION_REQUESTED")
        if institution_id:
            rejected_query = rejected_query.where(CaseEvent.case_id.in_(case_ids_subquery))
        rejected_events = session.scalars(rejected_query).first() or 0
        
        return {
            "total_cases": total_cases,
            "today_cases": today_cases,
            "average_processing_hours": round(average_processing_hours, 2),
            "human_review_ratio": round(human_review_ratio, 2),
            "department_distribution": department_distribution,
            "draft_metrics": {
                "approved": approved_drafts,
                "rejected": rejected_events
            }
        }


@app.get("/api/analyses")
def get_analyses(
    limit: int = 20, 
    offset: int = 0, 
    institution_id: Optional[str] = None,
    status: Optional[str] = None, 
    document_type: Optional[str] = None, 
    process_intent: Optional[str] = None
):
    items = []
    states = get_analysis_repository().list_analyses(
        institution_id=institution_id,
        status=status,
        document_type=document_type,
        process_intent=process_intent,
    )
    for state in states:
        analysis_id = state["analysis_id"]
        doc = state.get("document", {})
        hr = state.get("human_review", {})
        q = state.get("quality", {})
        r = state.get("routing", {})
        t = state.get("telemetry", {})
        
        items.append({
            "analysis_id": analysis_id,
            "institution_id": state.get("institution_id") or state.get("kurum_profili_id"),
            "document_id": state.get("document_id", ""),
            "document_type": doc.get("document_type"),
            "process_intent": doc.get("process_intent"),
            "subject": _analysis_list_subject(state),
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
    for state in get_analysis_repository().list_pending_reviews():
        analysis_id = state["analysis_id"]
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
                "subject": _analysis_list_subject(state),
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


# ---------------------------------------------------------------------------
# Track 3 — Çoklu Kurum Endpoint'leri
# ---------------------------------------------------------------------------

class TransferRequest(BaseModel):
    kaynak_kurum: str
    hedef_kurum: str
    konu: str
    evrak_ozeti: str
    process_intent: Optional[str] = "iletim"


@app.get("/api/institutions")
def list_institutions():
    """
    Sistemde tanımlı tüm kurum profillerini listeler.
    data/institutions/ altında YAML'u olan kurumları döndürür.
    """
    try:
        profiles = list_available_profiles()
        institution_options = []
        for profile_id in profiles:
            profile = load_institution_profile(profile_id)
            ui_config = profile.raw.get("ui_config", {})
            if not isinstance(ui_config, dict):
                ui_config = {}
            display_name = ui_config.get("institution_display_name")
            institution_options.append({
                "id": profile_id,
                "label": display_name or profile_id.replace("_", " ").title(),
                "ui_config": ui_config,
            })
        return {
            "institutions": profiles,
            "institution_options": institution_options,
            "count": len(profiles),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "institutions_error", "message": str(e)}
        )


@app.get("/api/institutions/{kurum_id}/profile")
def get_institution_profile(kurum_id: str):
    """
    Belirtilen kurumun profil detaylını döndürür.
    """
    try:
        profile = load_institution_profile(kurum_id)
        return {
            "kurum_id": kurum_id,
            "kurum_adi": profile.kurum_adi,
            "kurum_turu": profile.kurum_turu,
            "birimler": profile.birimler,
            "evrak_turleri": profile.evrak_turleri,
            "yazi_turleri": profile.yazi_turleri,
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "institution_not_found",
                "message": f"Kurum profili bulunamadı: '{kurum_id}'"
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "profile_parse_error", "message": str(e)}
        )


@app.post("/api/institutions/transfer")
def institution_transfer(req: TransferRequest):
    """
    Kurumlar arası evrak transfer kararı üretir.

    Örnek: Kaymakamılıktan Belediye'ye yapı ruhsatı ile
    ilgili resmî yazı transferi.
    """
    try:
        agent = TransferAgent()
        result = agent.transfer(
            kaynak_kurum=req.kaynak_kurum,
            hedef_kurum=req.hedef_kurum,
            konu=req.konu,
            evrak_ozeti=req.evrak_ozeti,
            process_intent=req.process_intent or "iletim",
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "transfer_error", "message": str(e)}
        )
