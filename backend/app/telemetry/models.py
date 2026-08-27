from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

class TelemetryRecord(BaseModel):
    analysis_id: str
    institution_id: Optional[str] = None
    processing_started_at: Optional[datetime] = None
    processing_finished_at: Optional[datetime] = None
    total_processing_ms: Optional[int] = None
    
    document_agent_ms: Optional[int] = None
    extraction_ms: Optional[int] = None
    legal_ms: Optional[int] = None
    missing_fields_ms: Optional[int] = None
    summary_ms: Optional[int] = None
    routing_ms: Optional[int] = None
    writing_ms: Optional[int] = None
    quality_ms: Optional[int] = None

    human_review_required: Optional[bool] = None
    human_review_status: Optional[str] = None
    review_started_at: Optional[datetime] = None
    review_action_at: Optional[datetime] = None
    human_review_seconds: Optional[int] = None

    llm_call_count: Optional[int] = None

class ROISummary(BaseModel):
    processed_documents: int = 0
    average_processing_seconds: float = 0.0
    human_review_required_rate: float = 0.0
    approved_count: int = 0
    edited_count: int = 0
    rejected_count: int = 0
    estimated_saved_seconds: int = 0
    estimated_saved_percentage: Optional[float] = None
