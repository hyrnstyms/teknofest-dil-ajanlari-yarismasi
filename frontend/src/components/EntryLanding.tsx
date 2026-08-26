import React, { useEffect, useRef } from "react";
import { ArrowRight, Bot, ChevronDown } from "lucide-react";

interface Props {
  onEnterDesk: () => void;
  onEnterAdmin: () => void;
}

/** Six-step pipeline used in both the origami visual and the "How It Works" strip */
const PIPELINE = [
  { id: "evrak",     label: "Evrak",        sub: "Belge girişi" },
  { id: "analiz",    label: "Analiz",       sub: "Tür & önem" },
  { id: "cikarim",  label: "Bilgi",         sub: "Alan çıkarma" },
  { id: "mevzuat",  label: "Mevzuat",       sub: "Yasal doğrulama" },
  { id: "yonlend",  label: "Yönlendirme",   sub: "Birim önerisi" },
  { id: "taslak",   label: "Taslak & Onay", sub: "Personel kararı" },
];

const VALUE_ITEMS = [
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} width={28} height={28} aria-hidden="true">
        <path d="M9 12h6M9 16h4M7 4H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2"/>
        <rect x="9" y="2" width="6" height="4" rx="1" ry="1"/>
      </svg>
    ),
    title: "Belgeyi Anlar",
    desc: "Evrak türü, amaç, özet ve eksik bilgileri çıkarır.",
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} width={28} height={28} aria-hidden="true">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
      </svg>
    ),
    title: "Mevzuatla Doğrular",
    desc: "İlgili mevzuatı güvenilir kaynaklardan bulur.",
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} width={28} height={28} aria-hidden="true">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
      </svg>
    ),
    title: "Karara Dönüştürür",
    desc: "Doğru birimi önerir ve resmî yazı taslağı hazırlar.",
  },
];

/** Origami SVG – paper → fold path → pipeline nodes */
const OrigamiVisual: React.FC = () => (
  <svg
    className="cover-origami-svg"
    viewBox="0 0 420 520"
    aria-hidden="true"
    role="img"
    aria-label="EVRAG belge akış diyagramı"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    {/* Document shape */}
    <g transform="translate(20, 20)">
      <rect x="60" y="20" width="120" height="150" rx="4" fill="white" fillOpacity="0.08" stroke="#249b9a" strokeWidth="1.5"/>
      {/* fold corner */}
      <path d="M 155 20 L 180 45 L 155 45 Z" fill="#249b9a" fillOpacity="0.3"/>
      <line x1="80" y1="75" x2="155" y2="75" stroke="#249b9a" strokeWidth="1.2" strokeDasharray="4 3"/>
      <line x1="80" y1="93" x2="155" y2="93" stroke="white" strokeWidth="1" strokeOpacity="0.25"/>
      <line x1="80" y1="109" x2="135" y2="109" stroke="white" strokeWidth="1" strokeOpacity="0.25"/>
      <line x1="80" y1="125" x2="145" y2="125" stroke="white" strokeWidth="1" strokeOpacity="0.25"/>
      {/* EVRAK label */}
      <text x="120" y="58" textAnchor="middle" fill="#249b9a" fontSize="10" fontWeight="700" letterSpacing="0.1em">EVRAK</text>
    </g>

    {/* Curved path from document down through nodes */}
    <path
      d="M 140 195 C 140 250 200 270 200 320 C 200 370 200 390 200 430"
      stroke="url(#pathGrad)"
      strokeWidth="2"
      strokeDasharray="6 4"
    />

    {/* Gradient definition */}
    <defs>
      <linearGradient id="pathGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#249b9a" stopOpacity="0.8"/>
        <stop offset="100%" stopColor="#0ea5e9" stopOpacity="0.4"/>
      </linearGradient>
      <linearGradient id="nodeGrad" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stopColor="#249b9a" stopOpacity="0.15"/>
        <stop offset="100%" stopColor="#0ea5e9" stopOpacity="0.08"/>
      </linearGradient>
    </defs>

    {/* Pipeline nodes */}
    {[
      { y: 235, label: "Analiz",        sub: "Sınıf · Önem · Özet" },
      { y: 300, label: "Mevzuat",       sub: "Yasal Doğrulama" },
      { y: 365, label: "Yönlendirme",   sub: "Birim Tahmini" },
      { y: 430, label: "Taslak & Onay", sub: "Personel Kararı" },
    ].map((node, i) => (
      <g key={i} transform={`translate(200, ${node.y})`}>
        {/* connector dot */}
        <circle cx={0} cy={0} r={5} fill="#249b9a" fillOpacity="0.7"/>
        {/* node card */}
        <rect x="18" y="-22" width="170" height="44" rx="6" fill="url(#nodeGrad)" stroke="#249b9a" strokeWidth="1" strokeOpacity="0.4"/>
        <text x="28" y="-5" fill="white" fontSize="11.5" fontWeight="700" fillOpacity="0.92">{node.label}</text>
        <text x="28" y="12" fill="#9ecfcf" fontSize="9.5">{node.sub}</text>
      </g>
    ))}

    {/* Final stamp at bottom */}
    <g transform="translate(200, 490)">
      <circle cx={0} cy={0} r={14} fill="#249b9a" fillOpacity="0.18" stroke="#249b9a" strokeWidth="1.5"/>
      <path d="M -5 0 L -1 4 L 6 -4" stroke="#249b9a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </g>

    {/* "AI" badge top right */}
    <g transform="translate(340, 40)">
      <rect x="-30" y="-14" width="60" height="28" rx="14" fill="#0ea5e9" fillOpacity="0.15" stroke="#0ea5e9" strokeWidth="1" strokeOpacity="0.5"/>
      <text x="0" y="5" textAnchor="middle" fill="#7dd3fc" fontSize="10.5" fontWeight="700">AI</text>
    </g>
  </svg>
);

