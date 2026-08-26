import React, { useState } from "react";
import { AlertTriangle, BookOpen, FileSearch, ListChecks, Route, Sparkles, UserCheck } from "lucide-react";
import type { DocumentState, LegalEvidence } from "../types";
import { HumanReviewPanel } from "./cards/HumanReviewPanel";

interface Props {
  state: DocumentState;
  onUpdate: () => void | Promise<void>;
}

type AnalysisTab = "analysis" | "routing" | "legal" | "review";

const tabs: Array<{ id: AnalysisTab; label: string; icon: React.ComponentType<{ size?: number }> }> = [
  { id: "analysis", label: "Analiz", icon: Sparkles },
  { id: "routing", label: "Yönlendirme", icon: Route },
  { id: "legal", label: "Mevzuat", icon: BookOpen },
  { id: "review", label: "İnceleme", icon: UserCheck },
];

export const AnalysisPanel: React.FC<Props> = ({ state, onUpdate }) => {
  const [activeTab, setActiveTab] = useState<AnalysisTab>("analysis");
  const missingFields = state.missing_fields?.missing_fields || [];
  const uncertainFields = state.missing_fields?.uncertain_fields || [];
  const routingEvidence = state.routing?.routing_evidence || state.routing?.evidence || [];
  const routingScore = state.routing?.routing_score ?? state.routing?.confidence;
  const legalEvidence = getLegalEvidence(state);
  const extractedFields = Object.entries(state.extraction?.fields || {}).slice(0, 8);
  const routingReason = state.routing?.reason || state.routing?.routing_reason;

  return (
    <aside className="analysis-panel no-print">
      <div className="analysis-panel-title">
        <span className="section-kicker">Belge asistanı</span>
        <h2>AI Değerlendirmesi</h2>
      </div>
      <nav className="analysis-tabs" aria-label="Analiz bölümleri">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button key={id} type="button" className={activeTab === id ? "active" : ""} onClick={() => setActiveTab(id)} aria-selected={activeTab === id}>
            <Icon size={15} /><span>{label}</span>
          </button>
        ))}
      </nav>

      <div className="analysis-tab-content">
        {activeTab === "analysis" && (
          <>
            <section className="analysis-section">
              <div className="analysis-heading"><FileSearch size={17} /><h3>Evrak Analizi</h3></div>
              <InfoRow label="Evrak türü" value={state.document?.document_type || "Belirlenemedi"} />
              {state.document?.process_intent && <InfoRow label="İşlem niyeti" value={state.document.process_intent} />}
              {state.summary?.short_summary && <div className="analysis-content-block"><span>Özet</span><p>{state.summary.short_summary}</p></div>}
            </section>
            <section className="analysis-section">
              <div className="analysis-heading"><ListChecks size={17} /><h3>Eksik Bilgiler</h3></div>
              {missingFields.length > 0 ? <><span className="analysis-field-label">Eksik alanlar</span><ul className="compact-list warning-list">{missingFields.map((field) => <li key={field}>{humanize(field)}</li>)}</ul></> : <p className="panel-positive">Zorunlu eksik bilgi tespit edilmedi.</p>}
              {uncertainFields.length > 0 && <><span className="analysis-field-label">Belirsiz alanlar</span><ul className="compact-list uncertain-list">{uncertainFields.map((field: string) => <li key={field}>{humanize(field)}</li>)}</ul></>}
            </section>
            {extractedFields.length > 0 && (
              <section className="analysis-section">
                <div className="analysis-heading"><Sparkles size={17} /><h3>Çıkarılan Bilgiler</h3></div>
                <dl className="extracted-list">{extractedFields.map(([key, field]) => <React.Fragment key={key}><dt>{humanize(key)}</dt><dd>{formatField(field)}</dd></React.Fragment>)}</dl>
              </section>
            )}
          </>
        )}

        {activeTab === "routing" && (
          <section className="analysis-section routing-section">
            <div className="analysis-heading"><Route size={17} /><h3>Birim Yönlendirme</h3></div>
            <span className="analysis-field-label">Önerilen birim</span>
            <strong className="routing-unit">{state.routing?.recommended_unit || "Yönlendirme üretilemedi"}</strong>
            {routingReason && <div className="analysis-content-block"><span>Routing gerekçesi</span><p>{routingReason}</p></div>}
            {Array.isArray(routingEvidence) && routingEvidence.length > 0 && <div className="analysis-content-block"><span>Kanıt</span><ul className="compact-list">{routingEvidence.map((item: unknown, index: number) => <li key={index}>{String(item)}</li>)}</ul></div>}
            {routingScore !== undefined && <InfoRow label="Güven / kural skoru" value={formatScore(routingScore)} />}
            {(state.routing?.needs_human_review || state.routing?.requires_human_review) && <span className="review-warning"><AlertTriangle size={14} /> Personel doğrulaması gerekli</span>}
          </section>
        )}

        {activeTab === "legal" && (
          <section className="analysis-section">
            <div className="analysis-heading"><BookOpen size={17} /><h3>Tespit Edilen Mevzuat</h3></div>
            {legalEvidence.length > 0 ? (
              <ul className="legal-compact-list">{legalEvidence.map((item, index) => (
                <li key={`${item.law_number || item.source}-${index}`}>
                  <strong>{item.law_name || item.source || "Mevzuat kaynağı"}</strong>
                  {(item.law_number || item.article) && <span>{[item.law_number, item.article && `Madde ${item.article}`].filter(Boolean).join(" · ")}</span>}
                  {item.text && <p>{item.text}</p>}
                </li>
              ))}</ul>
            ) : <p className="panel-muted">Doğrulanmış mevzuat kanıtı bulunamadı.</p>}
          </section>
        )}

        {activeTab === "review" && (
          <>
            <section className="analysis-section review-summary">
              <div className="analysis-heading"><UserCheck size={17} /><h3>Personel İncelemesi</h3></div>
              <InfoRow label="İnceleme gerekli" value={state.human_review?.required ? "Evet" : "Hayır"} />
              <InfoRow label="Durum" value={state.human_review?.status || "Bilinmiyor"} />
              <p className="review-disclaimer">AI tarafından oluşturulan taslak. Resmî işlem öncesinde personel kontrolü gerektirir.</p>
            </section>
            <HumanReviewPanel review={state.human_review} analysisId={state.analysis_id || state.document_id} onUpdate={onUpdate} />
          </>
        )}
      </div>
    </aside>
  );
};

