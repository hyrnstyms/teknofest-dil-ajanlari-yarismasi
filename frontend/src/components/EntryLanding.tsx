import React from "react";
import { ArrowRight, Building2, LayoutDashboard, ShieldCheck } from "lucide-react";

interface Props {
  onEnterDesk: () => void;
  onEnterAdmin: () => void;
}

export const EntryLanding: React.FC<Props> = ({ onEnterDesk, onEnterAdmin }) => (
  <main className="entry-landing">
    <section className="entry-hero" aria-labelledby="entry-title">
      <div className="entry-brand"><ShieldCheck size={22} /> Kamu kurumları için güvenli yapay zekâ</div>
      <p className="entry-kicker">KAMUAI</p>
      <h1 id="entry-title">Kamu Evrak Süreçleri için Yapay Zekâ Destekli Karar Destek Sistemi</h1>
      <p className="entry-description">
        Gelen evrakı analiz edin, doğru kurumsal birime yönlendirin, mevzuat kanıtını görün
        ve resmî yazı taslağını insan denetimiyle hazırlayın.
      </p>
      <div className="entry-actions">
        <button type="button" className="entry-primary" onClick={onEnterDesk}>
          <Building2 size={20} /> Evrak Masasına Gir <ArrowRight size={18} />
        </button>
        <button type="button" className="entry-secondary" onClick={onEnterAdmin}>
          <LayoutDashboard size={20} /> Yönetici Görünümü
        </button>
      </div>
      <p className="entry-note">Giriş gerektirmeyen demo akışı · Kurum profili seçimi çalışma alanında yapılır</p>
    </section>
    <aside className="entry-capabilities" aria-label="KAMUAI yetenekleri">
      <div><strong>01</strong><span>Evrak sınıflandırma ve alan çıkarımı</span></div>
      <div><strong>02</strong><span>Kurum profiline göre açıklanabilir yönlendirme</span></div>
      <div><strong>03</strong><span>Kanıtlı mevzuat ve kontrollü taslak desteği</span></div>
    </aside>
  </main>
);