export const EntryLanding: React.FC<Props> = ({ onEnterDesk, onEnterAdmin }) => {
  const heroRef = useRef<HTMLDivElement>(null);

  // subtle parallax on mouse move (desktop only, respects reduced-motion)
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) return;
    const hero = heroRef.current;
    if (!hero) return;
    const handler = (e: MouseEvent) => {
      const cx = window.innerWidth / 2;
      const cy = window.innerHeight / 2;
      const dx = (e.clientX - cx) / cx;
      const dy = (e.clientY - cy) / cy;
      hero.style.setProperty("--px", String(dx * 6));
      hero.style.setProperty("--py", String(dy * 4));
    };
    window.addEventListener("mousemove", handler, { passive: true });
    return () => window.removeEventListener("mousemove", handler);
  }, []);

  return (
    <div className="cover-root" role="main">
      {/* ─── Minimal top nav ─── */}
      <nav className="cover-nav" aria-label="EVRAG ana gezinti">
        <a href="/" className="cover-nav-logo" aria-label="EVRAG ana sayfa">
          <img src="/brand/evrag-logo.png" alt="EVRAG" height="38" />
        </a>
        <div className="cover-nav-links">
          <a href="#nasil-calisir" className="cover-nav-link">Nasıl Çalışır?</a>
          <a href="#teknoloji" className="cover-nav-link">Teknoloji</a>
          <button
            type="button"
            className="cover-nav-cta"
            onClick={onEnterDesk}
          >
            Evrak Masasına Gir <ArrowRight size={15} aria-hidden="true" />
          </button>
        </div>
      </nav>

      {/* ─── HERO ─── */}
      <section className="cover-hero" aria-labelledby="cover-headline" ref={heroRef}>
        <div className="cover-hero-text">
          {/* kicker badge */}
          <div className="cover-kicker" aria-hidden="true">
            <span className="cover-kicker-dot" />
            Akıllı Evrak ve Karar Destek Sistemi
          </div>

          <h1 id="cover-headline" className="cover-headline">
            Evraktan karara,<br />
            <span className="cover-headline-accent">tek akıllı akış.</span>
          </h1>

          <p className="cover-body">
            EVRAG; kamu kurumlarına gelen evrakları anlayan, önemli ve
            eksik bilgileri çıkaran, ilgili mevzuatı doğrulayan, doğru
            birime yönlendiren ve personel onayına sunulmak üzere resmî
            yazı taslağı hazırlayan yapay zekâ destekli karar sistemidir.
          </p>

          <div className="cover-actions">
            <button
              type="button"
              className="cover-btn-primary"
              onClick={onEnterDesk}
              autoFocus
            >
              Evrak Masasına Gir <ArrowRight size={18} aria-hidden="true" />
            </button>
            <button
              type="button"
              className="cover-btn-secondary"
              onClick={onEnterAdmin}
            >
              <Bot size={17} aria-hidden="true" /> AI Operasyon Merkezi
            </button>
          </div>

          <a href="#nasil-calisir" className="cover-scroll-hint" aria-label="Aşağı kaydır">
            <ChevronDown size={18} aria-hidden="true" /> Nasıl Çalışır?
          </a>
        </div>

        {/* Origami visual */}
        <div className="cover-hero-visual" aria-hidden="true">
          <div className="cover-origami-wrap">
            <OrigamiVisual />
          </div>
        </div>
      </section>

      {/* ─── Trust banner ─── */}
      <div className="cover-trust-banner" role="note">
        <span className="cover-trust-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
        </span>
        <strong>Yapay zekâ önerir.</strong>&nbsp;Nihai karar personeldedir.
      </div>

      {/* ─── 3-Value strip ─── */}
      <section className="cover-values" aria-label="Ürün değerleri">
        {VALUE_ITEMS.map((item) => (
          <div key={item.title} className="cover-value-card">
            <div className="cover-value-icon">{item.icon}</div>
            <h3 className="cover-value-title">{item.title}</h3>
            <p className="cover-value-desc">{item.desc}</p>
          </div>
        ))}
      </section>

      {/* ─── How It Works ─── */}
      <section id="nasil-calisir" className="cover-howto" aria-labelledby="howto-heading">
        <h2 id="howto-heading" className="cover-section-heading">Nasıl Çalışır?</h2>
        <div className="cover-pipeline" role="list">
          {PIPELINE.map((step, i) => (
            <React.Fragment key={step.id}>
              <div className="cover-pipeline-step" role="listitem">
                <div className="cover-pipeline-num" aria-hidden="true">{String(i + 1).padStart(2, "0")}</div>
                <div className="cover-pipeline-label">{step.label}</div>
                <div className="cover-pipeline-sub">{step.sub}</div>
              </div>
              {i < PIPELINE.length - 1 && (
                <div className="cover-pipeline-arrow" aria-hidden="true">→</div>
              )}
            </React.Fragment>
          ))}
        </div>
      </section>

      {/* ─── Multi-institution differentiator ─── */}
      <section className="cover-institutions" aria-labelledby="inst-heading">
        <div className="cover-inst-inner">
          <h2 id="inst-heading" className="cover-section-heading">Tek sistem, farklı kurum profilleri.</h2>
          <p className="cover-inst-body">
            Aynı yapay zekâ altyapısı, aktif kurumun organizasyon yapısı
            ve süreçlerine göre yönlendirme davranışını adapte eder.
          </p>
          <div className="cover-inst-diagram" aria-hidden="true">
            <div className="cover-inst-node">Kaymakamlık</div>
            <div className="cover-inst-arrows">↔</div>
            <div className="cover-inst-center">EVRAG<br/><span>AI Çekirdeği</span></div>
            <div className="cover-inst-arrows">↔</div>
            <div className="cover-inst-node">Belediye</div>
          </div>
        </div>
      </section>

      {/* ─── Local AI / tech statement ─── */}
      <section id="teknoloji" className="cover-tech" aria-labelledby="tech-heading">
        <h2 id="tech-heading" className="cover-tech-heading">Yerel çalışmaya hazır yapay zekâ altyapısı</h2>
        <p className="cover-tech-body">
          İnternet bağlantısı gerektirmez. Tüm modeller kurumun kendi
          sunucusunda çalışır.
        </p>
        <div className="cover-tech-chips" role="list">
          {["Ollama", "Qwen2.5", "BGE-M3", "Qdrant", "PaddleOCR"].map((chip) => (
            <span key={chip} className="cover-tech-chip" role="listitem">{chip}</span>
          ))}
        </div>
      </section>

      {/* ─── Footer CTA ─── */}
      <footer className="cover-footer">
        <button type="button" className="cover-btn-primary cover-footer-cta" onClick={onEnterDesk}>
          Evrak Masasına Gir <ArrowRight size={18} aria-hidden="true" />
        </button>
        <p className="cover-footer-note">
          Demo akışı · Giriş gerektirmiyor · Kurum profili çalışma alanında seçilir
        </p>
      </footer>
    </div>
  );
};
