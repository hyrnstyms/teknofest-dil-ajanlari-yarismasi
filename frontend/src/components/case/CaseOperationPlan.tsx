import React from "react";
import { AlertTriangle, MapPin, Sparkles } from "lucide-react";
import type { CaseRecord } from "../../types/case";

const preRouteStatuses = new Set(["RECEIVED", "ANALYZING", "WAITING_INITIAL_REVIEW", "WAITING_CITIZEN_INFO", "READY_TO_ROUTE"]);
const departmentLabels: Record<string, string> = { yazi_isleri: "Yazı İşleri Müdürlüğü", fen_isleri: "Fen İşleri Müdürlüğü", imar_sehircilik: "İmar ve Şehircilik Müdürlüğü", zabita: "Zabıta Müdürlüğü", temizlik_isleri: "Temizlik İşleri Müdürlüğü" };
const codeLabels: Record<string, string> = { YOL_BAKIM_INCELEME: "Yol bakım ve saha incelemesi", SAHA_INCELEMESI: "Saha incelemesi", GENEL_INCELEME: "Genel inceleme", BELGE_KONTROLU: "Belge kontrolü", SAHA_EKIBI: "Saha Ekibi", BIRIM_PERSONELI: "Birim Personeli", INSAAT_MUHENDISI: "İnşaat Mühendisi", TEKNIKER: "Tekniker" };
const taskStatusLabels: Record<string, string> = { ASSIGNMENT_PENDING: "Görevlendirme bekliyor", ASSIGNED: "Görevlendirildi", IN_PROGRESS: "İşlem yürütülüyor", WAITING_INFO: "Bilgi bekleniyor", DONE: "Görev tamamlandı" };
const priorityLabels: Record<string, string> = { HIGH: "Yüksek", MEDIUM: "Normal", LOW: "Düşük", URGENT: "Acil", Yüksek: "Yüksek", Normal: "Normal", Düşük: "Düşük", Acil: "Acil" };

function readableCode(value?: string | null) {
  if (!value) return undefined;
  return departmentLabels[value] || codeLabels[value] || value.replaceAll("_", " ").toLocaleLowerCase("tr-TR").replace(/(^|\s)\p{L}/gu, (letter) => letter.toLocaleUpperCase("tr-TR"));
}

function workflowTitle(item: CaseRecord, department: string, taskType?: string) {
  if (preRouteStatuses.has(item.workflow_status)) return `${department} için işlem önerisi`;
  if (item.workflow_status === "IN_DEPARTMENT") return `${department} birimine havale edildi`;
  if (item.workflow_status === "IN_PROGRESS") return `${taskType || "Birim işlemi"} yürütülüyor`;
  if (["RESPONSE_DRAFTED", "WAITING_FINAL_APPROVAL"].includes(item.workflow_status)) return "Cevap taslağı inceleme aşamasında";
  if (["COMPLETED", "CLOSED"].includes(item.workflow_status)) return "Dosya işlemi tamamlandı";
  return taskType || "Mevcut işlem";
}

export function CaseOperationPlan({ item }: { item: CaseRecord }) {
  const operation = item.ai_operation;
  const task = item.assignment || item.tasks?.at(-1);
  const isRecommendation = preRouteStatuses.has(item.workflow_status);
  const recommendedDepartment = item.routing_recommendation?.recommended_unit
    || readableCode(operation?.recommended_department || operation?.department_code)
    || item.current_department_name;
  const department = isRecommendation ? recommendedDepartment : item.current_department_name;
  const team = operation?.team_name || readableCode(task?.team_code || operation?.recommended_team || operation?.team_code);
  const taskType = readableCode(task?.task_type || operation?.recommended_task_type || operation?.task_type);
  const role = readableCode(task?.recommended_role || operation?.recommended_role);
  const fieldVisit = operation?.requires_field_visit ?? operation?.field_visit_required;
  const missing = item.clarification?.needs_clarification ? item.clarification.requested_fields : [];
  const reason = task?.reason || operation?.reason || item.routing_recommendation?.reason || "İşlem gerekçesi henüz oluşmadı.";
  const priority = item.priority_assessment?.priority || item.priority;
  const priorityLabel = priority ? priorityLabels[priority] : undefined;
  const risk = item.deadline?.risk_level;
  const urgentDeadline = item.deadline?.applicable && item.deadline.legal_basis?.verified && risk && ["APPROACHING", "CRITICAL", "OVERDUE"].includes(risk);
  const highUncertainty = typeof item.routing_recommendation?.score === "number" && item.routing_recommendation.score < 0.65;

  return <section className="operation-plan cockpit-operation" id="case-assignment">
    <header>
      <div><span className="section-kicker">{isRecommendation ? "Önerilen işlem" : "Mevcut işlem"}</span><h2>İşlem Planı</h2></div>
      <Sparkles aria-hidden="true"/>
    </header>
    <h3>{workflowTitle(item, department, taskType)}</h3>
    <dl className="operation-summary">
      <div><dt>Nereye?</dt><dd>{department}{team ? <> <span>→</span> {team}</> : null}</dd></div>
      <div><dt>Ne yapılacak?</dt><dd>{taskType || "İnsan incelemesiyle belirlenecek"}{task?.status && <small>{taskStatusLabels[task.status] || "Görev durumu güncellendi"}</small>}{role ? <small>Uygun rol: {role}</small> : null}</dd></div>
      <div><dt>Neden?</dt><dd>{reason}</dd></div>
    </dl>
    {(fieldVisit === true || (priorityLabel && !["Normal", "Düşük"].includes(priorityLabel))) && <div className="operation-tags">
      {fieldVisit === true && <span><MapPin/> Saha işlemi gerekli</span>}
      {priorityLabel && !["Normal", "Düşük"].includes(priorityLabel) && <span className="priority-tag">Öncelik: {priorityLabel}</span>}
    </div>}
    {missing.length > 0 && <div className="operation-alert"><AlertTriangle/><div><strong>Eksik bilgi işlemi durduruyor</strong><span>{item.clarification?.reason || missing.join(", ")}</span></div></div>}
    {urgentDeadline && <div className="operation-alert deadline-alert"><AlertTriangle/><div><strong>Son tarih yaklaşıyor</strong><span>{item.deadline?.due_at ? new Date(item.deadline.due_at).toLocaleDateString("tr-TR") : item.deadline?.deadline_days ? `${item.deadline.deadline_days} günlük süre` : risk}</span></div></div>}
    {highUncertainty && <div className="operation-alert"><AlertTriangle/><div><strong>Yönlendirme belirsizliği yüksek</strong><span>Birim seçimini işlemden önce doğrulayın.</span></div></div>}
    {isRecommendation && <p className="operation-disclaimer">AI önerisidir; işlem yalnız kullanıcı onayıyla gerçekleşir.</p>}
  </section>;
}
