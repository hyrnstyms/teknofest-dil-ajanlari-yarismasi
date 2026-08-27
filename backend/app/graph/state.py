from typing import Any, Literal, List, Dict
from pydantic import BaseModel, Field

class DocumentState(BaseModel):
    # Core Identity
    document_id: str = ""
    raw_text: str = ""

    # Yeni Eklenenler (Diğer projeden)
    kurum_profili_id: str = Field(default="kaymakamlik_v1")
    muhatap: Dict[str, Any] | None = None
    muhatap_turu: Literal["kurum_alt", "kurum_ust", "kurum_ayni", "kurum_karisik", "gercek_kisi"] | None = None
    karar_kaynagi: Literal["kural_tabanli", "llm_tabanli"] | None = None

    # Component States
    document: Dict[str, Any] = Field(default_factory=dict)
    extraction: Dict[str, Any] = Field(default_factory=dict)
    legal_analysis: Dict[str, Any] = Field(default_factory=dict)
    missing_fields: Dict[str, Any] = Field(default_factory=dict)
    summary: Dict[str, Any] = Field(default_factory=dict)
    routing: Dict[str, Any] = Field(default_factory=dict)
    transfer_routing: Dict[str, Any] = Field(default_factory=dict)  # Track 3: kurumlar arası transfer
    draft: Dict[str, Any] = Field(default_factory=dict)
    quality: Dict[str, Any] = Field(default_factory=dict)
    human_review: Dict[str, Any] = Field(default_factory=dict)
    telemetry: Dict[str, Any] = Field(default_factory=dict)
    
    # Global Workflow state
    warnings: List[str] = Field(default_factory=list)
    node_timings: Dict[str, Any] = Field(default_factory=dict)

    # Deprecated Legacy fields (do not use in new code, use canonical nested fields above)
    file_name: str = ""
    document_type: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    document_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    entities: Dict[str, Any] = Field(default_factory=dict)
    missing_information: List[str] = Field(default_factory=list)
    legal_references: List[Dict[str, Any]] = Field(default_factory=list)
    legal_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    department: str = ""
    routing_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    routing_reason: str = ""
    draft_type: str = ""
    draft_text: str = ""
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    requires_human_review: bool = False
    status: str = ""


def build_legacy_state_view(state_dict: dict) -> dict:
    """
    Populates deprecated flat legacy fields in the API response dictionary
    from the canonical nested states (document, routing, draft, etc.).
    This ensures backward compatibility for older API clients.
    """
    doc = state_dict.get("document", {})
    ext = state_dict.get("extraction", {})
    legal = state_dict.get("legal_analysis", {})
    missing = state_dict.get("missing_fields", {})
    routing = state_dict.get("routing", {})
    draft = state_dict.get("draft", {})
    quality = state_dict.get("quality", {})
    hr = state_dict.get("human_review", {})

    state_dict["document_type"] = doc.get("document_type", state_dict.get("document_type", ""))
    state_dict["confidence"] = doc.get("confidence", state_dict.get("confidence", 0.0))
    state_dict["document_confidence"] = doc.get("confidence", state_dict.get("document_confidence", 0.0))
    
    state_dict["entities"] = ext.get("fields", state_dict.get("entities", {}))
    
    state_dict["missing_information"] = missing.get("missing_fields", state_dict.get("missing_information", []))
    
    state_dict["legal_references"] = legal.get("sources", state_dict.get("legal_references", []))
    state_dict["legal_confidence"] = legal.get("confidence", state_dict.get("legal_confidence", 0.0))
    
    state_dict["department"] = routing.get("recommended_unit", state_dict.get("department", ""))
    state_dict["routing_confidence"] = routing.get("confidence", state_dict.get("routing_confidence", 0.0))
    state_dict["routing_reason"] = routing.get("reason", state_dict.get("routing_reason", ""))
    
    state_dict["draft_type"] = draft.get("draft_type", state_dict.get("draft_type", ""))
    state_dict["draft_text"] = draft.get("body", state_dict.get("draft_text", ""))
    
    state_dict["quality_score"] = quality.get("quality_score", state_dict.get("quality_score", 0.0))
    
    # Resolving requires_human_review from components
    if hr.get("required"):
        state_dict["requires_human_review"] = True
    elif quality.get("requires_human_review"):
        state_dict["requires_human_review"] = True
    
    return state_dict