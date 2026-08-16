from typing import TypedDict, Any

class DocumentState(TypedDict, total=False):
    # Core Identity
    document_id: str
    raw_text: str

    # Component States
    document: dict
    extraction: dict
    legal_analysis: dict
    missing_fields: dict
    summary: dict
    routing: dict
    draft: dict
    quality: dict
    human_review: dict
    telemetry: dict
    
    # Global Workflow state
    warnings: list[str]
    node_timings: dict

    # Legacy fields (to not break existing agents during transition, mapped later via adapter)
    file_name: str
    document_type: str
    document_confidence: float
    entities: dict[str, Any]
    missing_information: list[str]
    legal_references: list[dict[str, Any]]
    legal_confidence: float
    department: str
    routing_confidence: float
    routing_reason: str
    draft_type: str
    draft_text: str
    quality_score: float
    requires_human_review: bool
    status: str