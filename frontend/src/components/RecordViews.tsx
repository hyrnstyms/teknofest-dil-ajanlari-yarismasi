import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Download, FileText, Filter, Inbox, RefreshCw, Search, UserCheck } from "lucide-react";
import { api, type AnalysisListItem, type InstitutionOption, type PendingReviewItem } from "../services/api";
import type { DocumentState } from "../types";
import { formatDate, formatDisplayName as humanize } from "../utils/presentation";

interface ViewProps {
  onOpenAnalysis: (analysisId: string) => void | Promise<void>;
}

interface IncomingDocumentsProps extends ViewProps {
  institution: InstitutionOption | null;
}

interface DetailedAnalysis extends AnalysisListItem {
  detail?: DocumentState;
}

function useDetailedAnalyses(limit = 40, institution?: string) {
  const [items, setItems] = useState<DetailedAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);

  const load = useCallback(async () => {
    const requestId = ++requestIdRef.current;
    setLoading(true);
    setError(null);
    setItems([]);
    try {
      const result = await api.getAnalyses({ limit, institution });
      const detailed = await Promise.all(result.items.map(async (item) => {
        try {
          return { ...item, detail: await api.getAnalysis(item.analysis_id) };
        } catch {
          return item;
        }
      }));
      if (requestId === requestIdRef.current) setItems(detailed);
    } catch (loadError) {
      if (requestId === requestIdRef.current) {
        setError(loadError instanceof Error ? loadError.message : "Evrak kayıtları yüklenemedi.");
      }
    } finally {
      if (requestId === requestIdRef.current) setLoading(false);
    }
  }, [limit, institution]);

  useEffect(() => { void load(); }, [load]);
  return { items, loading, error, load };
}

