import React from "react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import type { DocumentState } from "../types";

export const DecisionSummary: React.FC<{ state: DocumentState }> = ({ state }) => {
  const missing = state.missing_fields?.missing_fields || [];
  const uncertain = state.missing_fields?.uncertain_fields || [];
  const legal = state.legal_analysis || {};
  const evidence = legal.evidence || legal.evidences || legal.sources;
  const evidenceCount = Array.isArray(evidence) ? evidence.length : 0;
  const reviewRequired = Boolean(state.human_review?.required || state.routing?.needs_human_review || missing.length || uncertain.length);
  return <section className="decision-summary no-print" aria-labelledby="decision-summary-title">
    <div className="decision-summary-heading"><div><span className="section-kicker">Personel karar desteği</span><h2 id="decision-summary-title">Evrak Değerlendirme Özeti</h2></div><span className={`decision-state ${reviewRequired ? "warning" : "success"}`}>{reviewRequired ? <AlertTriangle size={15} /> : <CheckCircle2 size={15} />}{reviewRequired ? "Personel kontrolü gerekli" : "Ön değerlendirme tamamlandı"}</span></div>
    <div className="decision-grid">
      <Item label="Belge Türü" value={state.document?.document_type} /><Item label="İşlem Amacı" value={state.document?.process_intent} /><Item label="Öncelik" value={reviewRequired ? "Kontrol öncelikli" : "Normal"} /><Item label="Önerilen Birim" value={state.routing?.recommended_unit} /><Item label="Eksik / Belirsiz" value={`${missing.length} / ${uncertain.length}`} /><Item label="Mevzuat" value={evidenceCount ? `${evidenceCount} doğrulanmış kanıt` : "Kanıt bulunamadı"} /><Item label="İnsan İncelemesi" value={state.human_review?.status || (reviewRequired ? "pending_review" : "not_required")} />
    </div>
  </section>;
};
const Item: React.FC<{ label: string; value?: string | null }> = ({ label, value }) => <div className="decision-item"><span>{label}</span><strong>{friendly(value || "Belirlenemedi")}</strong></div>;
function friendly(value: string): string { return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toLocaleUpperCase("tr-TR")); }