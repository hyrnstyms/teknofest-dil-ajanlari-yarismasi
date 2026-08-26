import React, { useState } from "react";
import { FileSignature, Download } from "lucide-react";
import { DraftInfo } from "../../types";
import { api } from "../../services/api";

interface Props {
  draft: DraftInfo;
  analysisId?: string;
}

export const OfficialDraftPanel: React.FC<Props> = ({ draft, analysisId }) => {
  const [activeTab, setActiveTab] = useState<"official" | "raw">("official");
  const [downloading, setDownloading] = useState(false);
  const officialText =
    typeof draft?.official_rendered_text === "string"
      ? draft.official_rendered_text
      : typeof draft?.official_render === "string"
        ? draft.official_render
        : "";
  const rawDraftText =
    typeof draft?.rendered_text === "string"
      ? draft.rendered_text
      : draft?.draft_text || draft?.draft?.body || "";

  const handleDownloadDocx = async () => {
    if (!analysisId) return;
    setDownloading(true);
    try {
      const response = await fetch(api.getDocxUrl(analysisId));
      if (!response.ok) {
        throw new Error("DOCX indirme hatası");
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "resmi_yazi_taslak.docx";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("DOCX indirme hatası:", err);
    } finally {
      setDownloading(false);
    }
  };

  if (!officialText && !rawDraftText) {
    return (
      <div className="card mb-4">
        <div className="card-header"><FileSignature size={18}/> Resmî Cevap Taslağı</div>
        <div className="card-body">
          <p className="text-secondary">Taslak oluşturulamadı.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card mb-4">
      <div className="card-header flex justify-between items-center w-full">
        <div className="flex items-center gap-2">
          <FileSignature size={18}/> Resmî Cevap Taslağı
        </div>
        <div className="flex items-center gap-2">
          {draft.draft_type && (
            <div className="badge badge-info text-xs">
              Taslak Türü: {formatDraftType(draft.draft_type)}
            </div>
          )}
          {analysisId && (
            <button
              className="btn btn-sm btn-outline flex items-center gap-1"
              onClick={handleDownloadDocx}
              disabled={downloading}
              title="DOCX olarak indir"
            >
              <Download size={14}/>
              {downloading ? "İndiriliyor..." : "DOCX"}
            </button>
          )}
        </div>
      </div>
      <div className="card-body bg-gray-50">
        <div className="tabs">
          <div 
            className={`tab ${activeTab === "official" ? "active" : ""}`}
            onClick={() => setActiveTab("official")}
          >
            Resmî Görünüm
          </div>
          <div 
            className={`tab ${activeTab === "raw" ? "active" : ""}`}
            onClick={() => setActiveTab("raw")}
          >
            Ham Taslak
          </div>
        </div>

        <div className="mt-4">
          {activeTab === "official" ? (
            <div className="official-document">
              {officialText || <p className="text-center text-secondary mt-10">Resmî görünüm mevcut değil.</p>}
            </div>
          ) : (
            <textarea 
              readOnly 
              value={rawDraftText || "Ham taslak mevcut değil."}
              style={{ minHeight: '400px', backgroundColor: '#fff' }}
            />
          )}
        </div>
      </div>
    </div>
  );
};

function formatDraftType(type: string): string {
  switch(type) {
    case "cevap_yazisi": return "Cevap Yazısı";
    case "ust_yazi": return "Üst Yazı";
    case "bilgilendirme_metni": return "Bilgilendirme Metni";
    case "eksik_bilgi_talebi": return "Eksik Bilgi Talebi";
    default: return type.replace(/_/g, ' ').toUpperCase();
  }
}

