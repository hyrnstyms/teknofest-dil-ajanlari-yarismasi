import React, { useEffect, useState } from 'react';
import { getSystemStatus } from '../services/metrics';
import { getEBYSStatus, EBYSStatus } from '../services/system';
import { SystemStatusResponse } from '../types/metrics';
import { ApiError } from '../types/api';
import { getLabel, STATUS_LABELS } from '../utils/labels';
import { Activity, Server, Brain, Database, FileText, Search, RefreshCw, Layers } from 'lucide-react';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';

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
      <Badge status={isOk ? 'success' : isPartial ? 'warning' : 'fail'}>
        {label}
      </Badge>
    );
  };

  const DataRow = ({ label, value, children }: { label: string, value?: React.ReactNode, children?: React.ReactNode }) => (
    <div className="flex justify-between items-center py-3 border-b border-border-light last:border-0 last:pb-0">
      <span className="text-sm font-medium text-muted">{label}</span>
      {value !== undefined && <span className="text-sm font-medium text-text-main">{value}</span>}
      {children}
    </div>
  );

  return (
    <div className="max-w-5xl mx-auto flex flex-col h-full gap-6 pb-8">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-2xl font-bold text-text-heading mb-1">Sistem Durumu</h2>
          <p className="text-muted text-sm">KAMUAI bileşenlerinin çalışma ve indeks durumunu görüntüleyin.</p>
        </div>
        <Button variant="secondary" onClick={fetchStatus} disabled={loading}>
          <RefreshCw size={16} className={`mr-2 ${loading ? 'animate-spin' : ''}`} />
          Durumu Yenile
        </Button>
      </div>

      {error && (
        <div className="p-4 bg-danger-light text-danger border border-danger rounded-md">
          <strong>Sistem durumu alınamadı:</strong> {error.message}
        </div>
      )}

      {loading && !status && (
        <div className="flex-1 flex flex-col items-center justify-center p-12 text-muted gap-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
          <span className="font-medium">Sistem durumu yükleniyor...</span>
        </div>
      )}

      {status && (
        <div className="grid-2 sm:grid-2 gap-6">
          {/* API */}
          <Card title="API Sunucusu" icon={<Server size={18} />}>
            <div className="flex flex-col">
              <DataRow label="Durum">
                {renderStatusBadge(status.api)}
              </DataRow>
            </div>
          </Card>

          {/* Dil Modeli */}
          <Card title="Dil Modeli (LLM)" icon={<Brain size={18} />}>
            <div className="flex flex-col">
              {status.ollama && <DataRow label="Sağlayıcı" value={<span className="capitalize">Ollama</span>} />}
              {status.llm_model && <DataRow label="Model" value={<span className="font-mono text-xs bg-bg-color px-2 py-1 rounded">{status.llm_model}</span>} />}
              <DataRow label="Durum">
                {renderStatusBadge(status.ollama ? "online" : "offline")}
              </DataRow>
            </div>
          </Card>

          {/* Embedding */}
          <Card title="Embedding Modeli" icon={<Activity size={18} />}>
            <div className="flex flex-col">
              {status.embedding_model && <DataRow label="Model" value={<span className="font-mono text-xs bg-bg-color px-2 py-1 rounded">{status.embedding_model}</span>} />}
              {status.embedding_dimension && <DataRow label="Boyut" value={status.embedding_dimension} />}
              <DataRow label="Durum">
                {renderStatusBadge('online')}
              </DataRow>
            </div>
          </Card>

          {/* Qdrant */}
          <Card title="Vektör Veritabanı" icon={<Database size={18} />}>
            <div className="flex flex-col">
              <DataRow label="Kayıt Sayısı (Points)" value={status.qdrant?.total_points || 0} />
              <DataRow label="Collection Sayısı" value={status.qdrant ? "2" : "0"} />
              <DataRow label="Durum">
                {renderStatusBadge(status.qdrant ? 'online' : 'offline')}
              </DataRow>
            </div>
          </Card>

          {/* Mevzuat İndeksi */}
          <Card title="Mevzuat İndeksi" icon={<Search size={18} />}>
            <div className="flex flex-col">
              <DataRow label="Durum">
                {renderStatusBadge(status.qdrant?.index_status || "offline")}
              </DataRow>
              <DataRow label="İndekslenen Kayıt" value={`${status.qdrant?.legal_points || 0} / 7559`} />
              
              {status.qdrant?.index_status === 'partial' && (
                <div className="text-xs text-warning bg-warning-light p-2 rounded-md mt-3 border border-warning">
                  Mevzuat indeksi kısmi. Tüm veriler aranabilir olmayabilir.
                </div>
              )}
            </div>
          </Card>

          {/* Belge İndeksi */}
          <Card title="Belge İndeksi" icon={<FileText size={18} />}>
            <div className="flex flex-col">
              <DataRow label="Durum">
                {renderStatusBadge('online')}
              </DataRow>
              <DataRow label="İndekslenen Kayıt" value={`${status.qdrant?.document_points || 0} / 106`} />
            </div>
          </Card>

          {/* EBYS Entegrasyonu */}
          <Card title="EBYS Entegrasyonu" icon={<Layers size={18} />}>
            <div className="flex flex-col">
              <DataRow label="Durum">
                <Badge status={ebysStatus?.connected ? 'success' : 'warning'}>
                  {ebysStatus?.connected ? 'Bağlı' : 'Simülasyon Modu'}
                </Badge>
              </DataRow>
              <DataRow label="Adaptör" value={ebysStatus?.adapter_type === 'mock' ? 'Demo Adapter' : ebysStatus?.adapter_type || '-'} />
              
              <div className="text-xs text-muted leading-relaxed mt-3 pt-3 border-t border-border-light bg-sidebar-bg/5 p-3 rounded-md">
                KAMUAI, mevcut EBYS sistemlerinin yerine geçmek yerine karar destek katmanı olarak entegre olacak şekilde tasarlanmıştır.
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

