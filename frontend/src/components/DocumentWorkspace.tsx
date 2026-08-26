import React, { useState } from "react";
import type { DocumentState } from "../types";
import { AnalysisPanel } from "./AnalysisPanel";
import { AIProcessPanel } from "./AIProcessPanel";
import { DecisionSummary } from "./DecisionSummary";
import { AuditDrawer } from "./AuditDrawer";
import { DocumentPreview } from "./DocumentPreview";
import { DocumentToolbar } from "./DocumentToolbar";

interface Props {
  state: DocumentState;
  onUpdate: () => void | Promise<void>;
}

export const DocumentWorkspace: React.FC<Props> = ({ state, onUpdate }) => {
  const [auditOpen, setAuditOpen] = useState(false);
  const hasDocument = Boolean(
    state.draft?.mod_c_validated_context
      || (typeof state.draft?.official_render === "object" && state.draft.official_render?.context)
      || state.draft?.official_rendered_text,
  );

  return (
    <>
      <DecisionSummary state={state} />
      <AIProcessPanel state={state} />
      <div className="document-workspace">
        <main className="document-column">
          <DocumentToolbar
            analysisId={state.analysis_id}
            hasDocument={hasDocument}
            reviewStatus={state.human_review?.status}
            copyText={state.draft?.official_rendered_text || state.draft?.draft_text || state.draft?.draft?.body}
            onOpenAudit={() => setAuditOpen(true)}
          />
          <p className="draft-disclaimer">AI tarafından oluşturulan taslak. Resmî işlem öncesinde personel kontrolü gerektirir.</p>
          <DocumentPreview draft={state.draft} analysisId={state.analysis_id} />
        </main>
        <AnalysisPanel state={state} onUpdate={onUpdate} />
      </div>
      <AuditDrawer open={auditOpen} events={state.audit_history || []} onClose={() => setAuditOpen(false)} />
    </>
  );
};
