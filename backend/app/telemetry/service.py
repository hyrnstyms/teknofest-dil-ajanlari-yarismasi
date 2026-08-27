from typing import Dict, Any, List
from datetime import datetime
from backend.app.telemetry.models import TelemetryRecord, ROISummary

class TelemetryService:
    def __init__(self):
        self.records: Dict[str, TelemetryRecord] = {}

    def build_record_from_state(
        self,
        analysis_id: str,
        state: Dict[str, Any],
    ) -> TelemetryRecord:
        """Kalıcı analiz state'inden ROI için telemetry kaydı oluştur."""
        record = TelemetryRecord(
            analysis_id=analysis_id,
            institution_id=(
                state.get("institution_id")
                or state.get("kurum_profili_id")
            ),
        )
        
        # We don't have processing_started_at in state but let's assume it was passed or just recorded now
        record.processing_finished_at = datetime.utcnow()
        
        timings = state.get("node_timings", {})
        total_ms = 0
        
        if "document_agent" in timings:
            record.document_agent_ms = timings["document_agent"].get("duration_ms", 0)
            total_ms += record.document_agent_ms
        if "extraction_agent" in timings:
            record.extraction_ms = timings["extraction_agent"].get("duration_ms", 0)
            total_ms += record.extraction_ms
        if "legal_agent" in timings:
            record.legal_ms = timings["legal_agent"].get("duration_ms", 0)
            total_ms += record.legal_ms
        if "missing_field_agent" in timings:
            record.missing_fields_ms = timings["missing_field_agent"].get("duration_ms", 0)
            total_ms += record.missing_fields_ms
        if "summary_agent" in timings:
            record.summary_ms = timings["summary_agent"].get("duration_ms", 0)
            total_ms += record.summary_ms
        if "routing_agent" in timings:
            record.routing_ms = timings["routing_agent"].get("duration_ms", 0)
            total_ms += record.routing_ms
        if "writing_agent" in timings:
            record.writing_ms = timings["writing_agent"].get("duration_ms", 0)
            total_ms += record.writing_ms
        if "quality_agent" in timings:
            record.quality_ms = timings["quality_agent"].get("duration_ms", 0)
            total_ms += record.quality_ms
            
        record.total_processing_ms = total_ms
        
        hr = state.get("human_review", {})
        record.human_review_required = hr.get("required", False)
        record.human_review_status = hr.get("status")
        
        # Start review timer if required
        if record.human_review_required:
            record.review_started_at = datetime.utcnow()
            
        return record

    def extract_from_state(self, analysis_id: str, state: Dict[str, Any]) -> TelemetryRecord:
        record = self.build_record_from_state(analysis_id, state)
        self.records[analysis_id] = record
        return record

    def update_human_review(self, analysis_id: str, status: str):
        if analysis_id in self.records:
            record = self.records[analysis_id]
            record.human_review_status = status
            record.review_action_at = datetime.utcnow()
            if record.review_started_at:
                delta = record.review_action_at - record.review_started_at
                record.human_review_seconds = int(delta.total_seconds())

    def get_record(self, analysis_id: str) -> TelemetryRecord:
        return self.records.get(analysis_id)

    def get_all_records(
        self,
        institution_id: str | None = None,
    ) -> List[TelemetryRecord]:
        records = list(self.records.values())
        if institution_id:
            return [
                record
                for record in records
                if record.institution_id == institution_id
            ]
        return records

telemetry_service = TelemetryService()
