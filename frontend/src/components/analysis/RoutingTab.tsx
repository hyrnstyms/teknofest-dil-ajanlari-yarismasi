import React from 'react';
import { AnalysisResponse } from '../../types/analysis';
import { ArrowRightCircle, AlertTriangle, Building2, HelpCircle } from 'lucide-react';
import { Badge } from '../ui/Badge';

export function RoutingTab({ analysis }: { analysis: AnalysisResponse }) {
  const routing = analysis?.routing || {};

  const getConfidenceLabel = (type?: string) => {
    if (type === 'rule_margin') return 'Yönlendirme Belirsizliği';
    return type || 'Eşleşme Tipi';
  };

  return (
    <div className="flex flex-col gap-6">
      
      {routing.needs_human_review ? (
        <div className="p-4 bg-warning-light text-warning rounded-md border border-warning flex items-start gap-3">
          <HelpCircle size={24} className="mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="font-semibold text-lg mb-1">Manuel Yönlendirme Gerekli</h4>
            <p className="text-sm">Otomatik yönlendirme kuralları kesin bir sonuç üretemedi. Personel kararı gereklidir.</p>
            {routing.ambiguity_reason && (
              <p className="text-sm mt-2 font-medium">Gerekçe: {routing.ambiguity_reason}</p>
            )}
          </div>
        </div>
      ) : routing.recommended_unit ? (
        <div className="p-6 bg-accent-light border border-accent/20 rounded-md flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-accent text-white rounded-full flex items-center justify-center">
              <Building2 size={24} />
            </div>
            <div>
              <h4 className="text-sm text-muted font-medium mb-1">Önerilen Hedef Birim</h4>
              <h2 className="text-xl font-bold text-text-heading">{routing.recommended_unit}</h2>
            </div>
          </div>
          {routing.registry_source === 'demo' && (
            <Badge status="info">Demo Birim</Badge>
          )}
        </div>
      ) : (
        <div className="p-4 bg-danger-light text-danger rounded-md border border-danger flex items-start gap-3">
          <AlertTriangle size={20} className="mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="font-semibold">Birim Belirlenemedi</h4>
            <p className="text-sm mt-1">{routing.reason || "Yönlendirme kararı alınamadı."}</p>
          </div>
        </div>
      )}

      {/* Main Justification */}
      {routing.reason && (
        <div className="bg-bg-color border border-border-color rounded-md p-4 flex flex-col gap-2">
          <span className="text-sm text-muted font-medium">Yönlendirme Gerekçesi</span>
          <p className="text-sm text-text-main leading-relaxed">{routing.reason}</p>
        </div>
      )}

      {/* V2 Routing Details */}
      <div className="grid-2">
        {(routing.routing_score !== undefined || routing.routing_confidence_type) && (
          <div className="bg-bg-color border border-border-color rounded-md p-4 flex flex-col gap-3">
            <h4 className="font-semibold text-sm border-b border-border-color pb-2">Skorlama Detayları</h4>
            
            {routing.routing_score !== undefined && (
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted">Kural Eşleşme Skoru</span>
                <span className="font-medium bg-white px-2 py-1 rounded border border-border-color">{routing.routing_score}</span>
              </div>
            )}
            
            {routing.routing_confidence_type && (
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted">{getConfidenceLabel(routing.routing_confidence_type)}</span>
                <span className="font-medium text-warning">{routing.routing_confidence_type === 'rule_margin' ? 'Yüksek' : 'Normal'}</span>
              </div>
            )}

            {routing.score_breakdown && routing.score_breakdown.length > 0 && (
              <div className="mt-2 text-xs">
                <span className="text-muted mb-1 block">Skor Kırılımı:</span>
                <ul className="space-y-1">
                  {routing.score_breakdown.map((sb: any, i: number) => (
                    <li key={i} className="flex justify-between border-b border-border-light pb-1">
                      <span>{sb?.signal || "Belirsiz Sinyal"}</span>
                      <span className="font-mono">{sb?.value >= 0 ? `+${sb.value}` : sb?.value}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Alternative Units */}
        {routing.ranked_units && routing.ranked_units.length > 1 && (
          <div className="bg-bg-color border border-border-color rounded-md p-4 flex flex-col gap-3">
            <h4 className="font-semibold text-sm border-b border-border-color pb-2">Alternatif Birimler</h4>
            <div className="flex flex-col gap-2 text-sm">
              {routing.ranked_units.slice(1).map((ru: any, i: number) => {
                const name = typeof ru === 'string' ? ru : ru?.name || 'Bilinmeyen Birim';
                const score = typeof ru === 'object' && ru?.score !== undefined ? ru.score : '-';
                return (
                  <div key={i} className="flex items-center justify-between p-2 bg-white rounded border border-border-color">
                    <span className="font-medium">{name}</span>
                    <span className="text-xs text-muted">Skor: {score}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

    </div>
  );
}


