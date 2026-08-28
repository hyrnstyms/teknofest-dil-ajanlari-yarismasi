import React from "react";
import { AlertTriangle, Check, Circle, Clock3 } from "lucide-react";
import type { CaseEvent, CaseStatus } from "../../types/case";
import { formatCaseStatus } from "../../utils/presentation";
export const statusLabel = (status: CaseStatus) => formatCaseStatus(status);
export function StatusBadge({ status }: { status: CaseStatus }) { return <span className={`case-status status-${status.toLowerCase()}`}>{statusLabel(status)}</span>; }
export function CaseTimeline({ events }: { events: CaseEvent[] }) { return <ol className="case-timeline">{events.map((event, index) => <li key={event.id}><span className="timeline-node">{index === events.length - 1 ? <Clock3 size={15}/> : <Check size={15}/>}</span><div><strong>{event.label}</strong>{event.actor_name && <span>{event.actor_name}</span>}<time>{new Date(event.created_at).toLocaleString("tr-TR")}</time></div></li>)}</ol>; }
export function ConfirmAction({ title, text, busy, onCancel, onConfirm }: { title: string; text: string; busy?: boolean; onCancel: () => void; onConfirm: () => void }) { return <div className="confirm-backdrop" role="presentation"><section className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title"><span className="confirm-icon"><AlertTriangle/></span><h2 id="confirm-title">{title}</h2><p>{text}</p><div><button className="btn btn-secondary" onClick={onCancel} disabled={busy}>Vazgeç</button><button className="btn btn-primary" onClick={onConfirm} disabled={busy}>{busy ? "Kaydediliyor…" : "Onayla"}</button></div></section></div>; }
export function EmptyState({ title, text }: { title: string; text: string }) { return <div className="case-empty"><Circle/><h3>{title}</h3><p>{text}</p></div>; }
