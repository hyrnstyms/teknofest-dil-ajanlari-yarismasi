import React from "react";
import {
  BookOpen,
  Building2,
  FilePlus2,
  FileText,
  Home,
  Inbox,
  LayoutDashboard,
  Settings,
  UserCheck,
} from "lucide-react";

export type AppView =
  | "home"
  | "new-document"
  | "incoming"
  | "drafts"
  | "reviews"
  | "document-workspace"
  | "admin";

interface Props {
  activeView: AppView;
  onViewChange: (view: AppView) => void;
}

const navigationItems: Array<{
  view: Exclude<AppView, "document-workspace">;
  label: string;
  icon: React.ComponentType<{ size?: number }>;
}> = [
  { view: "home", label: "Anasayfa", icon: Home },
  { view: "new-document", label: "Yeni Evrak", icon: FilePlus2 },
  { view: "incoming", label: "Gelen Evraklar", icon: Inbox },
  { view: "drafts", label: "Taslaklarım", icon: FileText },
  { view: "reviews", label: "İnceleme Bekleyenler", icon: UserCheck },
];

export const Sidebar: React.FC<Props> = ({ activeView, onViewChange }) => (
  <aside className="app-sidebar no-print">
    <div className="sidebar-brand">
      <div className="sidebar-logo"><Building2 size={22} /></div>
      <div><strong>KAMUAI Evrak Masası</strong><span>Personel çalışma alanı</span></div>
    </div>

    <nav className="sidebar-nav" aria-label="Ana menü">
      {navigationItems.map(({ view, label, icon: Icon }) => (
        <button
          key={view}
          type="button"
          className={activeView === view ? "active" : ""}
          onClick={() => onViewChange(view)}
        >
          <Icon size={18} /> {label}
        </button>
      ))}
      <button type="button" disabled title="Bağlı bir mevzuat listeleme endpoint'i bulunmuyor">
        <BookOpen size={18} /> Mevzuat Kütüphanesi <span className="soon-label">Yakında</span>
      </button>
      <button
        type="button"
        className={activeView === "admin" ? "active" : ""}
        onClick={() => onViewChange("admin")}
      >
        <LayoutDashboard size={18} /> Yönetici Paneli
      </button>
      <button type="button" disabled title="Bu özellik henüz kullanıma açık değil">
        <Settings size={18} /> Ayarlar <span className="soon-label">Yakında</span>
      </button>
    </nav>
  </aside>
);
