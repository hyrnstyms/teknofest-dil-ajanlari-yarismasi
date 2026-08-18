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
import { DraftPanel } from '../components/analysis/DraftPanel';
import { formatMs } from '../utils/formatters';
import { Button } from '../components/ui/Button';

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
      <div className="flex flex-col items-center justify-center h-full gap-4 text-muted">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
        <p>Analiz verileri yükleniyor...</p>
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="p-6 bg-danger-light text-danger rounded-md border border-danger">
        <strong>Hata:</strong> {error?.message || "Analiz kaydı bulunamadı."}
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-heading text-lg font-semibold">Evrak Detayı</h1>
          <p className="text-xs text-muted font-mono">ID: {analysis.analysis_id}</p>
        </div>
      </div>

      {/* Main Layout */}
      <div className="analysis-layout">
        
        {/* Left Side: Tabs & Content */}
        <div className="analysis-main bg-card-bg border border-border-color rounded-md flex flex-col overflow-hidden">
          {/* Tabs Header */}
          <div className="flex border-b border-border-color bg-bg-color px-2">
            {[
              { id: 'overview', label: 'Genel Bakış' },
              { id: 'extraction', label: 'Çıkarılan Bilgiler' },
              { id: 'missing', label: 'Eksik & Belirsiz' },
              { id: 'legal', label: 'Mevzuat' },
              { id: 'routing', label: 'Yönlendirme' },
              { id: 'quality', label: 'Kalite' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 ${
                  activeTab === tab.id 
                    ? 'border-accent text-accent bg-white' 
                    : 'border-transparent text-muted hover:text-text-main hover:bg-white/50'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {activeTab === 'overview' && <OverviewTab analysis={analysis} />}
            {activeTab === 'extraction' && <ExtractionTab analysis={analysis} />}
            {activeTab === 'missing' && <MissingFieldsTab analysis={analysis} />}
            {activeTab === 'legal' && <LegalTab analysis={analysis} />}
            {activeTab === 'routing' && <RoutingTab analysis={analysis} />}
            {activeTab === 'quality' && <QualityTab analysis={analysis} />}
          </div>

          {/* Footer - Technical details */}
          <div className="p-4 border-t border-border-color bg-bg-color">
            <Button variant="secondary" className="text-xs py-1 px-3" onClick={() => setShowTechnical(!showTechnical)}>
              Teknik Detaylar {showTechnical ? '▲' : '▼'}
            </Button>
            
            {showTechnical && analysis.node_timings && (
              <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
                {Object.entries(analysis.node_timings).map(([key, val]) => (
                  <div key={key} className="flex justify-between p-1 bg-white rounded border border-border-color">
                    <span className="text-muted">{key}:</span>
                    <span className="font-medium">{formatMs(val.duration_ms)}</span>
                  </div>
                ))}
              </div>
            )}
            
            {showTechnical && analysis.audit_history && (
              <div className="mt-4 border-t border-border-color pt-4 text-xs">
                <h5 className="font-semibold mb-2">İşlem Geçmişi</h5>
                <ul className="list-disc pl-4 text-muted space-y-1">
                  {analysis.audit_history.map((a, i) => (
                    <li key={i}>{a.message} <span className="opacity-50">({new Date(a.timestamp).toLocaleString()})</span></li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Right Side: Sticky Draft Panel */}
        <div className="analysis-sidebar-sticky">
          <DraftPanel analysis={analysis} onUpdate={fetchAnalysis} />
        </div>
        
      </div>
    </div>
  );
}

