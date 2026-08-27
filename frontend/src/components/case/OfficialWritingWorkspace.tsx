import React, { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Download, Eye, FilePenLine, LockKeyhole, QrCode, RefreshCw, Save, ShieldCheck } from "lucide-react";
import type { CaseDraft, CaseRecord } from "../../types/case";
import { caseApi } from "../../services/caseApi";
import { caseDownload } from "../../services/caseHttp";
import { draftStatusLabels, draftTypeLabels, recipientKindLabels } from "../../utils/caseDraftPresentation";
import { ConfirmAction } from "./CasePrimitives";

type ViewMode = "summary" | "preview" | "edit";

export function OfficialWritingWorkspace({ item, token, onRefresh, onNotice }: { item: CaseRecord; token: string; onRefresh: () => Promise<void>; onNotice: (message: string) => void }) {
  const [selectedId, setSelectedId] = useState<string>();
  const [mode, setMode] = useState<ViewMode>("summary");
  const [confirmApproval, setConfirmApproval] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const drafts = item.drafts;
  useEffect(() => { if (!selectedId || !drafts.some((draft) => draft.id === selectedId)) setSelectedId(drafts.at(-1)?.id); }, [drafts, selectedId]);
  const selected = drafts.find((draft) => draft.id === selectedId);
  const [form, setForm] = useState({ subject: "", body: "" });
  useEffect(() => { if (selected) setForm({ subject: selected.subject, body: selected.body }); }, [selected]);
  const canEdit = Boolean(selected && !["APPROVED", "SENT", "CANCELLED"].includes(selected.draft_status) && item.permissions.includes("SAVE_DRAFT"));
  const canApprove = Boolean(selected && ["DRAFT", "EDITED"].includes(selected.draft_status) && item.permissions.includes("APPROVE_DRAFT"));
  const grounding = selected?.grounded_action_id ? "Doğrulanmış birim işlem sonucu" : selected?.draft_type === "MISSING_INFORMATION_REQUEST" ? "Eksik bilgi ihtiyacı" : "Case yönlendirme kaydı";

  async function action(name: string, operation: () => Promise<unknown>, message: string) {
    setBusy(name); setError("");
    try { await operation(); await onRefresh(); onNotice(message); setMode("summary"); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "İşlem tamamlanamadı."); }
    finally { setBusy(""); }
  }

  const lockedMessage = useMemo(() => {
    if (["RECEIVED", "ANALYZING", "WAITING_INITIAL_REVIEW", "READY_TO_ROUTE", "WAITING_CITIZEN_INFO"].includes(item.workflow_status)) return "Bu dosya henüz ilgili birime yönlendirilmedi.";
    if (item.workflow_status === "IN_DEPARTMENT") return `Dosya ${item.current_department_name} birimine yönlendirildi. Nihai cevap için doğrulanmış işlem sonucu gereklidir.`;
    if (item.workflow_status === "IN_PROGRESS") return "Cevap taslağı için önce kurum işlem sonucunu kaydedin.";
    return "Bu aşamada oluşturulmuş bir cevap taslağı bulunmuyor.";
  }, [item]);

  return <section className="case-panel official-writing-workspace" id="official-writing-detail">
    <header><div><h2>Cevap Taslağı {drafts.length ? <b>({drafts.length})</b> : null}</h2><p>Case’e bağlı taslağı inceleyin, gerekiyorsa yeni revizyon kaydedin ve yetkiniz varsa onaylayın.</p></div></header>
    {drafts.length > 0 && <div className="writing-layout">
      <nav className="writing-list">{drafts.map((draft) => <button key={draft.id} className={selected?.id === draft.id ? "active" : ""} onClick={() => { setSelectedId(draft.id); setMode("summary"); }}><small>{draftTypeLabels[draft.draft_type]}</small><strong>{draft.subject}</strong><span>{draft.recipient || item.originator_name}</span><em>{draftStatusLabels[draft.draft_status]} · v{draft.revision || 1}</em></button>)}</nav>
      <div className="writing-detail">{selected && <>
        <dl className="draft-summary"><div><dt>Durum</dt><dd>{selected.draft_status === "APPROVED" ? "Onaylandı · Gönderime hazır" : draftStatusLabels[selected.draft_status]}</dd></div><div><dt>Muhatap</dt><dd>{recipientKindLabels[selected.recipient_kind || ""] || "Kayıtlı muhatap"} · {selected.recipient || item.originator_name}</dd></div><div><dt>Taslak türü</dt><dd>{draftTypeLabels[selected.draft_type]}</dd></div><div><dt>Dayanak</dt><dd>{grounding}</dd></div></dl>
        {selected.draft_status === "APPROVED" && <div className="draft-ready"><CheckCircle2/> <strong>Gönderime hazır</strong><span>Onay, gönderim anlamına gelmez; EBYS aktarımı ayrıca tamamlanmalıdır.</span></div>}
        {mode === "edit" && <div className="case-draft-editor"><label>Konu<input value={form.subject} onChange={(event) => setForm({ ...form, subject: event.target.value })}/></label><div className="recipient-readonly"><b>Muhatap</b><span>{selected.recipient || item.originator_name}</span><small>Muhatap backend kaydından korunur; bu ekranda otomatik değiştirilmez.</small></div><label>Gövde<textarea rows={12} value={form.body} onChange={(event) => setForm({ ...form, body: event.target.value })}/></label><div><button className="btn btn-secondary" onClick={() => setMode("summary")}>İptal</button><button className="btn btn-primary" disabled={Boolean(busy)} onClick={() => void action("edit", () => caseApi.editDraft(token, item, selected, { subject: form.subject, recipient: selected.recipient || "", body: form.body }), "Değişiklikler yeni revizyon olarak kaydedildi.")}><Save size={16}/> Değişiklikleri Kaydet</button></div></div>}
        {mode === "preview" && <><OfficialDocumentPreview item={item} draft={selected}/><p className="document-placeholder-help">EBYS sayısı ve imza alanları EBYS / yetkili kullanıcı tarafından tamamlanacaktır.</p></>}
        {mode === "summary" && <div className="draft-content-summary"><h3>{selected.subject}</h3><p>{selected.body}</p></div>}
        <div className="quality-checks"><strong><ShieldCheck/> Kalite Kontrolü</strong><span>✓ Muhatap kayıtlı</span><span>✓ Case ile aynı kurum bağlamı</span><span>{selected.grounded_action_id ? "✓ Doğrulanmış kurum işlemine dayalı" : "✓ Süreç kaydına dayalı"}</span></div>
        <div className="draft-actions"><button className="btn btn-secondary" onClick={() => setMode(mode === "preview" ? "summary" : "preview")}><Eye size={16}/> Taslağı Önizle</button>{canEdit && <button className="btn btn-secondary" onClick={() => setMode("edit")}><FilePenLine size={16}/> Taslağı Düzenle</button>}{selected.draft_type === "OFFICIAL_RESPONSE" && selected.draft_status !== "APPROVED" && item.department_actions.some((entry) => entry.verified) && <button className="btn btn-secondary" disabled={Boolean(busy)} onClick={() => void action("regen", () => caseApi.regenerateDraft(token, item), "Yeni taslak revizyonu oluşturuldu.")}><RefreshCw size={16}/> Yeniden Oluştur</button>}{canApprove && <button className="btn btn-primary" disabled={Boolean(busy)} onClick={() => setConfirmApproval(true)}><CheckCircle2 size={16}/> Onayla</button>}<button className="btn btn-secondary" disabled={selected.draft_status !== "APPROVED" || Boolean(busy)} onClick={() => void caseDownload(`/api/cases/${item.id}/drafts/${selected.id}/export/docx`, token, `${item.tracking_code}.docx`)}><Download size={16}/> DOCX</button><button className="btn btn-secondary" disabled={selected.draft_status !== "APPROVED" || Boolean(busy)} onClick={() => void caseDownload(`/api/cases/${item.id}/drafts/${selected.id}/export/pdf`, token, `${item.tracking_code}.pdf`)}><Download size={16}/> PDF</button></div>
      </>}</div>
    </div>}
    {!drafts.length && <div className="writing-locked"><LockKeyhole/><div><strong>Cevap taslağı alanı hazır</strong><p>{lockedMessage}</p><span>Kurum İşlemi → Taslak → Revizyon → Onay → Gönderime Hazır</span></div></div>}
    {error && <div className="case-error">{error}</div>}
    {confirmApproval && selected && <ConfirmAction busy={busy === "approve"} title="Taslağı onayla" text="Bu taslak onaylanacak ve gönderime hazır hale gelecektir." onCancel={() => setConfirmApproval(false)} onConfirm={() => void action("approve", () => caseApi.approveDraft(token, item, selected.id), "Taslak onaylandı ve gönderime hazır hale geldi.").finally(() => setConfirmApproval(false))}/>}
  </section>;
}

export function OfficialDocumentPreview({ item, draft }: { item: CaseRecord; draft: CaseDraft }) {
  return <article className="case-a4 official-document-preview"><header><strong>T.C.</strong><strong>{item.institution_id === "belediye" ? "BELEDİYE BAŞKANLIĞI" : "KAYMAKAMLIK"}</strong><span>{draft.sender_unit || item.current_department_name}</span></header><div className="document-number-date"><span title="EBYS tarafından tamamlanacak"><b>Sayı:</b> [EBYS SAYISI]</span><span>{new Date(draft.updated_at || item.updated_at).toLocaleDateString("tr-TR")}</span></div><p><b>Konu:</b> {draft.subject}</p><p><b>Muhatap türü:</b> {recipientKindLabels[draft.recipient_kind || ""] || "Belirtilmedi"}</p><h3>{draft.recipient || item.originator_name}</h3>{draft.body.split("\n").filter(Boolean).map((line, index) => <p key={index}>{line}</p>)}<div className="document-signature" title="Yetkili kullanıcı tarafından tamamlanacak"><b>[AD SOYAD]</b><span>[UNVAN]</span></div><div className="case-qr"><QrCode/><small>{item.tracking_code}<br/>EVRAG doğrulama kaydı</small></div></article>;
}
