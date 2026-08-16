export const STATUS_LABELS: Record<string, string> = {
  pending_review: "İnceleme Bekliyor",
  approved: "Onaylandı",
  edited: "Düzenlendi",
  rejected: "Reddedildi",
  pass: "Başarılı",
  warning: "Uyarı",
  fail: "Başarısız",
};

export const DOC_TYPE_LABELS: Record<string, string> = {
  dilekce: "Dilekçe",
  resmi_yazi: "Resmî Yazı",
  bilgi_talebi: "Bilgi Talebi",
  belge_talebi: "Belge Talebi",
  basvuru: "Başvuru",
  sikayet: "Şikâyet",
  itiraz: "İtiraz",
  eksik_bilgi_talebi: "Eksik Bilgi Talebi",
  cevap_yazisi: "Cevap Yazısı",
  ust_yazi: "Üst Yazı",
};

export const FIELD_LABELS: Record<string, string> = {
  person_name: "Ad Soyad",
  national_id: "T.C. Kimlik Numarası",
  address: "Adres",
  phone: "Telefon",
  email: "E-posta",
  document_date: "Belge Tarihi",
  document_number: "Belge Sayısı",
  institution: "Kurum",
  sender_unit: "Gönderen Birim",
  recipient: "Muhatap",
  subject: "Konu",
  request: "Talep",
  attachments: "Ekler",
  signature_present: "İmza Durumu",
  authority_document_present: "Yetki Belgesi",
};

export const DRAFT_MODE_LABELS: Record<string, string> = {
  deterministic_verified_facts_fallback: "Doğrulanmış bilgilerden güvenli taslak",
  deterministic_fallback: "Kural tabanlı güvenli taslak",
  llm: "Yapay zekâ destekli taslak",
  blocked_insufficient_context: "Taslak için ek bilgi gerekli",
};

export function getLabel(key: string | undefined | null, map: Record<string, string>): string {
  if (!key) return "Belirtilmedi";
  return map[key] || key;
}
