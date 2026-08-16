import React from 'react';
import { AnalysisResponse } from '../../types/analysis';
import { getLabel, FIELD_LABELS } from '../../utils/labels';
import { AlertCircle, HelpCircle } from 'lucide-react';

export function MissingFieldsTab({ analysis }: { analysis: AnalysisResponse }) {
  const { missing_fields, uncertain_fields, warnings } = analysis.missing_fields;

  return (
    <div>
      <h4 style={{ fontSize: '1rem', color: 'var(--primary)', marginBottom: '1rem' }}>Eksik Bilgiler</h4>
      
      {missing_fields.length === 0 && uncertain_fields.length === 0 && (
        <div className="alert alert-success">
          Zorunlu bilgiler açısından eksik alan tespit edilmedi.
        </div>
      )}

      {missing_fields.length > 0 && (
        <div style={{ marginBottom: '1.5rem' }}>
          {missing_fields.map(field => (
            <div key={field} className="alert alert-danger" style={{ display: 'flex', alignItems: 'center' }}>
              <AlertCircle size={18} style={{ flexShrink: 0 }} />
              <div>
                <strong>Eksik Bilgi:</strong> {getLabel(field, FIELD_LABELS)}
              </div>
            </div>
          ))}
        </div>
      )}

      {uncertain_fields.length > 0 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <h5 style={{ fontSize: '0.875rem', marginBottom: '0.75rem', color: 'var(--text-main)' }}>Doğrulanması Gereken Bilgiler</h5>
          {uncertain_fields.map(field => (
            <div key={field} className="alert alert-warning" style={{ display: 'flex', alignItems: 'center' }}>
              <HelpCircle size={18} style={{ flexShrink: 0 }} />
              <div>
                <strong>{getLabel(field, FIELD_LABELS)}:</strong> Metin üzerinden doğrulanamadı.
              </div>
            </div>
          ))}
        </div>
      )}

      {warnings.length > 0 && (
        <div>
          <h5 style={{ fontSize: '0.875rem', marginBottom: '0.75rem', color: 'var(--text-main)' }}>Uyarılar</h5>
          <ul style={{ paddingLeft: '1.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            {warnings.map((w, i) => (
              <li key={i} style={{ marginBottom: '0.25rem' }}>{w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
