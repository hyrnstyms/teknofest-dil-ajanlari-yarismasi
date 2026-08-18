import React, { useEffect, useState } from 'react';
import { getAnalyses } from '../services/analysis';
import { AnalysisListItem } from '../types/analysis';
import { ApiError } from '../types/api';
import { FileText, AlertTriangle, CheckCircle, Search, Filter } from 'lucide-react';
import { getLabel, DOC_TYPE_LABELS, STATUS_LABELS } from '../utils/labels';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';

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
    if (!status) return <span className="text-muted">-</span>;
    if (status === 'pending_review') return <Badge status="warning">İnceleme Bekliyor</Badge>;
    if (status === 'approved') return <Badge status="success">Onaylandı</Badge>;
    if (status === 'rejected') return <Badge status="fail">Reddedildi</Badge>;
    if (status === 'edited') return <Badge status="info">Düzenlendi</Badge>;
    return <Badge status="info">{getLabel(status, STATUS_LABELS)}</Badge>;
  };

  return (
    <div className="max-w-7xl mx-auto flex flex-col h-full">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:justify-between sm:items-end">
        <div>
          <h2 className="text-2xl font-bold text-text-heading mb-1">Evraklar</h2>
          <p className="text-muted text-sm">Sistemde analiz edilmiş tüm evrakları listeleyin.</p>
        </div>
        
        <div className="flex flex-wrap items-center gap-3 p-3 bg-card-bg border border-border-color rounded-md shadow-sm">
          <div className="flex items-center gap-2 text-muted">
            <Filter size={16} />
            <span className="text-sm font-medium">Filtreler:</span>
          </div>
          
          <select 
            className="form-control text-sm py-1.5 px-3 min-w-[150px]" 
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          >
            <option value="">Tüm Evrak Türleri</option>
            <option value="dilekce">Dilekçe</option>
            <option value="resmi_yazi">Resmi Yazı</option>
          </select>

          <select 
            className="form-control text-sm py-1.5 px-3 min-w-[150px]" 
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
      </div>

      {error && (
        <div className="p-4 bg-danger-light text-danger border border-danger rounded-md mb-6">
          <strong>Evraklar yüklenemedi:</strong> {error.message}
        </div>
      )}

      {loading ? (
        <div className="flex-1 flex flex-col items-center justify-center p-12 text-muted gap-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
          <span className="font-medium">Yükleniyor...</span>
        </div>
      ) : items.length === 0 ? (
        <div className="flex-1 bg-card-bg border border-border-color rounded-md flex flex-col items-center justify-center p-12 text-center shadow-sm">
          <div className="w-16 h-16 bg-bg-color text-muted rounded-full flex items-center justify-center mb-4 border border-border-color">
            <FileText size={32} />
          </div>
          <h3 className="text-xl font-bold text-text-heading mb-2">Henüz analiz edilmiş evrak bulunmuyor.</h3>
          <p className="text-muted">Yeni bir evrak yükleyerek analize başlayabilirsiniz.</p>
        </div>
      ) : (
        <div className="bg-card-bg border border-border-color rounded-md shadow-sm overflow-hidden flex-1">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-sidebar-bg/5 border-b border-border-color text-muted uppercase text-xs tracking-wider">
                <tr>
                  <th className="px-6 py-4 font-semibold">Evrak Konusu</th>
                  <th className="px-6 py-4 font-semibold">Tür / İşlem Amacı</th>
                  <th className="px-6 py-4 font-semibold">Önerilen Birim</th>
                  <th className="px-6 py-4 font-semibold">Kalite</th>
                  <th className="px-6 py-4 font-semibold">Durum</th>
                  <th className="px-6 py-4 font-semibold text-right">Süre</th>
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
                    <td className="px-6 py-4 font-medium text-text-main">
                      {item.recommended_unit || "-"}
                    </td>
                    <td className="px-6 py-4">
                      {item.quality_status === 'pass' && <Badge status="success">Başarılı</Badge>}
                      {item.quality_status === 'warning' && <Badge status="warning">Uyarı</Badge>}
                      {item.quality_status === 'fail' && <Badge status="fail">Başarısız</Badge>}
                      {!item.quality_status && <span className="text-muted">-</span>}
                    </td>
                    <td className="px-6 py-4">
                      {renderStatus(item.human_review_status)}
                    </td>
                    <td className="px-6 py-4 text-right text-muted text-xs">
                      {item.total_processing_ms ? `${(item.total_processing_ms / 1000).toFixed(1)} sn` : '-'}
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

