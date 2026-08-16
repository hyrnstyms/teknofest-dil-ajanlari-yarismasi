import React, { useEffect, useState } from 'react';
import { getROISummary } from '../services/metrics';
import { ROISummaryResponse } from '../types/metrics';
import { ApiError } from '../types/api';
import { Clock, FileCheck2, UserCheck, Settings, CheckCircle2, XCircle } from 'lucide-react';
import { formatMs } from '../utils/formatters';

export function PerformancePage() {
  const [roi, setRoi] = useState<ROISummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  const fetchROI = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getROISummary();
      setRoi(data);
    } catch (err: any) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchROI();
  }, []);

  const formatSeconds = (sec: number) => {
    if (sec < 60) return `${sec.toFixed(1)} sn`;
    const mins = Math.floor(sec / 60);
    const remaining = Math.round(sec % 60);
    return `${mins} dk ${remaining > 0 ? remaining + ' sn' : ''}`;
  };

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.5rem', color: 'var(--primary)', marginBottom: '0.5rem' }}>Operasyonel Performans</h2>
        <p style={{ color: 'var(--text-muted)' }}>KAMUAI kullanımından elde edilen gerçek işlem ve inceleme sürelerini görüntüleyin.</p>
      </div>

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: '1.5rem' }}>
          <strong>Performans verileri alınamadı.</strong> {error.message}
          <button className="btn btn-outline" style={{ marginTop: '0.5rem', padding: '0.25rem 0.75rem', fontSize: '0.75rem' }} onClick={fetchROI}>Tekrar Dene</button>
        </div>
      )}

      {loading && !roi && (
        <div className="loading-container" style={{ padding: '2rem' }}>
          <div className="spinner" style={{ marginBottom: '0.5rem' }}><Clock size={24} /></div>
          <div>Performans verileri yükleniyor...</div>
        </div>
      )}

      {roi && roi.processed_documents === 0 && (
        <div className="alert alert-warning" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <strong style={{ fontSize: '1.1rem' }}>Henüz yeterli işlem verisi bulunmuyor.</strong>
          <div>Belgeler analiz edildikçe gerçek süre ve kullanım metrikleri burada görüntülenecektir.</div>
        </div>
      )}

      {roi && roi.processed_documents > 0 && (
        <div>
          <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
            <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '1.5rem', marginBottom: 0 }}>
              <div style={{ backgroundColor: 'var(--bg-color)', padding: '1rem', borderRadius: '50%', color: 'var(--accent)' }}>
                <FileCheck2 size={32} />
              </div>
              <div>
                <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)', fontWeight: 500 }}>İşlenen Evrak</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--primary)' }}>{roi.processed_documents}</div>
              </div>
            </div>

            <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '1.5rem', marginBottom: 0 }}>
              <div style={{ backgroundColor: '#f0fdf4', padding: '1rem', borderRadius: '50%', color: 'var(--success)' }}>
                <Clock size={32} />
              </div>
              <div>
                <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)', fontWeight: 500 }}>Ortalama AI İşlem Süresi</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--success)' }}>
                  {formatSeconds(roi.average_processing_seconds)}
                </div>
              </div>
            </div>
          </div>

          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div className="card-header" style={{ marginBottom: '1.5rem' }}>
              <h3 className="card-title"><UserCheck size={20} /> İnsan İncelemesi İstatistikleri</h3>
            </div>
            <div className="data-list">
              <div className="data-row">
                <div className="data-label">İnsan İncelemesi Gereken Oran</div>
                <div className="data-value">
                  <span className="badge badge-blue">
                    {(roi.human_review_required_rate * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="data-row">
                <div className="data-label" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <CheckCircle2 size={16} color="var(--success)" /> Onaylanan
                </div>
                <div className="data-value">{roi.approved_count}</div>
              </div>
              <div className="data-row">
                <div className="data-label" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Settings size={16} color="var(--warning)" /> Düzenlenen
                </div>
                <div className="data-value">{roi.edited_count}</div>
              </div>
              <div className="data-row" style={{ borderBottom: 'none' }}>
                <div className="data-label" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <XCircle size={16} color="var(--danger)" /> Reddedilen
                </div>
                <div className="data-value">{roi.rejected_count}</div>
              </div>
            </div>
          </div>

          <div className="card" style={{ backgroundColor: 'var(--primary)', color: 'white' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '1rem', fontWeight: 500, opacity: 0.9, marginBottom: '0.25rem' }}>
                  Tahmini Kazanılan Süre
                </div>
                <div style={{ fontSize: '0.75rem', opacity: 0.7, maxWidth: '80%' }} title="Bu değer yapılandırılmış manuel işlem süresi ile ölçülen AI destekli işlem süresi karşılaştırılarak hesaplanmaktadır.">
                  Manuel süreçlere kıyasla (Tahmini)
                </div>
              </div>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: '#60a5fa' }}>
                {formatSeconds(roi.estimated_saved_seconds)}
              </div>
            </div>
            {roi.estimated_saved_percentage && (
              <div style={{ marginTop: '1rem', fontSize: '0.875rem', opacity: 0.9, borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '1rem' }}>
                Zaman tasarrufu oranı: <strong style={{ color: '#60a5fa' }}>%{roi.estimated_saved_percentage.toFixed(1)}</strong>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
