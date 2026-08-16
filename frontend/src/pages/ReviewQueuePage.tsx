import React, { useEffect, useState } from 'react';
import { getPendingReviews } from '../services/analysis';
import { ReviewQueueItem } from '../types/analysis';
import { ApiError } from '../types/api';
import { FileSearch, Clock, AlertTriangle, CheckCircle } from 'lucide-react';
import { getLabel, DOC_TYPE_LABELS } from '../utils/labels';

export function ReviewQueuePage({ onNavigateToAnalysis }: { onNavigateToAnalysis: (id: string) => void }) {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  const fetchQueue = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPendingReviews({ limit: 50 });
      setItems(data.items);
    } catch (err: any) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.5rem', color: 'var(--primary)', marginBottom: '0.5rem' }}>İnceleme Kuyruğu</h2>
        <p style={{ color: 'var(--text-muted)' }}>Personel incelemesi ve onayı bekleyen evraklar listelenmektedir.</p>
      </div>

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: '1.5rem' }}>
          <strong>Kuyruk yüklenemedi.</strong> {error.message}
        </div>
      )}

      {loading ? (
        <div className="loading-container" style={{ padding: '3rem' }}>
          <div className="spinner"></div>
          <div>Yükleniyor...</div>
        </div>
      ) : items.length === 0 ? (
        <div className="card" style={{ padding: '3rem', textAlign: 'center' }}>
          <FileSearch size={48} color="var(--success)" style={{ margin: '0 auto 1rem' }} />
          <h3 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>İnceleme bekleyen evrak bulunmuyor.</h3>
          <p style={{ color: 'var(--text-muted)' }}>Tüm kuyruk temiz.</p>
        </div>
      ) : (
        <div className="card" style={{ overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--bg-color)', borderBottom: '1px solid var(--border-color)' }}>
                  <th style={{ padding: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>Evrak</th>
                  <th style={{ padding: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>Tür</th>
                  <th style={{ padding: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>İşlem Amacı</th>
                  <th style={{ padding: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>İnceleme Nedeni</th>
                  <th style={{ padding: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>Önerilen Birim</th>
                  <th style={{ padding: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>Kalite</th>
                  <th style={{ padding: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>Aksiyon</th>
                </tr>
              </thead>
              <tbody>
                {items.map(item => (
                  <tr key={item.analysis_id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '1rem' }}>
                      <div style={{ fontWeight: 500, fontSize: '0.875rem' }}>
                        {item.subject || "Konu Bulunamadı"}
                      </div>
                    </td>
                    <td style={{ padding: '1rem', fontSize: '0.875rem' }}>{getLabel(item.document_type || "unknown", DOC_TYPE_LABELS)}</td>
                    <td style={{ padding: '1rem', fontSize: '0.875rem' }}>{getLabel(item.process_intent || "unknown", DOC_TYPE_LABELS)}</td>
                    <td style={{ padding: '1rem', fontSize: '0.875rem', maxWidth: '250px' }}>
                      <ul style={{ margin: 0, paddingLeft: '1rem' }}>
                        {item.review_reasons.map((reason, idx) => (
                          <li key={idx} style={{ color: 'var(--warning)', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                            {reason}
                          </li>
                        ))}
                      </ul>
                    </td>
                    <td style={{ padding: '1rem', fontSize: '0.875rem' }}>{item.recommended_unit || "-"}</td>
                    <td style={{ padding: '1rem', fontSize: '0.875rem' }}>
                      {item.quality_status === 'pass' && <CheckCircle size={16} color="var(--success)" />}
                      {item.quality_status === 'warning' && <AlertTriangle size={16} color="var(--warning)" />}
                      {item.quality_status === 'fail' && <AlertTriangle size={16} color="var(--danger)" />}
                    </td>
                    <td style={{ padding: '1rem' }}>
                      <button 
                        className="btn btn-primary" 
                        style={{ padding: '0.25rem 0.75rem', fontSize: '0.75rem' }}
                        onClick={() => onNavigateToAnalysis(item.analysis_id)}
                      >
                        İncele
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
