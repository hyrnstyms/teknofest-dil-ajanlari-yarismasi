import React, { useEffect, useState } from 'react';
import { getSystemStatus } from '../services/metrics';
import { getEBYSStatus, EBYSStatus } from '../services/system';
import { SystemStatusResponse } from '../types/metrics';
import { ApiError } from '../types/api';
import { getLabel, STATUS_LABELS } from '../utils/labels';
import { Activity, Server, Brain, Database, FileText, Search, RefreshCw, Layers } from 'lucide-react';

export function SystemStatusPage() {
  const [status, setStatus] = useState<SystemStatusResponse | null>(null);
  const [ebysStatus, setEbysStatus] = useState<EBYSStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  const fetchStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getSystemStatus();
      setStatus(data);
      try {
        const ebys = await getEBYSStatus();
        setEbysStatus(ebys);
      } catch (ebysErr) {
        console.warn('EBYS status could not be fetched', ebysErr);
      }
    } catch (err: any) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const renderStatusBadge = (val: string) => {
    const isOk = val === 'online' || val === 'ready' || val === 'tamamlandı';
    const isPartial = val === 'partial' || val === 'kısmi';
    let label = getLabel(val, STATUS_LABELS);
    
    if (val === 'online') label = 'Çalışıyor';
    if (val === 'offline') label = 'Çalışmıyor';
    if (val === 'partial') label = 'Kısmi';
    if (val === 'ready') label = 'Hazır';

    return (
      <span className={`badge ${isOk ? 'badge-green' : isPartial ? 'badge-yellow' : 'badge-red'}`}>
        {label}
      </span>
    );
  };

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', color: 'var(--primary)', marginBottom: '0.5rem' }}>Sistem Durumu</h2>
          <p style={{ color: 'var(--text-muted)' }}>KAMUAI bileşenlerinin çalışma ve indeks durumunu görüntüleyin.</p>
        </div>
        <button 
          className="btn btn-outline" 
          onClick={fetchStatus} 
          disabled={loading}
        >
          <RefreshCw size={16} className={loading ? "spinner" : ""} />
          Durumu Yenile
        </button>
      </div>

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: '1.5rem' }}>
          <strong>Sistem durumu alınamadı.</strong> {error.message}
          <button className="btn btn-outline" style={{ marginTop: '0.5rem', padding: '0.25rem 0.75rem', fontSize: '0.75rem' }} onClick={fetchStatus}>Tekrar Dene</button>
        </div>
      )}

      {loading && !status && (
        <div className="loading-container" style={{ padding: '2rem' }}>
          <div className="spinner" style={{ marginBottom: '0.5rem' }}><RefreshCw size={24} /></div>
          <div>Sistem durumu yükleniyor...</div>
        </div>
      )}

      {status && (
        <div className="grid-2">
          {/* API */}
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-header" style={{ marginBottom: '1rem', borderBottom: 'none', paddingBottom: 0 }}>
              <h3 className="card-title"><Server size={20} /> API</h3>
            </div>
            <div className="data-list">
              <div className="data-row">
                <div className="data-label">Durum</div>
                <div className="data-value">{renderStatusBadge(status.api)}</div>
              </div>
            </div>
          </div>

          {/* Dil Modeli */}
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-header" style={{ marginBottom: '1rem', borderBottom: 'none', paddingBottom: 0 }}>
              <h3 className="card-title"><Brain size={20} /> Dil Modeli</h3>
            </div>
            <div className="data-list">
              {status.ollama && (
                <div className="data-row">
                  <div className="data-label">Sağlayıcı</div>
                  <div className="data-value" style={{ textTransform: 'capitalize' }}>Ollama</div>
                </div>
              )}
              {status.llm_model && (
                <div className="data-row">
                  <div className="data-label">Model</div>
                  <div className="data-value">{status.llm_model}</div>
                </div>
              )}
              <div className="data-row">
                <div className="data-label">Durum</div>
                <div className="data-value">{renderStatusBadge(status.ollama ? "online" : "offline")}</div>
              </div>
            </div>
          </div>

          {/* Embedding */}
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-header" style={{ marginBottom: '1rem', borderBottom: 'none', paddingBottom: 0 }}>
              <h3 className="card-title"><Activity size={20} /> Embedding Modeli</h3>
            </div>
            <div className="data-list">
              {status.embedding_model && (
                <div className="data-row">
                  <div className="data-label">Model</div>
                  <div className="data-value">{status.embedding_model}</div>
                </div>
              )}
              {status.embedding_dimension && (
                <div className="data-row">
                  <div className="data-label">Boyut</div>
                  <div className="data-value">{status.embedding_dimension}</div>
                </div>
              )}
              <div className="data-row">
                <div className="data-label">Durum</div>
                <div className="data-value">{renderStatusBadge('online')}</div>
              </div>
            </div>
          </div>

          {/* Qdrant */}
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-header" style={{ marginBottom: '1rem', borderBottom: 'none', paddingBottom: 0 }}>
              <h3 className="card-title"><Database size={20} /> Vektör Veritabanı</h3>
            </div>
            <div className="data-list">
              <div className="data-row">
                <div className="data-label">Toplam İndekslenmiş Kayıt</div>
                <div className="data-value">{status.qdrant?.total_points || 0}</div>
              </div>
              <div className="data-row">
                <div className="data-label">Collection Sayısı</div>
                <div className="data-value">{status.qdrant ? "2" : "0"}</div>
              </div>
              <div className="data-row">
                <div className="data-label">Durum</div>
                <div className="data-value">{renderStatusBadge(status.qdrant ? 'online' : 'offline')}</div>
              </div>
            </div>
          </div>

          {/* Mevzuat İndeksi */}
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-header" style={{ marginBottom: '1rem', borderBottom: 'none', paddingBottom: 0 }}>
              <h3 className="card-title"><Search size={20} /> Mevzuat İndeksi</h3>
            </div>
            <div className="data-list">
              <div className="data-row">
                <div className="data-label">Durum</div>
                <div className="data-value">{renderStatusBadge(status.qdrant?.index_status || "offline")}</div>
              </div>
              <div className="data-row" style={{ borderBottom: 'none' }}>
                <div className="data-label">İndekslenen (Kayıt)</div>
                <div className="data-value">{status.qdrant?.legal_points || 0} / 7559</div>
              </div>
              {status.qdrant?.index_status === 'partial' && (
                <div style={{ fontSize: '0.75rem', color: 'var(--warning)', marginTop: '0.5rem' }}>
                  Mevzuat indeksi kısmi.
                </div>
              )}
            </div>
          </div>

          {/* Belge İndeksi */}
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-header" style={{ marginBottom: '1rem', borderBottom: 'none', paddingBottom: 0 }}>
              <h3 className="card-title"><FileText size={20} /> Belge İndeksi</h3>
            </div>
            <div className="data-list">
              <div className="data-row">
                <div className="data-label">Durum</div>
                <div className="data-value">{renderStatusBadge('online')}</div>
              </div>
              <div className="data-row" style={{ borderBottom: 'none' }}>
                <div className="data-label">İndekslenen (Kayıt)</div>
                <div className="data-value">{status.qdrant?.document_points || 0} / 106</div>
              </div>
            </div>
          </div>

          {/* EBYS Entegrasyonu */}
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-header" style={{ marginBottom: '1rem', borderBottom: 'none', paddingBottom: 0 }}>
              <h3 className="card-title"><Layers size={20} /> EBYS Entegrasyonu</h3>
            </div>
            <div className="data-list">
              <div className="data-row">
                <div className="data-label">Durum</div>
                <div className="data-value">
                  <span className={`badge ${ebysStatus?.connected ? 'badge-green' : 'badge-yellow'}`}>
                    {ebysStatus?.connected ? 'Bağlı' : 'Gerçek bağlantı yapılandırılmadı'}
                  </span>
                </div>
              </div>
              <div className="data-row">
                <div className="data-label">Adaptör</div>
                <div className="data-value">
                  {ebysStatus?.adapter_type === 'mock' ? 'Demo Adapter' : ebysStatus?.adapter_type || '-'}
                </div>
              </div>
              <div className="data-row" style={{ borderBottom: 'none' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                  KAMUAI, mevcut EBYS sistemlerinin yerine geçmek yerine karar destek katmanı olarak entegre olacak şekilde tasarlanmıştır.
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
