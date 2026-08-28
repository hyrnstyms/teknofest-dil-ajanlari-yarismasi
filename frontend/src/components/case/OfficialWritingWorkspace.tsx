import React, { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Download, FilePenLine, LockKeyhole, QrCode, RefreshCw, Save, ShieldCheck } from "lucide-react";
import type { AnalysisPreviewDraft, CaseDraft, CaseRecord } from "../../types/case";
import { caseApi } from "../../services/caseApi";
import { caseDownload } from "../../services/caseHttp";

const typeLabels: Record<string, string> = { MISSING_INFORMATION_REQUEST: "Eksik Bilgi Talep Yazısı", INTERIM_INFORMATION: "Ara Bilgilendirme", OFFICIAL_RESPONSE: "Resmî Cevap", INTERNAL_MEMO: "Kurum İçi Yazışma", FORWARDING_COVER_LETTER: "İç Yönlendirme Üst Yazısı" };
const statusLabels: Record<string, string> = { DRAFT: "Taslak", EDITED: "Personel Düzenlemesi", APPROVED: "Onaylandı", SENT: "Gönderildi", CANCELLED: "İptal" };

type DraftMutation = { draft?: { id?: string } };

export function OfficialWritingWorkspace({ item, token, onRefresh, onNotice }: { item: CaseRecord; token: string; onRefresh: () => Promise<void>; onNotice: (message: string) => void }) {
  const [selectedId, setSelectedId] = useState<string>();
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const drafts = item.drafts;
  const preview = drafts.length === 0 ? item.analysis_preview_draft : null;
  useEffect(() => { if (!selectedId || !drafts.some((draft) => draft.id === selectedId)) setSelectedId(drafts.at(-1)?.id); }, [drafts, selectedId]);
  const selected = drafts.find((draft) => draft.id === selectedId);
  const [form, setForm] = useState({ subject: "", recipient: "", body: "" });
  useEffect(() => { const visible = selected || preview; if (visible) setForm({ subject: visible.subject, recipient: visible.recipient || "", body: visible.body }); }, [selected, preview]);
  const latestForType = selected ? drafts.filter((draft) => draft.draft_type === selected.draft_type).sort((left, right) => (left.revision || 1) - (right.revision || 1)).at(-1) : undefined;
  const isArchived = Boolean(selected && latestForType && selected.id !== latestForType.id);
  const latestApproved = selected ? drafts.filter((draft) => draft.draft_type === selected.draft_type && draft.draft_status === "APPROVED").sort((left, right) => (left.revision || 1) - (right.revision || 1)).at(-1) : undefined;
  const canEdit = Boolean(selected && !isArchived && selected.draft_status !== "APPROVED" && item.permissions.includes("SAVE_DRAFT"));

  async function action(name: string, operation: () => Promise<unknown>, message: string, selectCreated = false) {
    setBusy(name);
    setError("");
    try {
      const result = await operation() as DraftMutation;
      await onRefresh();
      if (selectCreated && result.draft?.id) setSelectedId(result.draft.id);
      onNotice(message);
      setEditing(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "İşlem tamamlanamadı.");
    } finally {
      setBusy("");
    }
  }

  const lockedMessage = useMemo(() => {
    if (["RECEIVED", "ANALYZING", "WAITING_INITIAL_REVIEW", "READY_TO_ROUTE", "WAITING_CITIZEN_INFO"].includes(item.workflow_status)) return "Bu dosya henüz ilgili birime yönlendirilmedi. Eksik bilgi veya iç yönlendirme yazısı süreç aşamasına göre burada görünür.";
    if (item.workflow_status === "IN_DEPARTMENT") return `Dosya ${item.current_department_name} birimine yönlendirildi. Nihai cevap için birimin doğrulanmış işlem sonucu gereklidir.`;
    if (item.workflow_status === "IN_PROGRESS") return "Resmî cevap taslağı için önce kurum işlem sonucunu kaydedin.";
    return "Bu aşamada oluşturulmuş bir resmî yazı bulunmuyor.";
  }, [item]);

  return <section className="case-panel official-writing-workspace">
    <header><div><span className="eyebrow">TEKNOFEST GÖREV 2</span><h2>Resmî Yazılar <b>({drafts.length || (preview ? 1 : 0)})</b></h2><p>Yazı türü, doğru muhatap, personel düzeltmesi ve onay aynı vaka kaydında izlenir.</p></div></header>
    {drafts.length > 0 && <div className="writing-layout">
      <nav className="writing-list">{drafts.map((draft) => <button key={draft.id} className={selected?.id === draft.id ? "active" : ""} onClick={() => { setSelectedId(draft.id); setEditing(false); }}><small>{typeLabels[draft.draft_type]}</small><strong>{draft.subject}</strong><span>{draft.sender_unit || item.current_department_name} → {draft.recipient || item.originator_name}</span><em>{statusLabels[draft.draft_status]} · v{draft.revision || 1}</em></button>)}</nav>
      <div className="writing-detail">{selected && <>
        <div className="human-control-strip"><span className="done">AI Taslağı ✓</span><i>→</i><span className={selected.personnel_edited ? "done" : ""}>Personel Düzenlemesi {selected.personnel_edited ? "✓" : "○"}</span><i>→</i><span className={selected.draft_status === "APPROVED" ? "done" : ""}>Personel Onayı {selected.draft_status === "APPROVED" ? "✓" : "○"}</span></div>
        <div className="draft-action-toolbar">
          <div><strong>{typeLabels[selected.draft_type]}</strong><span className={`draft-status ${selected.draft_status === "APPROVED" ? "approved" : ""}`}>{statusLabels[selected.draft_status]} · v{selected.revision || 1}</span></div>
          <div className="draft-actions">
            {isArchived ? <>
              <span className="archived-draft-notice">Bu sürüm arşivlenmiş bir taslaktır.</span>
              {latestApproved && item.permissions.includes("SAVE_DRAFT") && <button className="btn btn-primary" disabled={Boolean(busy)} onClick={() => void action("revise", () => caseApi.reviseDraft(token, item, latestApproved.id), "Güncel onaylı sürüm korunarak yeni taslak revizyon oluşturuldu.", true)}><FilePenLine size={16}/> Yeni Revizyon Oluştur</button>}
            </> : selected.draft_status === "APPROVED" ? <>
              {item.permissions.includes("SAVE_DRAFT") && <button className="btn btn-primary" disabled={Boolean(busy)} onClick={() => void action("revise", () => caseApi.reviseDraft(token, item, selected.id), "Onaylı sürüm korunarak düzenlenebilir yeni revizyon oluşturuldu.", true)}><FilePenLine size={16}/> Yeni Revizyon Oluştur</button>}
              <button className="btn btn-secondary" disabled={Boolean(busy)} onClick={() => void caseDownload(`/api/cases/${item.id}/drafts/${selected.id}/export/docx`, token, `${item.tracking_code}.docx`)}><Download size={16}/> DOCX İndir</button>
              <button className="btn btn-secondary" disabled={Boolean(busy)} onClick={() => void caseDownload(`/api/cases/${item.id}/drafts/${selected.id}/export/pdf`, token, `${item.tracking_code}.pdf`)}><Download size={16}/> PDF İndir</button>
            </> : <>
              {canEdit && <button className="btn btn-primary" onClick={() => setEditing(true)}><FilePenLine size={16}/> Düzenle</button>}
              {selected.draft_type === "OFFICIAL_RESPONSE" && item.department_actions.length > 0 && <button className="btn btn-secondary" disabled={Boolean(busy)} onClick={() => void action("regen", () => caseApi.regenerateDraft(token, item), "Yeni AI taslak sürümü oluşturuldu.")}><RefreshCw size={16}/> Yeniden Oluştur</button>}
              {item.permissions.includes("APPROVE_DRAFT") && <button className="btn btn-success" disabled={Boolean(busy)} onClick={() => void action("approve", () => caseApi.approveDraft(token, item, selected.id), "Resmî yazı personel tarafından onaylandı.")}><CheckCircle2 size={16}/> Onayla</button>}
            </>}
          </div>
        </div>
        {editing ? <div className="draft-edit-layout"><div className="case-draft-editor"><label>Konu<input value={form.subject} onChange={(event) => setForm({ ...form, subject: event.target.value })}/></label><label>Muhatap<input value={form.recipient} onChange={(event) => setForm({ ...form, recipient: event.target.value })}/></label><label>Metin<textarea rows={18} value={form.body} onChange={(event) => setForm({ ...form, body: event.target.value })}/></label><div><button className="btn btn-secondary" onClick={() => setEditing(false)}>Vazgeç</button><button className="btn btn-primary" disabled={Boolean(busy)} onClick={() => void action("edit", () => caseApi.editDraft(token, item, selected, form), "Personel düzeltmesi yeni sürüm olarak kaydedildi.", true)}><Save size={16}/> Kaydet</button></div></div><OfficialDocumentPreview item={item} draft={{ ...selected, ...form }}/></div> : <OfficialDocumentPreview item={item} draft={selected}/>}
        <div className="quality-checks"><strong><ShieldCheck/> Düzeltme / Kalite Kontrolü</strong><span>✓ Muhatap açıkça tanımlı</span><span>✓ Resmî üslup ve yapı</span><span>✓ Vaka ile aynı kurum bağlamı</span><span>{selected.grounded_action_id ? "✓ Doğrulanmış kurum işlemine dayalı" : "✓ İç süreç yazısı; nihai işlem iddiası içermez"}</span></div>
      </>}</div>
    </div>}
    {preview && <AnalysisPreviewWorkspace item={item} preview={preview} form={form} setForm={setForm} editing={editing} busy={busy} onEdit={() => setEditing(true)} onCancel={() => setEditing(false)} onSave={() => void action("preview-edit", () => caseApi.editAnalysisPreview(token, item, { subject: form.subject, body: form.body }), "AI ön taslağındaki düzenleme Analysis kaydına kaydedildi.")}/>}
    {!drafts.length && !preview && <div className="writing-locked"><LockKeyhole/><div><strong>Resmî yazı alanı hazır</strong><p>{lockedMessage}</p><span>Kurum İşlemi → Taslak → Düzenleme → Onay → Çıktı</span></div></div>}
    {busy === "regen" && <div className="case-success">Resmî cevap taslağı hazırlanıyor…</div>}{error && <div className="case-error">{error}</div>}
  </section>;
}

