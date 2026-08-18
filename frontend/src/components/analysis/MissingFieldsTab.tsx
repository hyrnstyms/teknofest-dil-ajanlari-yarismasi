import React from 'react';
import { AnalysisResponse } from '../../types/analysis';
import { getLabel, FIELD_LABELS } from '../../utils/labels';
import { AlertCircle, HelpCircle, CheckCircle2 } from 'lucide-react';

export function MissingFieldsTab({ analysis }: { analysis: AnalysisResponse }) {
  const mf = analysis?.missing_fields || {};
  const missing_fields = mf.missing_fields || [];
  const uncertain_fields = mf.uncertain_fields || [];
  const warnings = mf.warnings || [];
  const field_results = mf.field_results || {};
  const needs_human_review = !!mf.needs_human_review;

  const hasV2Data = Object.keys(field_results).length > 0;

  return (
    <div className="flex flex-col gap-6">
      
      {needs_human_review && (
        <div className="p-4 bg-warning-light text-warning rounded-md border border-warning flex items-start gap-3">
          <HelpCircle size={20} className="mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="font-semibold">İnsan Doğrulaması Gerekiyor</h4>
            <p className="text-sm mt-1">Bazı zorunlu alanlar tam olarak anlaşılamadı. İlgili personelin onay veya düzeltme yapması gerekmektedir.</p>
          </div>
        </div>
      )}

      {!needs_human_review && missing_fields.length === 0 && uncertain_fields.length === 0 && (
        <div className="p-4 bg-success-light text-success rounded-md border border-success flex items-center gap-3">
          <CheckCircle2 size={20} />
          <span>Zorunlu bilgiler açısından eksik alan tespit edilmedi.</span>
        </div>
      )}

      {/* V2 Fallback: If no field_results, show old way */}
      {!hasV2Data && (
        <>
          {missing_fields.length > 0 && (
            <div className="flex flex-col gap-2">
              <h4 className="font-semibold text-text-heading">Eksik Bilgiler</h4>
              {missing_fields.map(field => (
                <div key={field} className="p-3 bg-danger-light text-danger border border-danger rounded-md flex items-center gap-3">
                  <AlertCircle size={18} className="flex-shrink-0" />
                  <span className="font-medium">{getLabel(field, FIELD_LABELS)}</span>
                </div>
              ))}
            </div>
          )}

          {uncertain_fields.length > 0 && (
            <div className="flex flex-col gap-2">
              <h4 className="font-semibold text-text-heading">Doğrulanması Gereken Bilgiler</h4>
              {uncertain_fields.map(field => (
                <div key={field} className="p-3 bg-warning-light text-warning border border-warning rounded-md flex items-center gap-3">
                  <HelpCircle size={18} className="flex-shrink-0" />
                  <span><strong>{getLabel(field, FIELD_LABELS)}:</strong> Metin üzerinden doğrulanamadı.</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* V2 UI */}
      {hasV2Data && (
        <div className="flex flex-col gap-4">
           <h4 className="font-semibold text-text-heading">Alan Analizi Detayları</h4>
           <div className="grid-2 sm:grid-3">
            {Object.entries(field_results).map(([field, data]: [string, any]) => {
              const statusColor = data?.status === 'missing' ? 'border-danger bg-danger-light text-danger' :
                                  data?.status === 'uncertain' ? 'border-warning bg-warning-light text-warning' :
                                  'border-success bg-success-light text-success';
              const Icon = data?.status === 'missing' ? AlertCircle :
                           data?.status === 'uncertain' ? HelpCircle : CheckCircle2;
              
              return (
                <div key={field} className={`p-4 border rounded-md flex flex-col gap-2 ${statusColor}`}>
                  <div className="flex items-center gap-2 font-medium">
                    <Icon size={16} />
                    <span>{getLabel(field, FIELD_LABELS)}</span>
                  </div>
                  {data?.reason && <p className="text-xs opacity-90">{data.reason}</p>}
                </div>
              );
            })}
           </div>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="flex flex-col gap-2 mt-4">
          <h4 className="font-semibold text-text-heading">Uyarılar</h4>
          <ul className="list-disc pl-5 text-sm text-muted space-y-1">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}


