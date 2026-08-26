import React, { useState } from "react";
import { Book, ChevronDown, ChevronUp } from "lucide-react";
import { LegalAnalysis } from "../../types";

interface Props {
  legalAnalysis: LegalAnalysis;
}

export const LegalCard: React.FC<Props> = ({ legalAnalysis }) => {
  const rawEvidence = legalAnalysis?.evidence || [];
  const sources = Array.isArray(legalAnalysis?.sources) ? legalAnalysis.sources : [];
  const evidence = rawEvidence.map((entry: any, index: number) => {
    const value = typeof entry === "string" ? { evidence: entry } : entry;
    const sourceRef = typeof value?.source === "string" ? /^K(d+)$/i.exec(value.source) : null;
    const sourceIndex = sourceRef ? Number(sourceRef[1]) - 1 : index;
    const source = sources[sourceIndex] || {};
    return { ...source, ...value, text: value?.evidence || value?.text || source?.text };
  });

  if (evidence.length === 0) {
    return (
      <div className="card mb-4">
        <div className="card-header"><Book size={18}/> İlgili Mevzuat</div>
        <div className="card-body">
          <p className="text-secondary">Bu evrak için doğrulanmış mevzuat eşleşmesi bulunamadı.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card mb-4">
      <div className="card-header"><Book size={18}/> İlgili Mevzuat</div>
      <div className="card-body p-0">
        <div className="flex-col">
          {evidence.map((item, i) => (
            <LegalEvidenceItem key={i} item={item} isLast={i === evidence.length - 1} />
          ))}
        </div>
      </div>
    </div>
  );
};

const LegalEvidenceItem: React.FC<{ item: any, isLast: boolean }> = ({ item, isLast }) => {
  const [expanded, setExpanded] = useState(false);
  
  const title = item.law_name || item.title || item.document_id || item.source || "Mevzuat Maddesi";
  const num = item.law_number || "";
  const article = item.article || item.madde_no || "";

  return (
    <div className={`p-4 ${!isLast ? "border-b" : ""}`}>
      <div className="flex justify-between items-start mb-2">
        <div>
          <h4 className="font-medium text-primary">
            {title} {num ? `(${num})` : ""}
          </h4>
          {article && <p className="text-sm font-medium">Madde {article}</p>}
        </div>
        {item.score && (
          <div className="badge badge-info">
            Eşleşme: %{Math.round(item.score * 100)}
          </div>
        )}
      </div>
      
      {item.text && (
        <div className="mt-2 text-sm text-secondary">
          <p>
            {expanded ? item.text : `${item.text.substring(0, 150)}...`}
          </p>
          {item.text.length > 150 && (
            <button 
              className="text-primary hover:underline text-xs mt-1 flex items-center"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? <><ChevronUp size={14}/> Daralt</> : <><ChevronDown size={14}/> Devamını Gör</>}
            </button>
          )}
        </div>
      )}
    </div>
  );
};
