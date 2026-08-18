import React, { useEffect, useState } from 'react';
import { getROISummary } from '../services/metrics';
import { ROISummaryResponse } from '../types/metrics';
import { ApiError } from '../types/api';
import { Clock, FileCheck2, UserCheck, Settings, CheckCircle2, XCircle, TrendingUp, AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';

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
    <div className="max-w-5xl mx-auto flex flex-col h-full gap-6 pb-8">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-2xl font-bold text-text-heading mb-1">Operasyonel Performans</h2>
          <p className="text-muted text-sm">KAMUAI kullanımından elde edilen gerçek işlem ve inceleme sürelerini görüntüleyin.</p>
        </div>
        <Button variant="secondary" onClick={fetchROI} disabled={loading}>
          <RefreshCw size={16} className={`mr-2 ${loading ? 'animate-spin' : ''}`} />
          Yenile
        </Button>
      </div>

      {error && (
        <div className="p-4 bg-danger-light text-danger border border-danger rounded-md">
          <strong>Performans verileri alınamadı:</strong> {error.message}
        </div>
      )}

      {loading && !roi && (
        <div className="flex-1 flex flex-col items-center justify-center p-12 text-muted gap-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
          <span className="font-medium">Performans verileri yükleniyor...</span>
        </div>
      )}

      {roi && roi.processed_documents === 0 && (
        <div className="p-6 bg-warning-light text-warning border border-warning rounded-md flex items-start gap-4">
          <AlertCircle size={24} className="flex-shrink-0" />
          <div>
            <h4 className="text-lg font-bold mb-1">Henüz yeterli işlem verisi bulunmuyor.</h4>
            <p>Belgeler analiz edildikçe gerçek süre ve kullanım metrikleri burada görüntülenecektir.</p>
          </div>
        </div>
      )}

      {roi && roi.processed_documents > 0 && (
        <div className="flex flex-col gap-6">
          {/* Top KPIs */}
          <div className="grid-2">
            <div className="bg-card-bg border border-border-color rounded-md p-6 flex items-center gap-6 shadow-sm">
              <div className="w-16 h-16 rounded-full bg-accent-light text-accent flex items-center justify-center">
                <FileCheck2 size={32} />
              </div>
              <div>
                <h4 className="text-sm font-medium text-muted uppercase tracking-wider mb-1">İşlenen Evrak</h4>
                <div className="text-3xl font-bold text-text-heading">{roi.processed_documents}</div>
              </div>
            </div>

            <div className="bg-card-bg border border-border-color rounded-md p-6 flex items-center gap-6 shadow-sm">
              <div className="w-16 h-16 rounded-full bg-success-light text-success flex items-center justify-center">
                <Clock size={32} />
              </div>
              <div>
                <h4 className="text-sm font-medium text-muted uppercase tracking-wider mb-1">Ort. AI İşlem Süresi</h4>
                <div className="text-3xl font-bold text-success">{formatSeconds(roi.average_processing_seconds)}</div>
              </div>
            </div>
          </div>

          <div className="grid-2 gap-6">
            {/* Human Review Stats */}
            <Card title="İnsan İncelemesi İstatistikleri" icon={<UserCheck size={18} />}>
              <div className="flex flex-col gap-4">
                <div className="flex justify-between items-center py-2 border-b border-border-light">
                  <span className="font-medium text-muted text-sm">İnsan İncelemesi Gereken Oran</span>
                  <span className="font-mono bg-accent-light text-accent px-2 py-1 rounded font-bold text-sm">
                    {(roi.human_review_required_rate * 100).toFixed(1)}%
                  </span>
                </div>
                
                <div className="flex justify-between items-center py-2 border-b border-border-light">
                  <div className="flex items-center gap-2 text-success font-medium text-sm">
                    <CheckCircle2 size={16} /> Onaylanan
                  </div>
                  <span className="font-mono text-text-main font-bold">{roi.approved_count}</span>
                </div>

                <div className="flex justify-between items-center py-2 border-b border-border-light">
                  <div className="flex items-center gap-2 text-info font-medium text-sm">
                    <Settings size={16} /> Düzenlenen
                  </div>
                  <span className="font-mono text-text-main font-bold">{roi.edited_count}</span>
                </div>

                <div className="flex justify-between items-center py-2">
                  <div className="flex items-center gap-2 text-danger font-medium text-sm">
                    <XCircle size={16} /> Reddedilen
                  </div>
                  <span className="font-mono text-text-main font-bold">{roi.rejected_count}</span>
                </div>
              </div>
            </Card>

            {/* ROI Hero Card */}
            <div className="bg-primary text-white rounded-md p-6 flex flex-col justify-between shadow-md relative overflow-hidden">
              <div className="absolute -right-10 -top-10 opacity-10">
                <TrendingUp size={200} />
              </div>
              
              <div className="relative z-10 mb-8">
                <h3 className="text-xl font-bold mb-1">Tahmini Kazanılan Süre</h3>
                <p className="text-sm opacity-80 max-w-[80%]" title="Bu değer yapılandırılmış manuel işlem süresi ile ölçülen AI destekli işlem süresi karşılaştırılarak hesaplanmaktadır.">
                  Manuel süreçlere kıyasla elde edilen operasyonel zaman tasarrufu.
                </p>
              </div>

              <div className="relative z-10">
                <div className="text-5xl font-bold text-accent-light mb-4 drop-shadow-md">
                  {formatSeconds(roi.estimated_saved_seconds)}
                </div>
                
                {roi.estimated_saved_percentage && (
                  <div className="border-t border-white/20 pt-4 flex items-center justify-between text-sm">
                    <span className="opacity-90">Zaman Tasarrufu Oranı</span>
                    <span className="font-bold text-accent-light bg-white/10 px-3 py-1 rounded-full">
                      %{roi.estimated_saved_percentage.toFixed(1)}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

