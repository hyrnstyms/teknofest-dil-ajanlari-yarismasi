import React from 'react';
import { AnalysisResponse, LegalEvidence } from '../../types/analysis';
import { BookOpen, ShieldCheck, AlertCircle, Info } from 'lucide-react';
import { Badge } from '../ui/Badge';

export function LegalTab({ analysis }: { analysis: AnalysisResponse }) {
  const la = analysis?.legal_analysis || {};
  const evidences = la.evidences || [];
  const evidence = la.evidence || [];
  const sources = la.sources || [];

  const hasV1Evidences = evidences.length > 0;
  const hasV2Evidence = evidence.length > 0;
  const hasSources = sources.length > 0;

  const displaySources: LegalEvidence[] = hasSources ? sources : (hasV1Evidences ? evidences : []);
  const isVerified = hasV1Evidences || hasV2Evidence;

  if (!displaySources || displaySources.length === 0) {
    return (
      <div className="p-4 bg-warning-light text-warning rounded-md border border-warning flex items-start gap-3">
        <AlertCircle size={20} className="mt-0.5 flex-shrink-0" />
        <div>
          <h4 className="font-semibold">Mevzuat Bulunamadı</h4>
          <p className="text-sm mt-1">Bu belge için doğrulanmış mevzuat kaynağı bulunamadı veya eşleştirilemedi.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      
      {!isVerified && hasSources && (
        <div className="p-4 bg-warning-light text-warning rounded-md border border-warning flex items-start gap-3">
          <Info size={20} className="mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="font-semibold">Sadece Kaynak Bulundu</h4>
            <p className="text-sm mt-1">Kaynak bulundu, ancak doğrulanmış kanıt (evidence) çıkarılamadı. İçerikler varsayımsal veya yetersiz olabilir.</p>
          </div>
        </div>
      )}

      {isVerified && (
        <div className="p-4 bg-success-light text-success rounded-md border border-success flex items-start gap-3">
          <ShieldCheck size={20} className="mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="font-semibold">Hukuki Analiz Doğrulandı</h4>
            <p className="text-sm mt-1">Evraktaki hukuki argümanlar ilgili mevzuat kaynaklarıyla doğrulandı.</p>
          </div>
        </div>
      )}

      {hasV2Evidence && (
        <div className="flex flex-col gap-2">
          <h4 className="font-semibold text-text-heading">Doğrulanmış Kanıtlar</h4>
          <ul className="list-disc pl-5 text-sm space-y-2">
            {evidence.map((evStr, i) => (
              <li key={i}>{evStr}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex flex-col gap-4">
        <h4 className="font-semibold text-text-heading">Kullanılan Kaynaklar</h4>
        {displaySources.map((ev, idx) => {
          const isSourceVerified = hasV1Evidences ? true : (ev?.evidence ? true : false);

          return (
            <div key={idx} className="bg-bg-color border border-border-color rounded-md p-4">
              <div className="flex justify-between items-start mb-3">
                <div className="flex items-center gap-2 text-accent font-medium">
                  <BookOpen size={18} />
                  <span>{ev?.metadata?.law_name || "Mevzuat Metni"}</span>
                </div>
                {isSourceVerified && (
                  <Badge status="success">Kaynakta Doğrulandı</Badge>
                )}
              </div>
              
              <div className="flex flex-wrap gap-x-6 gap-y-2 mb-4 text-sm text-muted">
                {ev?.metadata?.law_number && <div><strong className="text-text-main">Kanun No:</strong> {ev.metadata.law_number}</div>}
                {ev?.metadata?.item_number && <div><strong className="text-text-main">Madde:</strong> {ev.metadata.item_number}</div>}
                {ev?.metadata?.source_type && <div><strong className="text-text-main">Tür:</strong> {ev.metadata.source_type}</div>}
                
                {ev?.retrieval_score !== undefined && (
                  <div title="Bu değer sorgu ile mevzuat kaynağı arasındaki benzerliği gösterir; hukuki doğruluk olasılığı değildir.">
                    <strong className="text-text-main">Kaynak Eşleşme Skoru:</strong> {ev.retrieval_score.toFixed(2)}
                  </div>
                )}
              </div>

              {(ev?.text || ev?.evidence) && (
                <div className="bg-white p-3 rounded-md text-sm border-l-4 border-accent shadow-sm">
                  {ev.evidence || ev.text}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}