export const IncomingDocumentsPage: React.FC<IncomingDocumentsProps> = ({ institution: activeInstitution, onOpenAnalysis }) => {
  const { items, loading, error, load } = useDetailedAnalyses(40, activeInstitution?.id);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [documentType, setDocumentType] = useState("");

  const documentTypes = unique(items.map((item) => item.document_type).filter(Boolean) as string[]);
  const filtered = useMemo(() => items.filter((item) => {
    const query = search.trim().toLocaleLowerCase("tr-TR");
    const subject = item.subject || getDraftSubject(item.detail) || "";
    const matchesSearch = !query || [item.document_id, item.analysis_id, subject, item.recommended_unit]
      .some((value) => String(value || "").toLocaleLowerCase("tr-TR").includes(query));
    return matchesSearch
      && (!status || item.human_review_status === status)
      && (!documentType || item.document_type === documentType);
  }), [items, search, status, documentType]);

  return (
    <div className="records-page no-print">
      <PageHeader icon={<Inbox />} eyebrow="Evrak kayıtları" title="Gelen Evraklar" description="Analiz edilmiş evrakları mevcut kayıt alanlarıyla inceleyin ve çalışma alanında açın." onRefresh={load} loading={loading} />
      {error && <div className="inline-error" role="alert">{error}</div>}
      <div className="record-filters">
        <label className="search-filter"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Belge, analiz, konu veya birim ara" /></label>
        <span className="record-status neutral"><Filter size={15} />{activeInstitution?.label || "Aktif kurum seçilmedi"}</span>
        <label><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">Tüm durumlar</option><option value="pending_review">İnceleme bekliyor</option><option value="approved">Onaylandı</option><option value="approved_auto">Otomatik onay</option><option value="edited">Düzenlendi</option><option value="rejected">Reddedildi</option></select></label>
        <label><select value={documentType} onChange={(event) => setDocumentType(event.target.value)}><option value="">Tüm evrak türleri</option>{documentTypes.map((value) => <option key={value} value={value}>{humanize(value)}</option>)}</select></label>
      </div>

      <section className="records-table-card">
        <table className="records-table">
          <thead><tr><th>Belge / Analiz</th><th>Konu</th><th>Kurum</th><th>Tarih</th><th>Durum</th><th>Önerilen birim</th></tr></thead>
          <tbody>
            {filtered.length === 0 ? <EmptyTable loading={loading} columns={6} /> : filtered.map((item) => (
              <tr key={item.analysis_id} onClick={() => void onOpenAnalysis(item.analysis_id)}>
                <td><strong>{item.document_id || shortId(item.analysis_id)}</strong><span>{shortId(item.analysis_id)}</span></td>
                <td>{item.subject || getDraftSubject(item.detail) || humanize(item.document_type || "Belirsiz evrak")}</td>
                <td>{item.detail?.kurum_profili_id ? humanize(item.detail.kurum_profili_id) : "—"}</td>
                <td>{formatDate(item.created_at)}</td>
                <td><Status value={item.human_review_status || item.quality_status} /></td>
                <td>{item.recommended_unit || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
};

export const DraftsPage: React.FC<ViewProps> = ({ onOpenAnalysis }) => {
  const { items, loading, error, load } = useDetailedAnalyses();
  const drafts = items.filter((item) => hasDraft(item.detail));
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const download = async (analysisId: string) => {
    setDownloadError(null);
    const blob = await api.downloadDocx(analysisId);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "resmi_yazi_taslak.docx";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="records-page no-print">
      <PageHeader icon={<FileText />} eyebrow="Resmî yazılar" title="Taslaklarım" description="Gerçek analiz kayıtlarında resmî yazı taslağı bulunan çalışmalar." onRefresh={load} loading={loading} />
      {(error || downloadError) && <div className="inline-error" role="alert">{error || downloadError}</div>}
      <div className="draft-grid">
        {drafts.length === 0 ? <div className="records-empty">{loading ? "Taslaklar yükleniyor…" : "Henüz oluşturulmuş resmî yazı taslağı bulunmuyor."}</div> : drafts.map((item) => (
          <article className="draft-card" key={item.analysis_id}>
            <div className="draft-card-icon"><FileText size={19} /></div>
            <span className="section-kicker">{humanize(item.detail?.draft?.draft_type || "Resmî yazı")}</span>
            <h2>{getDraftSubject(item.detail) || item.subject || "Başlıksız taslak"}</h2>
            <p>{item.detail?.kurum_profili_id ? humanize(item.detail.kurum_profili_id) : "Kurum bilgisi yok"} · {formatDate(item.created_at)}</p>
            <Status value={item.human_review_status} />
            <div className="draft-actions">
              <button type="button" onClick={() => void onOpenAnalysis(item.analysis_id)}>A4 önizlemeyi aç</button>
              <button type="button" disabled={item.human_review_status !== "approved"} title={item.human_review_status === "approved" ? "Onaylı taslağı indir" : "DOCX için personel onayı gerekir"} onClick={() => void download(item.analysis_id).catch((downloadFailure) => setDownloadError(downloadFailure instanceof Error ? downloadFailure.message : "DOCX indirilemedi."))}><Download size={14} /> DOCX</button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
};

export const ReviewQueuePage: React.FC<ViewProps> = ({ onOpenAnalysis }) => {
  const [items, setItems] = useState<PendingReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try { setItems((await api.getPendingReviews(40)).items); }
    catch (loadError) { setError(loadError instanceof Error ? loadError.message : "İnceleme kuyruğu yüklenemedi."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  return (
    <div className="records-page no-print">
      <PageHeader icon={<UserCheck />} eyebrow="Personel onayı" title="İnceleme Bekleyenler" description="AI önerisi veya resmî yazı taslağı personel kararı gerektiren evraklar." onRefresh={load} loading={loading} />
      {error && <div className="inline-error" role="alert">{error}</div>}
      <div className="review-queue-list">
        {items.length === 0 ? <div className="records-empty">{loading ? "İnceleme kuyruğu yükleniyor…" : "İnceleme bekleyen evrak bulunmuyor."}</div> : items.map((item) => (
          <button type="button" key={item.analysis_id} onClick={() => void onOpenAnalysis(item.analysis_id)}>
            <div className="review-queue-icon"><UserCheck size={18} /></div>
            <div><strong>{item.subject || humanize(item.document_type || "Belirsiz evrak")}</strong><span>{item.review_reasons?.join(" ") || "Personel incelemesi gerekli."}</span></div>
            <div className="review-queue-meta"><span>{item.recommended_unit || "Birim önerisi yok"}</span><time>{formatDate(item.created_at)}</time></div>
          </button>
        ))}
      </div>
    </div>
  );
};

const PageHeader: React.FC<{ icon: React.ReactNode; eyebrow: string; title: string; description: string; onRefresh: () => void | Promise<void>; loading: boolean }> = ({ icon, eyebrow, title, description, onRefresh, loading }) => (
  <header className="records-header"><div className="records-title-icon">{icon}</div><div><span className="section-kicker">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div><button type="button" className="btn btn-secondary" onClick={() => void onRefresh()} disabled={loading}><RefreshCw size={15} /> Yenile</button></header>
);

const Status: React.FC<{ value?: string }> = ({ value }) => value ? <span className={`record-status ${statusTone(value)}`}>{humanize(value)}</span> : <span>—</span>;
const EmptyTable: React.FC<{ loading: boolean; columns: number }> = ({ loading, columns }) => <tr><td colSpan={columns} className="records-empty">{loading ? "Kayıtlar yükleniyor…" : "Eşleşen evrak bulunamadı."}</td></tr>;

function unique(values: string[]): string[] { return [...new Set(values)].sort((a, b) => a.localeCompare(b, "tr")); }
function shortId(value: string): string { return value.length > 12 ? `${value.slice(0, 8)}…` : value; }
function statusTone(value: string): string { return value.includes("approved") || value === "pass" ? "success" : value.includes("pending") || value === "warning" ? "warning" : value === "rejected" || value === "fail" ? "danger" : "neutral"; }
function getDraftSubject(state?: DocumentState): string { return state?.draft?.edited_draft?.subject || state?.draft?.draft?.subject || ""; }
function hasDraft(state?: DocumentState): boolean { return Boolean(state?.draft && (state.draft.official_rendered_text || state.draft.draft_text || state.draft.draft?.body)); }
