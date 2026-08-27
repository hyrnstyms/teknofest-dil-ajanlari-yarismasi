import React from "react";
import { AlertTriangle, CheckCircle2, FileText, Scale } from "lucide-react";
import type { CaseRecord } from "../../types/case";
import { isResponseDraft } from "../../utils/caseDraftPresentation";

const documentTypeLabels: Record<string, string> = {
  dilekce: "Dilekçe",
  resmi_yazi: "Resmî Yazı",
  kurumlar_arasi_yazi: "Kurumlar Arası Yazı",
  ruhsat_basvurusu: "Ruhsat Başvurusu",
  form: "Form",
  tutanak: "Tutanak",
  rapor: "Rapor",
  diger: "Diğer",
};
const intentLabels: Record<string, string> = {
  basvuru: "Başvuru",
  bilgi_talebi: "Bilgi Talebi",
  bildirim: "Bildirim",
  sikayet: "Şikâyet",
  talep: "Talep",
  sevk: "Sevk",
  itiraz: "İtiraz",
  diger: "Diğer",
};
const fieldLabels: Record<string, string> = {
  person_name: "Gönderen / Başvuru Sahibi",
  institution: "Kurum",
  sender_unit: "Gönderen Birim",
  recipient: "Muhatap",
  subject: "Konu",
  request: "Talep",
  document_number: "Evrak Numarası",
  document_date: "Evrak Tarihi",
  deadline: "Son Teslim Tarihi",
  due_date: "Son Teslim Tarihi",
  address: "Adres",
  location: "Konum",
  event_location: "Olay Yeri",
  attachments: "Ekler",
  signature_present: "İmza",
  authority_document_present: "Yetki Belgesi",
  other_entities: "Diğer Temel Bilgiler",
};
const targetLabels: Record<string, string> = {
  VATANDAS: "Başvuru sahibi",
  DIS_KURUM: "Gönderen kurum",
  KURUM_ICI: "Gönderen birim",
  INTERNAL_DEPARTMENT: "Kurum içi birim",
};
const routedStatuses = new Set(["IN_DEPARTMENT", "IN_PROGRESS", "RESPONSE_DRAFTED", "WAITING_FINAL_APPROVAL", "COMPLETED", "CLOSED"]);

function isInternalIdentifier(value: string) {
  return /^DEMO:/i.test(value.trim());
}

function titleCaseCode(value: string) {
  return value.replaceAll("_", " ").toLocaleLowerCase("tr-TR").replace(/(^|\s)\p{L}/gu, (letter) => letter.toLocaleUpperCase("tr-TR"));
}

export function caseValueLabel(value: unknown): string {
  if (value == null || value === "") return "";
  if (typeof value === "boolean") return value ? "Var" : "Yok";
  if (Array.isArray(value)) return value.map(caseValueLabel).filter(Boolean).join(", ");
  if (typeof value === "object") return "";
  const text = String(value).trim();
  if (!text || isInternalIdentifier(text)) return "";
  return documentTypeLabels[text] || intentLabels[text] || targetLabels[text] || (text.includes("_") ? titleCaseCode(text) : text);
}

export function analysisFieldLabel(key: string) {
  return fieldLabels[key] || titleCaseCode(key);
}

function fieldValue(item: CaseRecord, key: string) {
  return caseValueLabel(item.analysis_details?.extraction?.fields?.[key]?.value);
}

export function caseHeaderSummary(item: CaseRecord) {
  const document = item.analysis_details?.document || {};
  return fieldValue(item, "subject")
    || caseValueLabel(document.subject_excerpt)
    || caseValueLabel(document.subject)
    || item.title;
}

function legalCitation(value: unknown): string {
  if (typeof value === "string") return value.trim();
  if (!value || typeof value !== "object") return "";
  const item = value as Record<string, unknown>;
  const metadata = item.metadata && typeof item.metadata === "object" ? item.metadata as Record<string, unknown> : {};
  const title = caseValueLabel(item.title || item.source_title || item.name || metadata.title);
  const lawNumber = caseValueLabel(item.law_number || metadata.law_number);
  const article = caseValueLabel(item.madde_no || item.article || metadata.madde_no || metadata.article);
  const citation = caseValueLabel(item.citation);
  if (citation) return citation;
  const law = title || lawNumber;
  return [law, article ? `Madde ${article}` : ""].filter(Boolean).join(" · ");
}

