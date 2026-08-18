import React, { useState } from 'react';
import { AnalysisResponse } from '../../types/analysis';
import { approveAnalysis, editAnalysis, rejectAnalysis } from '../../services/analysis';
import { getLabel, STATUS_LABELS } from '../../utils/labels';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { FileSignature, CheckCircle2, XCircle, Edit3 } from 'lucide-react';

interface DraftPanelProps {
  analysis: AnalysisResponse;
  onUpdate: () => void;
}

export function DraftPanel({ analysis, onUpdate }: DraftPanelProps) {
  const human_review = analysis?.human_review || {} as any;
  const draft = analysis?.draft || {} as any;
  
  const [isEditing, setIsEditing] = useState(false);
  const displaySubject = draft?.edited_draft?.subject || draft?.subject || draft?.draft?.subject || "";
  const displayBody = draft?.edited_draft?.body || draft?.rendered_text || draft?.draft_text || "";
  
  const [editSubject, setEditSubject] = useState(displaySubject);
  const [editBody, setEditBody] = useState(displayBody);
  const [isRejecting, setIsRejecting] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleApprove = async () => {
    if (confirm("Bu işlem yapay zeka tarafından oluşturulan analiz ve taslağı personel onayıyla işaretleyecektir. Onaylıyor musunuz?")) {
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

  const getStatusBadge = (status: string) => {
    if (status === 'approved') return <Badge status="success">Onaylandı</Badge>;
    if (status === 'rejected') return <Badge status="fail">Reddedildi</Badge>;
    if (status === 'edited') return <Badge status="info">Düzenlendi</Badge>;
    return <Badge status="warning">İnceleme Bekliyor</Badge>;
  };

  const officialMissingFields = Array.isArray(draft?.official_render?.missing_fields) 
    ? draft.official_render.missing_fields 
    : [];

  return (
    <div className="flex flex-col gap-4 h-full">
      
      {/* Draft Content Card */}
      <div className="bg-card-bg border border-border-color rounded-md flex flex-col flex-1 shadow-sm">
        <div className="p-4 border-b border-border-color bg-bg-color flex justify-between items-center">
          <div className="flex items-center gap-2 text-primary font-semibold">
            <FileSignature size={18} />
            <h3>Resmî Yazı Taslağı</h3>
          </div>
          <Badge status="info">TASLAK</Badge>
        </div>
        
        <div className="p-4 flex-1 flex flex-col overflow-y-auto">
          {displayBody ? (
            <div className="flex flex-col h-full gap-4">
              {isEditing ? (
                <div className="flex flex-col gap-4 h-full">
                  <div className="flex flex-col gap-1">
                    <label className="text-sm font-medium text-text-main">Konu</label>
                    <input 
                      className="form-control text-sm" 
                      value={editSubject} 
                      onChange={e => setEditSubject(e.target.value)} 
                    />
                  </div>
                  <div className="flex flex-col gap-1 flex-1">
                    <label className="text-sm font-medium text-text-main">Metin</label>
                    <textarea 
                      className="form-control text-sm font-mono flex-1 resize-none" 
                      value={editBody} 
                      onChange={e => setEditBody(e.target.value)} 
                    />
                  </div>
                  <div className="flex justify-end gap-2 mt-2">
                    <Button variant="secondary" onClick={() => setIsEditing(false)} disabled={isSubmitting}>İptal</Button>
                    <Button variant="primary" onClick={handleSaveEdit} disabled={isSubmitting}>Kaydet</Button>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col gap-4">
                  <div>
                    <h4 className="text-xs font-semibold text-muted uppercase tracking-wider mb-1">Konu</h4>
                    <p className="text-sm font-medium">{displaySubject}</p>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-muted uppercase tracking-wider mb-1">Metin</h4>
                    <div className="bg-bg-color p-4 rounded-md text-sm border border-border-light whitespace-pre-wrap font-serif leading-relaxed">
                      {displayBody}
                    </div>
                  </div>
                  
                  {human_review.original_draft && human_review.status === 'edited' && (
                    <div className="text-xs text-muted italic mt-2 border-l-2 border-info pl-2">
                      * Bu taslak personel tarafından düzenlenmiştir.
                    </div>
                  )}
                  {officialMissingFields.length > 0 && (
                    <div className="text-xs text-warning bg-warning-light p-2 rounded-md mt-2">
                      <strong>Uyarı:</strong> Format motoru şablonu tam dolduramadı (Eksik: {officialMissingFields.join(", ")})
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center text-muted gap-2">
              <FileSignature size={32} className="opacity-50" />
              <p className="text-sm">Taslak oluşturulamadı.<br/>Yeterli işlem bilgisi veya mevzuat dayanağı bulunmuyor olabilir.</p>
            </div>
          )}
        </div>
      </div>

      {/* Action Card */}
      <div className="bg-card-bg border border-border-color rounded-md shadow-sm">
        <div className="p-4 border-b border-border-color bg-bg-color flex justify-between items-center">
          <h3 className="font-semibold text-sm">Personel İncelemesi</h3>
          {getStatusBadge(human_review?.status)}
        </div>

        <div className="p-4">
          {isRejecting ? (
            <div className="flex flex-col gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-xs font-medium text-text-main">Red Gerekçesi</label>
                <textarea 
                  className="form-control text-sm resize-none" 
                  rows={3} 
                  value={rejectReason}
                  onChange={e => setRejectReason(e.target.value)}
                  placeholder="Lütfen reddetme gerekçenizi yazın..."
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="secondary" onClick={() => setIsRejecting(false)} disabled={isSubmitting}>İptal</Button>
                <Button variant="danger" onClick={handleReject} disabled={isSubmitting || !rejectReason.trim()}>Reddet</Button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              <Button 
                variant="primary" 
                className="w-full justify-center bg-success hover:bg-success/90 border-none"
                onClick={handleApprove}
                disabled={isSubmitting || human_review.status === 'approved'}
              >
                <CheckCircle2 size={16} /> Onayla
              </Button>
              <div className="flex gap-3">
                <Button 
                  variant="secondary" 
                  className="flex-1 justify-center"
                  onClick={() => setIsEditing(true)}
                  disabled={isSubmitting || isEditing || !displayBody || human_review.status === 'approved'}
                >
                  <Edit3 size={16} /> Düzenle
                </Button>
                <Button 
                  variant="secondary" 
                  className="flex-1 justify-center text-danger hover:text-danger hover:bg-danger-light hover:border-danger"
                  onClick={() => setIsRejecting(true)}
                  disabled={isSubmitting || human_review.status === 'rejected'}
                >
                  <XCircle size={16} /> Reddet
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

    </div>
  );
}

