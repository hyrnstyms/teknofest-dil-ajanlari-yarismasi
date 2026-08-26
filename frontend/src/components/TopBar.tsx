import React, { useEffect, useState } from "react";
import { Activity, Landmark } from "lucide-react";
import { api } from "../services/api";

interface Props {
  institutionSelector: React.ReactNode;
}

export const TopBar: React.FC<Props> = ({ institutionSelector }) => {
  const [ready, setReady] = useState<boolean | null>(null);
  const [provider, setProvider] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    api.checkSystemReady()
      .then((result) => { if (mounted) { setReady(Boolean(result.ready)); setProvider(result.services?.llm?.provider || null); } })
      .catch(() => mounted && setReady(false));
    return () => { mounted = false; };
  }, []);

  return (
    <header className="top-bar no-print">
      <div className="top-bar-brand"><Landmark size={19} /><strong>KAMUAI</strong></div>
      <div className="top-bar-context">
        {institutionSelector}
        <span className={`system-pill ${ready === true ? "online" : ready === false ? "offline" : ""}`}>
          <Activity size={14} /> {ready === null ? "Kontrol ediliyor" : ready ? "Sistem Hazır" : "Bir Servis Kullanılamıyor"}{provider && <small>{provider === "ollama" ? "Yerel • Ollama" : provider.toLocaleUpperCase("tr-TR")}</small>}
        </span>
      </div>
    </header>
  );
};
