import React, { useState } from "react";
import { UserCheck, Check, Edit3, X, Send } from "lucide-react";
import { HumanReview, TransferRouting } from "../../types";
import { api } from "../../services/api";

interface Props {
  review: HumanReview;
  analysisId: string;
  onUpdate: () => void | Promise<void>;
  onEdit?: () => void;
  transferRouting?: TransferRouting;
}

export const HumanReviewPanel: React.FC<Props> = ({
  review,
  analysisId,
  onUpdate,
  onEdit,
  transferRouting,
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [isTransferring, setIsTransferring] = useState(false);
  const [transferResult, setTransferResult] = useState<string | null>(null);
  const [transferError, setTransferError] = useState<string | null>(null);

  const handleApprove = async () => {
    setIsSubmitting(true);
    try {
      await api.approveAnalysis(analysisId);
      await onUpdate();
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
      await onUpdate();
    } catch {
      alert("Reddedilirken hata oluştu.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTransfer = async () => {
    setIsTransferring(true);
    setTransferError(null);
    setTransferResult(null);
    try {
      const result = await api.transferAnalysis(analysisId);
      setTransferResult(result.message || "Evrak başarıyla iletildi.");
      await onUpdate();
    } catch (err: any) {
      setTransferError(err.message || "İletim sırasında hata oluştu.");
    } finally {
      setIsTransferring(false);
    }
  };

  if (review.status === "approved") {
    const showTransferBtn =
      transferRouting?.transfer_required === true &&
      !transferRouting?.ebys_routed;

    const hedefAdi =
      transferRouting?.hedef_kurum_adi ||
      transferRouting?.hedef_kurum ||
      "Kuruma";

    return (
      <div className="card mb-4" style={{ borderColor: "var(--success-color)", backgroundColor: "#f0fdf4" }}>
        <div className="card-body flex-col gap-3">
          <div className="flex items-center justify-center gap-2 text-success font-medium">
            <Check size={20} /> Personel tarafından onaylandı.
          </div>

          {/* Transfer butonu — sadece transfer_required true ise görünür */}
          {showTransferBtn && (
            <div className="flex flex-col items-center gap-2">
              <button
                className="btn btn-primary"
                onClick={handleTransfer}
                disabled={isTransferring}
                style={{ gap: "6px" }}
              >
                <Send size={16} />
                {isTransferring
                  ? "Gönderiliyor..."
                  : `${hedefAdi}'ye Gönder`}
              </button>
              {transferError && (
                <div
                  className="text-sm text-error"
                  style={{ color: "var(--error-color)" }}
                >
                  ⚠ {transferError}
                </div>
              )}
            </div>
          )}

          {/* Transfer başarılı banner */}
          {(transferResult || transferRouting?.ebys_routed) && (
            <div
              className="flex items-center gap-2 text-sm font-medium"
              style={{ color: "#166534", background: "#dcfce7", padding: "8px 12px", borderRadius: "6px" }}
            >
              <Send size={14} />
              {transferResult ||
                `Evrak ${hedefAdi} / ${transferRouting?.hedef_birim || ""} birimine iletildi.`}
            </div>
          )}
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
    <div className="card mb-4 border-2 review-state review-state-warning" style={{ borderColor: "var(--warning-color)" }}>
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
