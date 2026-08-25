import React from "react";
import { AlertCircle, CheckCircle } from "lucide-react";
import { MissingFields } from "../../types";

interface Props {
  missingFields: MissingFields;
}

export const MissingFieldsCard: React.FC<Props> = ({ missingFields }) => {
  const fields = missingFields?.missing_fields || [];
  
  if (fields.length === 0) {
    return (
      <div className="card mb-4 missing-fields-state missing-fields-success">
        <div className="card-header">
          <CheckCircle size={18}/> Eksik Bilgi Kontrolü
        </div>
        <div className="card-body">
          <p>Belgede zorunlu eksik bilgi tespit edilmedi.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card mb-4 missing-fields-state missing-fields-danger">
      <div className="card-header">
        <AlertCircle size={18}/> Eksik Bilgiler
      </div>
      <div className="card-body">
        <ul style={{ listStyleType: "disc", paddingLeft: "1.5rem" }} className="mb-4 text-error">
          {fields.map((f, i) => (
            <li key={i}>{f}</li>
          ))}
        </ul>
        {missingFields.needs_human_review && (
          <div className="badge badge-warning">
            Personel incelemesi gerekli
          </div>
        )}
      </div>
    </div>
  );
};
