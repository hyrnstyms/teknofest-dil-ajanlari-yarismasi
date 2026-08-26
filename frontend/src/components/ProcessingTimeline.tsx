import React from "react";
import { CheckCircle2, CircleDashed, Loader2 } from "lucide-react";

interface Props {
  nodeTimings: Record<string, number | { duration_ms?: number; status?: string }>;
  isLoading: boolean;
}

const steps = [
  { id: "DocumentAgent", label: "Evrak Analizi" },
  { id: "ExtractionAgent", label: "Bilgi Çıkarımı" },
  { id: "LegalAgent", label: "Mevzuat Analizi" },
  { id: "MissingFieldAgent", label: "Eksik Kontrolü" },
  { id: "SummaryAgent", label: "Özetleme" },
  { id: "RoutingAgent", label: "Birim Yönlendirme" },
  { id: "WritingAgent", label: "Resmî Yazı Hazırlama" },
  { id: "QualityAgent", label: "Kalite Kontrol" },
];

export const ProcessingTimeline: React.FC<Props> = ({ nodeTimings, isLoading }) => {
  if (!isLoading && (!nodeTimings || Object.keys(nodeTimings).length === 0)) {
    return null; // Not started yet
  }

  return (
    <div className="card mb-6 overflow-hidden">
      <div className="card-body p-4 bg-gray-50 flex items-center justify-between" style={{ overflowX: 'auto', padding: '1.5rem' }}>
        <div className="flex items-center gap-2" style={{ minWidth: 'max-content' }}>
          {steps.map((step, idx) => {
            const timingKey = step.id.replace(/([a-z])([A-Z])/g, "$1_$2").toLowerCase();
            const rawTiming = nodeTimings ? nodeTimings[step.id] ?? nodeTimings[timingKey] : undefined;
            const timeTaken = typeof rawTiming === "number"
              ? rawTiming
              : rawTiming?.duration_ms !== undefined
                ? rawTiming.duration_ms / 1000
                : undefined;
            const isCompleted = timeTaken !== undefined;
            // Since we don't have real SSE progress for this MVP, 
            // if it's loading, we just show a generic loading state for the whole pipeline,
            // or we could show completed ones based on what we have (usually we get it all at the end).
            // For now, if isLoading is true and it's not completed, we show it as pending/loading.
            
            let status = "pending";
            if (isCompleted) status = "completed";
            else if (isLoading) status = "loading";

            return (
              <React.Fragment key={step.id}>
                <div className="flex flex-col items-center" style={{ width: '90px' }}>
                  <div className="mb-2">
                    {status === "completed" ? (
                      <CheckCircle2 size={24} className="text-success" />
                    ) : status === "loading" ? (
                      <Loader2 size={24} className="text-primary spinner" />
                    ) : (
                      <CircleDashed size={24} className="text-secondary opacity-50" />
                    )}
                  </div>
                  <div className="text-xs text-center font-medium leading-tight h-8 flex items-center justify-center">
                    {step.label}
                  </div>
                  <div className="text-[10px] text-secondary mt-1">
                    {timeTaken ? `${timeTaken.toFixed(2)} sn` : "--"}
                  </div>
                </div>
                {idx < steps.length - 1 && (
                  <div className="h-[2px] w-8 bg-gray-200 mt-[-30px]">
                    <div className={`h-full ${status === "completed" ? "bg-success" : ""}`}></div>
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
};
