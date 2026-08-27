import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, BookOpen, Bot, Building2, CheckCircle2, Cpu, Database, FileSearch, Gauge, Network, RefreshCw, Server, ShieldCheck, Workflow, ChevronRight } from "lucide-react";
import type { InstitutionOption, SystemStatus } from "../services/api";
import { api } from "../services/api";
import type { DocumentState } from "../types";
import { formatDocumentType, formatProcessIntent, formatReviewStatus, formatInstitution, formatDisplayName } from "../utils/presentation";
import "./ai-operations.css";

interface Props {
  institution: InstitutionOption | null;
  onOpenAnalysis: (analysisId: string) => void | Promise<void>;
}

interface ReadyState {
  ready?: boolean;
  services?: Record<string, { status?: string; provider?: string }>;
  message?: string;
}

const stages = [
  ["document_agent", "Belge Analizi", "Belge türü, amaç ve öncelik"],
  ["extraction_agent", "Bilgi Çıkarımı", "Belgedeki doğrulanabilir alanlar"],
  ["legal_agent", "Legal RAG", "Mevzuat arama ve kanıt doğrulama"],
  ["missing_field_agent", "Eksik Alan Kontrolü", "Eksik ve belirsiz bilgiler"],
  ["summary_agent", "Özetleme", "Karar destek özeti"],
  ["routing_agent", "Birim Yönlendirme", "Kurum profiline uygun birim"],
  ["writing_agent", "Resmî Yazı", "Kontrollü cevap taslağı"],
  ["quality_agent", "Kalite Kontrolü", "Format ve tutarlılık"],
  ["human_review_agent", "İnsan İncelemesi", "Nihai personel kararı"],
] as const;

type Tab = "GENEL BAKIŞ" | "AJANLAR" | "RAG & MEVZUAT" | "SİSTEM";

