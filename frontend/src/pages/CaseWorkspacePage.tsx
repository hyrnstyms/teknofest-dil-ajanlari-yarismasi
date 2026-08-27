import React, { useEffect, useState } from "react";
import { Bot, Building2, CalendarClock, FileText, LockKeyhole, Route, Save, UserRound } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { CaseTimeline, ConfirmAction, StatusBadge } from "../components/case/CasePrimitives";
import { useAuth } from "../contexts/AuthContext";
import { caseApi } from "../services/caseApi";
import type { CaseRecord, DepartmentAction } from "../types/case";

type Pending = "review" | "route" | "start" | "clarification" | null;
const blankAction = { action_type: "", result: "", decision: "", planned_date: "", notes: "" };

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
            : await caseApi.requestCitizenInfo(token, item);
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

  if (loading) return <div className="case-loading">Dosya ve yetkiler yükleniyor…</div>;
  if (error && !item) return <div className="case-page"><div className="case-error" role="alert">{error}</div></div>;
  if (!item) return null;

  const canAccept = item.permissions.includes("ACCEPT_REVIEW") && user?.role === "EVRAK_KAYIT";
  const canRoute = item.permissions.includes("ROUTE_CASE") && user?.role === "EVRAK_KAYIT";
  const canStart = item.permissions.includes("START_CASE") && user?.role === "BIRIM_PERSONELI";
  const canAction = item.permissions.includes("RECORD_DEPARTMENT_ACTION") && user?.role === "BIRIM_PERSONELI";
  const verifiedAction = item.department_actions.some((action) => action.verified);
  const closed = item.workflow_status === "CLOSED";

  return <div className="case-page case-workspace">
    <nav className="case-breadcrumb"><Link to="/dosyalar">Dosyalar</Link><span>›</span><span>{item.tracking_code}</span></nav>
    <header className="case-workspace-header">
      <div><span className="eyebrow">{item.tracking_code}</span><h1>{item.title}</h1><StatusBadge status={item.workflow_status}/></div>
      <div className="ownership-strip">
        <section><span><UserRound/> Kaynak / Başvuru Sahibi</span><strong>{item.originator_name}</strong><small>{item.source_type} · {item.source_channel}</small></section>
        <section><span><Building2/> Mevcut Sahip</span><strong>{item.current_department_name}</strong><small>Kurumsal sorumluluk</small></section>
        <section className="ai-owner"><span><Bot/> AI Önerisi</span><strong>{item.routing_recommendation?.recommended_unit || "Öneri bulunmuyor"}</strong><small>İnsan onayı olmadan sahiplik değişmez</small></section>
      </div>
    </header>
    {notice && <div className="case-success" role="status">{notice}</div>}
    {error && <div className="case-error" role="alert">{error}</div>}
    <div className="case-workspace-grid">
      <main>
        <section className="case-panel"><span className="eyebrow">AI ANALİZİ</span><h2>Başvuru özeti</h2><p>{item.analysis_summary || "Analiz özeti henüz hazır değil."}</p></section>
        {item.clarification?.needs_clarification && <section className="case-panel clarification-panel">
          <span className="eyebrow">BLOKE EDİCİ EKSİK BİLGİ</span><h2>Eksik bilgi nedeniyle bekliyor</h2>
          <blockquote>{item.clarification.question}</blockquote>
          {item.permissions.includes("REQUEST_CITIZEN_INFO") && <button className="btn btn-primary" disabled={closed} onClick={() => setPending("clarification")}>Vatandaştan Bilgi İste</button>}
        </section>}
        {item.routing_recommendation && <section className="case-panel routing-decision">
          <header><div><span className="eyebrow">AI ÖNERİSİ · İNSAN KARARI GEREKİR</span><h2>{item.routing_recommendation.recommended_unit}</h2></div><Route/></header>
          <h3>Gerekçe</h3><p>{item.routing_recommendation.reason}</p>
          {item.routing_recommendation.evidence.length > 0 && <ul>{item.routing_recommendation.evidence.map((evidence) => <li key={evidence}>{evidence}</li>)}</ul>}
          {canRoute && <button className="btn btn-primary" onClick={() => setPending("route")}>{item.routing_recommendation.recommended_unit} birimine yönlendir</button>}
        </section>}
        {canAction && <section className="case-panel">
          <span className="eyebrow">İNSAN TARAFINDAN DOĞRULANAN KAYNAK</span><h2>Kurum işlem sonucunu kaydet</h2>
          <form className="department-action-form" onSubmit={(event) => void saveAction(event)}>
            <label>İşlem Türü<input required value={form.action_type} onChange={(event) => setForm({ ...form, action_type: event.target.value })}/></label>
            <label>Sonuç<textarea required value={form.result} onChange={(event) => setForm({ ...form, result: event.target.value })}/></label>
            <label>Karar<textarea required value={form.decision} onChange={(event) => setForm({ ...form, decision: event.target.value })}/></label>
            <label>Planlanan Tarih<input type="date" value={form.planned_date} onChange={(event) => setForm({ ...form, planned_date: event.target.value })}/></label>
            <label className="full">Personel Notu<textarea value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })}/></label>
            <button className="btn btn-primary" disabled={busy}><Save size={16}/> Doğrulanmış işlem sonucunu kaydet</button>
          </form>
        </section>}
        <section className="case-panel draft-guard"><header><h2>Resmî cevap hazırlığı</h2><FileText/></header>
          {verifiedAction
            ? <p>Copilot’a “Vatandaşa cevap hazırla” diyerek doğrulanmış işlem sonucuna dayalı taslak oluşturabilirsiniz.</p>
            : <div className="guard-message"><LockKeyhole/><div><strong>Önce kurum işlem sonucu kaydedilmelidir.</strong><p>AI gerçekleşmemiş bir kamu işlemi adına nihai cevap oluşturamaz.</p></div></div>}
        </section>
      </main>
      <aside>
        <section className="case-panel next-action"><span className="eyebrow">SONRAKİ ADIM</span>
          <h2>{closed ? "Dosya kapatıldı" : canAccept ? "İlk incelemeyi onaylayın" : canRoute ? "Yönlendirmeyi doğrulayın" : canStart ? "Dosyayı işleme alın" : canAction ? "Kurum işlemini kaydedin" : "Mevcut aşamayı inceleyin"}</h2>
          {canAccept && <button className="btn btn-primary" onClick={() => setPending("review")}>İncelemeyi Onayla</button>}
          {canStart && <button className="btn btn-primary" onClick={() => setPending("start")}>İşleme Al</button>}
        </section>
        {item.deadline?.applicable && item.deadline.legal_basis?.verified
          ? <section className="case-panel deadline-card"><span><CalendarClock/> Yasal Süre</span><strong>{item.deadline.deadline_days} gün</strong><p>{item.deadline.due_at ? new Date(item.deadline.due_at).toLocaleDateString("tr-TR") : "Son tarih hesaplanamadı"}</p><small>{item.deadline.legal_basis.citation}</small></section>
          : <section className="case-panel"><p>Bu dosya için doğrulanmış bir yasal süre bulunamadı.</p></section>}
        <section className="case-panel"><h2>Dosya zaman çizelgesi</h2><CaseTimeline events={item.timeline}/></section>
      </aside>
    </div>
    {pending && <ConfirmAction
      busy={busy}
      title={pending === "review" ? "İlk incelemeyi onayla" : pending === "route" ? "Kurumsal sorumluluğu aktar" : pending === "start" ? "Dosyayı işleme al" : "Eksik bilgi talebini gönder"}
      text={pending === "route" ? `Dosyanın sorumluluğu ${item.routing_recommendation?.recommended_unit} birimine aktarılacaktır.` : "Bu işlem Case Engine tarafından kalıcı olarak kaydedilecektir."}
      onCancel={() => setPending(null)}
      onConfirm={() => void confirm()}
    />}
  </div>;
}
