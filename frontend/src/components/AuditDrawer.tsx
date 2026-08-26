import React from "react";
import { CheckCircle2, Clock3, FilePenLine, X, XCircle } from "lucide-react";
import type { AuditEvent } from "../types";

interface Props {
  open: boolean;
  events: AuditEvent[];
  onClose: () => void;
}

const eventLabels: Record<string, string> = {
  analysis_completed: "Analiz tamamlandı",
  approved: "Onaylandı",
  rejected: "Reddedildi",
  draft_edited: "Taslak düzenlendi",
  draft_edited_via_chat: "Taslak chatbot ile düzenlendi",
};

function EventIcon({ event }: { event: string }) {
  if (event === "approved") return <CheckCircle2 size={18} />;
  if (event === "rejected") return <XCircle size={18} />;
  if (event.includes("edited")) return <FilePenLine size={18} />;
  return <Clock3 size={18} />;
}

export const AuditDrawer: React.FC<Props> = ({ open, events, onClose }) => {
  if (!open) return null;

  return (
    <div className="drawer-backdrop no-print" role="presentation" onMouseDown={onClose}>
      <aside className="audit-drawer" role="dialog" aria-modal="true" aria-labelledby="audit-title" onMouseDown={(event) => event.stopPropagation()}>
        <div className="drawer-header">
          <div>
            <span className="section-kicker">Kayıt geçmişi</span>
            <h2 id="audit-title">İşlem Geçmişi</h2>
          </div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="İşlem geçmişini kapat"><X size={20} /></button>
        </div>
        <div className="audit-list">
          {events.length === 0 ? (
            <div className="panel-empty">Bu analiz için işlem kaydı bulunmuyor.</div>
          ) : events.map((event, index) => (
            <div className="audit-event" key={`${event.timestamp}-${index}`}>
              <div className="audit-icon"><EventIcon event={event.event} /></div>
              <div>
                <strong>{eventLabels[event.event] || event.event.replaceAll("_", " ")}</strong>
                <time>{formatTimestamp(event.timestamp)}</time>
                {event.message && <p>{event.message}</p>}
              </div>
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
};

function formatTimestamp(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("tr-TR", { dateStyle: "medium", timeStyle: "short" }).format(date);
}
