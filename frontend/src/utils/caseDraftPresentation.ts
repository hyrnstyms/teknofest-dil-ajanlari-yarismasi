import type { CaseDraft } from "../types/case";

export const draftTypeLabels: Record<CaseDraft["draft_type"], string> = {
  MISSING_INFORMATION_REQUEST: "Eksik Bilgi Talep Yazısı",
  INTERIM_INFORMATION: "Ara Bilgilendirme",
  OFFICIAL_RESPONSE: "Resmî Cevap",
  INTERNAL_MEMO: "Kurum İçi Yazışma",
  FORWARDING_COVER_LETTER: "İç Yönlendirme Üst Yazısı",
};

export const draftStatusLabels: Record<CaseDraft["draft_status"], string> = {
  DRAFT: "Taslak",
  EDITED: "Onay Bekliyor",
  APPROVED: "Gönderime Hazır",
  SENT: "Gönderildi",
  CANCELLED: "İptal Edildi",
};

export const recipientKindLabels: Record<string, string> = {
  VATANDAS: "Başvuru Sahibi",
  KURUM: "Gönderen Kurum",
  DIS_KURUM: "Gönderen Kurum",
  INTERNAL_UNIT: "Kurum İçi Birim",
  INTERNAL_DEPARTMENT: "Kurum İçi Birim",
};

export const isResponseDraft = (draft: CaseDraft) => draft.draft_type !== "FORWARDING_COVER_LETTER";
