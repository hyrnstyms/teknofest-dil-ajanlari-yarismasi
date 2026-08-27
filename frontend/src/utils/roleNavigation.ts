import type { UserRole } from "../types/case";
export interface RoleNavItem { to: string; text: string; key: string }
const registry: RoleNavItem[] = [
  { to: "/", text: "Ana Sayfa", key: "home" }, { to: "/dosyalar?view=incoming", text: "Gelen Evrak Havuzu", key: "incoming" }, { to: "/dosyalar?status=WAITING_CITIZEN_INFO", text: "Eksik Bilgi Bekleyenler", key: "clarification" }, { to: "/dosyalar?status=READY_TO_ROUTE", text: "Yönlendirme Bekleyenler", key: "routing" }, { to: "/resmi-yazilar", text: "Resmî Yazılar", key: "writings" }, { to: "/gecmis", text: "İşlem Geçmişi", key: "history" },
];
const department: RoleNavItem[] = [
  { to: "/", text: "Ana Sayfa", key: "home" }, { to: "/dosyalar?view=assigned", text: "Bana Atananlar", key: "assigned" }, { to: "/dosyalar?status=IN_PROGRESS", text: "İşlemdeki Dosyalar", key: "progress" }, { to: "/dosyalar?status=WAITING_FINAL_APPROVAL", text: "Cevap Bekleyenler", key: "approval" }, { to: "/resmi-yazilar", text: "Resmî Yazılar", key: "writings" }, { to: "/dosyalar?risk=APPROACHING", text: "Süresi Yaklaşanlar", key: "deadline" }, { to: "/gecmis", text: "İşlem Geçmişi", key: "history" },
];
export function navigationForRole(role: UserRole): RoleNavItem[] { return role === "EVRAK_KAYIT" ? registry : department; }
export const roleLabel = (role: UserRole) => role === "EVRAK_KAYIT" ? "Evrak Kayıt Personeli" : "Birim Personeli";
