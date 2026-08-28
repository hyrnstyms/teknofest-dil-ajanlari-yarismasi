import * as L from "./labels";

export function getLabel(key: string | undefined | null, map: Record<string, string>): string {
  if (!key) return "—";
  return map[key] || humanizeFallback(key);
}

function humanizeFallback(value: string): string {
  const words = value.replaceAll("_", " ").replaceAll("-", " ").split(" ").filter(Boolean);
  return words.map((word) => word.charAt(0).toLocaleUpperCase("tr-TR") + word.slice(1).toLocaleLowerCase("tr-TR")).join(" ");
}

export function formatDisplayName(value?: string | null): string {
  if (!value) return "—";
  
  // Generic lookup in all registries (not ideal but backward compatible)
  const allRegistries = [
    L.DOCUMENT_TYPE_LABELS, L.DOCUMENT_SUBTYPE_LABELS, L.PROCESS_INTENT_LABELS,
    L.DRAFT_TYPE_LABELS, L.FIELD_LABELS, L.PRIORITY_LABELS, L.REVIEW_STATUS_LABELS,
    L.QUALITY_STATUS_LABELS, L.INSTITUTION_LABELS, L.GENERATION_MODE_LABELS,
    L.CLASSIFICATION_MODE_LABELS, L.EVIDENCE_MODE_LABELS, L.CASE_STATUS_LABELS, L.SOURCE_TYPE_LABELS, L.CHANNEL_LABELS, L.DRAFT_STATUS_LABELS, L.CANONICAL_DRAFT_TYPE_LABELS
  ];
  
  for (const reg of allRegistries) {
    if (reg[value]) return reg[value];
  }
  
  return humanizeFallback(value);
}

export function formatDocumentType(value?: string | null): string {
  return getLabel(value, L.DOCUMENT_TYPE_LABELS);
}

export function formatDocumentSubtype(value?: string | null): string {
  return getLabel(value, L.DOCUMENT_SUBTYPE_LABELS);
}

export function formatProcessIntent(value?: string | null): string {
  return getLabel(value, L.PROCESS_INTENT_LABELS);
}

export function formatDraftType(value?: string | null): string {
  return getLabel(value, L.DRAFT_TYPE_LABELS);
}

export const formatCaseStatus = (value?: string | null) => getLabel(value, L.CASE_STATUS_LABELS);
export const formatSourceType = (value?: string | null) => getLabel(value, L.SOURCE_TYPE_LABELS);
export const formatChannel = (value?: string | null) => getLabel(value, L.CHANNEL_LABELS);
export const formatDraftStatus = (value?: string | null) => getLabel(value, L.DRAFT_STATUS_LABELS);

export function formatFieldName(value?: string | null): string {
  return getLabel(value, L.FIELD_LABELS);
}

export function formatPriority(value?: string | null): string {
  return getLabel(value, L.PRIORITY_LABELS);
}

export function formatReviewStatus(value?: string | null): string {
  return getLabel(value, L.REVIEW_STATUS_LABELS);
}

export function formatInstitution(value?: string | null): string {
  return getLabel(value, L.INSTITUTION_LABELS);
}

export function formatQualityStatus(value?: string | null): string {
  return getLabel(value, L.QUALITY_STATUS_LABELS);
}

export function formatLegalSource(source: unknown): { title: string; citation: string; article?: string; excerpt?: string; url?: string; relationship?: string } {
  if (typeof source === "string") return { title: source, citation: source };
  if (!source || typeof source !== "object") return { title: "Doğrulanmış kaynak", citation: "Doğrulanmış kaynak" };
  const row = source as Record<string, unknown>;
  const title = String(row.title || row.source || "Doğrulanmış mevzuat kaynağı");
  const law = String(row.law_number || "").trim();
  const article = String(row.madde_no || row.article || "").trim() || undefined;
  return { title, citation: law ? `${law} sayılı ${title}` : title, article, excerpt: String(row.text || row.evidence || "").trim() || undefined, url: String(row.url || "").trim() || undefined, relationship: String(row.relationship || "").trim() || undefined };
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

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "long", year: "numeric" }).format(date);
}