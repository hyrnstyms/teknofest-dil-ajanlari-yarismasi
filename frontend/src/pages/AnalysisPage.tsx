import React, { useEffect, useState } from 'react';
import { getAnalysis } from '../services/analysis';
import { AnalysisResponse } from '../types/analysis';
import { ApiError } from '../types/api';
import { OverviewTab } from '../components/analysis/OverviewTab';
import { ExtractionTab } from '../components/analysis/ExtractionTab';
import { MissingFieldsTab } from '../components/analysis/MissingFieldsTab';
import { LegalTab } from '../components/analysis/LegalTab';
import { RoutingTab } from '../components/analysis/RoutingTab';
import { QualityTab } from '../components/analysis/QualityTab';
import { ReviewPanel } from '../components/review/ReviewPanel';
import { formatMs } from '../utils/formatters';

interface AnalysisPageProps {
  analysisId: string;
}

export function AnalysisPage({ analysisId }: AnalysisPageProps) {
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [showTechnical, setShowTechnical] = useState(false);

  const fetchAnalysis = async () => {
    try {
      const data = await getAnalysis(analysisId);
      setAnalysis(data);
    } catch (err: any) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalysis();
  }, [analysisId]);

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="2" x2="12" y2="6"></line>
            <line x1="12" y1="18" x2="12" y2="22"></line>
            <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
            <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
            <line x1="2" y1="12" x2="6" y2="12"></line>
            <line x1="18" y1="12" x2="22" y2="12"></line>
            <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
            <line x1="16.24" y1="4.93" x2="19.07" y2="7.76"></line>
          </svg>
        </div>
        <div>Analiz verileri yükleniyor...</div>
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="alert alert-danger" style={{ maxWidth: '600px', margin: '2rem auto' }}>
        <strong>Hata:</strong> {error?.message || "Analiz kaydı bulunamadı."}
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
      <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', color: 'var(--primary)' }}>Analiz Sonucu</h2>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>ID: {analysis.analysis_id}</div>
        </div>
      </div>

      <div className="analysis-layout">
        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="tabs" style={{ padding: '0 1rem', paddingTop: '1rem' }}>
            <button className={`tab ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>Genel Bakış</button>
            <button className={`tab ${activeTab === 'extraction' ? 'active' : ''}`} onClick={() => setActiveTab('extraction')}>Önemli Bilgiler</button>
            <button className={`tab ${activeTab === 'missing' ? 'active' : ''}`} onClick={() => setActiveTab('missing')}>Eksik Bilgiler</button>
            <button className={`tab ${activeTab === 'legal' ? 'active' : ''}`} onClick={() => setActiveTab('legal')}>Mevzuat</button>
            <button className={`tab ${activeTab === 'routing' ? 'active' : ''}`} onClick={() => setActiveTab('routing')}>Yönlendirme</button>
            <button className={`tab ${activeTab === 'quality' ? 'active' : ''}`} onClick={() => setActiveTab('quality')}>Kalite</button>
          </div>
          
          <div style={{ padding: '1.5rem', flex: 1 }}>
            {activeTab === 'overview' && <OverviewTab analysis={analysis} />}
            {activeTab === 'extraction' && <ExtractionTab analysis={analysis} />}
            {activeTab === 'missing' && <MissingFieldsTab analysis={analysis} />}
            {activeTab === 'legal' && <LegalTab analysis={analysis} />}
            {activeTab === 'routing' && <RoutingTab analysis={analysis} />}
            {activeTab === 'quality' && <QualityTab analysis={analysis} />}
          </div>

          <div style={{ padding: '1rem 1.5rem', borderTop: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <button 
                className="btn btn-outline" 
                style={{ fontSize: '0.75rem', padding: '0.25rem 0.75rem' }}
                onClick={() => setShowTechnical(!showTechnical)}
              >
                Teknik Detaylar {showTechnical ? '▲' : '▼'}
              </button>
            </div>
            {showTechnical && analysis.node_timings && (
              <div style={{ marginTop: '1rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.5rem', fontSize: '0.75rem' }}>
                {Object.entries(analysis.node_timings).map(([key, val]) => (
                  <div key={key} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0' }}>
                    <span style={{ color: 'var(--text-muted)' }}>{key}:</span>
                    <span style={{ fontWeight: 500 }}>{formatMs(val.duration_ms)}</span>
                  </div>
                ))}
              </div>
            )}
            {showTechnical && analysis.audit_history && (
              <div style={{ marginTop: '1rem', borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
                <h5 style={{ fontSize: '0.75rem', marginBottom: '0.5rem' }}>İşlem Geçmişi</h5>
                <ul style={{ paddingLeft: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {analysis.audit_history.map((a, i) => (
                    <li key={i}>{a.message} <span style={{ opacity: 0.5 }}>({new Date(a.timestamp).toLocaleString()})</span></li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        <div>
          <ReviewPanel analysis={analysis} onUpdate={fetchAnalysis} />
        </div>
      </div>
    </div>
  );
}
