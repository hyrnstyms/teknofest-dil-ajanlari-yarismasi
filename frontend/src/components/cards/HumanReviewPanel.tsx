import React, { useState } from "react";
import { UserCheck, Check, Edit3, X } from "lucide-react";
import { HumanReview } from "../../types";
import { api } from "../../services/api";

interface Props {
  review: HumanReview;
  analysisId: string;
  onUpdate: () => void;
  onEdit?: () => void;
}

export const HumanReviewPanel: React.FC<Props> = ({ review, analysisId, onUpdate, onEdit }) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [showRejectForm, setShowRejectForm] = useState(false);

  const handleApprove = async () => {
    setIsSubmitting(true);
    try {
      await api.approveAnalysis(analysisId);
      onUpdate();
    } catch {
      alert("Onaylanırken hata oluştu.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      alert("Lütfen ret gerekçesi giriniz.");
      return;
    }
    setIsSubmitting(true);
    try {
      await api.rejectAnalysis(analysisId, rejectReason);
      onUpdate();
    } catch {
      alert("Reddedilirken hata oluştu.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (review.status === "approved") {
    return (
      <div className="card mb-4" style={{ borderColor: "var(--success-color)", backgroundColor: "#f0fdf4" }}>
        <div className="card-body flex items-center justify-center gap-2 text-success font-medium">
          <Check size={20} /> Personel tarafından onaylandı.
        </div>
      </div>
    );
  }

  if (review.status === "rejected") {
    return (
      <div className="card mb-4" style={{ borderColor: "var(--error-color)", backgroundColor: "#fef2f2" }}>
        <div className="card-body flex-col text-error font-medium">
          <div className="flex items-center gap-2 mb-2">
            <X size={20} /> Reddedildi
          </div>
          <div className="text-sm font-normal text-secondary bg-white p-3 rounded">
            <strong>Gerekçe:</strong> {review.reject_reason}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card mb-4 border-2" style={{ borderColor: "var(--warning-color)" }}>
      <div className="card-header bg-yellow-50" style={{ color: "#92400e" }}>
        <UserCheck size={18} />
        {review?.required ? "Personel Onayı Gerekiyor" : "Personel Kararı"}
      </div>
      <div className="card-body">
        {showRejectForm ? (
          <div className="flex-col gap-4">
            <textarea 
              placeholder="Ret gerekçesini yazınız..."
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              style={{ minHeight: '80px' }}
              disabled={isSubmitting}
            />
            <div className="flex gap-2 justify-end">
              <button 
                className="btn btn-secondary" 
                onClick={() => setShowRejectForm(false)}
                disabled={isSubmitting}
              >
                İptal
              </button>
              <button 
                className="btn btn-danger" 
                onClick={handleReject}
                disabled={isSubmitting}
              >
                {isSubmitting ? "Kaydediliyor..." : "Reddet"}
              </button>
            </div>
          </div>
        ) : (
          <div className="flex justify-center gap-4">
            {onEdit && (
              <button
                className="btn btn-secondary"
                onClick={onEdit}
                disabled={isSubmitting}
              >
                <Edit3 size={18}/> Düzenle
              </button>
            )}
            <button 
              className="btn btn-success" 
              onClick={handleApprove}
              disabled={isSubmitting}
            >
              {isSubmitting ? "İşleniyor..." : <><Check size={18}/> Onayla</>}
            </button>
            <button 
              className="btn btn-danger" 
              onClick={() => setShowRejectForm(true)}
              disabled={isSubmitting}
            >
              <X size={18}/> Reddet
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
