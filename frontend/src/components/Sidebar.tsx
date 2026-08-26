import React from "react";
import { NavLink } from "react-router-dom";
import { BookOpen, FilePlus, FileText, Home, Inbox, Settings, ShieldCheck, UserCheck } from "lucide-react";
const navItems = [
  { to: "/", icon: Home, label: "Ana Sayfa" },
  { to: "/yeni-evrak", icon: FilePlus, label: "Yeni Evrak" },
  { to: "/gelen-evraklar", icon: Inbox, label: "Gelen Evraklar" },
  { to: "/taslaklar", icon: FileText, label: "Taslaklarım" },
  { to: "/inceleme-bekleyenler", icon: UserCheck, label: "İnceleme Bekleyenler" },
];
export const Sidebar: React.FC = () => <aside className="sidebar no-print">
  <div className="sidebar-brand"><ShieldCheck size={28} className="text-primary" /><div className="sidebar-brand-text"><span className="sidebar-brand-title">KAMUAI Evrak Masası</span><span className="sidebar-brand-subtitle">Personel çalışma alanı</span></div></div>
  <nav className="sidebar-nav">
    {navItems.map((item) => <NavLink key={item.to} to={item.to} end={item.to === "/"} className={({ isActive }) => `sidebar-link ${isActive ? "sidebar-link-active" : ""}`}><item.icon size={20} /><span>{item.label}</span></NavLink>)}
    <button type="button" disabled title="Bağlı bir mevzuat listeleme endpoint'i bulunmuyor"><BookOpen size={20} /><span>Mevzuat Kütüphanesi</span><span className="soon-label">Yakında</span></button>
    <NavLink to="/yonetici" className={({ isActive }) => `sidebar-link ${isActive ? "sidebar-link-active" : ""}`}><Settings size={20} /><span>Yönetici Paneli</span></NavLink>
    <button type="button" disabled title="Bu özellik henüz kullanıma açık değil"><Settings size={20} /><span>Ayarlar</span><span className="soon-label">Yakında</span></button>
  </nav>
  <div className="sidebar-footer"><div className="sidebar-footer-text">KAMUAI — TEKNOFEST 2026</div></div>
</aside>;
