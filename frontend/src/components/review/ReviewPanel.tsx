import React, { useState } from 'react';
import { AnalysisResponse } from '../../types/analysis';
import { approveAnalysis, editAnalysis, rejectAnalysis } from '../../services/analysis';
import { getLabel, STATUS_LABELS } from '../../utils/labels';

interface ReviewPanelProps {
  analysis: AnalysisResponse;
  onUpdate: () => void;
}

export function ReviewPanel({ analysis, onUpdate }: ReviewPanelProps) {
  const human_review = analysis.human_review || {} as any;
  const draft = analysis.draft || {} as any;
  const [isEditing, setIsEditing] = useState(false);
  const displaySubject = draft?.edited_draft?.subject || draft?.subject || draft?.draft?.subject || "";
  const displayBody = draft?.edited_draft?.body || draft?.rendered_text || draft?.draft_text || "";
  
  const [editSubject, setEditSubject] = useState(displaySubject);
  const [editBody, setEditBody] = useState(displayBody);
  const [isRejecting, setIsRejecting] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleApprove = async () => {
    if (confirm("Bu işlem yapay zekâ tarafından oluşturulan analiz ve taslağı personel onayıyla işaretleyecektir. Onaylıyor musunuz?")) {
      setIsSubmitting(true);
      try {
        await approveAnalysis(analysis.analysis_id);
        alert("Analiz ve taslak onaylandı.");
        onUpdate();
      } catch (e: any) {
        alert(e.message);
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  const handleSaveEdit = async () => {
    setIsSubmitting(true);
    try {
      await editAnalysis(analysis.analysis_id, editSubject, editBody);
      alert("Yaptığınız düzenlemeler kaydedildi.");
      setIsEditing(false);
      onUpdate();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    setIsSubmitting(true);
    try {
      await rejectAnalysis(analysis.analysis_id, rejectReason);
      alert("Taslak reddedildi.");
      setIsRejecting(false);
      onUpdate();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', height: '100%' }}>
      
      <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', marginBottom: 0 }}>
        <div className="card-header">
          <h3 className="card-title">Resmî Yazı Taslağı</h3>
          <span className="badge badge-blue">TASLAK</span>
        </div>
        
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
          Yetkili personel onayı gerektirir.
        </div>

        {displayBody ? (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            {isEditing ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', flex: 1 }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Konu</label>
                  <input 
                    className="form-control" 
                    value={editSubject} 
                    onChange={e => setEditSubject(e.target.value)} 
                  />
                </div>
                <div className="form-group" style={{ flex: 1, marginBottom: 0, display: 'flex', flexDirection: 'column' }}>
                  <label className="form-label">Metin</label>
                  <textarea 
                    className="form-control" 
                    style={{ flex: 1 }}
                    value={editBody} 
                    onChange={e => setEditBody(e.target.value)} 
                  />
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                  <button className="btn btn-outline" onClick={() => setIsEditing(false)} disabled={isSubmitting}>İptal</button>
                  <button className="btn btn-primary" onClick={handleSaveEdit} disabled={isSubmitting}>Kaydet</button>
                </div>
              </div>
            ) : (
              <div>
                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-muted)' }}>Konu</div>
                  <div style={{ fontWeight: 500 }}>{displaySubject}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Metin</div>
                  <div style={{ 
                    whiteSpace: 'pre-wrap', 
                    backgroundColor: 'var(--bg-color)', 
                    padding: '1rem', 
                    borderRadius: '6px',
                    fontSize: '0.875rem',
                    border: '1px solid var(--border-color)'
                  }}>
                    {displayBody}
                  </div>
                </div>
                
                {human_review.original_draft && human_review.status === 'edited' && (
                  <div style={{ marginTop: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    * Bu taslak personel tarafından düzenlenmiştir. Orijinal yapay zekâ taslağı sistemde korunmaktadır.
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="alert alert-warning">
            <strong>Taslak oluşturulamadı.</strong><br/>
            Güvenilir bir resmî yazı hazırlamak için ek işlem bilgisi veya mevzuat dayanağı gerekiyor.
          </div>
        )}
      </div>

      <div className="card" style={{ marginBottom: 0 }}>
        <div className="card-header">
          <h3 className="card-title">Personel İncelemesi</h3>
          <span style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--primary)' }}>
            {getLabel(human_review?.status, STATUS_LABELS)}
          </span>
        </div>

        {isRejecting ? (
          <div>
            <div className="form-group">
              <label className="form-label">Red Gerekçesi</label>
              <textarea 
                className="form-control" 
                rows={3} 
                value={rejectReason}
                onChange={e => setRejectReason(e.target.value)}
                placeholder="Lütfen reddetme gerekçenizi yazın..."
              />
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
              <button className="btn btn-outline" onClick={() => setIsRejecting(false)} disabled={isSubmitting}>İptal</button>
              <button className="btn btn-danger" onClick={handleReject} disabled={isSubmitting || !rejectReason.trim()}>Reddet</button>
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <button 
              className="btn btn-success" 
              onClick={handleApprove}
              disabled={isSubmitting || human_review.status === 'approved'}
            >
              Onayla
            </button>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button 
                className="btn btn-outline" 
                style={{ flex: 1 }}
                onClick={() => setIsEditing(true)}
                disabled={isSubmitting || isEditing || !displayBody || human_review.status === 'approved'}
              >
                Düzenle
              </button>
              <button 
                className="btn btn-outline" 
                style={{ flex: 1, color: 'var(--danger)', borderColor: 'var(--danger)' }}
                onClick={() => setIsRejecting(true)}
                disabled={isSubmitting || human_review.status === 'rejected'}
              >
                Reddet
              </button>
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
