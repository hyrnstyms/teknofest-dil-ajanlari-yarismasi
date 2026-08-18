import React from 'react';
import { AnalysisResponse, QualityCheck } from '../../types/analysis';
import { CheckCircle2, AlertTriangle, XCircle, ShieldAlert } from 'lucide-react';
import { getLabel, STATUS_LABELS } from '../../utils/labels';
import { Badge } from '../ui/Badge';

export function QualityTab({ analysis }: { analysis: AnalysisResponse }) {
  const q = analysis?.quality || {};
  const status = q.status || 'warning';
  const checks = q.checks || [];
  const requires_human_review = !!q.requires_human_review;
  const issues = q.issues || [];

  const getIcon = (st: string) => {
    if (st === 'pass') return <CheckCircle2 size={18} className="text-success" />;
    if (st === 'warning') return <AlertTriangle size={18} className="text-warning" />;
    return <XCircle size={18} className="text-danger" />;
  };

  return (
    <div className="flex flex-col gap-6">
      
      <div className="flex justify-between items-center pb-4 border-b border-border-color">
        <h4 className="text-heading font-semibold">Kalite Kontrol Özeti</h4>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted font-medium">Genel Durum:</span>
          <Badge status={status}>{getLabel(status, STATUS_LABELS)}</Badge>
        </div>
      </div>

      {requires_human_review && (
        <div className="p-4 bg-danger-light text-danger rounded-md border border-danger flex items-start gap-3">
          <ShieldAlert size={20} className="mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="font-semibold">Sistem Tutarsızlığı Tespit Edildi</h4>
            <p className="text-sm mt-1">Agentlar arası analiz sonuçlarında ciddi tutarsızlıklar var. Kesinlikle manuel inceleme yapılmalıdır.</p>
          </div>
        </div>
      )}

      {issues && issues.length > 0 && (
        <div className="flex flex-col gap-2">
          <h5 className="font-semibold text-text-heading text-sm">Tespit Edilen Kritik Sorunlar</h5>
          <ul className="list-disc pl-5 text-sm text-danger space-y-1">
            {issues.map((iss, i) => (
              <li key={i}>{iss}</li>
            ))}
          </ul>
        </div>
      )}
      
      <div className="flex flex-col gap-3">
        {checks && Object.entries(checks).map(([key, checkVal]: [string, any], idx: number) => {
          // checks could be array or dictionary depending on backend v1/v2 schema
          const check = typeof checkVal === 'object' && checkVal !== null ? checkVal : { status: 'warning', message: 'Bilinmeyen sonuç', name: key };
          const checkStatus = check.status || 'warning';
          const bgClass = checkStatus === 'fail' ? 'bg-danger-light border-danger' :
                          checkStatus === 'warning' ? 'bg-warning-light border-warning' :
                          'bg-white border-border-color';

          return (
            <div key={idx} className={`flex items-start gap-3 p-4 border rounded-md ${bgClass}`}>
              <div className="mt-0.5 flex-shrink-0">{getIcon(checkStatus)}</div>
              <div>
                <div className="font-semibold text-text-heading text-sm mb-1">{check.name || key}</div>
                <div className="text-sm text-muted leading-relaxed">{check.message || JSON.stringify(check)}</div>
              </div>
            </div>
          );
        })}
        {(!checks || Object.keys(checks).length === 0) && (
          <div className="text-muted text-sm p-4 text-center border rounded-md border-border-color">
            Detaylı kalite kontrol verisi bulunamadı.
          </div>
        )}
      </div>
    </div>
  );
}


