import React, { useEffect, useState } from "react";
import { Building2, ChevronDown, ChevronUp, FlaskConical, MapPin, RefreshCw, Zap } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { demoApi, type DemoScenario } from "../../services/demoApi";

const sourceLabels: Record<string, string> = { VATANDAS: "Vatandaş", DIS_KURUM: "Dış Kurum", KURUM_ICI: "Kurum İçi" };
const scenarioIcons: Record<string, React.ReactNode> = {
  yol_onarim: <MapPin size={18}/>,
  eksik_adres: <MapPin size={18}/>,
  belirsiz_ruhsat: <Building2 size={18}/>,
  cop_temizlik: <Zap size={18}/>,
  dis_kurum_afet: <Building2 size={18}/>,
};
const primaryScenarios = ["yol_onarim", "eksik_adres", "belirsiz_ruhsat", "cop_temizlik", "dis_kurum_afet"];

export function DemoScenarioCenter({ token }: { token: string }) {
  const navigate = useNavigate();
  const [items, setItems] = useState<DemoScenario[]>([]);
  const [available, setAvailable] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const load = () => demoApi.scenarios(token)
    .then((response) => { setItems(response.items); setAvailable(true); })
    .catch(() => { setAvailable(false); setItems([]); });

  useEffect(() => { void load(); }, [token]);

  async function prepare(key: string) {
    setBusy(key);
    setError("");
    try {
      const result = await demoApi.prepare(token, key);
      navigate(`/dosya/${result.case.id}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Senaryo hazırlanamadı.");
    } finally {
      setBusy("");
    }
  }

  async function reset() {
    setBusy("reset");
    setError("");
    try {
      await demoApi.reset(token);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Demo verisi yenilenemedi.");
    } finally {
      setBusy("");
    }
  }

  if (!available) return null;
  const ordered = [...items].sort((left, right) => {
    const leftIndex = primaryScenarios.indexOf(left.key);
    const rightIndex = primaryScenarios.indexOf(right.key);
    return (leftIndex < 0 ? 99 : leftIndex) - (rightIndex < 0 ? 99 : rightIndex);
  });

  return <section className={`case-panel demo-scenario-center demo-scenario-collapsible ${expanded ? "expanded" : "collapsed"}`}>
    <header>
      <div><h2><FlaskConical/> Demo Senaryoları</h2><p>5 yarışma demo vakası</p></div>
      <button className="btn btn-secondary" onClick={() => setExpanded((value) => !value)} aria-expanded={expanded}>
        {expanded ? <><ChevronUp size={16}/> Gizle</> : <><ChevronDown size={16}/> Göster</>}
      </button>
    </header>
    {expanded && <div className="demo-scenario-content">
      <div className="demo-scenario-actions"><button className="btn btn-secondary" onClick={() => void reset()} disabled={Boolean(busy)} id="demo-reset-btn"><RefreshCw size={16}/> Demo verisini yenile</button></div>
      {error && <div className="case-error">{error}</div>}
      <div className="demo-scenario-grid">
        {ordered.map((item) => <button
          key={item.key}
          id={`demo-scenario-${item.key}`}
          onClick={() => void prepare(item.key)}
          disabled={Boolean(busy)}
          className={item.prepared ? "prepared" : ""}
        >
          <span className="demo-scenario-icon">{scenarioIcons[item.key] ?? <FlaskConical size={18}/>}</span>
          <strong>{item.title}</strong>
          <div className="demo-scenario-meta">
            {item.source_type && <em>{sourceLabels[item.source_type] ?? "Kurum kaydı"}</em>}
            {item.expected_department && <em>→ {item.expected_department}</em>}
          </div>
          <small>{item.prepared ? "Hazır · Dosyayı aç" : busy === item.key ? "Hazırlanıyor…" : "Senaryoyu hazırla"}</small>
        </button>)}
      </div>
    </div>}
  </section>;
}
