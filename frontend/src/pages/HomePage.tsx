import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FilePlus,
  FileText,
  Clock,
  CheckCircle,
  AlertTriangle,
  ArrowRight,
  Activity,
  TrendingUp,
} from 'lucide-react';
import { api } from '../services/api';
import type { AnalysisListItem } from '../types/analysis';
import type { ROISummaryResponse } from '../types/metrics';
import type { InstitutionOption } from '../services/api';
import { EVRAGBrand } from '../components/EVRAGBrand';
import { formatDocumentType, formatReviewStatus } from '../utils/presentation';

export const HomePage: React.FC<{ institution: InstitutionOption | null }> = ({ institution }) => {
  const navigate = useNavigate();
  const [recentAnalyses, setRecentAnalyses] = useState<AnalysisListItem[]>([]);
  const [roi, setRoi] = useState<ROISummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [analysesRes, roiRes] = await Promise.allSettled([
          api.getAnalyses({ limit: 5 }),
          api.getRoiSummary(),
        ]);

        if (analysesRes.status === 'fulfilled') {
          setRecentAnalyses(analysesRes.value.items);
        }
        if (roiRes.status === 'fulfilled') {
          setRoi(roiRes.value);
        }
      } catch {
        // silently fail — homepage should still render
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case 'approved':
        return <span className="badge badge-success"><CheckCircle size={12} /> Onaylandı</span>;
      case 'rejected':
        return <span className="badge badge-error">Reddedildi</span>;
      case 'edited':
        return <span className="badge badge-info">Düzenlendi</span>;
      case 'pending_review':
        return <span className="badge badge-warning"><AlertTriangle size={12} /> {formatReviewStatus(status)}</span>;
      default:
        return <span className="badge badge-neutral">{formatReviewStatus(status)}</span>;
    }
  };

  return (
    <div className="page-container">
      {/* Üst Aksiyonlar */}
      <div className="home-hero">
        <div className="home-hero-copy">
          <EVRAGBrand variant="compact" theme="dark" className="home-brand" />
          <span className="home-ai-kicker">AKILLI EVRAK VE KARAR DESTEK SİSTEMİ</span>
          <h2>Evraktan karara,<br />tek akıllı akış.</h2>
          <p className="text-secondary">Kurumsal evrakları anlayan, mevzuatla ilişkilendiren, doğru birime yönlendiren yapay zekâ destekli karar sistemi.</p>
          <span className="selected-context institution-profile-badge">Kurum Profili: <strong>{institution?.label || "Seçilmedi"}</strong></span>
        </div>
        <div className="home-hero-product" aria-label="Evraktan karara EVRAG akışı">
          <div className="origami-route" aria-hidden="true">
            <div className="origami-sheet"><span /></div>
            <div className="origami-fold-line" />
          </div>
          <div className="home-hero-actions">
            <button className="btn btn-primary" onClick={() => navigate('/yeni-evrak')}>
              <FilePlus size={18} /> Yeni Evrak Analizi
            </button>
            <button className="btn home-ai-button" onClick={() => navigate('/ai-operasyon')}>
              <Activity size={17} /> AI Operasyon Merkezi
            </button>
          </div>
          <div className="home-ai-flow" aria-label="EVRAG yapay zekâ işlem mimarisi">
            {["Analiz", "Mevzuat", "Yönlendirme", "Taslak"].map((stage, index) => (
              <React.Fragment key={stage}>
                <span>{stage}</span>{index < 3 && <ArrowRight size={13} />}
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>

      {/* İstatistik Kartları */}
      {roi && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon"><FileText size={24} /></div>
            <div className="stat-content">
              <span className="stat-value">{roi.processed_documents ?? 0}</span>
              <span className="stat-label">İşlenen Evrak</span>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon"><Clock size={24} /></div>
            <div className="stat-content">
              <span className="stat-value">
                {roi.average_processing_seconds
                  ? `${roi.average_processing_seconds.toFixed(1)}s`
                  : '-'}
              </span>
              <span className="stat-label">Ort. İşlem Süresi</span>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon"><CheckCircle size={24} /></div>
            <div className="stat-content">
              <span className="stat-value">{roi.approved_count ?? 0}</span>
              <span className="stat-label">Onaylanan</span>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon"><TrendingUp size={24} /></div>
            <div className="stat-content">
              <span className="stat-value">
                {roi.human_review_required_rate != null
                  ? `%${(roi.human_review_required_rate * 100).toFixed(0)}`
                  : '-'}
              </span>
              <span className="stat-label">İnceleme Oranı</span>
            </div>
          </div>
        </div>
      )}

      {/* Son İşlemler */}
      <div className="card" style={{ marginTop: '1.5rem' }}>
        <div className="card-header flex justify-between items-center w-full">
          <div className="flex items-center gap-2">
            <Activity size={18} /> Son İşlemler
          </div>
          <button
            className="btn btn-secondary"
            style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
            onClick={() => navigate('/gelen-evraklar')}
          >
            Tümünü Gör <ArrowRight size={14} />
          </button>
        </div>
        <div className="card-body p-0">
          {loading ? (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
              <span className="spinner" style={{ borderTopColor: 'var(--primary-color)', borderColor: 'var(--border-color)' }}></span>
              <p className="text-secondary" style={{ marginTop: '0.5rem' }}>Yükleniyor...</p>
            </div>
          ) : recentAnalyses.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
              <FileText size={40} className="text-secondary" style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
              <p className="text-secondary">Henüz analiz yapılmamış.</p>
              <button
                className="btn btn-primary"
                style={{ marginTop: '1rem' }}
                onClick={() => navigate('/yeni-evrak')}
              >
                <FilePlus size={16} /> İlk Evrakı Analiz Et
              </button>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Tür</th>
                  <th>Konu</th>
                  <th>Önerilen Birim</th>
                  <th>Durum</th>
                  <th>Tarih</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {recentAnalyses.map((item) => (
                  <tr
                    key={item.analysis_id}
                    className="table-row-clickable"
                    onClick={() => navigate(`/evrak/${item.analysis_id}`)}
                  >
                    <td>
                      <span className="font-medium">
                        {formatDocumentType(item.document_type)}
                      </span>
                    </td>
                    <td>{item.subject || '-'}</td>
                    <td>{item.recommended_unit || '-'}</td>
                    <td>{getStatusBadge(item.human_review_status)}</td>
                    <td className="text-secondary" style={{ fontSize: '0.8rem' }}>
                      {item.created_at
                        ? new Date(item.created_at).toLocaleString('tr-TR', {
                            day: '2-digit',
                            month: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : '-'}
                    </td>
                    <td>
                      <ArrowRight size={16} className="text-secondary" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};
