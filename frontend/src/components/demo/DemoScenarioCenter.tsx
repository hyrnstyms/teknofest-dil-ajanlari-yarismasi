import React, { useEffect, useState } from "react";
import { FlaskConical, RefreshCw } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { demoApi, type DemoScenario } from "../../services/demoApi";

export function DemoScenarioCenter({ token }: { token: string }) {
  const navigate = useNavigate();
  const [items, setItems] = useState<DemoScenario[]>([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const load = () => demoApi.scenarios(token).then((x) => setItems(x.items)).catch((e) => setError(e.message));
  useEffect(() => { void load(); }, [token]);
  async function prepare(key: string) { setBusy(key); setError(""); try { const result = await demoApi.prepare(token, key); navigate(`/dosya/${result.case.id}`); } catch (e) { setError(e instanceof Error ? e.message : "Senaryo hazırlanamadı."); } finally { setBusy(""); } }
  async function reset() { setBusy("reset"); setError(""); try { await demoApi.reset(token); await load(); } catch (e) { setError(e instanceof Error ? e.message : "Demo verisi yenilenemedi."); } finally { setBusy(""); } }
  return <section className="case-panel demo-scenario-center"><header><div><span className="eyebrow">YARIŞMA DEMOSU</span><h2><FlaskConical/> Demo Senaryoları</h2><p>Gerçek Case Engine kayıtlarını tek tıkla ve tekrar üretilebilir biçimde hazırlar.</p></div><button className="btn btn-secondary" onClick={() => void reset()} disabled={Boolean(busy)}><RefreshCw size={16}/> Tüm demo verisini yenile</button></header>{error && <div className="case-error">{error}</div>}<div className="demo-scenario-grid">{items.map((item) => <button key={item.key} onClick={() => void prepare(item.key)} disabled={Boolean(busy)}><span>{item.institution_id === "belediye" ? "Belediye" : "Kaymakamlık"}</span><strong>{item.title}</strong><small>{item.prepared ? "Hazır · dosyayı aç" : "Senaryoyu hazırla"}</small></button>)}</div></section>;
}
