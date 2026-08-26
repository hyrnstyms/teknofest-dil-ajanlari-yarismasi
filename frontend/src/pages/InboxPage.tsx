import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  FileText,
  Inbox,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import { ErrorDisplay } from '../components/ErrorDisplay';
import { api } from '../services/api';
import type {
  AnalysisListItem,
  ReviewQueueItem,
} from '../types/analysis';

export const InboxPage: React.FC = () => {
  const navigate = useNavigate();
  const [analyses, setAnalyses] = useState<AnalysisListItem[]>([]);
  const [pendingReviews, setPendingReviews] = useState<ReviewQueueItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const loadRecords = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [analysisResponse, pendingResponse] = await Promise.all([
        api.getAnalyses({ limit: 100 }),
        api.getPendingReviews({ limit: 100 }),
      ]);
      setAnalyses(analysisResponse.items);
      setPendingReviews(pendingResponse.items);
      setTotal(analysisResponse.total);
    } catch (requestError: unknown) {
      setError(requestError);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadRecords();
  }, [loadRecords]);

  return (
    <div className="page-container">
      <div className="page-heading">
        <div>
          <h2><Inbox size={24} /> Gelen Evraklar</h2>
          <p className="text-secondary">
            Backend'de kayıtlı gerçek analizler ve inceleme kuyruğu
          </p>
        </div>
        <button className="btn btn-secondary" onClick={loadRecords} disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spinner' : ''} /> Yenile
        </button>
      </div>

      {error ? <ErrorDisplay error={error} title="Evraklar Yüklenemedi" /> : null}

      {!error && (
        <div className="inbox-summary">
          <span><strong>{total}</strong> kayıt</span>
          <span className={pendingReviews.length ? 'text-warning' : 'text-secondary'}>
            <AlertTriangle size={15} /> {pendingReviews.length} inceleme bekliyor
          </span>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <FileText size={18} /> Evrak Kayıtları
        </div>
        <div className="card-body p-0 inbox-table-wrapper">
          {loading ? (
            <div className="empty-state">
              <Loader2 size={28} className="text-primary spinner" />
              <p className="text-secondary">Kayıtlar yükleniyor...</p>
            </div>
          ) : analyses.length === 0 ? (
            <div className="empty-state">
              <Inbox size={42} className="text-secondary" />
              <p className="font-medium">Henüz analiz yapılmamış.</p>
              <p className="text-secondary">Yeni bir evrak analiz edildiğinde burada görünür.</p>
              <button className="btn btn-primary" onClick={() => navigate('/yeni-evrak')}>
                Yeni Evrak Analiz Et
              </button>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Evrak Türü</th>
                  <th>Konu</th>
                  <th>Önerilen Birim</th>
                  <th>Durum</th>
                  <th>Tarih</th>
                  <th><span className="sr-only">Aç</span></th>
                </tr>
              </thead>
              <tbody>
                {analyses.map((item) => (
                  <tr
                    key={item.analysis_id}
                    className="table-row-clickable"
                    onClick={() => navigate(`/evrak/${item.analysis_id}`)}
                  >
                    <td>{item.document_type || 'Belirsiz'}</td>
                    <td>{item.subject || 'Konu belirtilmemiş'}</td>
                    <td>{item.recommended_unit || 'Öneri yok'}</td>
                    <td>{renderStatus(item.human_review_status)}</td>
                    <td>{formatDate(item.created_at)}</td>
                    <td><ArrowRight size={16} className="text-secondary" /></td>
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

function renderStatus(status?: string): React.ReactNode {
  switch (status) {
    case 'approved':
      return <span className="badge badge-success">Onaylandı</span>;
    case 'rejected':
      return <span className="badge badge-error">Reddedildi</span>;
    case 'edited':
      return <span className="badge badge-info">Düzenlendi</span>;
    case 'pending_review':
      return <span className="badge badge-warning">İnceleme Bekliyor</span>;
    default:
      return <span className="badge badge-neutral">{status || 'Bilinmiyor'}</span>;
  }
}

function formatDate(value?: string): string {
  if (!value) return 'Tarih yok';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Geçersiz tarih';
  return date.toLocaleString('tr-TR');
}
