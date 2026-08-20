import React from "react";
import { ShieldAlert, Check, X, AlertTriangle } from "lucide-react";
import { QualityInfo } from "../../types";

interface Props {
  quality: QualityInfo;
}

export const QualityFormatCard: React.FC<Props> = ({ quality }) => {
  if (!quality || Object.keys(quality).length === 0) {
    return null; // Don't show if not processed yet
  }

  const isPass = quality.status === "PASS";
  const isWarning = quality.status === "WARNING";
  const isFail = quality.status === "FAIL";

  let statusText = "Bilinmiyor";
  let badgeClass = "badge-neutral";
  
  if (isPass) {
    statusText = "Uygun";
    badgeClass = "badge-success";
  } else if (isWarning) {
    statusText = "Kontrol Gerekli";
    badgeClass = "badge-warning";
  } else if (isFail) {
    statusText = "Hata Tespit Edildi";
    badgeClass = "badge-error";
  }

  return (
    <div className="card mb-4">
      <div className="card-header flex justify-between items-center w-full">
        <div className="flex items-center gap-2">
          <ShieldAlert size={18}/> Resmî Yazışma Kontrolü
        </div>
        <div className={`badge ${badgeClass}`}>
          Format Durumu: {statusText}
        </div>
      </div>
      <div className="card-body p-0">
        <ul className="divide-y divide-gray-200">
          {(quality.issues || []).map((issue, idx) => (
            <li key={idx} className="p-3 flex items-start gap-3 text-sm">
              <div className="mt-0.5">
                {issue.severity === "critical" ? (
                  <X size={16} className="text-error" />
                ) : issue.severity === "warning" ? (
                  <AlertTriangle size={16} className="text-warning" />
                ) : (
                  <Check size={16} className="text-success" />
                )}
              </div>
              <div>
                <span className="font-medium text-primary block">{issue.field}</span>
                <span className="text-secondary">{issue.issue}</span>
              </div>
            </li>
          ))}
          {(!quality.issues || quality.issues.length === 0) && isPass && (
            <li className="p-4 text-center text-success flex justify-center items-center gap-2">
              <Check size={18} /> Tüm resmî yazışma kuralları (kurum başlığı, tarih, sayı) uygun.
            </li>
          )}
        </ul>
      </div>
    </div>
  );
};
