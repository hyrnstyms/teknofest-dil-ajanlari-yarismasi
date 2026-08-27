import React, { useEffect, useState } from "react";
import { CalendarDays, CheckCircle2, FileCheck2, FileText, Loader2, ShieldAlert } from "lucide-react";
import { useParams } from "react-router-dom";
import { api, type VerificationResult } from "../services/api";
import { EVRAGBrand } from "../components/EVRAGBrand";
import { formatDisplayName } from "../utils/presentation";

export function QrVerifyPage() {
  const { id = "" } = useParams<{ id: string }>();
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    void api.verifyDocument(id)
      .then((data) => {
        if (!cancelled) setResult(data);
      })
      .catch((requestError: unknown) => {
        if (!cancelled) {
          setError(requestError instanceof Error ? requestError.message : "Belge doğrulama servisine ulaşılamadı.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [id]);

  return (
    <main className="qr-verify-page">
      <header className="qr-verify-header">
        <EVRAGBrand variant="full" theme="dark" />
        <span>Kamusal belge doğrulama</span>
      </header>
      <section className="qr-verify-shell">
        <div className={`qr-verify-mark ${result?.found ? "verified" : ""}`}>
          {loading ? <Loader2 className="spinner" /> : result?.found ? <CheckCircle2 /> : <ShieldAlert />}
        </div>
        <span className="section-kicker">DOĞRULAMA KODU</span>
        <h1>{id || "Geçersiz doğrulama kodu"}</h1>

        {loading && <p className="qr-verify-message">Belge kaydı doğrulanıyor…</p>}
        {error && <div className="qr-verify-error" role="alert"><ShieldAlert size={19} /><div><strong>Belge doğrulanamadı</strong><p>{error}</p></div></div>}
        {result && <>
          <div className="qr-verify-success"><FileCheck2 size={18} /> Bu kayıt EVRAG doğrulama servisi tarafından bulundu.</div>
          <dl className="qr-verify-details">
            <div><dt><FileCheck2 /> Durum</dt><dd>{formatDisplayName(result.status_label || result.status || "Bilinmiyor")}</dd></div>
            <div><dt><FileText /> Evrak türü</dt><dd>{formatDisplayName(result.document_type || "Belirtilmemiş")}</dd></div>
            <div><dt><CalendarDays /> Tarih</dt><dd>{formatDate(result.received_at)}</dd></div>
          </dl>
        </>}
        <p className="qr-verify-privacy">Bu herkese açık ekran yalnız doğrulama için gerekli sınırlı belge bilgisini gösterir.</p>
      </section>
    </main>
  );
}

function formatDate(value: string | null): string {
  if (!value) return "Belirtilmemiş";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("tr-TR", { dateStyle: "long", timeStyle: "short" }).format(date);
}