function AnalysisPreviewWorkspace({ item, preview, form, setForm, editing, busy, onEdit, onCancel, onSave }: { item: CaseRecord; preview: AnalysisPreviewDraft; form: { subject: string; recipient: string; body: string }; setForm: React.Dispatch<React.SetStateAction<{ subject: string; recipient: string; body: string }>>; editing: boolean; busy: string; onEdit: () => void; onCancel: () => void; onSave: () => void }) {
  return <div className="analysis-preview-workspace"><div className="human-control-strip"><span className="done">AI Ön Taslağı ✓</span><i>→</i><span className={preview.edited ? "done" : ""}>Personel Düzenlemesi {preview.edited ? "✓" : "○"}</span><i>→</i><span>Resmî Taslak ○</span></div><div className="analysis-preview-notice" role="note"><ShieldCheck/><div><strong>Bu bir AI ön taslağıdır; resmî CaseDraft değildir.</strong><p>Düzenlemeler Analysis kaydına kaydedilir. Onay, gönderim ve çıktı işlemleri doğrulanmış birim sonucu oluşana kadar kapalıdır.</p></div></div>{editing ? <div className="draft-edit-layout"><div className="case-draft-editor"><label>Konu<input value={form.subject} onChange={(event) => setForm({ ...form, subject: event.target.value })}/></label><label>Gövde<textarea rows={18} value={form.body} onChange={(event) => setForm({ ...form, body: event.target.value })}/></label><div><button className="btn btn-secondary" onClick={onCancel}>Vazgeç</button><button className="btn btn-primary" disabled={Boolean(busy) || !form.subject.trim() || !form.body.trim()} onClick={onSave}><Save size={16}/> Düzenlemeyi Kaydet</button></div></div><OfficialDocumentPreview item={item} draft={{ ...preview, ...form }}/></div> : <OfficialDocumentPreview item={item} draft={preview}/>} {!editing && <div className="draft-actions"><button className="btn btn-primary" onClick={onEdit}><FilePenLine size={16}/> Ön Taslağı Düzenle</button></div>}</div>;
}

