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
import { ProcessingTimeline } from '../components/ProcessingTimeline';

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

  // Edit mode
  const [isEditing, setIsEditing] = useState(false);
  const [editSubject, setEditSubject] = useState('');
  const [editBody, setEditBody] = useState('');
  const [editSaving, setEditSaving] = useState(false);

  useEffect(() => {
    if (!id) return;
    const fetchAnalysis = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.getAnalysis(id);
        setState(data);
        onAnalysisLoaded?.(data);
      } catch (requestError: unknown) {
        setError(requestError);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalysis();
  }, [id, onAnalysisLoaded]);

  useEffect(() => {
    if (!externallyUpdatedDraft) return;
    setState((previous) =>
      previous ? { ...previous, draft: externallyUpdatedDraft } : previous
    );
  }, [externallyUpdatedDraft]);

  const handleUpdate = () => {
    if (id) {
      api.getAnalysis(id)
        .then((data) => {
          setState(data);
          onAnalysisLoaded?.(data);
        })
        .catch((requestError: unknown) => setError(requestError));
    }
  };

  const handleDownloadDocx = async () => {
    if (!id) return;
    setDownloading(true);
    try {
      const url = api.getDocxUrl(id);
      const response = await fetch(url);
      if (!response.ok) throw new Error('DOCX indirme hatası');
      const blob = await response.blob();
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
      handleUpdate();
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

  return (
    <div className="page-container">
      {/* Top bar */}
      <div className="workspace-topbar">
        <button className="btn btn-secondary" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} /> Geri
        </button>
        <div className="flex gap-2">
          <button
            className="btn btn-secondary"
            onClick={handlePrint}
            title="Yazdır / PDF olarak kaydet"
          >
            <Printer size={16} /> Yazdır
          </button>
          <button
            className="btn btn-primary"
            onClick={handleDownloadDocx}
            disabled={downloading}
            title="DOCX olarak indir"
          >
            <Download size={16} />
            {downloading ? 'İndiriliyor...' : 'DOCX İndir'}
          </button>
        </div>
      </div>

      {/* Processing Timeline */}
      {state.node_timings && Object.keys(state.node_timings).length > 0 && (
        <ProcessingTimeline nodeTimings={state.node_timings} isLoading={false} />
      )}

      {/* Workspace Grid: Left = A4 Preview, Right = AI Cards */}
      <div className="workspace-grid">
        {/* Left: A4 Document Preview */}
        <div className="workspace-left">
          <div className="card">
            <div className="card-header flex justify-between items-center w-full">
              <div className="flex items-center gap-2">
                <FileSignature size={18} /> Resmî Cevap Taslağı
              </div>
              <div className="flex items-center gap-2">
                {state.draft?.draft_type && (
                  <span className="badge badge-info" style={{ fontSize: '0.75rem' }}>
                    {formatDraftType(state.draft.draft_type)}
                  </span>
                )}
                {!isEditing && (
                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: '0.8rem', padding: '0.3rem 0.6rem' }}
                    onClick={startEdit}
                    title="Taslağı düzenle"
                  >
                    <Edit3 size={14} /> Düzenle
                  </button>
                )}
              </div>
            </div>
            <div className="card-body" style={{ backgroundColor: '#f8fafc' }}>
              {/* Tabs */}
              {!isEditing && (
                <div className="tabs">
                  <div
                    className={`tab ${activeTab === 'official' ? 'active' : ''}`}
                    onClick={() => setActiveTab('official')}
                  >
                    Resmî Görünüm
                  </div>
                  <div
                    className={`tab ${activeTab === 'raw' ? 'active' : ''}`}
                    onClick={() => setActiveTab('raw')}
                  >
                    Ham Taslak
                  </div>
                </div>
              )}

              {isEditing ? (
                <div className="flex-col gap-4">
                  {/* Format validator warning */}
                  <div
                    className="flex items-center gap-2"
                    style={{
                      padding: '0.6rem 0.8rem',
                      backgroundColor: '#fef3c7',
                      borderRadius: '6px',
                      fontSize: '0.8rem',
                      color: '#92400e',
                    }}
                  >
                    <AlertTriangle size={16} />
                    <span>
                      Manuel düzenlemeler resmî yazışma format kontrolünden
                      otomatik olarak geçirilmez. Lütfen format kurallarına
                      uygunluğu kendiniz doğrulayın.
                    </span>
                  </div>
                  <label style={{ fontWeight: 500, fontSize: '0.85rem' }}>Konu:</label>
                  <input
                    type="text"
                    value={editSubject}
                    onChange={(e) => setEditSubject(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.5rem 0.75rem',
                      border: '1px solid var(--border-color)',
                      borderRadius: 'var(--border-radius)',
                    }}
                    disabled={editSaving}
                  />
                  <label style={{ fontWeight: 500, fontSize: '0.85rem', marginTop: '0.5rem' }}>
                    İçerik:
                  </label>
                  <textarea
                    value={editBody}
                    onChange={(e) => setEditBody(e.target.value)}
                    style={{ minHeight: '400px' }}
                    disabled={editSaving}
                  />
                  <div className="flex gap-2 justify-end">
                    <button
                      className="btn btn-secondary"
                      onClick={() => setIsEditing(false)}
                      disabled={editSaving}
                    >
                      İptal
                    </button>
                    <button
                      className="btn btn-primary"
                      onClick={handleSaveEdit}
                      disabled={editSaving}
                    >
                      {editSaving ? 'Kaydediliyor...' : 'Kaydet'}
                    </button>
                  </div>
                </div>
              ) : activeTab === 'official' ? (
                <div className="official-document print-area">
                  {officialText || (
                    <p className="text-center text-secondary" style={{ marginTop: '4rem' }}>
                      Resmî görünüm mevcut değil.
                    </p>
                  )}
                </div>
              ) : (
                <textarea
                  readOnly
                  value={rawDraftText || 'Ham taslak mevcut değil.'}
                  style={{ minHeight: '400px', backgroundColor: '#fff' }}
                />
              )}
            </div>
          </div>
        </div>

        {/* Right: AI Analysis Cards */}
        <div className="workspace-right">
          <AnalysisCard document={state.document} documentId={state.document_id} />
          <SummaryCard summary={state.summary} />
          <ExtractionCard extraction={state.extraction} />
          <MissingFieldsCard missingFields={state.missing_fields} />
          <LegalCard legalAnalysis={state.legal_analysis} />
          <RoutingCard routing={state.routing} />
          <QualityFormatCard quality={state.quality} />
          <HumanReviewPanel
            review={state.human_review}
            analysisId={state.analysis_id || state.document_id}
            onUpdate={handleUpdate}
            onEdit={startEdit}
          />
        </div>
      </div>
    </div>
  );
};

function formatDraftType(type: string): string {
  switch (type) {
    case 'cevap_yazisi': return 'Cevap Yazısı';
    case 'ust_yazi': return 'Üst Yazı';
    case 'bilgilendirme_metni': return 'Bilgilendirme Metni';
    case 'eksik_bilgi_talebi': return 'Eksik Bilgi Talebi';
    default: return type.replace(/_/g, ' ').toUpperCase();
  }
}
