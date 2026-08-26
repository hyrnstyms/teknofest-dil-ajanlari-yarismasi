import React, { useEffect, useState } from "react";
import { Activity, Building2, ChevronRight } from "lucide-react";
import { useLocation } from "react-router-dom";
import { api } from "../services/api";

interface Props {
  institutionSelector: React.ReactNode;
}

const pageTitles: Record<string, string> = {
  "/": "Ana Sayfa",
  "/yeni-evrak": "Yeni Evrak",
  "/gelen-evraklar": "Gelen Evraklar",
  "/taslaklar": "Taslaklarım",
  "/inceleme-bekleyenler": "İnceleme Bekleyenler",
  "/yonetici": "Yönetici Paneli",
  "/ai-operasyon": "AI Operasyon Merkezi",
};

export const TopBar: React.FC<Props> = ({ institutionSelector }) => {
  const [ready, setReady] = useState<boolean | null>(null);
  const [provider, setProvider] = useState<string | null>(null);
  const location = useLocation();

  useEffect(() => {
    let mounted = true;
    api.checkSystemReady()
      .then((result) => { if (mounted) { setReady(Boolean(result.ready)); setProvider(result.services?.llm?.provider || null); } })
      .catch(() => mounted && setReady(false));
    return () => { mounted = false; };
  }, []);

  const currentPath = location.pathname;
  let pageTitle = pageTitles[currentPath];
  if (!pageTitle && currentPath.startsWith("/evrak/")) {
    pageTitle = "Evrak İnceleme";
  }

  return (
    <header className="top-bar no-print" style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '1rem 2rem',
      background: '#ffffff',
      borderBottom: '1px solid #e2e8f0',
      marginBottom: '1.5rem',
      borderRadius: '12px',
      boxShadow: '0 1px 3px rgba(15, 23, 42, 0.05)'
    }}>
      <div className="top-bar-breadcrumb" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#64748b', fontSize: '0.9rem', fontWeight: 500 }}>
        <Building2 size={16} />
        <span>EVRAG Workspace</span>
        <ChevronRight size={14} />
        <strong style={{ color: '#0f172a' }}>{pageTitle || "Sayfa"}</strong>
      </div>

      <div className="top-bar-context" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div className="institution-selector-wrapper" style={{ minWidth: '220px' }}>
          {institutionSelector}
        </div>

        <span className={`system-pill ${ready === true ? "online" : ready === false ? "offline" : ""}`} style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          padding: '0.4rem 0.75rem',
          background: ready === true ? '#ecfdf5' : '#fef2f2',
          color: ready === true ? '#10b981' : '#ef4444',
          borderRadius: '9999px',
          fontSize: '0.8rem',
          fontWeight: 600
        }}>
          <Activity size={14} />
          {ready === null ? "Kontrol ediliyor" : ready ? "Hazır" : "Hata"}
          {provider && <small style={{ color: ready === true ? '#059669' : '#b91c1c', marginLeft: '0.2rem', fontWeight: 500 }}>
            {provider === "ollama" ? "• Yerel" : "• API"}
          </small>}
        </span>
      </div>
    </header>
  );
};
