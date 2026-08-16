import React, { useState } from 'react';
import { AnalysisResponse } from '../../types/analysis';
import { getLabel, DOC_TYPE_LABELS, STATUS_LABELS } from '../../utils/labels';
import { CheckCircle2, AlertTriangle, XCircle, Clock } from 'lucide-react';

interface OverviewTabProps {
  analysis: AnalysisResponse;
}

export function OverviewTab({ analysis }: OverviewTabProps) {
  const document = analysis.document || {} as any;
  const human_review = analysis.human_review || {} as any;
  const routing = analysis.routing || {} as any;
  const summary = analysis.summary || "";
  
  return (
    <div className="data-list">
      <div className="data-row">
        <div className="data-label">Evrak Türü</div>
        <div className="data-value">{getLabel(document.document_type, DOC_TYPE_LABELS)}</div>
      </div>
      <div className="data-row">
        <div className="data-label">İşlem Amacı</div>
        <div className="data-value">{getLabel(document.process_intent, DOC_TYPE_LABELS)}</div>
      </div>
      <div className="data-row">
        <div className="data-label">Önerilen Birim</div>
        <div className="data-value">{routing.recommended_unit || "Belirlenemedi"}</div>
      </div>
      <div className="data-row">
        <div className="data-label">İnsan İncelemesi</div>
        <div className="data-value">
          {human_review.required ? "Gerekli" : "Gerekli Değil"}
        </div>
      </div>
      <div className="data-row">
        <div className="data-label">Durum</div>
        <div className="data-value">
          {human_review.status === "pending_review" && <span className="badge badge-yellow"><Clock size={14}/> {getLabel(human_review.status, STATUS_LABELS)}</span>}
          {human_review.status === "approved" && <span className="badge badge-green"><CheckCircle2 size={14}/> {getLabel(human_review.status, STATUS_LABELS)}</span>}
          {human_review.status === "edited" && <span className="badge badge-blue"><CheckCircle2 size={14}/> {getLabel(human_review.status, STATUS_LABELS)}</span>}
          {human_review.status === "rejected" && <span className="badge badge-red"><XCircle size={14}/> {getLabel(human_review.status, STATUS_LABELS)}</span>}
        </div>
      </div>
      <div className="data-row" style={{ flexDirection: 'column', alignItems: 'flex-start', borderBottom: 'none' }}>
        <div className="data-label" style={{ marginBottom: '0.5rem' }}>Belge Özeti</div>
        <div style={{ backgroundColor: 'var(--bg-color)', padding: '1rem', borderRadius: '6px', fontSize: '0.875rem' }}>
          {summary?.short_summary ? summary.short_summary : 
           (summary?.structured_summary ? "Yapılandırılmış özet mevcut (detay sekmesine bakınız)." : "Özet üretilemedi.")}
        </div>
      </div>
    </div>
  );
}
