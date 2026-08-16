from pydantic import BaseModel
from typing import Optional, Any, Dict

class EBYSDocument(BaseModel):
    document_id: str
    metadata: Dict[str, Any]
    content: str

class EBYSDraftRequest(BaseModel):
    document_id: str
    draft_text: str
    subject: str

class EBYSRouteRequest(BaseModel):
    document_id: str
    target_unit: str
    reason: Optional[str] = None

class EBYSApprovalRequest(BaseModel):
    document_id: str
    draft_id: Optional[str] = None
    status: str

class EBYSOperationResult(BaseModel):
    success: bool
    adapter_type: str
    operation: str
    message: str
    data: Optional[Dict[str, Any]] = None
