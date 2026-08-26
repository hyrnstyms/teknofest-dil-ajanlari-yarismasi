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

export const HomePage: React.FC = () => {
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
        return <span className="badge badge-warning"><AlertTriangle size={12} /> İnceleme Bekliyor</span>;
      default:
        return <span className="badge badge-neutral">{status || 'Bilinmiyor'}</span>;
    }
  };

  return (
    <div className="page-container">
      {/* Üst Aksiyonlar */}
      <div className="home-hero">
        <div>
          <h2 style={{ marginBottom: '0.5rem' }}>Hoş Geldiniz</h2>
          <p className="text-secondary">Kamu Evrak ve Yazışma Süreçleri için Akıllı Agent Destek Sistemi</p>
        </div>
        <button
          className="btn btn-primary"
          style={{ padding: '0.75rem 1.5rem', fontSize: '1rem' }}
          onClick={() => navigate('/yeni-evrak')}
        >
          <FilePlus size={20} /> Yeni Evrak Analiz Et
        </button>
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
                        {item.document_type || 'Belirsiz'}
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