const InfoRow: React.FC<{ label: string; value: string }> = ({ label, value }) => <div className="analysis-info-row"><span>{label}</span><strong>{humanize(value)}</strong></div>;

function getLegalEvidence(state: DocumentState): LegalEvidence[] {
  const analysis = state.legal_analysis as Record<string, unknown>;
  const candidates = analysis?.evidence || analysis?.evidences || analysis?.sources;
  return Array.isArray(candidates) ? candidates as LegalEvidence[] : [];
}

function formatField(field: unknown): string {
  const value = field && typeof field === "object" && "value" in field ? (field as { value?: unknown }).value : field;
  if (value === null || value === undefined || value === "") return "Belirtilmemiş";
  if (Array.isArray(value)) return value.map((item) => typeof item === "object" ? JSON.stringify(item) : String(item)).join(", ");
  if (typeof value === "object") return Object.values(value as Record<string, unknown>).filter(Boolean).join(", ");
  return String(value);
}

function legalValue(item: LegalEvidence, key: string): string {
  const direct = (item as Record<string, unknown>)[key];
  const metadata = (item as Record<string, unknown>).metadata;
  const nested = metadata && typeof metadata === "object" ? (metadata as Record<string, unknown>)[key] : undefined;
  return String(direct || nested || "");
}
function formatScore(value: unknown): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  return numeric <= 1 ? `%${Math.round(numeric * 100)}` : String(Math.round(numeric));
}
const FIELD_LABELS: Record<string, string> = { person_name: "Ad Soyad", gonderen_adi: "Ad Soyad", address: "Adres", adres: "Adres", signature_present: "İmza", imza: "İmza", date: "Tarih", tarih: "Tarih", subject: "Konu", konu: "Konu", request: "Talep", talep_metni: "Talep" };
function humanize(value: string): string { return FIELD_LABELS[value] || value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toLocaleUpperCase("tr-TR")); }