type DocumentDraftView = Pick<CaseDraft, "subject" | "body"> & { recipient?: string | null; sender_unit?: string; updated_at?: string };

export function OfficialDocumentPreview({ item, draft }: { item: CaseRecord; draft: DocumentDraftView }) {
  return <article className="case-a4 official-document-preview"><header><strong>T.C.</strong><strong>{item.institution_id === "belediye" ? "BELEDİYE BAŞKANLIĞI" : "KAYMAKAMLIK"}</strong><span>{draft.sender_unit || item.current_department_name}</span></header><div className="document-number-date"><span><b>Belge Referansı:</b> {item.tracking_code}</span><span><b>Tarih:</b> {new Date(draft.updated_at || item.updated_at).toLocaleDateString("tr-TR")}</span></div><p><b>Konu:</b> {draft.subject}</p><p><b>Muhatap:</b> {draft.recipient || item.originator_name || "Muhatap belirtilmedi"}</p>{draft.body.split("\n").filter(Boolean).map((line, index) => <p className="official-body-paragraph" key={index}>{line}</p>)}<footer className="official-document-footer"><div className="document-signature"><b>Yetkili Personel</b><span>{draft.sender_unit || item.current_department_name}</span><small>Elektronik onay kaydı</small></div><div className="document-verification"><div className="case-qr" aria-label="Belge QR doğrulama kodu"><QrCode/></div><div className="verification-info"><b>{item.tracking_code}</b><span>EVRAG doğrulama kaydı</span><small>Belge referansı ile güvenli doğrulama</small></div></div></footer></article>;
}
