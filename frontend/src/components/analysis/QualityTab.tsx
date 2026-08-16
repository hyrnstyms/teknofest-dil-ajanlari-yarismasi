import React from 'react';
import { AnalysisResponse, QualityCheck } from '../../types/analysis';
import { CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import { getLabel, STATUS_LABELS } from '../../utils/labels';

export function QualityTab({ analysis }: { analysis: AnalysisResponse }) {
  const { status, checks } = analysis.quality;

  const getIcon = (st: string) => {
    if (st === 'pass') return <CheckCircle2 size={18} color="var(--success)" />;
    if (st === 'warning') return <AlertTriangle size={18} color="var(--warning)" />;
    return <XCircle size={18} color="var(--danger)" />;
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h4 style={{ fontSize: '1rem', color: 'var(--primary)', margin: 0 }}>Kalite Kontrolü</h4>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600 }}>
          Genel Durum: 
          <span style={{ 
            color: status === 'pass' ? 'var(--success)' : status === 'warning' ? 'var(--warning)' : 'var(--danger)' 
          }}>
            {getLabel(status, STATUS_LABELS)}
          </span>
        </div>
      </div>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {checks.map((check: QualityCheck, idx: number) => (
          <div key={idx} style={{ 
            display: 'flex', 
            alignItems: 'flex-start', 
            gap: '1rem',
            padding: '1rem',
            border: '1px solid var(--border-color)',
            borderRadius: '6px',
            backgroundColor: 'var(--card-bg)'
          }}>
            <div style={{ marginTop: '0.125rem' }}>{getIcon(check.status)}</div>
            <div>
              <div style={{ fontWeight: 500, marginBottom: '0.25rem' }}>{check.name}</div>
              <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>{check.message}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
