import React from "react";
import { DocumentState } from "../types";
import { AnalysisCard } from "./cards/AnalysisCard";
import { SummaryCard } from "./cards/SummaryCard";
import { ExtractionCard } from "./cards/ExtractionCard";
import { MissingFieldsCard } from "./cards/MissingFieldsCard";
import { LegalCard } from "./cards/LegalCard";
import { RoutingCard } from "./cards/RoutingCard";
import { OfficialDraftPanel } from "./cards/OfficialDraftPanel";
import { QualityFormatCard } from "./cards/QualityFormatCard";
import { HumanReviewPanel } from "./cards/HumanReviewPanel";

interface Props {
  state: DocumentState;
  onUpdate: () => void;
}

export const Dashboard: React.FC<Props> = ({ state, onUpdate }) => {
  return (
    <div className="dashboard-grid">
      {/* Sol Kolon */}
      <div className="flex-col">
        <AnalysisCard document={state.document} documentId={state.document_id} />
        <SummaryCard summary={state.summary} />
        <ExtractionCard extraction={state.extraction} />
        <MissingFieldsCard missingFields={state.missing_fields} />
        <LegalCard legalAnalysis={state.legal_analysis} />
      </div>

      {/* Sağ Kolon */}
      <div className="flex-col">
        <RoutingCard routing={state.routing} />
        <OfficialDraftPanel draft={state.draft} />
        <QualityFormatCard quality={state.quality} />
        <HumanReviewPanel 
          review={state.human_review} 
          analysisId={state.analysis_id || state.document_id} 
          onUpdate={onUpdate}
        />
      </div>
    </div>
  );
};
