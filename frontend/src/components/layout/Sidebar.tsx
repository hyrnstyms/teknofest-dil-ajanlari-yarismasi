import React from 'react';
import { FileText, LayoutDashboard, FileSearch, Settings, BookOpen, Activity, Server } from 'lucide-react';

interface SidebarProps {
  currentPath: string;
  onNavigate: (path: string) => void;
}

export function Sidebar({ currentPath, onNavigate }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1>KAMUAI</h1>
      </div>
      <nav className="sidebar-nav">
        <a 
          href="#" 
          className={`nav-item ${currentPath === 'new' || currentPath === 'analysis' ? 'active' : ''}`}
          onClick={(e) => { e.preventDefault(); onNavigate('new'); }}
        >
          <FileText size={18} />
          <span>Yeni Evrak</span>
        </a>
        
        {/* Dummy items */}
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
    </aside>
  );
}
