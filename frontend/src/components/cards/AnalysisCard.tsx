import React from "react";
import { Info, FileSearch } from "lucide-react";
import { DocumentInfo } from "../../types";
import { formatDocumentType, formatIntent } from "../../utils/presentation";

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
            <span className="font-medium">{formatDocumentType(document.document_type)}</span>
          </div>
          <div className="flex justify-between items-center border-b pb-2">
            <span className="text-secondary flex items-center gap-2"><Info size={16}/> İşlem Niyeti</span>
            <span className="font-medium">{formatIntent(document.process_intent)}</span>
          </div>

        </div>
      </div>
    </div>
  );
};