export const AIOperationsPage: React.FC<Props> = ({ institution, onOpenAnalysis }) => {
  const [activeTab, setActiveTab] = useState<Tab>("GENEL BAKIŞ");
  const [ready, setReady] = useState<ReadyState | null>(null);
  const [system, setSystem] = useState<SystemStatus | null>(null);
  const [analysis, setAnalysis] = useState<DocumentState | null>(null);
  const [institutions, setInstitutions] = useState<InstitutionOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const results = await Promise.allSettled([
      api.checkSystemReady(),
      api.getSystemStatus(),
      api.getAnalyses(20),
      api.listInstitutionOptions(),
    ]);
    if (results[0].status === "fulfilled") setReady(results[0].value);
    else setReady(null);
    if (results[1].status === "fulfilled") setSystem(results[1].value);
    else setSystem(null);
    if (results[3].status === "fulfilled") setInstitutions(results[3].value);

    if (results[2].status === "fulfilled" && results[2].value.items.length) {
      const preferred = results[2].value.items.find((item) => !institution?.id || item.analysis_id);
      try {
        setAnalysis(await api.getAnalysis((preferred || results[2].value.items[0]).analysis_id));
      } catch {
        setAnalysis(null);
      }
    } else {
      setAnalysis(null);
    }
    if (results.every((result) => result.status === "rejected")) {
      setError("Backend servislerine erişilemedi. Sistem durumunu yeniden deneyebilirsiniz.");
    }
    setLoading(false);
  }, [institution?.id]);

  useEffect(() => { void load(); }, [load]);

  const timings = analysis?.node_timings || {};
  const totalMs = useMemo(() => Object.values(timings).reduce<number>((sum, value) => {
    const duration = typeof value === "number" ? value : value?.duration_ms;
    return sum + (typeof duration === "number" ? duration : 0);
  }, 0), [timings]);
  const evidence = Array.isArray(analysis?.legal_analysis?.evidence) ? analysis.legal_analysis.evidence : [];
  const sources = Array.isArray(analysis?.legal_analysis?.sources) ? analysis.legal_analysis.sources : [];
  const maxTiming = Math.max(1, ...Object.values(timings).map((value) => typeof value === "number" ? value : value?.duration_ms || 0));
  const reviewStatus = analysis?.human_review?.status || "Veri yok";

  const renderGenelBakis = () => (
    <>
      <section className="aiops-status-grid" aria-label="Sistem özeti">
        <StatusCard icon={<Server />} label="Backend" value={ready?.ready ? "Hazır" : "Kullanılamıyor"} ok={Boolean(ready?.ready)} detail={ready?.message} />
        <StatusCard icon={<Bot />} label="LLM" value={system?.llm_provider || ready?.services?.llm?.provider || "Veri yok"} ok={ready?.services?.llm?.status === "ok"} detail={system?.llm_model} />
        <StatusCard icon={<Database />} label="Vector DB" value="Qdrant" ok={ready?.services?.qdrant?.status === "ok"} detail={system?.qdrant ? system.qdrant.legal_points + " mevzuat noktası" : "Sayaç sağlanmıyor"} />
        <StatusCard icon={<Building2 />} label="Aktif Kurum" value={institution?.label || "Seçilmedi"} ok={Boolean(institution)} detail={institutions.length ? institutions.length + " kurum profili" : "Kurum verisi alınamadı"} />
        <StatusCard icon={<ShieldCheck />} label="Son Analiz" value={analysis ? formatReviewStatus(reviewStatus) : "Kayıt yok"} ok={Boolean(analysis)} detail={analysis?.analysis_id} />
      </section>

      {!analysis ? (
        <section className="aiops-empty">
          <Workflow size={34} />
          <h2>Henüz analiz edilmiş evrak bulunmuyor</h2>
          <p>Yeni Evrak ekranından bir evrak analiz ederek AI sürecini burada inceleyebilirsiniz.</p>
        </section>
      ) : (
        <>
          <div className="aiops-primary-grid">
            <section className="aiops-panel">
              <SectionTitle icon={<Workflow />} eyebrow="Son analizin gözlemlenebilir kaydı" title="Son Analizin AI İşlem Akışı" />
              <div className="aiops-pipeline-container">
                <div className="aiops-flow">
                  {stages.map(([id, label, description], index) => {
                    const value = timings[id];
                    const normalized = typeof value === "number" ? { duration_ms: value, status: "completed" } : value;
                    const complete = Boolean(normalized);
                    return (
                      <React.Fragment key={id}>
                        <div className={`aiops-node ${complete ? "complete" : "unknown"}`}>
                          <span className="aiops-node-index">{complete ? <CheckCircle2 size={16} /> : index + 1}</span>
                          <div className="aiops-node-content">
                            <strong>{label}</strong>
                            <small>{description}</small>
                          </div>
                          <div className="aiops-node-time">
                            {normalized?.duration_ms !== undefined ? formatDuration(normalized.duration_ms) : "Bekliyor"}
                          </div>
                        </div>
                        {index < stages.length - 1 && <ChevronRight className="aiops-flow-arrow" size={20} />}
                      </React.Fragment>
                    );
                  })}
                </div>
              </div>
            </section>

            <section className="aiops-panel aiops-report">
              <SectionTitle icon={<FileSearch />} eyebrow="Backend analysis detail" title="Son Analiz Özeti" />
              <dl>
                <Metric label="Analysis ID" value={analysis.analysis_id} />
                <Metric label="Kurum" value={formatInstitution(analysis.kurum_profili_id)} />
                <Metric label="Evrak türü" value={formatDocumentType(analysis.document?.document_type)} />
                <Metric label="İşlem amacı" value={formatProcessIntent(analysis.document?.process_intent)} />
                <Metric label="Öncelik" value={analysis.document?.priority} />
                <Metric label="Önerilen birim" value={analysis.routing?.recommended_unit} />
                <Metric label="Eksik / belirsiz" value={String((analysis.missing_fields?.missing_fields || []).length + (analysis.missing_fields?.uncertain_fields || []).length)} />
                <Metric label="Doğrulanmış kanıt" value={String(evidence.length)} />
                <Metric label="İnceleme" value={formatReviewStatus(reviewStatus)} />
                <Metric label="Toplam node süresi" value={formatDuration(totalMs)} />
              </dl>
              {analysis.analysis_id && (
                <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} type="button" onClick={() => void onOpenAnalysis(analysis.analysis_id!)}>Evrakı Aç</button>
              )}
            </section>
          </div>

          <section className="aiops-panel">
            <SectionTitle icon={<Activity />} eyebrow="Gerçek node_timings" title="Performans ve Süre Dağılımı" />
            <div className="aiops-bars">
              {stages.map(([id, label]) => {
                const value = timings[id];
                const duration = typeof value === "number" ? value : value?.duration_ms;
                if (typeof duration !== "number") return null;
                return (
                  <div className="aiops-bar-row" key={id}>
                    <span>{label}</span>
                    <div><i style={{ width: Math.max(1, duration / maxTiming * 100) + "%" }} /></div>
                    <strong>{formatDuration(duration)}</strong>
                  </div>
                );
              })}
            </div>
          </section>
        </>
      )}
    </>
  );

  const renderAjanlar = () => (
    <section className="aiops-agent-grid">
      <AgentCard title="Document Agent" task="Belge türü, amaç, özet ve öncelik çıkarımı" result={[analysis?.document?.document_type ? formatDocumentType(analysis.document.document_type) : null, analysis?.document?.process_intent ? formatProcessIntent(analysis.document.process_intent) : null].filter(Boolean).join(" · ")} timing={durationOf(timings.document_agent)} />
      <AgentCard title="Extraction Agent" task="Belgedeki doğrulanabilir alanların çıkarılması" result={analysis?.missing_fields ? "Alanlar çıkarıldı" : "Bekleniyor"} timing={durationOf(timings.extraction_agent)} />
      <AgentCard title="Legal Agent" task="Qdrant üzerinde mevzuat arama ve doğrulanmış kanıt üretimi" result={evidence.length ? evidence.length + " doğrulanmış kanıt" : "Doğrulanmış kanıt bulunamadı"} timing={durationOf(timings.legal_agent)} />
      <AgentCard title="Missing Field Agent" task="Eksik ve belirsiz bilgilerin tespiti" result={String((analysis?.missing_fields?.missing_fields || []).length) + " eksik alan"} timing={durationOf(timings.missing_field_agent)} />
      <AgentCard title="Summary Agent" task="Karar destek özeti oluşturma" result={analysis?.document?.summary ? "Özet oluşturuldu" : "Bekleniyor"} timing={durationOf(timings.summary_agent)} />
      <AgentCard title="Routing Agent" task="Aktif kurum profiline göre yetkili birim önerisi" result={analysis?.routing?.recommended_unit || "Birim önerisi yok"} timing={durationOf(timings.routing_agent)} />
      <AgentCard title="Writing Agent" task="Doğrulanmış bağlamdan kontrollü resmî yazı taslağı" result={analysis?.draft?.draft ? "Taslak üretildi" : "Taslak bloke veya mevcut değil"} timing={durationOf(timings.writing_agent)} />
      <AgentCard title="Quality Agent" task="Format ve tutarlılık kontrolü" result={analysis?.human_review?.status ? "Kontrol edildi" : "Bekleniyor"} timing={durationOf(timings.quality_agent)} />
      <AgentCard title="Human Review Agent" task="Nihai personel kararı için bekletme" result={formatReviewStatus(reviewStatus)} timing={durationOf(timings.human_review_agent)} />
    </section>
  );

  const renderRagMevzuat = () => (
    <div className="aiops-secondary-grid">
      <section className="aiops-panel">
        <SectionTitle icon={<Network />} eyebrow="Açıklanabilir yönlendirme" title="Kurum Zekâsı" />
        <dl className="aiops-report">
          <Metric label="Aktif kurum" value={institution?.label || formatInstitution(analysis?.kurum_profili_id)} />
          <Metric label="Analiz kurumu" value={formatInstitution(analysis?.kurum_profili_id)} />
          <Metric label="Önerilen birim" value={analysis?.routing?.recommended_unit} />
          <Metric label="Karar gerekçesi" value={analysis?.routing?.reason || analysis?.routing?.routing_reason} />
          <Metric label="Güven" value={typeof analysis?.routing?.confidence === "number" ? String(analysis.routing.confidence) : undefined} />
          <Metric label="Personel incelemesi" value={formatReviewStatus(reviewStatus)} />
        </dl>
      </section>

      <section className="aiops-panel">
        <SectionTitle icon={<BookOpen />} eyebrow="Analizde kullanılan mevzuat" title="RAG Kanıt Denetçisi" />
        {evidence.length ? (
          <div className="aiops-evidence">
            {evidence.map((entry: any, index: number) => {
              const sourceRef = typeof entry?.source === "string" ? /^K(\d+)$/i.exec(entry.source) : null;
              const source = sources[sourceRef ? Number(sourceRef[1]) - 1 : index] || {};
              return (
                <article key={index}>
                  <strong>{source.title || source.document_id || entry.law_name || "Mevzuat kaynağı"}</strong>
                  <span>{source.law_number ? source.law_number + " sayılı" : "Kanun numarası sağlanmıyor"} {source.madde_no || source.article ? " · Madde " + (source.madde_no || source.article) : ""}</span>
                  <p>{entry.evidence || entry.text || source.text}</p>
                  <small>{source.source || entry.source}</small>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="aiops-inline-empty">Bu analizde doğrulanmış mevzuat kanıtı bulunmuyor. Retrieval adayları kanıt olarak gösterilmez.</div>
        )}
      </section>
    </div>
  );

  const renderSistem = () => (
    <div className="aiops-secondary-grid">
      <section className="aiops-panel">
        <SectionTitle icon={<Cpu />} eyebrow="Doğrulanmış ürün mimarisi" title="AI Teknoloji Yığını" />
        <div className="aiops-tech-grid">
          <Tech label="Üretken model" value={system?.llm_model || "Qwen2.5 3B Instruct"} />
          <Tech label="Provider" value={system?.llm_provider || "Ollama"} />
          <Tech label="Embedding" value={system?.embedding_model || "BAAI/bge-m3"} />
          <Tech label="Vector DB" value="Qdrant" />
          <Tech label="OCR" value="PaddleOCR" />
          <Tech label="Backend" value="FastAPI" />
          <Tech label="Frontend" value="React + Vite" />
          <Tech label="Mode" value={system?.llm_provider === "ollama" ? "Yerel / Offline" : "Yerel / Offline"} />
        </div>
        <div className="aiops-architecture">
          <span>React UI</span><b>→</b><span>FastAPI</span><b>→</b><span>Multi-Agent Workflow</span><b>→</b><span>Human Review</span><b>→</b><span>DOCX</span>
        </div>
      </section>

      <section className="aiops-panel">
        <SectionTitle icon={<Gauge />} eyebrow="Backend sözleşmesi görünürlüğü" title="Sistem Telemetrisi & Gelişmiş Özellikler" />
        <div className="aiops-telemetry">
          <Telemetry label="Qdrant mevzuat noktası" value={system?.qdrant?.legal_points} available={Boolean(system?.qdrant)} />
          <Telemetry label="Qdrant belge noktası" value={system?.qdrant?.document_points} available={Boolean(system?.qdrant)} />
          <Telemetry label="GPU Telemetrisi" value="Entegrasyon bekleniyor" available={false} />
          <Telemetry label="OCR Health" value="Ayrı health endpoint'i sağlanmıyor" available={false} />
          <Telemetry label="Canlı Agent Durumu" value="Streaming/progress endpoint'i mevcut değil" available={false} />
        </div>
      </section>
    </div>
  );

  return (
    <div className="aiops-page no-print">
      <header className="aiops-hero">
        <div>
          <span className="section-kicker">Teknik görünüm · gerçek runtime verisi</span>
          <h1>AI Operasyon Merkezi</h1>
          <p>Çok ajanlı evrak işleme, yerel yapay zekâ altyapısı, RAG kanıtları ve son analiz performansı.</p>
        </div>
        <button className="btn btn-secondary" type="button" onClick={() => void load()} disabled={loading}>
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} /> {loading ? "Yenileniyor" : "Verileri Yenile"}
        </button>
      </header>

      {error && <div className="aiops-alert" role="alert"><AlertTriangle size={18} />{error}</div>}

      <div className="aiops-tabs">
        {(["GENEL BAKIŞ", "AJANLAR", "RAG & MEVZUAT", "SİSTEM"] as Tab[]).map((tab) => (
          <button
            key={tab}
            className={`aiops-tab ${activeTab === tab ? "active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "GENEL BAKIŞ" && renderGenelBakis()}
      {activeTab === "AJANLAR" && analysis && renderAjanlar()}
      {activeTab === "AJANLAR" && !analysis && (
        <section className="aiops-empty">
          <h2>Evrak seçilmedi</h2>
          <p>Ajan metriklerini görüntülemek için analiz edilmiş bir evrak gereklidir.</p>
        </section>
      )}
      {activeTab === "RAG & MEVZUAT" && renderRagMevzuat()}
      {activeTab === "SİSTEM" && renderSistem()}

    </div>
  );
};

const SectionTitle: React.FC<{ icon: React.ReactNode; eyebrow: string; title: string }> = ({ icon, eyebrow, title }) => (
  <header className="aiops-section-title">
    <span>{icon}</span>
    <div>
      <small>{eyebrow}</small>
      <h2>{title}</h2>
    </div>
  </header>
);

const StatusCard: React.FC<{ icon: React.ReactNode; label: string; value: string; ok: boolean; detail?: string }> = ({ icon, label, value, ok, detail }) => (
  <article className="aiops-status-card">
    <span className={`aiops-status-icon ${ok ? "ok" : "warn"}`}>{icon}</span>
    <div>
      <small>{label}</small>
      <strong>{value}</strong>
      <p>{detail || "Ek veri sağlanmıyor"}</p>
    </div>
  </article>
);

const AgentCard: React.FC<{ title: string; task: string; result: string; timing?: number }> = ({ title, task, result, timing }) => (
  <article className="aiops-agent-card">
    <span className="aiops-agent-dot" />
    <h3>{title}</h3>
    <small>Görev</small>
    <p>{task}</p>
    <small>Son sonuç</small>
    <strong>{result || "Veri sağlanmıyor"}</strong>
    <time>{timing === undefined ? "Süre kaydı yok" : formatDuration(timing)}</time>
  </article>
);

const Metric: React.FC<{ label: string; value?: string | null }> = ({ label, value }) => (
  <div>
    <dt>{label}</dt>
    <dd>{value || "Veri sağlanmıyor"}</dd>
  </div>
);

const Tech: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div>
    <small>{label}</small>
    <strong>{value}</strong>
  </div>
);

const Telemetry: React.FC<{ label: string; value: string | number | undefined; available: boolean }> = ({ label, value, available }) => (
  <div>
    <span className={available ? "available" : "missing"}>{available ? "AVAILABLE" : "MISSING"}</span>
    <strong>{label}</strong>
    <p>{value ?? "Veri sağlanmıyor"}</p>
  </div>
);

function durationOf(value: number | { duration_ms?: number } | undefined): number | undefined {
  return typeof value === "number" ? value : value?.duration_ms;
}

function formatDuration(ms: number): string {
  return ms >= 1000 ? (ms / 1000).toLocaleString("tr-TR", { maximumFractionDigits: 2 }) + " sn" : ms + " ms";
}
