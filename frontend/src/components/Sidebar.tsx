import React from "react";
import { NavLink } from "react-router-dom";
import { BookOpen, Bot, FilePlus, FileText, Home, Inbox, Settings, ShieldCheck, UserCheck, LayoutDashboard } from "lucide-react";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Ana Sayfa" },
  { to: "/yeni-evrak", icon: FilePlus, label: "Yeni Evrak" },
  { to: "/gelen-evraklar", icon: Inbox, label: "Gelen Evraklar" },
  { to: "/taslaklar", icon: FileText, label: "Taslaklarım" },
  { to: "/inceleme-bekleyenler", icon: UserCheck, label: "İnceleme Bekleyenler" },
];

const linkClass = ({ isActive }: { isActive: boolean }) =>
  "sidebar-link " + (isActive ? "sidebar-link-active" : "");

export const Sidebar: React.FC = () => (
  <aside className="sidebar no-print">
    <div className="sidebar-brand">
      <div className="sidebar-logo">
        <ShieldCheck size={28} className="text-primary" />
      </div>
      <div className="sidebar-brand-text">
        <span className="sidebar-brand-title">EVRAG / KAMUAI</span>
        <span className="sidebar-brand-subtitle">Akıllı Evrak ve Karar Destek</span>
      </div>
    </div>
    <nav className="sidebar-nav">
      <span className="sidebar-section-label" style={{ padding: '0.75rem 1rem 0.25rem', fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', letterSpacing: '0.05em' }}>EVRAK YÖNETİMİ</span>
      {navItems.map((item) => (
        <NavLink key={item.to} to={item.to} end={item.to === "/"} className={linkClass}>
          <item.icon size={20} />
          <span>{item.label}</span>
        </NavLink>
      ))}

      <span className="sidebar-section-label" style={{ padding: '1rem 1rem 0.25rem', fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', letterSpacing: '0.05em' }}>YAPAY ZEKÂ</span>
      <NavLink to="/ai-operasyon" className={linkClass}>
        <Bot size={20} />
        <span>AI Operasyon Merkezi</span>
      </NavLink>
      <button type="button" disabled title="Bağlı bir mevzuat listeleme endpoint'i bulunmuyor" className="sidebar-link" style={{ background: 'transparent', border: 'none', cursor: 'not-allowed', width: '100%', opacity: 0.7 }}>
        <BookOpen size={20} />
        <span>Mevzuat Kütüphanesi</span>
        <span className="soon-label" style={{ marginLeft: 'auto', fontSize: '0.65rem', background: 'rgba(255,255,255,0.1)', padding: '0.15rem 0.4rem', borderRadius: '4px' }}>Yakında</span>
      </button>

      <span className="sidebar-section-label" style={{ padding: '1rem 1rem 0.25rem', fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', letterSpacing: '0.05em' }}>YÖNETİM</span>
      <NavLink to="/yonetici" className={linkClass}>
        <Settings size={20} />
        <span>Yönetici Paneli</span>
      </NavLink>
      <button type="button" disabled title="Bu özellik henüz kullanıma açık değil" className="sidebar-link" style={{ background: 'transparent', border: 'none', cursor: 'not-allowed', width: '100%', opacity: 0.7 }}>
        <Settings size={20} />
        <span>Ayarlar</span>
        <span className="soon-label" style={{ marginLeft: 'auto', fontSize: '0.65rem', background: 'rgba(255,255,255,0.1)', padding: '0.15rem 0.4rem', borderRadius: '4px' }}>Yakında</span>
      </button>
    </nav>
    <div className="sidebar-footer" style={{ borderTop: '1px solid rgba(255,255,255,0.08)', padding: '1rem' }}>
      <div className="sidebar-footer-text" style={{ fontSize: '0.75rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981' }}></div>
        Sistem Hazır
      </div>
      <div className="sidebar-footer-text" style={{ fontSize: '0.7rem', color: '#475569', marginTop: '0.25rem', marginLeft: '12px' }}>
        Yerel • Qwen2.5 3B
      </div>
    </div>
  </aside>
);
