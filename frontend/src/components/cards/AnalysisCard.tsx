import React from "react";
import { Info, FileSearch, Hash } from "lucide-react";
import { DocumentInfo } from "../../types";

interface Props {
  document: DocumentInfo;
  documentId?: string;
}

export const AnalysisCard: React.FC<Props> = ({ document, documentId }) => {
  if (!document || Object.keys(document).length === 0) {
    return (
      <div className="card mb-4">
        <div className="card-header"><Info size={18}/> Evrak Analizi</div>
        <div className="card-body">
          <p className="text-secondary">Analiz bilgisi bulunamadı.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card mb-4">
      <div className="card-header"><Info size={18}/> Evrak Analizi</div>
      <div className="card-body">
        <div className="flex-col gap-4">
          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-secondary flex items-center gap-2"><FileSearch size={16}/> Evrak Türü</span>
            <span className="font-medium">{document.document_type || "Belirsiz"}</span>
          </div>
          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-secondary flex items-center gap-2"><Info size={16}/> İşlem Niyeti</span>
            <span className="font-medium">{document.process_intent || "Belirsiz"}</span>
          </div>
          {documentId && (
            <div className="flex justify-between items-center pb-2">
              <span className="text-secondary flex items-center gap-2"><Hash size={16}/> Belge ID</span>
              <span className="text-sm font-mono bg-gray-100 px-2 py-1 rounded">{documentId}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
