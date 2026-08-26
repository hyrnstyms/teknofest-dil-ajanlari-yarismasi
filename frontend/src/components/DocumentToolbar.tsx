import React, { useState } from "react";
import { Check, Copy, Download, History, Pencil, Printer, RefreshCw } from "lucide-react";
import { api } from "../services/api";

interface Props {
  analysisId?: string;
  hasDocument: boolean;
  reviewStatus?: string;
  copyText?: string;
  onOpenAudit: () => void;
}

export const DocumentToolbar: React.FC<Props> = ({ analysisId, hasDocument, reviewStatus, copyText, onOpenAudit }) => {
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const canDownloadDocx = reviewStatus === "approved";

  const downloadDocx = async () => {
    if (!analysisId) return;
    setDownloading(true);
    setDownloadError(null);
    try {
      const blob = await api.downloadDocx(analysisId);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "resmi_yazi_taslak.docx";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : "DOCX indirilemedi.");
    } finally {
      setDownloading(false);
    }
  };

  const copyDocument = async () => {
    if (!copyText) return;
    try {
      await navigator.clipboard.writeText(copyText);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setDownloadError("Belge metni panoya kopyalanamadı.");
    }
  };

  return (
    <div className="document-toolbar no-print">
      <div className="toolbar-actions">
        <button type="button" disabled title="Genel düzenleme endpoint'i resmî yazı context'ini güvenli biçimde güncellemiyor"><Pencil size={16} /> Düzenle</button>
        <button type="button" disabled title="Yeniden oluşturma backend akışı mevcut değil"><RefreshCw size={16} /> Yeniden Oluştur</button>
        <button type="button" onClick={downloadDocx} disabled={!analysisId || downloading || !canDownloadDocx} title={canDownloadDocx ? "Onaylı resmî yazıyı DOCX olarak indir" : "DOCX indirmek için önce personel onayı gerekir"}><Download size={16} /> {downloading ? "İndiriliyor" : "DOCX İndir"}</button>
        <button type="button" onClick={() => window.print()} disabled={!hasDocument}><Printer size={16} /> PDF / Yazdır</button>
        <button type="button" onClick={() => void copyDocument()} disabled={!copyText}>{copied ? <Check size={16} /> : <Copy size={16} />} {copied ? "Kopyalandı" : "Kopyala"}</button>
      </div>
      <button type="button" className="history-button" onClick={onOpenAudit} disabled={!analysisId}><History size={16} /> İşlem Geçmişi</button>
      {downloadError && <span className="toolbar-error" role="alert">{downloadError}</span>}
    </div>
  );
};
