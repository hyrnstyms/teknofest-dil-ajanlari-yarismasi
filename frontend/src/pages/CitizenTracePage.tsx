import React, { useEffect, useState } from "react";
import { Check, Circle, FileCheck2, ShieldCheck } from "lucide-react";
import { useParams, useSearchParams } from "react-router-dom";
import { EVRAGBrand } from "../components/EVRAGBrand";
import { publicCaseApi } from "../services/publicCaseApi";
import type { PublicCase } from "../types/case";

export function CitizenTracePage() {
  const { trackingCode = "" } = useParams();
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [item, setItem] = useState<PublicCase>();
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token) {
      setError("Güvenli takip bağlantısı eksik veya geçersiz.");
      return;
    }
    void publicCaseApi.get(trackingCode, token).then(setItem).catch((cause) => setError(cause.message));
  }, [trackingCode, token]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      setItem(await publicCaseApi.completeInfo(trackingCode, token, answers));
      setSubmitted(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Bilgi gönderilemedi.");
    } finally {
      setBusy(false);
    }
  }

  return <main className="citizen-page">
    <header><EVRAGBrand variant="full" theme="light"/><span><ShieldCheck/> Güvenli Başvuru Takibi</span></header>
    <div className="citizen-shell">
      <section className="citizen-intro"><span className="eyebrow">BAŞVURU TAKİP NUMARASI</span><h1>{trackingCode}</h1><p>Bu sayfa yalnız güvenli ve sade süreç bilgisini gösterir.</p></section>
      {error && <div className="case-error" role="alert">{error}</div>}
      {!error && !item && <div className="case-loading">Başvuru bilgileri güvenli biçimde alınıyor…</div>}
      {item && <>
        <section className="citizen-summary">
          <div><small>Alınma tarihi</small><strong>{new Date(item.received_at).toLocaleDateString("tr-TR")}</strong></div>
          <div><small>Güncel durum</small><strong>{item.public_status}</strong></div>
          <div><small>Son güncelleme</small><strong>{new Date(item.updated_at).toLocaleDateString("tr-TR")}</strong></div>
        </section>
        <section className="citizen-progress"><h2>Başvurunuzun yolculuğu</h2><ol>{item.timeline.map((step, index) => <li className={index === item.timeline.length - 1 ? "current" : "completed"} key={`${step.event}-${index}`}><span>{index === item.timeline.length - 1 ? <Circle/> : <Check/>}</span><strong>{step.label}</strong></li>)}</ol></section>
        {item.clarification && !submitted && <section className="citizen-info-form"><FileCheck2/><div>
          <span className="eyebrow">İŞLEME DEVAM ETMEK İÇİN</span><h2>Bir bilginizi tamamlamanız gerekiyor</h2><p>{item.clarification.question}</p>
          <form onSubmit={(event) => void submit(event)}>{item.clarification.requested_fields.map((field) => <label key={field}>{field === "location" ? "Açık adres" : field === "permit_type" ? "Ruhsat türü" : "İstenen bilgi"}
            {item.clarification?.question_type === "choice"
              ? <select required value={answers[field] || ""} onChange={(event) => setAnswers({ ...answers, [field]: event.target.value })}><option value="">Seçiniz</option>{item.clarification.options.map((option) => <option value={option.value} key={option.value}>{option.label}</option>)}</select>
              : <input required value={answers[field] || ""} onChange={(event) => setAnswers({ ...answers, [field]: event.target.value })}/>}</label>)}
            <button className="btn btn-primary" disabled={busy}>{busy ? "Gönderiliyor…" : "Bilgiyi güvenli biçimde gönder"}</button>
          </form>
        </div></section>}
        {submitted && <section className="citizen-success"><Check/><div><h2>Bilginiz alındı</h2><p>Başvurunuz gerekli aşamalardan yeniden değerlendirildi.</p></div></section>}
        <p className="citizen-privacy">Bu ekranda kurum içi notlar, AI ayrıntıları veya başka kişilere ait bilgiler gösterilmez.</p>
      </>}
    </div>
  </main>;
}
