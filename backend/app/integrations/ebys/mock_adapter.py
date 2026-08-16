from typing import Dict, Any, Optional
from .base import EBYSAdapter
from .schemas import (
    EBYSDocument,
    EBYSDraftRequest,
    EBYSRouteRequest,
    EBYSApprovalRequest,
    EBYSOperationResult
)

class MockEBYSAdapter(EBYSAdapter):
    """
    Mock adapter for demonstrating KAMUAI EBYS integration capabilities.
    Does not actually connect to any production systems.
    """
    
    @property
    def adapter_type(self) -> str:
        return "mock"
        
    def get_document(self, document_id: str) -> Optional[EBYSDocument]:
        return EBYSDocument(
            document_id=document_id,
            metadata={"source": "mock_ebys", "status": "received"},
            content="Mock document content for demonstration."
        )
        
    def create_draft(self, request: EBYSDraftRequest) -> EBYSOperationResult:
        return EBYSOperationResult(
            success=True,
            adapter_type=self.adapter_type,
            operation="create_draft",
            message="Demo EBYS adaptörü üzerinden taslak oluşturma işlemi simüle edildi.",
            data={"draft_id": "mock-draft-123"}
        )
        
    def route_document(self, request: EBYSRouteRequest) -> EBYSOperationResult:
        return EBYSOperationResult(
            success=True,
            adapter_type=self.adapter_type,
            operation="route_document",
            message=f"Demo EBYS adaptörü üzerinden evrak {request.target_unit} birimine yönlendirildi."
        )
        
    def send_for_approval(self, request: EBYSApprovalRequest) -> EBYSOperationResult:
        return EBYSOperationResult(
            success=True,
            adapter_type=self.adapter_type,
            operation="send_for_approval",
            message="Demo EBYS adaptörü üzerinden onay işlemi simüle edildi."
        )
        
    def get_status(self) -> Dict[str, Any]:
        return {
            "adapter_type": self.adapter_type,
            "connected": False,
            "mode": "demo",
            "message": "Gerçek bir EBYS bağlantısı yapılandırılmamıştır."
        }
