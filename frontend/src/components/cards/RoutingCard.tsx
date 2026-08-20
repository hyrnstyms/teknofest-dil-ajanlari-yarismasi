import React from "react";
import { ArrowRightCircle, ShieldCheck } from "lucide-react";
import { RoutingInfo } from "../../types";

interface Props {
  routing: RoutingInfo;
}

export const RoutingCard: React.FC<Props> = ({ routing }) => {
  if (!routing?.recommended_unit) {
    return (
      <div className="card mb-4">
        <div className="card-header"><ArrowRightCircle size={18}/> Birim Yönlendirme</div>
        <div className="card-body">
          <p className="text-secondary">Yönlendirme önerisi üretilemedi.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card mb-4 border-2" style={{ borderColor: "var(--secondary-color)" }}>
      <div className="card-header bg-blue-50 text-primary">
        <ArrowRightCircle size={18}/> Birim Yönlendirme
      </div>
      <div className="card-body">
        <div className="text-center mb-6">
          <h2 className="text-2xl font-bold text-primary mb-2">
            {routing.recommended_unit}
          </h2>
          {routing.confidence && (
            <div className="badge badge-success" style={{ fontSize: '0.875rem', padding: '0.25rem 0.75rem' }}>
              <ShieldCheck size={16}/> Güven Skoru: %{Math.round(routing.confidence * 100)}
            </div>
          )}
        </div>
        
        {routing.reason && (
          <div className="bg-gray-50 p-4 rounded-md text-sm text-secondary">
            <strong>Gerekçe:</strong> {routing.reason}
          </div>
        )}
      </div>
    </div>
  );
};
