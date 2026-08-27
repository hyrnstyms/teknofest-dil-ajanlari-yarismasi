import React, { useEffect, useState } from "react";
import { ShieldCheck, Activity, Database, Cpu } from "lucide-react";
import { api } from "../services/api";

export const Header: React.FC = () => {
  const [status, setStatus] = useState<any>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await api.checkSystemReady();
        setStatus(data);
      } catch {
        setStatus({ ready: false, services: {} });
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (state: string) => {
    if (state === "ok") return "badge-success";
    if (state === "error" || state === "unavailable" || state === "unreachable") return "badge-error";
    return "badge-neutral";
  };

  return (
    <header className="app-header">
      <div className="flex items-center gap-4">
        <ShieldCheck size={32} className="text-primary" />
        <div className="app-title">
          <h1>EVRAG</h1>
          <span>Kamu Evrak ve Yazışma Süreçleri için Akıllı Agent Destek Sistemi</span>
        </div>
      </div>

      <div className="flex gap-2">
        <div className={`badge ${status?.ready ? "badge-success" : "badge-error"}`}>
          <Activity size={14} />
          API: {status ? (status.ready ? "Aktif" : "Hata") : "Bağlanıyor..."}
        </div>
        
        {status?.services?.qdrant && (
          <div className={`badge ${getStatusColor(status.services.qdrant.status)}`}>
            <Database size={14} />
            Mevzuat DB: {status.services.qdrant.status === "ok" ? "Aktif" : "Erişilemiyor"}
          </div>
        )}
        
        {status?.services?.ollama && (
          <div className={`badge ${getStatusColor(status.services.ollama.status)}`}>
            <Cpu size={14} />
            LLM: {status.services.ollama.status === "ok" ? "Aktif" : "Bekliyor"}
          </div>
        )}
      </div>
    </header>
  );
};
