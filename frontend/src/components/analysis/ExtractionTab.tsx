import React, { useState } from 'react';
import { AnalysisResponse } from '../../types/analysis';
import { getLabel, FIELD_LABELS } from '../../utils/labels';
import { maskPII } from '../../utils/formatters';
import { Eye, EyeOff } from 'lucide-react';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';

export function ExtractionTab({ analysis }: { analysis: AnalysisResponse }) {
  const extraction = analysis?.extraction || {};
  const fields = extraction.fields || {};
  const unknown_fields = extraction.unknown_fields || [];
  const missing_fields = extraction.missing_fields || [];
  
  const [showMask, setShowMask] = useState(true);

  // Group all fields
  const allKeys = Array.from(new Set([
    ...Object.keys(fields),
    ...unknown_fields,
    ...missing_fields
  ]));

  const formatValue = (val: any): string => {
    if (val === null || val === undefined) return "";
    if (typeof val === 'boolean') return val ? "Evet" : "Hayır";
    if (Array.isArray(val)) return val.map(formatValue).join(", ");
    if (typeof val === 'object') return formatValue(val.value || val.text || JSON.stringify(val));
    return String(val);
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-between items-center">
        <h3 className="font-semibold text-text-heading">Çıkarılan Bilgiler</h3>
        <Button 
          variant="secondary"
          className="text-xs py-1"
          onClick={() => setShowMask(!showMask)}
        >
          {showMask ? <><Eye size={14}/> PII Gizlemeyi Kaldır</> : <><EyeOff size={14}/> PII Gizle</>}
        </Button>
      </div>
      
      <div className="bg-bg-color border border-border-color rounded-md overflow-hidden">
        {allKeys.length === 0 ? (
          <div className="p-6 text-center text-muted text-sm">
            Çıkarılan bilgi bulunamadı.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-sidebar-bg/5 border-b border-border-color text-muted text-left">
                <th className="px-4 py-3 font-medium">Alan Adı</th>
                <th className="px-4 py-3 font-medium">Çıkarılan Değer</th>
                <th className="px-4 py-3 font-medium w-32">Durum</th>
              </tr>
            </thead>
            <tbody>
              {allKeys.map(key => {
                let rawValue = fields[key];
                let valueStr = formatValue(rawValue);

                let statusNode;
                
                if (missing_fields.includes(key)) {
                  valueStr = "Bulunamadı";
                  statusNode = <Badge status="fail">Eksik</Badge>;
                } else if (unknown_fields.includes(key)) {
                  valueStr = "Metin üzerinden doğrulanamadı";
                  statusNode = <Badge status="warning">Belirsiz</Badge>;
                } else {
                  valueStr = maskPII(valueStr, key, showMask);
                  statusNode = <Badge status="success">Mevcut</Badge>;
                }

                const isMuted = missing_fields.includes(key) || unknown_fields.includes(key);

                return (
                  <tr key={key} className="border-b border-border-light hover:bg-white transition-colors">
                    <td className="px-4 py-3 font-medium text-text-main">
                      {getLabel(key, FIELD_LABELS)}
                    </td>
                    <td className={`px-4 py-3 ${isMuted ? 'text-muted italic' : 'text-text-main'}`}>
                      {valueStr}
                    </td>
                    <td className="px-4 py-3">
                      {statusNode}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}


