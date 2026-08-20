import React from "react";
import { List, Check } from "lucide-react";
import { ExtractionInfo } from "../../types";

interface Props {
  extraction: ExtractionInfo;
}

export const ExtractionCard: React.FC<Props> = ({ extraction }) => {
  if (!extraction?.fields || Object.keys(extraction.fields).length === 0) {
    return (
      <div className="card mb-4">
        <div className="card-header"><List size={18}/> Çıkarılan Bilgiler</div>
        <div className="card-body">
          <p className="text-secondary">Çıkarılan bilgi bulunamadı.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card mb-4">
      <div className="card-header"><List size={18}/> Çıkarılan Bilgiler</div>
      <div className="card-body p-0">
        <table className="data-table">
          <tbody>
            {Object.entries(extraction.fields).map(([key, value]) => (
              <tr key={key}>
                <th>{formatKey(key)}</th>
                <td>
                  {value ? (
                    <span className="font-medium">{value.toString()}</span>
                  ) : (
                    <span className="text-secondary text-sm">Belirtilmemiş</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

function formatKey(key: string): string {
  return key
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
