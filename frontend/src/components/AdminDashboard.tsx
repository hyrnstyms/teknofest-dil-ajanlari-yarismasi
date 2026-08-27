import React, { useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, Clock3, FilePenLine, Files, RefreshCw, UserCheck, XCircle } from "lucide-react";
import {
  api,
  type AnalysisListItem,
  type PendingReviewItem,
  type RoiSummary,
} from "../services/api";
import { formatDocumentType, formatProcessIntent, formatReviewStatus } from "../utils/presentation";

interface Props {
  onOpenAnalysis: (analysisId: string) => void | Promise<void>;
}

export const AdminDashboard: React.FC<Props> = ({ onOpenAnalysis }) => {
  const [roi, setRoi] = useState<RoiSummary | null>(null);
  const [analyses, setAnalyses] = useState<AnalysisListItem[]>([]);
  const [pending, setPending] = useState<PendingReviewItem[]>([]);
  const [pendingTotal, setPendingTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [roiResult, analysesResult, pendingResult] = await Promise.all([
        api.getRoiSummary(),
        api.getAnalyses(20),
        api.getPendingReviews(20),
      ]);
      setRoi(roiResult);
      setAnalyses(analysesResult.items);
      setPending(pendingResult.items);
      setPendingTotal(pendingResult.total);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Yönetici verileri yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const departmentDistribution = useMemo(() => {
    const counts = new Map<string, number>();
    analyses.forEach((item) => {
      const department = item.recommended_unit?.trim();
      if (department) counts.set(department, (counts.get(department) || 0) + 1);
    });
    return [...counts.entries()]
      .map(([department, count]) => ({ department, count }))
      .sort((left, right) => right.count - left.count || left.department.localeCompare(right.department, "tr"));
  }, [analyses]);

  return (
    <div className="admin-dashboard">
      <div className="page-intro admin-intro">
        <div>
          <span className="section-kicker">Gerçek sistem verileri</span>
          <h2>Operasyon Özeti</h2>
          <p>İşlenen evraklar, personel incelemeleri ve mevcut AI işlem metrikleri.</p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={() => void load()} disabled={loading}>
          <RefreshCw size={16} /> Yenile
        </button>
      </div>

      {error && <div className="inline-error" role="alert">{error}</div>}

      <div className="metric-grid" aria-busy={loading}>
        <Metric icon={<Files />} label="Toplam işlenen evrak" value={roi ? String(roi.processed_documents) : "—"} />
        <Metric icon={<Clock3 />} label="Ortalama AI işlem süresi" value={roi ? `${roi.average_processing_seconds.toFixed(2)} sn` : "—"} />
        <Metric icon={<UserCheck />} label="Human review oranı" value={roi ? `%${(roi.human_review_required_rate * 100).toFixed(1)}` : "—"} />
        <Metric icon={<CheckCircle2 />} label="Onaylanan" value={roi ? String(roi.approved_count) : "—"} />
        <Metric icon={<FilePenLine />} label="Düzenlenen" value={roi ? String(roi.edited_count) : "—"} />
        <Metric icon={<XCircle />} label="Reddedilen" value={roi ? String(roi.rejected_count) : "—"} />
        <Metric icon={<UserCheck />} label="İnceleme bekleyen" value={loading ? "—" : String(pendingTotal)} accent />
      </div>

      <DepartmentDistributionChart data={departmentDistribution} loading={loading} />

      <section className="admin-table-card">
        <div className="table-card-header"><div><span className="section-kicker">Kayıtlar</span><h3>Son Evraklar</h3></div><span>{analyses.length} kayıt gösteriliyor</span></div>
        <div className="table-scroll">
          <table className="admin-table">
            <thead><tr><th>Belge</th><th>Tür / Konu</th><th>Önerilen birim</th><th>İnceleme durumu</th><th>Oluşturulma</th></tr></thead>
            <tbody>
              {analyses.length === 0 ? <EmptyRow columns={5} text={loading ? "Yükleniyor…" : "Henüz analiz kaydı bulunmuyor."} /> : analyses.map((item) => (
                <tr key={item.analysis_id} className="clickable-row" onClick={() => void onOpenAnalysis(item.analysis_id)}>
                  <td><strong>{item.document_id || shortId(item.analysis_id)}</strong><span>{shortId(item.analysis_id)}</span></td>
                  <td><strong>{formatDocumentType(item.document_type)}</strong><span>{item.subject || formatProcessIntent(item.process_intent)}</span></td>
                  <td>{item.recommended_unit || "—"}</td>
                  <td><StatusBadge status={item.human_review_status} /></td>
                  <td>{formatDate(item.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="admin-table-card">
        <div className="table-card-header"><div><span className="section-kicker">Personel kuyruğu</span><h3>İnceleme Bekleyenler</h3></div><span>{pendingTotal} bekleyen</span></div>
        <div className="table-scroll">
          <table className="admin-table">
            <thead><tr><th>Analiz</th><th>Evrak</th><th>Önerilen birim</th><th>İnceleme nedeni</th><th>Oluşturulma</th></tr></thead>
            <tbody>
              {pending.length === 0 ? <EmptyRow columns={5} text={loading ? "Yükleniyor…" : "İnceleme bekleyen evrak bulunmuyor."} /> : pending.map((item) => (
                <tr key={item.analysis_id} className="clickable-row" onClick={() => void onOpenAnalysis(item.analysis_id)}>
                  <td><strong>{shortId(item.analysis_id)}</strong></td>
                  <td>{formatDocumentType(item.document_type)}</td>
                  <td>{item.recommended_unit || "—"}</td>
                  <td>{item.review_reasons?.join(" ") || "Personel incelemesi gerekli."}</td>
                  <td>{formatDate(item.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};

const DepartmentDistributionChart: React.FC<{
  data: Array<{ department: string; count: number }>;
  loading: boolean;
}> = ({ data, loading }) => {
  const maximum = Math.max(...data.map((item) => item.count), 1);
  return (
    <section className="department-chart-card" aria-labelledby="department-chart-title">
      <header className="table-card-header">
        <div><span className="section-kicker">Gerçek analiz kayıtları</span><h3 id="department-chart-title">Birim Dağılımı</h3></div>
        <span>{loading ? "Yükleniyor…" : `${data.reduce((sum, item) => sum + item.count, 0)} yönlendirme`}</span>
      </header>
      {data.length ? <div className="department-bars" role="img" aria-label="Önerilen birimlere göre evrak dağılımı">
        {data.map((item) => <div className="department-bar-row" key={item.department}>
          <div><strong>{item.department}</strong><span>{item.count} evrak</span></div>
          <span className="department-bar-track" aria-hidden="true"><i style={{ width: `${(item.count / maximum) * 100}%` }} /></span>
        </div>)}
      </div> : <div className="chart-empty">{loading ? "Birim dağılımı hesaplanıyor…" : "Birim önerisi bulunan analiz kaydı yok."}</div>}
    </section>
  );
};

const Metric: React.FC<{ icon: React.ReactNode; label: string; value: string; accent?: boolean }> = ({ icon, label, value, accent }) => (
  <div className={`metric-card ${accent ? "accent" : ""}`}><div className="metric-icon">{icon}</div><div><span>{label}</span><strong>{value}</strong></div></div>
);

const EmptyRow: React.FC<{ columns: number; text: string }> = ({ columns, text }) => <tr><td colSpan={columns} className="empty-table">{text}</td></tr>;

const StatusBadge: React.FC<{ status?: string }> = ({ status }) => {
  const normalized = status || "bilinmiyor";
  const className = normalized === "approved" || normalized === "approved_auto" ? "success" : normalized === "rejected" ? "danger" : normalized === "pending_review" ? "warning" : "neutral";
  return <span className={`table-status ${className}`}>{formatReviewStatus(normalized)}</span>;
};

function shortId(value: string): string { return value.length > 12 ? `${value.slice(0, 8)}…` : value; }
function formatDate(value?: string): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("tr-TR", { dateStyle: "short", timeStyle: "short" }).format(date);
}
