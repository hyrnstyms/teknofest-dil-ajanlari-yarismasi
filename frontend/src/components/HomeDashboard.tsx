import React, { useCallback, useEffect, useState } from "react";
import { ArrowRight, FileClock, FilePlus2, Files, RefreshCw } from "lucide-react";
import {
  api,
  type AnalysisListItem,
  type PendingReviewItem,
  type InstitutionOption,
} from "../services/api";
import { formatDocumentType, formatInstitution, formatDisplayName } from "../utils/presentation";

interface Props {
  institution: InstitutionOption | null;
  onNewDocument: () => void;
  onOpenAnalysis: (analysisId: string) => void | Promise<void>;
}

interface HomeAnalysisItem extends AnalysisListItem {
  institution_id?: string;
}

export const HomeDashboard: React.FC<Props> = ({ institution, onNewDocument, onOpenAnalysis }) => {
  const [analyses, setAnalyses] = useState<HomeAnalysisItem[]>([]);
  const [pending, setPending] = useState<PendingReviewItem[]>([]);
  const [pendingTotal, setPendingTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [analysesResult, pendingResult] = await Promise.all([
        api.getAnalyses(8),
        api.getPendingReviews(6),
      ]);
      const enrichedAnalyses = await Promise.all(
        analysesResult.items.map(async (item): Promise<HomeAnalysisItem> => {
          try {
            const detail = await api.getAnalysis(item.analysis_id);
            return { ...item, institution_id: detail.kurum_profili_id };
          } catch {
            return item;
          }
        }),
      );
      setAnalyses(enrichedAnalyses);
      setPending(pendingResult.items);
      setPendingTotal(pendingResult.total);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Anasayfa verileri yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const isEmpty = !loading && analyses.length === 0;

  return (
    <div className="home-dashboard no-print">
      <header className="home-header">
        <div>
          <span className="section-kicker">KAMUAI karar destek sistemi</span>
          <h1>KAMUAI Evrak Masası</h1>
          <p>Kamu evraklarını analiz eder, eksikleri tespit eder, ilgili mevzuatı bulur, doğru birime yönlendirir ve resmî yazı taslağı hazırlar.</p>
          <span className="institution-profile-badge">Kurum Profili: <strong>{institution?.label || "Kurum seçilmedi"}</strong></span>
        </div>
        <div className="home-actions">
          <button type="button" className="icon-button" onClick={() => void load()} disabled={loading} title="Verileri yenile"><RefreshCw size={17} /></button>
          <button type="button" className="btn btn-primary" onClick={onNewDocument}><FilePlus2 size={17} /> Yeni Evrak Yükle</button>
        </div>
      </header>

      {error && <div className="inline-error" role="alert">{error}</div>}

      {isEmpty ? (
        <section className="home-empty">
          <Files size={34} />
          <h2>Henüz işlenmiş evrak bulunmuyor.</h2>
          <button type="button" className="btn btn-primary" onClick={onNewDocument}>İlk Evrakı Yükle</button>
        </section>
      ) : (
        <div className="home-work-layout">
          <section className="home-list-card">
            <div className="home-card-header"><div><span className="section-kicker">Kayıtlar</span><h2>Son Evraklar</h2></div><span>{analyses.length} kayıt</span></div>
            <div className="home-record-list">
              {analyses.map((item) => (
                <button type="button" key={item.analysis_id} onClick={() => void onOpenAnalysis(item.analysis_id)}>
                  <div>
                    <strong>{item.document_id || formatDocumentType(item.document_type) || "Belirsiz evrak"}</strong>
                    <span>Analiz: {shortId(item.analysis_id)} · Kurum: {item.institution_id ? formatInstitution(item.institution_id) : "—"}</span>
                  </div>
                  <div className="record-meta">
                    <Status status={item.quality_status} />
                    <Status status={item.human_review_status} />
                    <time>{formatDate(item.created_at)}</time><ArrowRight size={15} />
                  </div>
                </button>
              ))}
            </div>
          </section>

          <aside className="home-side-stack">
            {analyses[0] && (
              <section className="last-work-card">
                <div className="last-work-icon"><FileClock size={19} /></div>
                <span className="section-kicker">Son çalışma</span>
                <h2>{analyses[0].subject || analyses[0].document_id || formatDocumentType(analyses[0].document_type) || "Son analiz"}</h2>
                <p>Analiz: {shortId(analyses[0].analysis_id)} · {formatDate(analyses[0].created_at)}</p>
                <button type="button" onClick={() => void onOpenAnalysis(analyses[0].analysis_id)}>Çalışma alanını aç <ArrowRight size={15} /></button>
              </section>
            )}

            <section className="home-list-card pending-card">
              <div className="home-card-header"><div><span className="section-kicker">Personel kuyruğu</span><h2>İnceleme Bekleyen Evraklar</h2></div><span>{pendingTotal} bekleyen</span></div>
              {pending.length === 0 ? (
                <div className="home-list-empty">İnceleme bekleyen evrak bulunmuyor.</div>
              ) : (
                <div className="pending-list">
                  {pending.map((item) => (
                    <button type="button" key={item.analysis_id} onClick={() => void onOpenAnalysis(item.analysis_id)}>
                      <div><strong>{item.subject || formatDocumentType(item.document_type) || "Belirsiz evrak"}</strong><span>{item.review_reasons?.join(" ") || "Personel incelemesi gerekli."}</span></div>
                      <time>{formatDate(item.created_at)}</time>
                    </button>
                  ))}
                </div>
              )}
            </section>
          </aside>
        </div>
      )}
    </div>
  );
};

const Status: React.FC<{ status?: string }> = ({ status }) => {
  if (!status) return null;
  const value = status;
  const tone = value.includes("approved") || value === "pass" ? "success" : value.includes("pending") || value === "warning" ? "warning" : value === "rejected" || value === "fail" ? "danger" : "neutral";
  return <span className={`home-status ${tone}`}>{formatDisplayName(value)}</span>;
};

function shortId(value: string): string { return value.length > 12 ? `${value.slice(0, 8)}…` : value; }
function formatDate(value?: string): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("tr-TR", { dateStyle: "short", timeStyle: "short" }).format(date);
}
