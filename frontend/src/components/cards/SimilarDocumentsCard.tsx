import React from "react";
import { Files, Info } from "lucide-react";

export const SimilarDocumentsCard: React.FC = () => (
  <section className="similar-documents-card" aria-labelledby="similar-documents-title">
    <header>
      <span className="similar-documents-icon"><Files size={19} /></span>
      <div>
        <span className="section-kicker">Kurumsal belge hafızası</span>
        <h2 id="similar-documents-title">Benzer Evraklar</h2>
      </div>
      <span className="integration-badge">API bağlantısı bekleniyor</span>
    </header>
    <div className="integration-notice" role="status">
      <Info size={18} />
      <div>
        <strong>Benzer evrak arama servisi henüz HTTP API olarak sunulmuyor.</strong>
        <p>
          <code>document_knowledge</code> araması analiz akışında kullanılıyor; ancak bu
          sonuçları çalışma alanına güvenle taşıyan bir endpoint bulunmadığı için örnek
          veya tahmini kayıt gösterilmiyor.
        </p>
      </div>
    </div>
  </section>
);
