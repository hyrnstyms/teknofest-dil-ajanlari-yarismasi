import React, { useEffect, useState } from "react";
import { ArrowRight, Building2, ShieldCheck, UserRound } from "lucide-react";
import { EVRAGBrand } from "../components/EVRAGBrand";
import { useAuth } from "../contexts/AuthContext";
import { demoApi, type DemoPersona } from "../services/demoApi";

export function DemoLoginPage() {
  const { login } = useAuth();
  const [personas, setPersonas] = useState<DemoPersona[]>([]);
  const [busy, setBusy] = useState<string>();
  const [error, setError] = useState("");
  useEffect(() => { void demoApi.personas().then((x) => setPersonas(x.items)).catch((e) => setError(e.message)); }, []);
  async function select(key: string) { setBusy(key); setError(""); try { await login(key); } catch (e) { setError(e instanceof Error ? e.message : "Demo oturumu başlatılamadı."); } finally { setBusy(undefined); } }
  return <main className="role-login"><section className="role-login-hero"><EVRAGBrand variant="full" theme="dark"/><span className="eyebrow">KURUMSAL İŞ AKIŞI</span><h1>Doğru rol, doğru dosya,<br/>insan denetiminde yapay zekâ.</h1><p>EVRAG, kamu evrakını güvenli insan kararlarıyla uçtan uca yöneten karar destek katmanıdır.</p><div className="trust-line"><ShieldCheck size={18}/> Yapay zekâ önerir, kurum personeli karar verir.</div></section><section className="role-login-panel"><div><span className="eyebrow">YARIŞMA DEMOSU</span><h2>Gerçek demo rolünü seçin</h2><p>Kimlik, kurum ve birim yetkisi backend tarafından doğrulanır.</p></div><div className="persona-list">{personas.map((p) => <button key={p.user_key} className="persona-card" disabled={Boolean(busy)} onClick={() => void select(p.user_key)}><span className="persona-icon"><UserRound/></span><span className="persona-copy"><strong>{p.name}</strong><small><Building2 size={14}/> {p.institution_id === "belediye" ? "Belediye" : "Kaymakamlık"} · {p.department_code.replaceAll("_", " ")}</small><b>{p.role === "EVRAK_KAYIT" ? "Evrak Kayıt Personeli" : "Birim Personeli"}</b><em>{p.role === "EVRAK_KAYIT" ? "İlk inceleme ve güvenli yönlendirme" : "Birim işlemi ve resmî cevap"}</em></span><ArrowRight className="persona-arrow"/></button>)}</div>{error && <div className="case-error" role="alert">{error}</div>}<a className="public-trace-link" href="/takip">Vatandaş başvuru takip ekranına git</a></section></main>;
}
