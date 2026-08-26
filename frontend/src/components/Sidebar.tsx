import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Home,
  FilePlus,
  FileText,
  Inbox,
  BookOpen,
  Settings,
  ShieldCheck,
  UserCheck,
} from 'lucide-react';

const navItems = [
  { to: '/', icon: Home, label: 'Anasayfa' },
  { to: '/yeni-evrak', icon: FilePlus, label: 'Yeni Evrak' },
  { to: '/taslaklar', icon: FileText, label: 'Taslaklar\u0131m' },
  { to: '/inceleme-bekleyenler', icon: UserCheck, label: '\u0130nceleme Bekleyenler' },
  { to: '/gelen-evraklar', icon: Inbox, label: 'Gelen Evraklar' },
  { to: '/yonetici', icon: Settings, label: 'Yönetici Paneli' },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <ShieldCheck size={28} className="text-primary" />
        <div className="sidebar-brand-text">
          <span className="sidebar-brand-title">KAMUAI</span>
          <span className="sidebar-brand-subtitle">Evrak Destek Sistemi</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'sidebar-link-active' : ''}`
            }
          >
            <item.icon size={20} />
            <span>{item.label}</span>
          </NavLink>
        ))}
        <button type="button" disabled title="No regulation listing endpoint is available">
          <BookOpen size={20} />
          <span>Mevzuat K\u00FCt\u00FCphanesi</span>
        </button>
        <button type="button" disabled title="This feature is not available yet">
          <Settings size={20} />
          <span>Ayarlar</span>
        </button>
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-footer-text">
          KAMUAI — TEKNOFEST 2026
        </div>
      </div>
    </aside>
  );
};
