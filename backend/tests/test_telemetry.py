import pytest
from backend.app.telemetry.models import TelemetryRecord
from backend.app.telemetry.roi import calculate_roi_summary
import os

def test_roi_calculation(monkeypatch):
    monkeypatch.setenv("MANUAL_BASELINE_SECONDS", "300")
    
    r1 = TelemetryRecord(
        analysis_id="1",
        total_processing_ms=10000,  # 10s
        human_review_required=True,
        human_review_status="approved",
        human_review_seconds=60
    )
    r2 = TelemetryRecord(
        analysis_id="2",
        total_processing_ms=12000,  # 12s
        human_review_required=False
    )
    r3 = TelemetryRecord(
        analysis_id="3",
        total_processing_ms=8000,   # 8s
        human_review_required=True,
        human_review_status="edited",
        human_review_seconds=120
    )
    
    summary = calculate_roi_summary([r1, r2, r3])
    
    assert summary.processed_documents == 3
    # AI processing total = 30s. Average = 10s.
    assert summary.average_processing_seconds == 10.0
    
    # hr required for 2 out of 3 = 66%
    assert round(summary.human_review_required_rate, 2) == 0.67
    
    assert summary.approved_count == 1
    assert summary.edited_count == 1
    assert summary.rejected_count == 0
    
    # baseline = 3 * 300 = 900s manual
    # assisted = ai (30s) + review (60 + 120 = 180s) = 210s
    # saved = 900 - 210 = 690s
    assert summary.estimated_saved_seconds == 690
    assert summary.estimated_saved_percentage == (690 / 900) * 100
