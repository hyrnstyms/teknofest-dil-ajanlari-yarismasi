import React from "react";
import { ArrowDown } from "lucide-react";
import type { CaseRecord } from "../../types/case";

const draftLabels: Record<string, string> = {
  MISSING_INFORMATION_REQUEST: "Eksik bilgi talebi",
  INTERIM_INFORMATION: "Ara bilgilendirme",
  OFFICIAL_RESPONSE: "Resmî cevap",
  INTERNAL_MEMO: "Kurum içi yazı",
  FORWARDING_COVER_LETTER: "Havale üst yazısı",
};
export function WritingGroundingSummary({ item, onInspect }: { item: CaseRecord; onInspect?: () => void }) {
  const draft = item.drafts.at(-1);
  if (!draft) return null;
  const grounding = draft.grounded_action_id
    ? "Doğrulanmış kurum işlem sonucu"
    : draft.draft_type === "MISSING_INFORMATION_REQUEST"
      ? item.clarification?.reason || "Süreç için gereken eksik bilgi"
      : draft.draft_type === "FORWARDING_COVER_LETTER"
        ? "Onaylanan kurumsal havale"
        : "Dosya analizi ve insan kontrolü";
  return <section className="writing-summary">
    <div><h2>Cevap Taslağı</h2><p>Üretim dayanağı ve muhatap özeti</p></div>
    <dl>
      <div><dt>Tür</dt><dd>{draftLabels[draft.draft_type] || draft.draft_type}</dd></div>
      <div><dt>Muhatap</dt><dd>{draft.recipient || item.originator_name}</dd></div>
      <div><dt>Dayanak</dt><dd>{grounding}</dd></div>
    </dl>
    {onInspect && <button className="btn btn-secondary" onClick={onInspect}>Taslağı İncele <ArrowDown size={15}/></button>}
  </section>;
}
