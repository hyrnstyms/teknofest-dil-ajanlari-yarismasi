import type { UserRole } from "../types/case";
export interface RoleNavItem { to: string; text: string; key: string }
const registry: RoleNavItem[] = [
  { to: "/", text: "Ana Sayfa", key: "home" }, { to: "/dosyalar?view=incoming", text: "Gelen Evraklar", key: "incoming" }, { to: "/dosyalar?status=READY_TO_ROUTE", text: "Havale Bekleyenler", key: "routing" }, { to: "/dosyalar?status=WAITING_CITIZEN_INFO", text: "Eksik Bilgi", key: "clarification" }, { to: "/resmi-yazilar", text: "Resmî Yazılar", key: "writings" }, { to: "/gecmis", text: "Geçmiş", key: "history" },
];
const department: RoleNavItem[] = [
  { to: "/", text: "Ana Sayfa", key: "home" }, { to: "/dosyalar?view=assigned", text: "Birim İşleri", key: "assigned" }, { to: "/dosyalar?status=IN_PROGRESS", text: "Saha İşleri", key: "progress" }, { to: "/dosyalar?status=WAITING_CITIZEN_INFO", text: "Eksik Bilgi", key: "clarification" }, { to: "/dosyalar?status=WAITING_FINAL_APPROVAL", text: "Cevaplar", key: "approval" }, { to: "/dosyalar?risk=APPROACHING", text: "Süreler", key: "deadline" }, { to: "/resmi-yazilar", text: "Resmî Yazılar", key: "writings" }, { to: "/gecmis", text: "Geçmiş", key: "history" },
];
export function navigationForRole(role: UserRole): RoleNavItem[] { return role === "EVRAK_KAYIT" ? registry : department; }
export const roleLabel = (role: UserRole) => role === "EVRAK_KAYIT" ? "Evrak Kayıt Personeli" : "Birim Personeli";