function LegalResult({ item }: { item: CaseRecord }) {
  const legal = item.analysis_details?.legal_analysis;
  const evidence = Array.isArray(legal?.evidence) ? legal.evidence.map(legalCitation).filter(Boolean).slice(0, 2) : [];
  const verifiedText = legal?.verified ? caseValueLabel(legal.text || legal.answer) : "";
  const citations = evidence.length ? evidence : verifiedText ? [verifiedText] : [];
  return <div className="analysis-result-block legal-result">
    <h3><Scale/> Mevzuat / Dayanak</h3>
    {citations.length
      ? <><span className="verified-legal"><CheckCircle2/> Doğrulanmış mevzuat dayanağı</span><ul>{citations.map((citation) => <li key={citation}>{citation}</li>)}</ul></>
      : <p>Bu işlem için doğrulanmış özel mevzuat dayanağı bulunamadı.</p>}
  </div>;
}

function MissingInformationResult({ item }: { item: CaseRecord }) {
  const analysisMissing = item.analysis_details?.missing_fields?.blocking_fields
    || item.analysis_details?.missing_fields?.missing_fields
    || [];
  const active = Boolean(item.clarification?.needs_clarification);
  const missing = active && item.clarification?.requested_fields.length ? item.clarification.requested_fields : analysisMissing;
  if (!missing.length) return <div className="analysis-missing-success"><CheckCircle2/><span>İşlemi engelleyen eksik bilgi bulunmadı</span></div>;
  const target = item.clarification?.target_name
    || targetLabels[item.clarification?.target_type || item.source_type]
    || "Kaynak kişi veya kurum";
  return <div className="analysis-missing-warning">
    <AlertTriangle/>
    <div><h3>Eksik Bilgi</h3><dl>
      <div><dt>Eksik</dt><dd>{missing.map(analysisFieldLabel).join(", ")}</dd></div>
      <div><dt>Neden gerekli</dt><dd>{item.clarification?.reason || "Dosya işleminin devamı için gereklidir."}</dd></div>
      <div><dt>Kimden alınacak</dt><dd>{target}</dd></div>
      <div><dt>Önerilen işlem</dt><dd>Bilgi talebi oluştur</dd></div>
    </dl></div>
  </div>;
}

export function CaseAnalysisOverview({ item, onOpenDraft }: { item: CaseRecord; onOpenDraft?: () => void }) {
  const analysis = item.analysis_details;
  const document = analysis?.document || {};
  const documentType = caseValueLabel(document.document_subtype || document.document_type);
  const intent = caseValueLabel(document.process_intent);
  const subject = fieldValue(item, "request")
    || caseValueLabel(document.request_excerpt)
    || fieldValue(item, "subject")
    || caseValueLabel(document.subject_excerpt);
  const extraction = Object.entries(analysis?.extraction?.fields || {})
    .map(([key, field]) => ({ key, label: analysisFieldLabel(key), value: caseValueLabel(field?.value), validated: field?.validated }))
    .filter((field) => field.value && field.validated !== false)
    .slice(0, 8);
  const routed = routedStatuses.has(item.workflow_status);
  const routeDepartment = routed ? item.current_department_name : item.routing_recommendation?.recommended_unit;
  const routeReason = item.ai_operation?.reason || item.routing_recommendation?.reason;

  return <section className="document-analysis-result" aria-labelledby="analysis-result-title">
    <header><FileText/><div><h2 id="analysis-result-title">Evrak analiz sonucu</h2><p>Belgeden çıkarılan ve iş akışında kullanılan temel sonuçlar</p></div></header>
    <dl className="analysis-primary-facts">
      {documentType && <div><dt>Belge Türü</dt><dd>{documentType}</dd></div>}
      {intent && <div><dt>İşlem Amacı</dt><dd>{intent}</dd></div>}
      <div><dt>Gönderen / Kaynak</dt><dd>{item.originator_name}</dd></div>
      {subject && <div><dt>Konu / Talep</dt><dd>{subject}</dd></div>}
    </dl>
    {extraction.length > 0 && <div className="analysis-result-block extraction-result"><h3>Çıkarılan Bilgiler</h3><ul>{extraction.map((field) => <li key={field.key}><b>{field.label}:</b> {field.value}</li>)}</ul></div>}
    <MissingInformationResult item={item}/>
    <LegalResult item={item}/>
    {item.analysis_summary && <div className="analysis-result-block summary-result"><h3>Özet</h3><p>{item.analysis_summary}</p></div>}
    {routeDepartment && <div className="analysis-result-block routing-result"><h3>Yönlendirme</h3><strong>{routeDepartment}</strong>{routeReason && <p><b>Gerekçe:</b> {routeReason}</p>}<small>Durum: {routed ? "Havale tamamlandı" : "Havale kararı bekliyor"}</small></div>}
    {item.drafts.filter(isResponseDraft).length > 0 && <div className="analysis-draft-status"><div><span>Cevap</span><strong>{item.drafts.filter(isResponseDraft).length} taslak hazır</strong></div>{onOpenDraft && <button className="btn btn-secondary" onClick={onOpenDraft}>Taslağa Git</button>}</div>}
  </section>;
}
