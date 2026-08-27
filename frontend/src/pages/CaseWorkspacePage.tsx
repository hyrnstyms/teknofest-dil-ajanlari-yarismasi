import React, { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { ConfirmAction, StatusBadge } from "../components/case/CasePrimitives";
import { caseHeaderSummary } from "../components/case/CaseAnalysisOverview";
import { CaseProductPanels, type CaseWorkspaceTab } from "../components/case/CaseProductPanels";
import { CaseOperationPlan } from "../components/case/CaseOperationPlan";
import { OperationalNextAction, type OperationalAction } from "../components/case/OperationalNextAction";
import { useAuth } from "../contexts/AuthContext";
import { caseApi } from "../services/caseApi";
import type { CaseRecord, DepartmentAction } from "../types/case";

type Pending = "review" | "route" | "start" | "clarification" | "generate" | null;
const blankAction = { action_type: "", result: "", decision: "", planned_date: "", notes: "" };
const sourceLabels: Record<CaseRecord["source_type"], string> = { VATANDAS: "Vatandaş", DIS_KURUM: "Dış Kurum", KURUM_ICI: "Kurum İçi" };

export function CaseWorkspacePage() {
  const { id = "" } = useParams();
  const { token, user } = useAuth();
  const [item, setItem] = useState<CaseRecord>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState<Pending>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState(blankAction);
  const [activeTab, setActiveTab] = useState<CaseWorkspaceTab>("overview");

  useEffect(() => {
    if (!token) return;
    const load = () => {
      void caseApi.get(token, id)
        .then(setItem)
        .catch((cause) => setError(cause.message))
        .finally(() => setLoading(false));
    };
    const updated = (event: Event) => {
      if ((event as CustomEvent<{ caseId?: string }>).detail?.caseId === id) load();
    };
    load();
    window.addEventListener("evrag:case-updated", updated);
    return () => window.removeEventListener("evrag:case-updated", updated);
  }, [token, id]);

  async function confirm() {
    if (!token || !item || !pending) return;
    setBusy(true);
    setError("");
    try {
      const result = pending === "review"
        ? await caseApi.acceptReview(token, item)
        : pending === "route"
          ? await caseApi.route(token, item, item.routing_recommendation!.recommended_department_code)
          : pending === "start"
            ? await caseApi.start(token, item)
            : pending === "generate"
              ? await caseApi.regenerateDraft(token, item)
              : await caseApi.requestInformation(token, item);
      setItem(result.case);
      setNotice(result.message);
      setPending(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "İşlem tamamlanamadı.");
    } finally {
      setBusy(false);
    }
  }

  async function saveAction(event: React.FormEvent) {
    event.preventDefault();
    if (!token || !item) return;
    setBusy(true);
    setError("");
    try {
      const result = await caseApi.departmentAction(
        token,
        item,
        form as Omit<DepartmentAction, "id" | "verified" | "recorded_by_user_id" | "created_at">,
      );
      setItem(result.case);
      setNotice(result.message);
      setForm(blankAction);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "İşlem sonucu kaydedilemedi.");
    } finally {
      setBusy(false);
    }
  }

  function openTabAndScroll(tab: CaseWorkspaceTab, elementId: string) {
    setActiveTab(tab);
    window.setTimeout(() => document.getElementById(elementId)?.scrollIntoView({ behavior: "smooth", block: "start" }), 0);
  }

  function handleOperationalAction(action: OperationalAction) {
    if (action === "assignment") return document.getElementById("case-assignment")?.scrollIntoView({ behavior: "smooth", block: "center" });
    if (action === "result") return openTabAndScroll("overview", "department-action");
    if (action === "draft") return openTabAndScroll("writings", "official-writing-detail");
    if (action === "generate") return setPending("generate");
    setPending(action);
  }

  if (loading) return <div className="case-loading">Dosya ve yetkiler yükleniyor…</div>;
  if (error && !item) return <div className="case-page"><div className="case-error" role="alert">{error}</div></div>;
  if (!item) return null;

  const canAction = item.permissions.includes("RECORD_DEPARTMENT_ACTION") && user?.role === "BIRIM_PERSONELI";
  const actionPanel = canAction ? <section className="case-panel" id="department-action">
    <h2>Kurum İşlem Sonucu</h2><p>Doğrulanmış saha veya kurum sonucunu dosyaya kaydedin.</p>
    <form className="department-action-form" onSubmit={(event) => void saveAction(event)}>
      <label>İşlem Türü<input required value={form.action_type} onChange={(event) => setForm({ ...form, action_type: event.target.value })}/></label>
      <label>Sonuç<textarea required value={form.result} onChange={(event) => setForm({ ...form, result: event.target.value })}/></label>
      <label>Karar<textarea required value={form.decision} onChange={(event) => setForm({ ...form, decision: event.target.value })}/></label>
      <label>Planlanan Tarih<input type="date" value={form.planned_date} onChange={(event) => setForm({ ...form, planned_date: event.target.value })}/></label>
      <label className="full">Personel Notu<textarea value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })}/></label>
      <button className="btn btn-primary" disabled={busy}><Save size={16}/> İşlem Sonucunu Kaydet</button>
    </form>
  </section> : undefined;

  return <div className="case-page case-workspace">
    <nav className="case-breadcrumb"><Link to="/dosyalar">Dosyalar</Link><span>›</span><span>{item.tracking_code}</span></nav>
    <header className="case-workspace-header cockpit-header">
      <span className="tracking-code">{item.tracking_code}</span>
      <h1>{caseHeaderSummary(item)}</h1>
      <div className="case-header-meta"><span>{sourceLabels[item.source_type]}</span><i>•</i><span>{item.current_department_name}</span><i>•</i><StatusBadge status={item.workflow_status}/></div>
    </header>
    {notice && <div className="case-success" role="status">{notice}</div>}
    {error && <div className="case-error" role="alert">{error}</div>}
    <div className="case-cockpit">
      <CaseOperationPlan item={item}/>
      <OperationalNextAction item={item} user={user} onAction={handleOperationalAction}/>
    </div>
    {token && <CaseProductPanels
      item={item}
      token={token}
      activeTab={activeTab}
      onTabChange={setActiveTab}
      actionPanel={actionPanel}
      onRefresh={async () => setItem(await caseApi.get(token, id))}
      onNotice={setNotice}
    />}
    {pending && <ConfirmAction
      busy={busy}
      title={pending === "review" ? "İlk incelemeyi onayla" : pending === "route" ? "Kurumsal sorumluluğu aktar" : pending === "start" ? "Dosyayı işleme al" : pending === "generate" ? "Cevap taslağı oluştur" : "Eksik bilgi talebini gönder"}
      text={pending === "route" ? `Dosyanın sorumluluğu ${item.routing_recommendation?.recommended_unit} birimine aktarılacaktır.` : "Bu işlem Case Engine tarafından kalıcı olarak kaydedilecektir."}
      onCancel={() => setPending(null)}
      onConfirm={() => void confirm()}
    />}
  </div>;
}
