import React from 'react';
import { AnalysisResponse } from '../../types/analysis';
import { BookOpen, ShieldCheck, AlertCircle } from 'lucide-react';

export function LegalTab({ analysis }: { analysis: AnalysisResponse }) {
  const { evidences } = analysis.legal_analysis;

  if (!evidences || evidences.length === 0) {
    return (
      <div className="alert alert-warning" style={{ display: 'flex', alignItems: 'center' }}>
        <AlertCircle size={18} style={{ flexShrink: 0 }} />
        <div>
          Bu belge için doğrulanmış mevzuat kaynağı bulunamadı.
        </div>
      </div>
    );
  }

  return (
    <div>
      <h4 style={{ fontSize: '1rem', color: 'var(--primary)', marginBottom: '1rem' }}>Mevzuat Dayanağı</h4>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {evidences.map((ev, idx) => (
          <div key={idx} style={{ 
            border: '1px solid var(--border-color)', 
            borderRadius: '6px', 
            padding: '1.25rem',
            backgroundColor: 'var(--card-bg)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--primary)', fontWeight: 500 }}>
                <BookOpen size={18} />
                <span>{ev.metadata.law_name || "Mevzuat Metni"}</span>
              </div>
              <span className="badge badge-green" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <ShieldCheck size={14} /> Kaynakta Doğrulandı
              </span>
            </div>
            
            <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              {ev.metadata.law_number && <div><strong>Kanun No:</strong> {ev.metadata.law_number}</div>}
              {ev.metadata.item_number && <div><strong>Madde:</strong> {ev.metadata.item_number}</div>}
              {ev.metadata.source_type && <div><strong>Tür:</strong> {ev.metadata.source_type}</div>}
              
              {ev.retrieval_score && (
                <div title="Bu değer sorgu ile mevzuat kaynağı arasındaki benzerliği gösterir; hukuki doğruluk olasılığı değildir.">
                  <strong>Kaynak Eşleşme Skoru:</strong> {ev.retrieval_score.toFixed(2)}
                </div>
              )}
            </div>

            <div style={{ 
              backgroundColor: 'var(--bg-color)', 
              padding: '1rem', 
              borderRadius: '4px',
              fontSize: '0.875rem',
              borderLeft: '3px solid var(--accent)'
            }}>
              {ev.text}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
