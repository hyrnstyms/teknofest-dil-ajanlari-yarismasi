from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from .schemas import (
    EBYSDocument,
    EBYSDraftRequest,
    EBYSRouteRequest,
    EBYSApprovalRequest,
    EBYSOperationResult
)

class EBYSAdapter(ABC):
    """
    Base abstraction for integrating KAMUAI with an EBYS (Electronic Document Management System).
    KAMUAI acts as a decision support layer over the EBYS.
    """
    
    @property
    @abstractmethod
    def adapter_type(self) -> str:
        pass
        
    @abstractmethod
    def get_document(self, document_id: str) -> Optional[EBYSDocument]:
        pass
        
    @abstractmethod
    def create_draft(self, request: EBYSDraftRequest) -> EBYSOperationResult:
        pass
        
    @abstractmethod
    def route_document(self, request: EBYSRouteRequest) -> EBYSOperationResult:
        pass
        
    @abstractmethod
    def send_for_approval(self, request: EBYSApprovalRequest) -> EBYSOperationResult:
        pass
        
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass
