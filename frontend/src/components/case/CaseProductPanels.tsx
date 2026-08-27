import React, { useState, type ReactNode } from "react";
import { BookOpen, Check, CheckCircle2, FileSearch, History, Route, ShieldCheck } from "lucide-react";
import type { CaseRecord } from "../../types/case";
import { analysisFieldLabel, CaseAnalysisOverview, caseValueLabel } from "./CaseAnalysisOverview";
import { CaseTimeline } from "./CasePrimitives";
import { OfficialWritingWorkspace } from "./OfficialWritingWorkspace";
import { WritingGroundingSummary } from "./WritingGroundingSummary";

const stages = ["Alındı", "Ön İnceleme", "Havale", "Birim İşlemi", "Cevap", "Tamamlandı"];
const rank: Record<string, number> = { RECEIVED: 0, ANALYZING: 1, WAITING_INITIAL_REVIEW: 1, WAITING_CITIZEN_INFO: 1, READY_TO_ROUTE: 2, IN_DEPARTMENT: 3, IN_PROGRESS: 3, RESPONSE_DRAFTED: 4, WAITING_FINAL_APPROVAL: 4, COMPLETED: 5, CLOSED: 5 };

export type CaseWorkspaceTab = "overview" | "writings" | "timeline" | "report";

function CaseLifecycle({ item }: { item: CaseRecord }) {
  const current = rank[item.workflow_status] ?? 0;
  return <section className="case-lifecycle" aria-label="Dosya ilerleme durumu">
    {stages.map((stage, index) => <React.Fragment key={stage}>
      <span className={index < current ? "done" : index === current ? "current" : "future"}><i>{index < current ? <Check/> : index + 1}</i>{stage}</span>
      {index < stages.length - 1 && <b>→</b>}
    </React.Fragment>)}
  </section>;
}

interface Props {
  item: CaseRecord;
  token: string;
  onRefresh: () => Promise<void>;
  onNotice: (text: string) => void;
  activeTab?: CaseWorkspaceTab;
  onTabChange?: (tab: CaseWorkspaceTab) => void;
  actionPanel?: ReactNode;
}

export function CaseProductPanels({ item, token, onRefresh, onNotice, activeTab, onTabChange, actionPanel }: Props) {
  const [internalTab, setInternalTab] = useState<CaseWorkspaceTab>("overview");
  const tab = activeTab || internalTab;
  const selectTab = (value: CaseWorkspaceTab) => { setInternalTab(value); onTabChange?.(value); };
  const analysis = item.analysis_details;
  const fields = Object.entries(analysis?.extraction?.fields || {}).filter(([, value]) => caseValueLabel(value?.value));
  const missing = analysis?.missing_fields?.missing_fields || [];
  const legal = analysis?.legal_analysis;

  return <>
    <CaseLifecycle item={item}/>
    {tab === "overview" && <CaseAnalysisOverview item={item} onOpenDraft={() => selectTab("writings")}/>}
    <nav className="case-workspace-tabs" aria-label="Dosya çalışma alanı bölümleri">
      <button className={tab === "overview" ? "active" : ""} onClick={() => selectTab("overview")}>Genel Bakış</button>
      <button className={tab === "writings" ? "active" : ""} onClick={() => selectTab("writings")}>Cevap Taslağı{item.drafts.length ? ` (${item.drafts.length})` : ""}</button>
      <button className={tab === "timeline" ? "active" : ""} onClick={() => selectTab("timeline")}>İşlem Geçmişi</button>
      <button className={tab === "report" ? "active" : ""} onClick={() => selectTab("report")}>Teknik AI Detayı</button>
    </nav>
    <div className="case-tab-content">
      {tab === "overview" && <>{actionPanel || (item.department_actions.length ? <section className="case-panel recorded-actions"><h2>Kaydedilen İşlem Sonuçları</h2>{item.department_actions.map((action) => <article key={action.id}><strong>{action.action_type}</strong><p>{action.result}</p><small>{action.decision}</small></article>)}</section> : <section className="case-tab-empty"><h2>Genel Bakış</h2><p>Dosyanın güncel durumu ve yapılacak işlem yukarıdaki cockpit alanında özetlenmiştir.</p></section>)}</>}
      {tab === "writings" && <><WritingGroundingSummary item={item} onInspect={() => document.getElementById("official-writing-detail")?.scrollIntoView({ behavior: "smooth", block: "start" })}/><OfficialWritingWorkspace item={item} token={token} onRefresh={onRefresh} onNotice={onNotice}/></>}
      {tab === "timeline" && <section className="case-panel timeline-panel"><h2><History/> İşlem Geçmişi</h2><CaseTimeline events={item.timeline}/></section>}
      {tab === "report" && <section className="case-panel ai-report-view"><header><div><h2><FileSearch/> Teknik AI Detayı</h2><p>Belge analizi ve karar desteğinin teknik ayrıntıları.</p></div></header><div className="report-section-grid"><article><h3>Belge</h3><p><b>Tür:</b> {caseValueLabel(analysis?.document?.document_type) || "—"}</p><p><b>İşlem amacı:</b> {caseValueLabel(analysis?.document?.process_intent) || "—"}</p></article><article><h3>Özet</h3><p>{item.analysis_summary || "Özet bulunmuyor."}</p></article><article><h3>Çıkarılan Bilgiler</h3>{fields.length ? fields.map(([key, value]) => <p key={key}><b>{analysisFieldLabel(key)}:</b> {caseValueLabel(value.value)}</p>) : <p>Doğrulanmış alan yok.</p>}</article><article><h3>Eksik Bilgiler</h3><p>{missing.length ? missing.map(analysisFieldLabel).join(", ") : "İşlemi engelleyen eksik bilgi yok."}</p></article><article><h3><BookOpen/> Mevzuat / Kanıt</h3><p>{legal?.text || (legal?.verified ? "Doğrulanmış mevzuat kanıtı mevcut." : "Doğrulanmış özel mevzuat kanıtı bulunamadı.")}</p></article><article><h3><Route/> Yönlendirme</h3><p><b>Yönlendirme sonucu:</b> {item.routing_recommendation?.recommended_unit || item.current_department_name}</p><p>{item.routing_recommendation?.reason}</p>{item.routing_recommendation?.alternatives?.length ? <p><b>Alternatif:</b> {item.routing_recommendation.alternatives.map((alternative) => alternative.unit).join(", ")}</p> : null}</article><article className="full"><h3><ShieldCheck/> Resmî Yazışma Kontrolleri</h3><div className="report-checks"><span><CheckCircle2/> Muhatap doğruluğu</span><span><CheckCircle2/> Resmî üslup ve yapı</span><span><CheckCircle2/> Kurum işlem sonucu ile uyum</span><span><CheckCircle2/> Desteksiz işlem iddiası kontrolü</span></div></article></div></section>}
    </div>
  </>;
}
