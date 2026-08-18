import React from 'react';
import { AnalysisResponse } from '../../types/analysis';
import { getLabel, DOC_TYPE_LABELS, STATUS_LABELS } from '../../utils/labels';
import { CheckCircle2, AlertTriangle, XCircle, Clock } from 'lucide-react';
import { Badge } from '../ui/Badge';

interface OverviewTabProps {
  analysis: AnalysisResponse;
}

export function OverviewTab({ analysis }: OverviewTabProps) {
  const document = analysis?.document || {} as any;
  const human_review = analysis?.human_review || {} as any;
  const routing = analysis?.routing || {} as any;
  const summary = analysis?.summary || {} as any;
  
  const renderStatus = (status: string) => {
    switch (status) {
      case "pending_review": return <Badge status="warning"><Clock size={12} className="mr-1 inline"/> {getLabel(status, STATUS_LABELS)}</Badge>;
      case "approved": return <Badge status="success"><CheckCircle2 size={12} className="mr-1 inline"/> {getLabel(status, STATUS_LABELS)}</Badge>;
      case "edited": return <Badge status="info"><CheckCircle2 size={12} className="mr-1 inline"/> {getLabel(status, STATUS_LABELS)}</Badge>;
      case "rejected": return <Badge status="fail"><XCircle size={12} className="mr-1 inline"/> {getLabel(status, STATUS_LABELS)}</Badge>;
      default: return <span className="text-muted">-</span>;
    }
  };

  const renderSummaryMode = (mode?: string) => {
    if (!mode) return null;
    if (mode === "deterministic") return <span className="text-xs text-muted ml-2">(Kural Tabanlı)</span>;
    if (mode === "llm_grounded") return <span className="text-xs text-muted ml-2">(Yapay Zeka Destekli)</span>;
    if (mode === "unavailable") return <span className="text-xs text-muted ml-2">(Kullanılamıyor)</span>;
    return null;
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="grid-2 sm:grid-4">
        <div className="flex flex-col gap-1 p-4 bg-bg-color border border-border-color rounded-md">
          <span className="text-xs text-muted font-medium">Evrak Türü</span>
          <span className="font-semibold text-text-main">{getLabel(document.document_type, DOC_TYPE_LABELS)}</span>
        </div>
        <div className="flex flex-col gap-1 p-4 bg-bg-color border border-border-color rounded-md">
          <span className="text-xs text-muted font-medium">İşlem Niyeti</span>
          <span className="font-semibold text-text-main">{getLabel(document.process_intent, DOC_TYPE_LABELS)}</span>
        </div>
        <div className="flex flex-col gap-1 p-4 bg-bg-color border border-border-color rounded-md">
          <span className="text-xs text-muted font-medium">Önerilen Birim</span>
          <span className="font-semibold text-text-main">{routing.recommended_unit || "Belirlenemedi"}</span>
        </div>
        <div className="flex flex-col gap-1 p-4 bg-bg-color border border-border-color rounded-md">
          <span className="text-xs text-muted font-medium">İnceleme Durumu</span>
          <div className="mt-1">{renderStatus(human_review.status)}</div>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex items-center">
          <h3 className="font-semibold text-text-main">Belge Özeti</h3>
          {renderSummaryMode(summary.summary_mode)}
        </div>
        <div className="p-4 bg-bg-color border border-border-color rounded-md text-sm leading-relaxed">
          {summary?.short_summary ? summary.short_summary : 
           (summary?.structured_summary ? "Yapılandırılmış özet mevcut (detay sekmesine bakınız)." : "Özet üretilemedi.")}
        </div>
      </div>
    </div>
  );
}


