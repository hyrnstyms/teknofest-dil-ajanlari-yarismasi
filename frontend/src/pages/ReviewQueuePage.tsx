import React, { useEffect, useState } from 'react';
import { getPendingReviews } from '../services/analysis';
import { ReviewQueueItem } from '../types/analysis';
import { ApiError } from '../types/api';
import { FileSearch, AlertTriangle, CheckCircle, Search } from 'lucide-react';
import { getLabel, DOC_TYPE_LABELS } from '../utils/labels';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';

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
    <div className="max-w-6xl mx-auto flex flex-col h-full">
      <div className="mb-6 flex justify-between items-end">
        <div>
          <h2 className="text-2xl font-bold text-text-heading mb-1">İnceleme Kuyruğu</h2>
          <p className="text-muted text-sm">Personel incelemesi ve onayı bekleyen evraklar listelenmektedir.</p>
        </div>
        <Button variant="secondary" onClick={fetchQueue} disabled={loading}>Yenile</Button>
      </div>

      {error && (
        <div className="p-4 bg-danger-light text-danger border border-danger rounded-md mb-6">
          <strong>Kuyruk yüklenemedi:</strong> {error.message}
        </div>
      )}

      {loading ? (
        <div className="flex-1 flex flex-col items-center justify-center p-12 text-muted gap-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
          <span className="font-medium">Kuyruk Yükleniyor...</span>
        </div>
      ) : items.length === 0 ? (
        <div className="flex-1 bg-card-bg border border-border-color rounded-md flex flex-col items-center justify-center p-12 text-center shadow-sm">
          <div className="w-16 h-16 bg-success-light text-success rounded-full flex items-center justify-center mb-4">
            <CheckCircle size={32} />
          </div>
          <h3 className="text-xl font-bold text-text-heading mb-2">İnceleme bekleyen evrak bulunmuyor.</h3>
          <p className="text-muted">Tüm kuyruk temiz.</p>
        </div>
      ) : (
        <div className="bg-card-bg border border-border-color rounded-md shadow-sm overflow-hidden flex-1">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-sidebar-bg/5 border-b border-border-color text-muted uppercase text-xs tracking-wider">
                <tr>
                  <th className="px-6 py-4 font-semibold">Evrak Konusu</th>
                  <th className="px-6 py-4 font-semibold">Tür / İşlem Amacı</th>
                  <th className="px-6 py-4 font-semibold">İnceleme Nedeni</th>
                  <th className="px-6 py-4 font-semibold">Önerilen Birim</th>
                  <th className="px-6 py-4 font-semibold">Kalite</th>
                  <th className="px-6 py-4 font-semibold text-right">Aksiyon</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-light">
                {items.map(item => (
                  <tr key={item.analysis_id} className="hover:bg-bg-color transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-medium text-text-main">
                        {item.subject || "Konu Bulunamadı"}
                      </div>
                      <div className="text-xs text-muted mt-1 font-mono">{item.analysis_id.substring(0, 8)}...</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-1 items-start">
                        <Badge status="info">{getLabel(item.document_type || "unknown", DOC_TYPE_LABELS)}</Badge>
                        <span className="text-xs text-muted">{getLabel(item.process_intent || "unknown", DOC_TYPE_LABELS)}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 max-w-xs">
                      <div className="flex flex-col gap-1">
                        {item.review_reasons.map((reason, idx) => (
                          <span key={idx} className="text-xs bg-warning-light text-warning px-2 py-1 rounded inline-flex items-center gap-1">
                            <AlertTriangle size={10} />
                            {reason}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-6 py-4 font-medium text-text-main">
                      {item.recommended_unit || "-"}
                    </td>
                    <td className="px-6 py-4">
                      {item.quality_status === 'pass' && <Badge status="success">Başarılı</Badge>}
                      {item.quality_status === 'warning' && <Badge status="warning">Uyarı</Badge>}
                      {item.quality_status === 'fail' && <Badge status="fail">Başarısız</Badge>}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Button 
                        variant="primary" 
                        size="sm"
                        onClick={() => onNavigateToAnalysis(item.analysis_id)}
                      >
                        <Search size={14} className="mr-1 inline" /> İncele
                      </Button>
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

