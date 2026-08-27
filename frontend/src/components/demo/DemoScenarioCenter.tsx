import React, { useEffect, useState } from "react";
import { Building2, FlaskConical, MapPin, RefreshCw, Zap } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { demoApi, type DemoScenario } from "../../services/demoApi";

const SOURCE_LABELS: Record<string, string> = {
  VATANDAS: "Vatandaş",
  DIS_KURUM: "Dış Kurum",
  KURUM_ICI: "Kurum İçi",
};

const SCENARIO_ICONS: Record<string, React.ReactNode> = {
  yol_onarim: <MapPin size={18} />,
  eksik_adres: <MapPin size={18} />,
  belirsiz_ruhsat: <Building2 size={18} />,
  cop_temizlik: <Zap size={18} />,
  dis_kurum_afet: <Building2 size={18} />,
};

// Golden demo case labels — shown prominently in the jury demo
const GOLDEN_CASES = ["yol_onarim", "eksik_adres", "belirsiz_ruhsat", "cop_temizlik", "dis_kurum_afet"];

export function DemoScenarioCenter({ token }: { token: string }) {
  const navigate = useNavigate();
  const [items, setItems] = useState<DemoScenario[]>([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const load = () =>
    demoApi.scenarios(token).then((x) => setItems(x.items)).catch((e) => setError(e.message));

  useEffect(() => { void load(); }, [token]);

  async function prepare(key: string) {
    setBusy(key);
    setError("");
    try {
      const result = await demoApi.prepare(token, key);
      navigate(`/dosya/${result.case.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Senaryo hazırlanamadı.");
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
    } catch (e) {
      setError(e instanceof Error ? e.message : "Demo verisi yenilenemedi.");
    } finally {
      setBusy("");
    }
  }

  // Split: golden belediye cases first, then the rest
  const golden = items.filter((x) => GOLDEN_CASES.includes(x.key));
  const others = items.filter((x) => !GOLDEN_CASES.includes(x.key));

  return (
    <section className="case-panel demo-scenario-center">
      <header>
        <div>
          <span className="eyebrow">YARIŞ DEMOSU — 5 ALTIN SENARYO</span>
          <h2><FlaskConical /> Demo Senaryoları</h2>
          <p>
            Gerçek Case Engine kayıtlarını tek tıkla üretir.{" "}
            <strong>Demo fixture</strong> olduklarını açıkça belirtir.
          </p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={() => void reset()}
          disabled={Boolean(busy)}
          id="demo-reset-btn"
        >
          <RefreshCw size={16} /> Tüm demo verisini yenile
        </button>
      </header>

      {error && <div className="case-error">{error}</div>}

      {golden.length > 0 && (
        <>
          <span className="eyebrow" style={{ marginBottom: "0.5rem", display: "block" }}>
            BELEDİYE — 5 GOLDEN DEMO CASE
          </span>
          <div className="demo-scenario-grid">
            {golden.map((item) => (
              <button
                key={item.key}
                id={`demo-scenario-${item.key}`}
                onClick={() => void prepare(item.key)}
                disabled={Boolean(busy)}
                className={item.prepared ? "prepared" : ""}
              >
                <span className="demo-scenario-icon">{SCENARIO_ICONS[item.key] ?? <FlaskConical size={18} />}</span>
                <strong>{item.title}</strong>
                <div className="demo-scenario-meta">
                  {item.source_type && (
                    <em>{SOURCE_LABELS[item.source_type] ?? item.source_type}</em>
                  )}
                  {item.expected_department && (
                    <em>→ {item.expected_department}</em>
                  )}
                </div>
                <small>{item.prepared ? "Hazır · Dosyayı aç" : busy === item.key ? "Hazırlanıyor…" : "Senaryoyu hazırla"}</small>
              </button>
            ))}
          </div>
        </>
      )}

      {others.length > 0 && (
        <>
          <span className="eyebrow" style={{ marginTop: "1.5rem", marginBottom: "0.5rem", display: "block" }}>
            DİĞER SENARYOLAR
          </span>
          <div className="demo-scenario-grid">
            {others.map((item) => (
              <button
                key={item.key}
                id={`demo-scenario-${item.key}`}
                onClick={() => void prepare(item.key)}
                disabled={Boolean(busy)}
                className={item.prepared ? "prepared" : ""}
              >
                <span>{item.institution_id === "belediye" ? "Belediye" : "Kaymakamlık"}</span>
                <strong>{item.title}</strong>
                <small>{item.prepared ? "Hazır · dosyayı aç" : "Senaryoyu hazırla"}</small>
              </button>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
