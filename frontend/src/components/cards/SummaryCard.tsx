import React from "react";
import { AlignLeft } from "lucide-react";
import { SummaryInfo } from "../../types";

interface Props {
  summary: SummaryInfo;
}

export const SummaryCard: React.FC<Props> = ({ summary }) => {
  if (!summary?.short_summary) {
    return null;
  }

  return (
    <div className="card mb-4">
      <div className="card-header"><AlignLeft size={18}/> Kısa Özet</div>
      <div className="card-body">
        <p className="text-sm" style={{ lineHeight: 1.6 }}>
          {summary.short_summary}
        </p>
      </div>
    </div>
  );
};
