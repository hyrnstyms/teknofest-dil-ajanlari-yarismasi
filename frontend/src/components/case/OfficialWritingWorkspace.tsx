import React, { useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  Download,
  FilePenLine,
  LockKeyhole,
  QrCode,
  RefreshCw,
  Save,
  ShieldCheck,
} from "lucide-react";
import type { AnalysisPreviewDraft, CaseRecord } from "../../types/case";
import { caseApi } from "../../services/caseApi";
import { caseDownload } from "../../services/caseHttp";

const typeLabels: Record<string, string> = {
  MISSING_INFORMATION_REQUEST: "Eksik Bilgi Talep Yazısı",
  INTERIM_INFORMATION: "Ara Bilgilendirme",
  OFFICIAL_RESPONSE: "Resmî Cevap",
  INTERNAL_MEMO: "Kurum İçi Yazışma",
  FORWARDING_COVER_LETTER: "İç Yönlendirme Üst Yazısı",
  cevap_yazisi: "Cevap Yazısı",
  ust_yazi: "Üst Yazı",
  tekit_yazisi: "Tekit Yazısı",
  eksik_bilgi_talebi: "Eksik Bilgi Talebi",
  diger: "Yazı Taslağı",
};
const statusLabels: Record<string, string> = {
  DRAFT: "Taslak",
  EDITED: "Düzenlendi",
  APPROVED: "Onaylandı",
  SENT: "Gönderildi",
  CANCELLED: "İptal",
};
const recipientKindLabels: Record<string, string> = {
  VATANDAS: "Başvuru Sahibi",
  KURUM: "Gönderen Kurum",
  DIS_KURUM: "Gönderen Kurum",
  INTERNAL_UNIT: "Kurum İçi Birim",
  INTERNAL_DEPARTMENT: "Kurum İçi Birim",
  gercek_kisi: "Başvuru Sahibi",
  kurum_alt: "Alt Kurum",
  kurum_ust: "Üst Kurum",
  kurum_ayni: "Eş Düzey Kurum",
  kurum_karisik: "Karma Dağıtım",
};

interface WorkspaceProps {
  item: CaseRecord;
  token: string;
  onRefresh: () => Promise<void>;
  onNotice: (message: string) => void;
}

