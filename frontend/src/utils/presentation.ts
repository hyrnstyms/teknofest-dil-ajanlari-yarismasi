const ENUM_LABELS: Record<string, string> = {
  dilekce: "Dilekçe", bilgi_talebi: "Bilgi Talebi", basvuru: "Başvuru",
  sikayet: "Şikâyet", resmi_yazi: "Resmî Yazı", izin_talebi: "İzin Talebi",
  pending_review: "İnceleme Bekliyor", approved: "Onaylandı",
  approved_auto: "Otomatik Onaylandı", rejected: "Reddedildi", edited: "Düzenlendi",
  not_required: "İnceleme Gerekmiyor", low: "Normal", medium: "Orta",
  high: "Yüksek", urgent: "Acil", belediye: "Belediye", kaymakamlik: "Kaymakamlık",
  cevap_yazisi: "Cevap Yazısı", ust_yazi: "Üst Yazı",
  bilgilendirme_metni: "Bilgilendirme Metni", eksik_bilgi_talebi: "Eksik Bilgi Talebi",
};

export function formatDisplayName(value?: string | null): string {
  if (!value) return "—";
  const key = value.trim().toLocaleLowerCase("tr-TR");
  if (ENUM_LABELS[key]) return ENUM_LABELS[key];
  const words = value.replaceAll("_", " ").replaceAll("-", " ").split(" ").filter(Boolean);
  return words.map((word) => word.charAt(0).toLocaleUpperCase("tr-TR") + word.slice(1)).join(" ");
}

export function humanizeFilename(filename?: string | null): { title: string; extension?: string; original?: string } {
  if (!filename) return { title: "Başlıksız Evrak" };
  const normalizedPath = filename.replaceAll(String.fromCharCode(92), "/");
  const normalized = normalizedPath.split("/").pop() || filename;
  const dotIndex = normalized.lastIndexOf(".");
  const hasExtension = dotIndex > 0;
  const extension = hasExtension ? normalized.slice(dotIndex + 1).toLocaleUpperCase("tr-TR") : undefined;
  let stem = hasExtension ? normalized.slice(0, dotIndex) : normalized;
  const prefix = stem.split(/[_-]/)[0];
  if (/^[0-9]{1,2}$/.test(prefix) && !["3071", "4982", "5442"].includes(prefix)) {
    stem = stem.slice(prefix.length + 1);
  }
  return { title: formatDisplayName(stem), extension, original: normalized };
}

export const formatDocumentType = formatDisplayName;
export const formatIntent = formatDisplayName;
export const formatReviewStatus = formatDisplayName;
export const formatPriority = formatDisplayName;
export const formatInstitution = formatDisplayName;

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "long", year: "numeric" }).format(date);
}