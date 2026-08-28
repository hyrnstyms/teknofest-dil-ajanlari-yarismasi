export const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  dilekce: "Dilekçe",
  resmi_yazi: "Resmî Yazı",
  form: "Form",
  tutanak: "Tutanak",
  rapor: "Rapor",
  karar: "Karar",
  tebligat: "Tebligat",
  eposta: "E-posta",
  diger: "Diğer",
};

export const DOCUMENT_SUBTYPE_LABELS: Record<string, string> = {
  bilgi_edinme: "Bilgi Edinme Başvurusu",
  sosyal_yardim_basvuru: "Sosyal Yardım Başvurusu",
  tapu_kadastro_basvuru: "Tapu ve Kadastro Başvurusu",
  ihale_itirazi: "İhale İtirazı",
  kurumlar_arasi_yazi: "Kurumlar Arası Yazı",
  ruhsat_basvurusu: "Ruhsat Başvurusu",
  imar_talebi: "İmar Talebi",
  sikayet: "Şikâyet",
};

export const PROCESS_INTENT_LABELS: Record<string, string> = {
  basvuru: "Başvuru",
  bilgi_talebi: "Bilgi Talebi",
  belge_talebi: "Belge Talebi",
  itiraz: "İtiraz",
  izin_talebi: "İzin Talebi",
  bildirim: "Bildirim",
  cevap: "Cevap",
  iletim: "İletim",
};

export const DRAFT_TYPE_LABELS: Record<string, string> = {
  ust_yazi: "Üst Yazı",
  cevap_yazisi: "Cevap Yazısı",
  bilgilendirme_metni: "Bilgilendirme Metni",
  eksik_bilgi_talebi: "Eksik Bilgi Talebi",
};

export const FIELD_LABELS: Record<string, string> = {
  signature_present: "İmza Durumu",
  authority_document_present: "Yetki Belgesi",
  person_name: "Başvuru Sahibi",
  document_number: "Belge Sayısı",
  document_date: "Belge Tarihi",
  sender_unit: "Gönderen Birim",
  recipient: "Muhatap",
  subject: "Konu",
  request: "Talep",
  address: "Adres",
  phone: "Telefon",
  email: "E-posta",
  attachments: "Ekler",
  national_id: "T.C. Kimlik Numarası",
  institution: "Kurum",
  other_entities: "Diğer Varlıklar",
  name: "Ad",
  value: "Değer",
  text: "Metin",
  type: "Tür",
  evidence: "Kanıt",
  status: "Durum",
  validated: "Doğrulandı",
  confidence: "Güven Skoru",
};

export const PRIORITY_LABELS: Record<string, string> = {
  high: "Yüksek",
  medium: "Orta",
  low: "Normal",
  urgent: "Acil",
};

export const REVIEW_STATUS_LABELS: Record<string, string> = {
  pending_review: "İnceleme Bekliyor",
  approved: "Onaylandı",
  approved_auto: "Otomatik Onaylandı",
  rejected: "Reddedildi",
  edited: "Düzenlendi",
  not_required: "İnceleme Gerekmiyor",
};

export const QUALITY_STATUS_LABELS: Record<string, string> = {
  pass: "Başarılı",
  warning: "Uyarı",
  fail: "Başarısız",
};

export const INSTITUTION_LABELS: Record<string, string> = {
  kaymakamlik: "Kaymakamlık",
  belediye: "Belediye",
};

export const GENERATION_MODE_LABELS: Record<string, string> = {
  heuristic_fallback: "Kural Tabanlı Yedekleme",
  deterministic_verified_facts_fallback: "Doğrulanmış Bilgilerden Güvenli Taslak",
  deterministic_fallback: "Kural Tabanlı Güvenli Taslak",
  llm: "Yapay Zekâ Destekli",
  blocked_insufficient_context: "Taslak İçin Ek Bilgi Gerekli",
};

export const CLASSIFICATION_MODE_LABELS: Record<string, string> = {
  heuristic_fallback: "Kural Tabanlı Yedekleme",
  deterministic_validation: "Kural Tabanlı Doğrulama",
  llm: "Yapay Zekâ Destekli",
};

export const EVIDENCE_MODE_LABELS: Record<string, string> = {
  heuristic_fallback: "Kural Tabanlı Yedekleme",
  deterministic_validation: "Kural Tabanlı Doğrulama",
  llm: "Yapay Zekâ Destekli",
};

export const CASE_STATUS_LABELS: Record<string, string> = {
  RECEIVED: "Alındı", ANALYZING: "AI Analizi Yapılıyor", WAITING_INITIAL_REVIEW: "İlk İnceleme Bekliyor",
  WAITING_CITIZEN_INFO: "Vatandaştan Bilgi Bekleniyor", READY_TO_ROUTE: "Yönlendirme Onayı Bekliyor",
  IN_DEPARTMENT: "Birime Atandı", IN_PROGRESS: "İşlemde", RESPONSE_DRAFTED: "Cevap Taslağı Hazır",
  WAITING_FINAL_APPROVAL: "Cevap Onayı Bekleniyor", COMPLETED: "Tamamlandı", CLOSED: "Sonuçlandı",
};
export const SOURCE_TYPE_LABELS: Record<string, string> = { VATANDAS: "Vatandaş", DIS_KURUM: "Dış Kurum", KURUM_ICI: "Kurum İçi" };
export const CHANNEL_LABELS: Record<string, string> = { WEB_FORM: "Web Formu", FIZIKI_EVRAK: "Fizikî Evrak", EPOSTA: "E-posta", KEP: "KEP", EBYS: "EBYS", KURUM_ICI: "Kurum İçi" };
export const DRAFT_STATUS_LABELS: Record<string, string> = { DRAFT: "Taslak", EDITED: "Personel Tarafından Düzenlendi", WAITING_APPROVAL: "Onay Bekliyor", APPROVED: "Onaylandı", SENT: "İletildi", CANCELLED: "İptal Edildi" };
export const CANONICAL_DRAFT_TYPE_LABELS: Record<string, string> = { OFFICIAL_RESPONSE: "Resmî Cevap", FORWARDING_COVER_LETTER: "Sevk / Üst Yazı", MISSING_INFORMATION_REQUEST: "Eksik Bilgi Talep Yazısı", INTERNAL_MEMO: "Kurum İçi Yazı", INTERIM_INFORMATION: "Ara Bilgilendirme" };

export function getLabel(key: string | undefined | null, map: Record<string, string>): string {
  const normalized = String(key ?? "").trim();
  return map[normalized] || normalized.replaceAll("_", " ");
}
