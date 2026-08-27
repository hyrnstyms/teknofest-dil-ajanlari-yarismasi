import React from "react";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import type { CaseRecord, CurrentUser } from "../../types/case";

export type OperationalAction = "review" | "route" | "start" | "clarification" | "assignment" | "result" | "draft";
type NextAction = { title: string; body: string; label?: string; action?: OperationalAction; done?: boolean };

export function OperationalNextAction({ item, user, onAction }: { item: CaseRecord; user?: CurrentUser | null; onAction: (action: OperationalAction) => void }) {
  const task = item.assignment || item.tasks?.at(-1);
  const pendingInformationRequest = item.information_requests?.some((request) => request.status === "PENDING");
  const needsInfo = Boolean(item.clarification?.needs_clarification && !pendingInformationRequest);
  const canReview = user?.role === "EVRAK_KAYIT" && item.permissions.includes("ACCEPT_REVIEW");
  const canRoute = user?.role === "EVRAK_KAYIT" && item.permissions.includes("ROUTE_CASE") && Boolean(item.routing_recommendation);
  const canStart = user?.role === "BIRIM_PERSONELI" && item.permissions.includes("START_CASE");
  const canRecordResult = user?.role === "BIRIM_PERSONELI" && item.permissions.includes("RECORD_DEPARTMENT_ACTION");
  const reviewDraft = item.drafts.some((draft) => draft.draft_status !== "APPROVED");

  let next: NextAction;
  if (needsInfo) next = { title: "Eksik bilgiyi doğru muhataptan isteyin", body: item.clarification?.reason || "Backend tarafından belirlenen eksik bilgi talebini oluşturun.", label: "Eksik Bilgi Talebi Oluştur", action: "clarification" };
  else if (pendingInformationRequest) next = { title: "Eksik bilgi yanıtını bekleyin", body: "Bilgi talebi gerçek Case API üzerinden kaydedildi; aynı talebi yeniden göndermeyin.", done: true };
  else if (canReview) next = { title: "Ön incelemeyi doğrulayın", body: "EVRAG analizini kontrol ederek dosyayı havale kararına hazırlayın.", label: "İncelemeyi Onayla", action: "review" };
  else if (canRoute) next = { title: "Havale kararını verin", body: `${item.routing_recommendation!.recommended_unit} önerisini ve gerekçesini kontrol edin.`, label: `${item.routing_recommendation!.recommended_unit} Birimine Havale Et`, action: "route" };
  else if (user?.role === "BIRIM_PERSONELI" && task?.status === "ASSIGNMENT_PENDING") next = { title: "Birim içi görevlendirmeyi inceleyin", body: "Ekip ve rol önerisi hazır. Gerçek personel seçimi insan onayı ve backend kullanıcı listesi gerektirir.", label: "Görevlendirmeyi İncele", action: "assignment" };
  else if (canStart) next = { title: "Dosyayı işleme alın", body: "Atanmış birim görevini ve operasyon önerisini kontrol ederek işlemi başlatın.", label: "İşleme Al", action: "start" };
  else if (canRecordResult) next = { title: "İşlem sonucunu kaydedin", body: "Saha veya kurum işleminin doğrulanmış sonucunu vaka kaydına ekleyin.", label: "İşlem Sonucunu Kaydet", action: "result" };
  else if (reviewDraft) next = { title: "Cevap taslağını inceleyin", body: "Muhatap ve dayanak bilgilerini kontrol ederek taslağı personel onayına hazırlayın.", label: "Taslağı İncele", action: "draft" };
  else next = { title: item.workflow_status === "CLOSED" ? "Dosya kapatıldı" : "Mevcut aşamayı inceleyin", body: item.workflow_status === "CLOSED" ? "Bu dosyada yeni bir operasyon adımı beklenmiyor." : "Backend yeni bir işlem yetkisi sağladığında burada doğrudan eylem gösterilir.", done: true };

  return <section className="case-panel next-action next-action-operational">
    <span className="eyebrow">ŞİMDİ NE YAPMALIYIM?</span>
    <h2>{next.title}</h2><p>{next.body}</p>
    {next.action && next.label
      ? <button className="btn btn-primary" onClick={() => onAction(next.action!)}>{next.label}<ArrowRight size={16}/></button>
      : <div className="next-action-done"><CheckCircle2 size={18}/> {next.done ? "Bekleyen kullanıcı işlemi yok" : "İşlem bekleniyor"}</div>}
  </section>;
}