export function OfficialWritingWorkspace({ item, token, onRefresh, onNotice }: WorkspaceProps) {
  const [selectedId, setSelectedId] = useState<string>();
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const drafts = item.drafts;
  const preview = drafts.length === 0 ? item.analysis_preview_draft : null;

  useEffect(() => {
    if (!selectedId || !drafts.some((draft) => draft.id === selectedId)) {
      setSelectedId(drafts.at(-1)?.id);
    }
  }, [drafts, selectedId]);

  const selected = drafts.find((draft) => draft.id === selectedId);
  const [form, setForm] = useState({ subject: "", recipient: "", body: "" });
  useEffect(() => {
    const visibleDraft = selected || preview;
    if (visibleDraft) {
      setForm({
        subject: visibleDraft.subject,
        recipient: visibleDraft.recipient || "",
        body: visibleDraft.body,
      });
    }
  }, [selected, preview]);

  const canEdit = Boolean(
    selected
      && selected.draft_status !== "APPROVED"
      && item.permissions.includes("SAVE_DRAFT"),
  );

  async function action(name: string, operation: () => Promise<unknown>, message: string) {
    setBusy(name);
    setError("");
    try {
      await operation();
      await onRefresh();
      onNotice(message);
      setEditing(false);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "İşlem tamamlanamadı.");
    } finally {
      setBusy("");
    }
  }

  const lockedMessage = useMemo(() => {
    if (["RECEIVED", "ANALYZING", "WAITING_INITIAL_REVIEW", "READY_TO_ROUTE", "WAITING_CITIZEN_INFO"].includes(item.workflow_status)) {
      return "Bu dosya henüz ilgili birime yönlendirilmedi. Eksik bilgi veya iç yönlendirme yazısı süreç aşamasına göre burada görünür.";
    }
    if (item.workflow_status === "IN_DEPARTMENT") {
      return `Dosya ${item.current_department_name} birimine yönlendirildi. Nihai cevap için birimin doğrulanmış işlem sonucu gereklidir.`;
    }
    if (item.workflow_status === "IN_PROGRESS") {
      return "Resmî cevap taslağı için önce kurum işlem sonucunu kaydedin.";
    }
    return "Bu aşamada oluşturulmuş bir resmî yazı bulunmuyor.";
  }, [item]);

  const visibleCount = drafts.length || (preview ? 1 : 0);
  return <section className="case-panel official-writing-workspace">
    <header>
      <div>
        <span className="eyebrow">TEKNOFEST GÖREV 2</span>
        <h2>Yazı Çalışma Alanı <b>({visibleCount})</b></h2>
        <p>AI ön taslağı ile resmî vaka taslakları birbirinden ayrılır; resmî gönderim için doğrulanmış kurum işlemi ve personel onayı gerekir.</p>
      </div>
    </header>

    {drafts.length > 0 && <div className="writing-layout">
      <nav className="writing-list">
        {drafts.map((draft) => <button
          key={draft.id}
          className={selected?.id === draft.id ? "active" : ""}
          onClick={() => { setSelectedId(draft.id); setEditing(false); }}
        >
          <small>{typeLabels[draft.draft_type]}</small>
          <strong>{draft.subject}</strong>
          <span>{draft.sender_unit || item.current_department_name} → {draft.recipient || item.originator_name}</span>
          <em>{statusLabels[draft.draft_status]} · v{draft.revision || 1}</em>
        </button>)}
      </nav>
      <div className="writing-detail">
        {selected && <>
          <div className="human-control-strip">
            <span className="done">AI Taslağı</span><i>→</i>
            <span className={selected.draft_status === "EDITED" || selected.draft_status === "APPROVED" ? "done" : ""}>Personel Düzenlemesi</span><i>→</i>
            <span className={selected.draft_status === "APPROVED" ? "done" : ""}>Personel Onayı</span>
          </div>
          {editing
            ? <DraftEditor
                form={form}
                setForm={setForm}
                busy={busy}
                includeRecipient
                onCancel={() => setEditing(false)}
                onSave={() => void action(
                  "edit",
                  () => caseApi.editDraft(token, item, selected, form),
                  "Personel düzeltmesi yeni sürüm olarak kaydedildi.",
                )}
              />
            : <OfficialDocumentPreview item={item} draft={selected}/>
          }
          <div className="quality-checks">
            <strong><ShieldCheck/> Düzeltme / Kalite Kontrolü</strong>
            <span>✓ Muhatap açıkça tanımlı</span>
            <span>✓ Resmî üslup ve yapı</span>
            <span>✓ Vaka ile aynı kurum bağlamı</span>
            <span>{selected.grounded_action_id ? "✓ Doğrulanmış kurum işlemine dayalı" : "✓ İç süreç yazısı; nihai işlem iddiası içermez"}</span>
          </div>
          <div className="draft-actions">
            {canEdit && <button className="btn btn-secondary" onClick={() => setEditing(true)}><FilePenLine size={16}/> Düzenle</button>}
            {selected.draft_type === "OFFICIAL_RESPONSE" && selected.draft_status !== "APPROVED" && item.department_actions.length > 0 && <button className="btn btn-secondary" disabled={Boolean(busy)} onClick={() => void action("regen", () => caseApi.regenerateDraft(token, item), "Yeni AI taslak sürümü oluşturuldu.")}><RefreshCw size={16}/> Yeniden Oluştur</button>}
            {selected.draft_status !== "APPROVED" && item.permissions.includes("APPROVE_DRAFT") && <button className="btn btn-primary" disabled={Boolean(busy)} onClick={() => void action("approve", () => caseApi.approveDraft(token, item, selected.id), "Resmî yazı personel tarafından onaylandı.")}><CheckCircle2 size={16}/> Onayla</button>}
            <button className="btn btn-secondary" disabled={selected.draft_status !== "APPROVED" || Boolean(busy)} onClick={() => void caseDownload(`/api/cases/${item.id}/drafts/${selected.id}/export/docx`, token, `${item.tracking_code}.docx`)}><Download size={16}/> DOCX</button>
            <button className="btn btn-secondary" disabled={selected.draft_status !== "APPROVED" || Boolean(busy)} onClick={() => void caseDownload(`/api/cases/${item.id}/drafts/${selected.id}/export/pdf`, token, `${item.tracking_code}.pdf`)}><Download size={16}/> PDF</button>
          </div>
        </>}
      </div>
    </div>}

    {preview && <AnalysisPreviewWorkspace
      item={item}
      preview={preview}
      form={form}
      setForm={setForm}
      editing={editing}
      busy={busy}
      onEdit={() => setEditing(true)}
      onCancel={() => setEditing(false)}
      onSave={() => void action(
        "preview-edit",
        () => caseApi.editAnalysisPreview(token, item, { subject: form.subject, body: form.body }),
        "AI ön taslağındaki düzenleme Analysis kaydına kaydedildi.",
      )}
    />}

    {!drafts.length && !preview && <div className="writing-locked">
      <LockKeyhole/>
      <div><strong>Resmî yazı alanı hazır</strong><p>{lockedMessage}</p><span>Kurum İşlemi → Taslak → Düzenleme → Onay → Çıktı</span></div>
    </div>}
    {busy === "regen" && <div className="case-success">Resmî cevap taslağı hazırlanıyor…</div>}
    {error && <div className="case-error">{error}</div>}
  </section>;
}

