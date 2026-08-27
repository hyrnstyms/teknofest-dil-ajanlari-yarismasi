import type { UserRole } from "../types/case";
export interface RoleNavItem { to: string; text: string; key: string }

/** Yazı İşleri / Evrak Kayıt: gelen evrak → havale → eksik bilgi → giden evraklar → geçmiş */
const registry: RoleNavItem[] = [
  { to: "/", text: "Ana Sayfa", key: "home" },
  { to: "/dosyalar?view=incoming", text: "Gelen Evraklar", key: "incoming" },
  { to: "/dosyalar?status=READY_TO_ROUTE", text: "Havale Bekleyenler", key: "routing" },
  { to: "/dosyalar?status=WAITING_CITIZEN_INFO", text: "Eksik Bilgi", key: "clarification" },
  { to: "/resmi-yazilar", text: "Giden Evraklar", key: "outgoing" },
  { to: "/gecmis", text: "Geçmiş", key: "history" },
];

/** Fen İşleri / Birim Personeli: cevap taslakları case içinde görünür; ayrı menü yok */
const department: RoleNavItem[] = [
  { to: "/", text: "Ana Sayfa", key: "home" },
  { to: "/dosyalar?view=assigned", text: "Birim İşleri", key: "assigned" },
  { to: "/dosyalar?status=IN_PROGRESS", text: "Saha İşleri", key: "progress" },
  { to: "/dosyalar?status=WAITING_CITIZEN_INFO", text: "Eksik Bilgi", key: "clarification" },
  { to: "/resmi-yazilar", text: "Cevaplar", key: "approval" },
  { to: "/dosyalar?risk=APPROACHING", text: "Süreler", key: "deadline" },
  { to: "/gecmis", text: "Geçmiş", key: "history" },
];

export function navigationForRole(role: UserRole): RoleNavItem[] { return role === "EVRAK_KAYIT" ? registry : department; }
export const roleLabel = (role: UserRole) => role === "EVRAK_KAYIT" ? "Evrak Kayıt Personeli" : "Birim Personeli";
