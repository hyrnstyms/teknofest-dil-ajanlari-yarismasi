import React from "react";
import { FileCheck2, ShieldCheck } from "lucide-react";
import type { CaseRecord } from "../../types/case";

const draftLabels: Record<string, string> = {
  MISSING_INFORMATION_REQUEST: "Eksik bilgi talebi",
  INTERIM_INFORMATION: "Ara bilgilendirme",
  OFFICIAL_RESPONSE: "Resmî cevap",
  INTERNAL_MEMO: "Kurum içi yazı",
  FORWARDING_COVER_LETTER: "Havale üst yazısı",
};
const recipientKindLabels: Record<string, string> = { VATANDAS: "Başvuru Sahibi", KURUM: "Gönderen Kurum", DIS_KURUM: "Gönderen Kurum", INTERNAL_UNIT: "Kurum İçi Birim", INTERNAL_DEPARTMENT: "Kurum İçi Birim" };

export function WritingGroundingSummary({ item }: { item: CaseRecord }) {
  const draft = item.drafts.at(-1);
  if (!draft) return <section className="case-panel writing-grounding empty-grounding"><FileCheck2/><div><span className="eyebrow">RESMÎ YAZI</span><h2>Taslak henüz oluşturulmadı</h2><p>Doğrulanmış kurum işlemi veya eksik bilgi talebi oluştuğunda yazı burada gerekçesiyle görünür.</p></div></section>;
  const recipientKind = recipientKindLabels[draft.recipient_kind || ""] || draft.recipient_kind || "Muhatap türü belirtilmedi";
  const grounding = draft.grounded_action_id
    ? "Doğrulanmış kurum işlemi"
    : draft.draft_type === "MISSING_INFORMATION_REQUEST"
      ? item.clarification?.reason || "Süreç için gereken eksik bilgi"
      : draft.draft_type === "FORWARDING_COVER_LETTER"
        ? "İnsan tarafından onaylanan kurumsal havale"
        : "Dosya analizi ve insan kontrolü";
  return <section className="case-panel writing-grounding">
    <header><div><span className="eyebrow">BU TASLAK NEDEN ÜRETİLDİ?</span><h2>{draftLabels[draft.draft_type] || draft.draft_type}</h2></div><ShieldCheck/></header>
    <div className="grounding-facts">
      <span><small>Konu</small><strong>{draft.subject}</strong></span>
      <span><small>Muhatap</small><strong>{recipientKind}</strong></span>
      <span><small>Alıcı</small><strong>{draft.recipient || "Alıcı henüz belirlenmedi"}</strong></span>
      <span><small>Üretim nedeni / dayanak</small><strong>{grounding}</strong></span>
      <span><small>Durum</small><strong>{draft.draft_status}</strong></span>
    </div>
    <p>Kaynak dosya: <b>{item.tracking_code}</b> · Kaynak: <b>{item.originator_name}</b>. Gönderim öncesinde insan onayı zorunludur.</p>
  </section>;
}
