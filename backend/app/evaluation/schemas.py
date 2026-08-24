from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class GoldDocument(BaseModel):
    id: str
    evrak_turu_dogru: str
    hedef_birim_dogru: Optional[str] = None
    uretim_yontemi: Optional[str] = None
    eksik_alan_var_mi: Optional[bool] = None
    zorluk: Optional[str] = None
    metin: str
    beklenen_alanlar: Dict[str, Any] = Field(default_factory=dict)
    
class PredictedDocument(BaseModel):
    id: str
    evrak_turu: Optional[str] = None
    hedef_birim: Optional[str] = None
    ranked_units: List[str] = Field(default_factory=list)
    eksik_alan_var_mi: Optional[bool] = None
    extracted_fields: Dict[str, Any] = Field(default_factory=dict)
    
class CoverageInfo(BaseModel):
    total_records: int = 0
    evaluable_records: int = 0
    skipped_records: int = 0
    coverage_rate: float = 0.0
    unsupported_labels: List[str] = Field(default_factory=list)
    skip_reasons: Dict[str, int] = Field(default_factory=dict)

class EvaluationReport(BaseModel):
    dataset_name: str
    status: str = "pass"
    coverage: CoverageInfo = Field(default_factory=CoverageInfo)
    metrics: Dict[str, float] = Field(default_factory=dict)
    diagnostics: Dict[str, Any] = Field(default_factory=dict)
    unsupported: Dict[str, Any] = Field(default_factory=dict)
    runtime_failures: int = 0
    errors: List[str] = Field(default_factory=list)
    failure_examples: List[Dict[str, Any]] = Field(default_factory=list)
