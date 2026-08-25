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

    # Legacy fields
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