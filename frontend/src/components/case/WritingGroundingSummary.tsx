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

export function WritingGroundingSummary({ item }: { item: CaseRecord }) {
  const draft = item.drafts.at(-1);
  if (!draft) return <section className="case-panel writing-grounding empty-grounding"><FileCheck2/><div><span className="eyebrow">RESMÎ YAZI</span><h2>Taslak henüz oluşturulmadı</h2><p>Doğrulanmış kurum işlemi veya eksik bilgi talebi oluştuğunda yazı burada gerekçesiyle görünür.</p></div></section>;
  return <section className="case-panel writing-grounding">
    <header><div><span className="eyebrow">BU TASLAK NEDEN ÜRETİLDİ?</span><h2>{draftLabels[draft.draft_type] || draft.draft_type}</h2></div><ShieldCheck/></header>
    <div className="grounding-facts">
      <span><small>Konu</small><strong>{draft.subject}</strong></span>
      <span><small>Alıcı</small><strong>{draft.recipient || "Alıcı henüz belirlenmedi"}</strong></span>
      <span><small>Dayanak</small><strong>{draft.grounded_action_id ? "Doğrulanmış kurum işlemi" : "Dosya analizi ve insan kontrolü"}</strong></span>
      <span><small>Durum</small><strong>{draft.draft_status}</strong></span>
    </div>
    <p>Kaynak dosya: <b>{item.tracking_code}</b> · Başvuru sahibi: <b>{item.originator_name}</b>. Gönderim öncesinde insan onayı zorunludur.</p>
  </section>;
}
