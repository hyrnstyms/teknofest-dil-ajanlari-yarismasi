import React, { useState } from 'react';
import { AnalysisResponse } from '../../types/analysis';
import { getLabel, FIELD_LABELS } from '../../utils/labels';
import { maskPII } from '../../utils/formatters';
import { Eye, EyeOff } from 'lucide-react';

export function ExtractionTab({ analysis }: { analysis: AnalysisResponse }) {
  const { fields, unknown_fields, missing_fields } = analysis.extraction;
  const [showMask, setShowMask] = useState(true);

  // Group all fields
  const allKeys = Array.from(new Set([
    ...Object.keys(fields || {}),
    ...(unknown_fields || []),
    ...(missing_fields || [])
  ]));

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h4 style={{ fontSize: '1rem', color: 'var(--primary)' }}>Çıkarılan Bilgiler</h4>
        <button 
          className="btn btn-outline" 
          style={{ padding: '0.25rem 0.75rem', fontSize: '0.75rem' }}
          onClick={() => setShowMask(!showMask)}
        >
          {showMask ? <><Eye size={14}/> Detayı Göster</> : <><EyeOff size={14}/> Gizle</>}
        </button>
      </div>
      
      <div className="data-list">
        {allKeys.map(key => {
          let valueStr = fields[key] || "";
          let statusLabel = "";
          
          if ((missing_fields || []).includes(key)) {
            valueStr = "Bulunamadı";
            statusLabel = "Eksik";
          } else if ((unknown_fields || []).includes(key)) {
            valueStr = "Metin üzerinden doğrulanamadı";
            statusLabel = "Belirsiz";
          } else {
            valueStr = maskPII(valueStr, key, showMask);
            statusLabel = "Mevcut";
          }

          return (
            <div className="data-row" key={key}>
              <div className="data-label">{getLabel(key, FIELD_LABELS)}</div>
              <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.25rem' }}>
                <div className="data-value" style={{ 
                  color: (missing_fields || []).includes(key) || (unknown_fields || []).includes(key) ? 'var(--text-muted)' : 'inherit',
                  fontStyle: (missing_fields || []).includes(key) || (unknown_fields || []).includes(key) ? 'italic' : 'normal'
                }}>
                  {valueStr}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
