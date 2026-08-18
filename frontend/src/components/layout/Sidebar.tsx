import React from 'react';
import { FileText, LayoutDashboard, FileSearch, Settings, BookOpen, Activity, Server, Database } from 'lucide-react';

interface SidebarProps {
  currentPath: string;
  onNavigate: (path: string) => void;
}

export function Sidebar({ currentPath, onNavigate }: SidebarProps) {
  return (
    <aside className="sidebar flex flex-col h-full">
      <div className="sidebar-header flex flex-col gap-1">
        <h1 className="text-white font-semibold">KAMUAI</h1>
        <span className="text-xs text-sidebar-text">Kamu Evrak Karar Destek Sistemi</span>
      </div>
      <nav className="sidebar-nav flex-1">
        <a 
          href="#" 
          className={`nav-item ${currentPath === 'new' || currentPath === 'analysis' ? 'active' : ''}`}
          onClick={(e) => { e.preventDefault(); onNavigate('new'); }}
        >
          <FileText size={18} />
          <span>Yeni Evrak</span>
        </a>
        
        <a 
          href="#" 
          className={`nav-item ${currentPath === 'documents' ? 'active' : ''}`}
          onClick={(e) => { e.preventDefault(); onNavigate('documents'); }}
        >
          <LayoutDashboard size={18} />
          <span>Evraklar</span>
        </a>
        <a 
          href="#" 
          className={`nav-item ${currentPath === 'review-queue' ? 'active' : ''}`}
          onClick={(e) => { e.preventDefault(); onNavigate('review-queue'); }}
        >
          <FileSearch size={18} />
          <span>İnceleme Kuyruğu</span>
        </a>
        <div className="nav-item disabled" title="Bu aşamada aktif değil">
          <BookOpen size={18} />
          <span>Mevzuat Explorer</span>
        </div>
        <a 
          href="#" 
          className={`nav-item ${currentPath === 'performance' ? 'active' : ''}`}
          onClick={(e) => { e.preventDefault(); onNavigate('performance'); }}
        >
          <Activity size={18} />
          <span>Performans (ROI)</span>
        </a>
        <a 
          href="#" 
          className={`nav-item ${currentPath === 'status' ? 'active' : ''}`}
          onClick={(e) => { e.preventDefault(); onNavigate('status'); }}
        >
          <Server size={18} />
          <span>Sistem Durumu</span>
        </a>
        <div className="nav-item disabled" title="Bu aşamada aktif değil">
          <Settings size={18} />
          <span>Ayarlar</span>
        </div>
      </nav>
      
      <div className="p-4 border-t border-sidebar-hover">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2 text-xs text-sidebar-text">
            <span className="w-2 h-2 rounded-full bg-success"></span>
            <span>API: Connected</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-sidebar-text">
            <Database size={12} />
            <span className="bg-sidebar-hover px-2 py-1 rounded-md">EBYS: Demo</span>
          </div>
        </div>
      </div>
    </aside>
  );
}

