import React from "react";
import { Building2, ChevronRight, LogOut, UserRound } from "lucide-react";
import { useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import type { CurrentUser } from "../types/case";
import { roleLabel } from "../utils/roleNavigation";
const titles: Record<string, string> = { "/": "Ana Sayfa", "/dosyalar": "Dosyalar", "/gecmis": "İşlem Geçmişi", "/yeni-evrak": "Demo Evrak Girişi", "/kurum-rehberi": "Kurum Rehberi", "/ai-operasyon": "AI Operasyonları" };
export function TopBar({ user }: { user: CurrentUser }) { const { logout } = useAuth(); const location = useLocation(); const title = location.pathname.startsWith("/dosya/") ? "Dosya Çalışma Alanı" : location.pathname.startsWith("/evrak/") ? "AI Analiz İncelemesi" : titles[location.pathname] || "EVRAG"; return <header className="top-bar no-print"><div className="top-bar-breadcrumb"><Building2 size={16}/><span>EVRAG</span><ChevronRight size={14}/><strong>{title}</strong></div><div className="current-user"><span className="current-user-icon"><UserRound/></span><div><strong>{user.name}</strong><small>{user.department_name || user.department_code} · {roleLabel(user.role)}</small></div><button onClick={logout} title="Güvenli çıkış"><LogOut/><span>Çıkış</span></button></div></header>; }
