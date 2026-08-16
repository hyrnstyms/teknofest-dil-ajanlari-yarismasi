import React from 'react';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

interface LayoutProps {
  currentPath: string;
  onNavigate: (path: string) => void;
  children: React.ReactNode;
}

export function Layout({ currentPath, onNavigate, children }: LayoutProps) {
  return (
    <div className="app-container">
      <Sidebar currentPath={currentPath} onNavigate={onNavigate} />
      <div className="main-content">
        <Topbar />
        <main className="page-content">
          {children}
        </main>
      </div>
    </div>
  );
}
