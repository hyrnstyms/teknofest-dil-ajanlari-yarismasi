import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Loader2,
  ArrowLeft,
  Download,
  Printer,
  Edit3,
  FileSignature,
  AlertTriangle,
} from 'lucide-react';
import { api } from '../services/api';
import { DocumentState, DraftInfo } from '../types';
import { ErrorDisplay } from '../components/ErrorDisplay';

// Import existing cards
import { AnalysisCard } from '../components/cards/AnalysisCard';
import { SummaryCard } from '../components/cards/SummaryCard';
import { ExtractionCard } from '../components/cards/ExtractionCard';
import { MissingFieldsCard } from '../components/cards/MissingFieldsCard';
import { LegalCard } from '../components/cards/LegalCard';
import { RoutingCard } from '../components/cards/RoutingCard';
import { QualityFormatCard } from '../components/cards/QualityFormatCard';
import { HumanReviewPanel } from '../components/cards/HumanReviewPanel';
import { formatDate, formatDisplayName, formatInstitution, formatPriority, formatReviewStatus } from '../utils/presentation';

interface Props {
  onAnalysisLoaded?: (state: DocumentState) => void;
  externallyUpdatedDraft?: DraftInfo;
}

export const DocumentWorkspacePage: React.FC<Props> = ({
  onAnalysisLoaded,
  externallyUpdatedDraft,
}) => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [state, setState] = useState<DocumentState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [downloading, setDownloading] = useState(false);
  const [activeTab, setActiveTab] = useState<'official' | 'raw'>('official');
  const [reloadKey, setReloadKey] = useState(0);
  const [workspaceTab, setWorkspaceTab] = useState<'overview' | 'document' | 'legal' | 'draft'>('overview');
  const [reviewOpen, setReviewOpen] = useState(false);

  // Edit mode
  const [isEditing, setIsEditing] = useState(false);
  const [editSubject, setEditSubject] = useState('');
  const [editBody, setEditBody] = useState('');
  const [editSaving, setEditSaving] = useState(false);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    const fetchAnalysis = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.getAnalysis(id);
        if (cancelled) return;
        setState(data);
        onAnalysisLoaded?.(data);
      } catch (requestError: unknown) {
        if (!cancelled) setError(requestError);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void fetchAnalysis();
    return () => { cancelled = true; };
  }, [id, onAnalysisLoaded, reloadKey]);

  useEffect(() => {
    if (!externallyUpdatedDraft) return;
    setState((previous) =>
      previous ? { ...previous, draft: externallyUpdatedDraft } : previous
    );
  }, [externallyUpdatedDraft]);

  const handleUpdate = async () => {
    if (!id) return;
    setError(null);
    const data = await api.getAnalysis(id);
    setState(data);
    onAnalysisLoaded?.(data);
  };

  const handleDownloadDocx = async () => {
    if (!id) return;
    setDownloading(true);
    try {
      const blob = await api.downloadDocx(id);
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = 'resmi_yazi_taslak.docx';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(blobUrl);
    } catch {
      alert('DOCX indirme sırasında bir hata oluştu.');
    } finally {
      setDownloading(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const startEdit = () => {
    if (!state?.draft) return;
    setEditSubject(
      state.draft.edited_draft?.subject ||
      state.draft.draft?.subject ||
      state.draft.subject ||
      ''
    );
    setEditBody(
      state.draft.edited_draft?.body ||
      state.draft.draft_text ||
      state.draft.draft?.body ||
      state.draft.rendered_text ||
      ''
    );
    setIsEditing(true);
  };

  const handleSaveEdit = async () => {
    if (!id) return;
    setEditSaving(true);
    try {
      await api.editAnalysis(id, editSubject, editBody);
      setIsEditing(false);
      await handleUpdate();
    } catch (requestError: unknown) {
      alert(requestError instanceof Error ? requestError.message : 'Düzenleme kaydedilemedi.');
    } finally {
      setEditSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container" style={{ textAlign: 'center', paddingTop: '4rem' }}>
        <Loader2 size={40} className="text-primary spinner" />
        <p className="text-secondary" style={{ marginTop: '1rem' }}>Analiz yükleniyor...</p>
      </div>
    );
  }

  if (error || !state) {
    return (
      <div className="page-container">
        <button className="btn btn-secondary mb-6" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} /> Geri
        </button>
        <ErrorDisplay
          error={error || new Error('Bu analiz kaydı mevcut değil veya silinmiş olabilir.')}
          title="Analiz Bulunamadı"
          onRetry={() => setReloadKey((value) => value + 1)}
        />
      </div>
    );
  }

  // Extract text content for preview
  const editedDraft = state.draft?.edited_draft;
  const editedText = editedDraft
    ? [editedDraft.subject, editedDraft.body].filter(Boolean).join('\n\n')
    : '';
  const officialText = editedText ||
    (typeof state.draft?.official_rendered_text === 'string'
      ? state.draft.official_rendered_text
      : typeof state.draft?.official_render === 'string'
        ? state.draft.official_render
        : '');
  const rawDraftText =
    editedDraft?.body ||
    (typeof state.draft?.rendered_text === 'string'
      ? state.draft.rendered_text
      : state.draft?.draft_text || state.draft?.draft?.body || '');

  const title = state.draft?.edited_draft?.subject || state.draft?.draft?.subject || state.document?.subject_excerpt || "Evrak Detayı";
  const evidenceCount = Array.isArray(state.legal_analysis?.evidence) ? state.legal_analysis.evidence.length : 0;
  const missingCount = (state.missing_fields?.missing_fields || []).length + (state.missing_fields?.uncertain_fields || []).length;
  const compactStages = [
    ["document_agent", "Belge"],
    ["extraction_agent", "Analiz"],
    ["legal_agent", "Mevzuat"],
    ["routing_agent", "Yönlendirme"],
    ["writing_agent", "Taslak"],
    ["human_review_agent", "İnsan İncelemesi"],
  ];

  return (
    <div className="page-container product-workspace">
      <header className="workspace-product-header">
        <div>
          <button className="workspace-breadcrumb" type="button" onClick={() => navigate('/gelen-evraklar')}>Gelen Evraklar / Evrak Detayı</button>
          <h1>{title}</h1>
          <div className="workspace-meta">
            <span>{formatInstitution(state.kurum_profili_id)}</span><i>•</i>
            <span>{formatDisplayName(state.document?.document_type)}</span><i>•</i>
            <span>{formatDate(state.created_at)}</span><i>•</i>
            <span className={"record-status " + statusTone(state.human_review?.status)}>{formatReviewStatus(state.human_review?.status)}</span>
          </div>
        </div>
        {state.human_review?.status === 'approved' ? (
          <button className="btn btn-primary" type="button" onClick={handleDownloadDocx} disabled={downloading}><Download size={17}/>{downloading ? 'İndiriliyor' : 'DOCX İndir'}</button>
        ) : (
          <button className="btn btn-primary" type="button" onClick={() => { setWorkspaceTab('draft'); setReviewOpen(true); }}>İncelemeyi Tamamla</button>
        )}
      </header>

      <section className="workspace-decision-hero">
        <div className="workspace-decision-main">
          <span>AI Karar Özeti</span>
          <small>Önerilen Birim</small>
          <h2>{state.routing?.recommended_unit || "Personel değerlendirmesi gerekli"}</h2>
          {state.routing?.reason && <p>{state.routing.reason}</p>}
        </div>
        <div className="workspace-decision-facts">
          <Fact label="Evrak Türü" value={formatDisplayName(state.document?.document_type)} />
          <Fact label="İşlem" value={formatDisplayName(state.document?.process_intent)} />
          <Fact label="Öncelik" value={formatPriority(state.document?.priority || state.priority)} />
        </div>
      </section>

      <nav className="workspace-tabs" aria-label="Evrak çalışma alanı">
        {([
          ['overview', 'Genel Bakış'],
          ['document', 'Belge Bilgileri'],
          ['legal', 'Mevzuat'],
          ['draft', 'Taslak'],
        ] as const).map(([key, label]) => <button key={key} type="button" className={workspaceTab === key ? 'active' : ''} onClick={() => setWorkspaceTab(key)}>{label}{key === 'legal' && evidenceCount > 0 ? <span>{evidenceCount}</span> : null}</button>)}
      </nav>

      {workspaceTab === 'overview' && <div className="workspace-overview-grid">
        <section className="workspace-section">
          <h2>Özet</h2>
          <SummaryCard summary={state.summary} />
        </section>
        <section className="workspace-glance">
          <div><strong>{missingCount}</strong><span>Eksik veya belirsiz bilgi</span><button type="button" onClick={() => setWorkspaceTab('document')}>Detayları Gör</button></div>
          <div><strong>{evidenceCount}</strong><span>Doğrulanmış mevzuat kaynağı</span><button type="button" onClick={() => setWorkspaceTab('legal')}>Kaynakları Gör</button></div>
          <div><strong>{formatReviewStatus(state.human_review?.status)}</strong><span>Personel incelemesi</span><button type="button" onClick={() => setWorkspaceTab('draft')}>Taslağı Gör</button></div>
        </section>
        <section className="workspace-process-compact">
          <div><h2>AI İşlem Akışı</h2><p>Yalnız tamamlanmış backend aşamaları gösterilir.</p></div>
          <div className="workspace-process-steps">{compactStages.map(([key, label]) => <div className={state.node_timings?.[key] ? 'complete' : ''} key={key}><span>{state.node_timings?.[key] ? '✓' : '○'}</span><strong>{label}</strong></div>)}</div>
        </section>
      </div>}

      {workspaceTab === 'document' && <div className="workspace-detail-grid">
        <div><AnalysisCard document={state.document} /><ExtractionCard extraction={state.extraction} /></div>
        <MissingFieldsCard missingFields={state.missing_fields} />
      </div>}

      {workspaceTab === 'legal' && <section className="workspace-legal"><LegalCard legalAnalysis={state.legal_analysis} /></section>}

      {workspaceTab === 'draft' && <div className="workspace-draft-layout">
        <section className="workspace-document-paper">
          <header><div><span>Resmî Cevap Taslağı</span><strong>{formatDraftType(state.draft?.draft_type || '')}</strong></div>{!isEditing && <button type="button" className="btn btn-secondary" onClick={startEdit}><Edit3 size={15}/>Düzenle</button>}</header>
          {isEditing ? <div className="draft-edit-form">
            <div className="review-disclaimer"><AlertTriangle size={16}/>Manuel düzenlemeleri resmî işlem öncesinde kontrol edin.</div>
            <label>Konu<input value={editSubject} onChange={(event) => setEditSubject(event.target.value)} disabled={editSaving}/></label>
            <label>İçerik<textarea value={editBody} onChange={(event) => setEditBody(event.target.value)} disabled={editSaving}/></label>
            <div className="flex gap-2 justify-end"><button className="btn btn-secondary" type="button" onClick={() => setIsEditing(false)}>İptal</button><button className="btn btn-primary" type="button" onClick={handleSaveEdit} disabled={editSaving}>{editSaving ? 'Kaydediliyor' : 'Kaydet'}</button></div>
          </div> : <div className="official-document">{officialText || rawDraftText || <p className="workspace-empty">Henüz resmî taslak oluşturulmadı.</p>}</div>}
        </section>
        <aside className="workspace-draft-side"><RoutingCard routing={state.routing}/><QualityFormatCard quality={state.quality}/>{!reviewOpen && state.human_review?.status !== 'approved' && <button className="btn btn-primary" type="button" onClick={() => setReviewOpen(true)}>İncelemeyi Tamamla</button>}{reviewOpen && <div className="review-sheet"><header><h2>Personel İncelemesi</h2><button type="button" onClick={() => setReviewOpen(false)}>×</button></header><HumanReviewPanel review={state.human_review} analysisId={state.analysis_id || state.document_id} onUpdate={async () => { await handleUpdate(); setReviewOpen(false); }} onEdit={() => { startEdit(); setReviewOpen(false); }}/></div>}</aside>
      </div>}
    </div>
  );
};

const Fact: React.FC<{ label: string; value: string }> = ({ label, value }) => <div><span>{label}</span><strong>{value}</strong></div>;
function statusTone(value?: string): string { return value?.includes('approved') ? 'success' : value === 'pending_review' ? 'warning' : value === 'rejected' ? 'danger' : 'neutral'; }

function formatDraftType(type: string): string {
  switch (type) {
    case 'cevap_yazisi': return 'Cevap Yazısı';
    case 'ust_yazi': return 'Üst Yazı';
    case 'bilgilendirme_metni': return 'Bilgilendirme Metni';
    case 'eksik_bilgi_talebi': return 'Eksik Bilgi Talebi';
    default: return type.replace(/_/g, ' ').toUpperCase();
  }
}
