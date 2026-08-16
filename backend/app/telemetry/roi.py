import os
from typing import List
from backend.app.telemetry.models import TelemetryRecord, ROISummary

def calculate_roi_summary(records: List[TelemetryRecord]) -> ROISummary:
    summary = ROISummary()
    if not records:
        return summary
        
    summary.processed_documents = len(records)
    
    total_processing_ms = 0
    hr_required_count = 0
    
    for r in records:
        if r.total_processing_ms:
            total_processing_ms += r.total_processing_ms
        if r.human_review_required:
            hr_required_count += 1
            if r.human_review_status == "approved":
                summary.approved_count += 1
            elif r.human_review_status == "edited":
                summary.edited_count += 1
            elif r.human_review_status == "rejected":
                summary.rejected_count += 1

    summary.average_processing_seconds = (total_processing_ms / 1000.0) / summary.processed_documents
    summary.human_review_required_rate = hr_required_count / summary.processed_documents

    # ROI Calculation
    baseline_seconds = int(os.environ.get("MANUAL_BASELINE_SECONDS", "300"))
    
    total_estimated_manual = baseline_seconds * summary.processed_documents
    total_ai_processing = total_processing_ms / 1000.0
    
    total_human_review = 0
    for r in records:
        if r.human_review_seconds:
            total_human_review += r.human_review_seconds
            
    assisted_total = total_ai_processing + total_human_review
    saved = total_estimated_manual - assisted_total
    
    summary.estimated_saved_seconds = int(saved)
    if total_estimated_manual > 0:
        summary.estimated_saved_percentage = (saved / total_estimated_manual) * 100
    else:
        summary.estimated_saved_percentage = 0.0

    return summary
