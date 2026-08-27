import React from "react";
import { NavLink } from "react-router-dom";
import { Bot, FilePlus, FileText, Inbox, LayoutDashboard, MessageSquareText, Settings, UserCheck } from "lucide-react";
import { EVRAGBrand } from "./EVRAGBrand";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  "sidebar-link " + (isActive ? "sidebar-link-active" : "");

interface Props {
  onOpenCopilot?: () => void;
}

const groups = [
  { label: "EVRAK", items: [
    { to: "/", icon: LayoutDashboard, text: "Ana Sayfa", end: true },
    { to: "/yeni-evrak", icon: FilePlus, text: "Yeni Evrak" },
    { to: "/gelen-evraklar", icon: Inbox, text: "Gelen Evraklar" },
  ]},
  { label: "ÇALIŞMA", items: [
    { to: "/taslaklar", icon: FileText, text: "Taslaklar" },
    { to: "/inceleme-bekleyenler", icon: UserCheck, text: "İnceleme Bekleyenler" },
  ]},
  { label: "YAPAY ZEKÂ", items: [
    { to: "/ai-operasyon", icon: Bot, text: "AI Operasyon Merkezi" },
  ]},
  { label: "YÖNETİM", items: [
    { to: "/yonetici", icon: Settings, text: "Yönetici Paneli" },
  ]},
];

export const Sidebar: React.FC<Props> = ({ onOpenCopilot }) => <aside className="sidebar no-print">
  <div className="sidebar-brand">
    <EVRAGBrand variant="full" theme="light" />
  </div>
  <nav className="sidebar-nav">
    {groups.map((group) => <React.Fragment key={group.label}>
      <span className="sidebar-section-label">{group.label}</span>
      {group.items.map((item) => <NavLink key={item.to} to={item.to} end={item.end} className={linkClass}><item.icon size={19}/><span>{item.text}</span></NavLink>)}
      {group.label === "YAPAY ZEKÂ" && <button type="button" className="sidebar-link sidebar-copilot-link" onClick={onOpenCopilot}><MessageSquareText size={19}/><span>EVRAG Copilot</span></button>}
    </React.Fragment>)}
  </nav>
  <div className="sidebar-footer"><div className="sidebar-footer-text"><span className="sidebar-health-dot"/>Sistem Hazır</div><div className="sidebar-runtime">Yerel · Qwen2.5 3B</div></div>
</aside>;