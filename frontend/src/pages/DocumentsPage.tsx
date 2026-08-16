import React, { useEffect, useState } from 'react';
import { getAnalyses } from '../services/analysis';
import { AnalysisListItem } from '../types/analysis';
import { ApiError } from '../types/api';
import { FileText, Clock, AlertTriangle, CheckCircle, Search, Filter } from 'lucide-react';
import { getLabel, DOC_TYPE_LABELS, STATUS_LABELS } from '../utils/labels';

export function DocumentsPage({ onNavigateToAnalysis }: { onNavigateToAnalysis: (id: string) => void }) {
  const [items, setItems] = useState<AnalysisListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  const fetchDocuments = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAnalyses({
        limit: 50,
        status: statusFilter || undefined,
        document_type: typeFilter || undefined
      });
      setItems(data.items);
    } catch (err: any) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [statusFilter, typeFilter]);

  const renderStatus = (status?: string) => {
    if (!status) return <span className="badge">Belirtilmedi</span>;
    if (status === 'pending_review') return <span className="badge badge-warning">İnceleme Bekliyor</span>;
    if (status === 'approved') return <span className="badge badge-success">Onaylandı</span>;
    if (status === 'rejected') return <span className="badge badge-danger">Reddedildi</span>;
    if (status === 'edited') return <span className="badge badge-blue">Düzenlendi</span>;
    return <span className="badge">{getLabel(status, STATUS_LABELS)}</span>;
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', color: 'var(--primary)', marginBottom: '0.5rem' }}>Evraklar</h2>
          <p style={{ color: 'var(--text-muted)' }}>Sistemde analiz edilmiş tüm evrakları listeleyin.</p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '1.5rem', padding: '1rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Filter size={18} color="var(--text-muted)" />
          <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>Filtreler:</span>
        </div>
        
        <select 
          className="form-input" 
          style={{ width: 'auto', padding: '0.25rem 0.5rem' }}
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
        >
          <option value="">Tüm Evrak Türleri</option>
          <option value="dilekce">Dilekçe</option>
          <option value="resmi_yazi">Resmi Yazı</option>
        </select>

        <select 
          className="form-input" 
          style={{ width: 'auto', padding: '0.25rem 0.5rem' }}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">Tüm Durumlar</option>
          <option value="pending_review">İnceleme Bekliyor</option>
          <option value="approved">Onaylandı</option>
          <option value="rejected">Reddedildi</option>
          <option value="edited">Düzenlendi</option>
        </select>
      </div>

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: '1.5rem' }}>
          <strong>Evraklar yüklenemedi.</strong> {error.message}
        </div>
      )}

      {loading ? (
        <div className="loading-container" style={{ padding: '3rem' }}>
          <div className="spinner"></div>
          <div>Yükleniyor...</div>
        </div>
      ) : items.length === 0 ? (
        <div className="card" style={{ padding: '3rem', textAlign: 'center' }}>
          <FileText size={48} color="var(--border-color)" style={{ margin: '0 auto 1rem' }} />
          <h3 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Henüz analiz edilmiş evrak bulunmuyor.</h3>
          <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }}>Yeni bir evrak yükleyerek analize başlayabilirsiniz.</p>
        </div>
      ) : (
        <div className="card" style={{ overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--bg-color)', borderBottom: '1px solid var(--border-color)' }}>
                  <th style={{ padding: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>Evrak / Konu</th>
                  <th style={{ padding: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>Evrak Türü</th>
                  <th style={{ padding: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>İşlem Amacı</th>
                  <th style={{ padding: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>Önerilen Birim</th>
                  <th style={{ padding: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>Kalite</th>
                  <th style={{ padding: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>İnceleme Durumu</th>
                  <th style={{ padding: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>İşlem Süresi</th>
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
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                        {item.document_id}
                      </div>
                    </td>
                    <td style={{ padding: '1rem', fontSize: '0.875rem' }}>{getLabel(item.document_type || "unknown", DOC_TYPE_LABELS)}</td>
                    <td style={{ padding: '1rem', fontSize: '0.875rem' }}>{getLabel(item.process_intent || "unknown", DOC_TYPE_LABELS)}</td>
                    <td style={{ padding: '1rem', fontSize: '0.875rem' }}>{item.recommended_unit || "-"}</td>
                    <td style={{ padding: '1rem', fontSize: '0.875rem' }}>
                      {item.quality_status === 'pass' && <CheckCircle size={16} color="var(--success)" />}
                      {item.quality_status === 'warning' && <AlertTriangle size={16} color="var(--warning)" />}
                      {item.quality_status === 'fail' && <AlertTriangle size={16} color="var(--danger)" />}
                      {!item.quality_status && "-"}
                    </td>
                    <td style={{ padding: '1rem' }}>{renderStatus(item.human_review_status)}</td>
                    <td style={{ padding: '1rem', fontSize: '0.875rem' }}>
                      {item.total_processing_ms ? `${(item.total_processing_ms / 1000).toFixed(1)} sn` : '-'}
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
