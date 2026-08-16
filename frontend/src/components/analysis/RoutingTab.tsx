import React from 'react';
import { AnalysisResponse } from '../../types/analysis';
import { ArrowRightCircle, AlertTriangle } from 'lucide-react';

export function RoutingTab({ analysis }: { analysis: AnalysisResponse }) {
  const { routing } = analysis;

  return (
    <div>
      <h4 style={{ fontSize: '1rem', color: 'var(--primary)', marginBottom: '1rem' }}>Yönlendirme</h4>
      
      {routing.recommended_unit ? (
        <div style={{ marginBottom: '2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <ArrowRightCircle size={24} color="var(--accent)" />
            <h5 style={{ fontSize: '1.25rem', color: 'var(--text-main)', margin: 0 }}>{routing.recommended_unit}</h5>
            {routing.registry_source === 'demo' && (
              <span className="badge badge-gray">Demo Birim Tanımları</span>
            )}
          </div>
          
          <div className="data-list" style={{ backgroundColor: 'var(--bg-color)', padding: '1.25rem', borderRadius: '8px' }}>
            <div className="data-row" style={{ borderBottom: 'none', paddingBottom: 0 }}>
              <div className="data-label">Yönlendirme Gerekçesi</div>
              <div className="data-value" style={{ textAlign: 'left', maxWidth: '100%', marginTop: '0.5rem', fontWeight: 400 }}>
                {routing.reason}
              </div>
            </div>
            
            {routing.routing_score !== undefined && (
              <div className="data-row" style={{ marginTop: '1rem', borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
                <div className="data-label">Yönlendirme Eşleşme Skoru</div>
                <div className="data-value">{routing.routing_score}</div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="alert alert-warning" style={{ display: 'flex', alignItems: 'flex-start' }}>
          <AlertTriangle size={20} style={{ flexShrink: 0 }} />
          <div>
            <div style={{ fontWeight: 500, marginBottom: '0.25rem' }}>Uygun birim güvenilir şekilde belirlenemedi.</div>
            <div style={{ fontSize: '0.875rem' }}>Personel incelemesi gereklidir. Gerekçe: {routing.reason}</div>
          </div>
        </div>
      )}
    </div>
  );
}