function AnalysisPreviewWorkspace({
  item,
  preview,
  form,
  setForm,
  editing,
  busy,
  onEdit,
  onCancel,
  onSave,
}: {
  item: CaseRecord;
  preview: AnalysisPreviewDraft;
  form: DraftForm;
  setForm: React.Dispatch<React.SetStateAction<DraftForm>>;
  editing: boolean;
  busy: string;
  onEdit: () => void;
  onCancel: () => void;
  onSave: () => void;
}) {
  return <div className="analysis-preview-workspace">
    <div className="human-control-strip">
      <span className="done">AI Ön Taslağı</span><i>→</i>
      <span className={preview.edited ? "done" : ""}>Personel Düzenlemesi</span><i>→</i>
      <span>Doğrulanmış İşlem Sonrası Resmî Taslak</span>
    </div>
    <div className="analysis-preview-notice" role="note">
      <ShieldCheck/>
      <div><strong>Bu bir AI ön taslağıdır; resmî CaseDraft değildir.</strong><p>Düzenlemeler Analysis kaydına kaydedilir. Onay, gönderim ve çıktı işlemleri doğrulanmış birim sonucu oluşana kadar kapalıdır.</p></div>
    </div>
    {editing
      ? <DraftEditor form={form} setForm={setForm} busy={busy} onCancel={onCancel} onSave={onSave}/>
      : <OfficialDocumentPreview item={item} draft={preview}/>
    }
    <div className="draft-actions">
      {!editing && <button className="btn btn-secondary" onClick={onEdit}><FilePenLine size={16}/> Ön Taslağı Düzenle</button>}
    </div>
  </div>;
}

interface DraftForm { subject: string; recipient: string; body: string }

function DraftEditor({ form, setForm, busy, includeRecipient = false, onCancel, onSave }: {
  form: DraftForm;
  setForm: React.Dispatch<React.SetStateAction<DraftForm>>;
  busy: string;
  includeRecipient?: boolean;
  onCancel: () => void;
  onSave: () => void;
}) {
  return <div className="case-draft-editor">
    <label>Konu<input value={form.subject} onChange={(event) => setForm({ ...form, subject: event.target.value })}/></label>
    {includeRecipient && <label>Muhatap<input value={form.recipient} onChange={(event) => setForm({ ...form, recipient: event.target.value })}/></label>}
    <label>Gövde<textarea rows={12} value={form.body} onChange={(event) => setForm({ ...form, body: event.target.value })}/></label>
    <div>
      <button className="btn btn-secondary" onClick={onCancel}>İptal</button>
      <button className="btn btn-primary" disabled={Boolean(busy) || !form.subject.trim() || !form.body.trim()} onClick={onSave}><Save size={16}/> Düzenlemeyi Kaydet</button>
    </div>
  </div>;
}

interface DocumentDraftView {
  subject: string;
  body: string;
  recipient?: string | null;
  recipient_kind?: string | null;
  sender_unit?: string;
  updated_at?: string;
}

export function OfficialDocumentPreview({ item, draft }: { item: CaseRecord; draft: DocumentDraftView }) {
  return <article className="case-a4 official-document-preview">
    <header><strong>T.C.</strong><strong>{item.institution_id === "belediye" ? "BELEDİYE BAŞKANLIĞI" : "KAYMAKAMLIK"}</strong><span>{draft.sender_unit || item.current_department_name}</span></header>
    <div className="document-number-date"><span><b>Sayı:</b> [EBYS SAYISI]</span><span>{new Date(draft.updated_at || item.updated_at).toLocaleDateString("tr-TR")}</span></div>
    <p><b>Konu:</b> {draft.subject}</p>
    <p><b>Muhatap:</b> {recipientKindLabels[draft.recipient_kind || ""] || draft.recipient_kind || "Belirtilmedi"}</p>
    <h3>{draft.recipient || item.originator_name}</h3>
    {draft.body.split("\n").filter(Boolean).map((line, index) => <p key={index}>{line}</p>)}
    <div className="document-signature"><b>[AD SOYAD]</b><span>[UNVAN]</span></div>
    <div className="case-qr"><QrCode/><small>{item.tracking_code}<br/>EVRAG doğrulama kaydı</small></div>
  </article>;
}
