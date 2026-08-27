import React from "react";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import type { CaseRecord, CurrentUser } from "../../types/case";

export type OperationalAction = "review" | "route" | "start" | "clarification" | "assignment" | "result" | "draft";
type NextAction = { title: string; body: string; label?: string; action?: OperationalAction; done?: boolean };

function informationActionLabel(item: CaseRecord) {
  const target = item.clarification?.target_type || item.source_type;
  const location = item.clarification?.requested_fields.some((field) => ["address", "location", "event_location"].includes(field));
  if (target === "VATANDAS") return location ? "Vatandaştan Konum Bilgisi İste" : "Vatandaştan Bilgi İste";
  if (target === "DIS_KURUM") return "Gönderen Kurumdan Bilgi İste";
  return "Gönderen Birimden Bilgi İste";
}

export function OperationalNextAction({ item, user, onAction }: { item: CaseRecord; user?: CurrentUser | null; onAction: (action: OperationalAction) => void }) {
  const task = item.assignment || item.tasks?.at(-1);
  const pendingInformationRequest = item.information_requests?.some((request) => request.status === "PENDING");
  const needsInfo = Boolean(item.clarification?.needs_clarification && !pendingInformationRequest);
  const canReview = user?.role === "EVRAK_KAYIT" && item.permissions.includes("ACCEPT_REVIEW");
  const canRoute = user?.role === "EVRAK_KAYIT" && item.permissions.includes("ROUTE_CASE") && Boolean(item.routing_recommendation);
  const canStart = user?.role === "BIRIM_PERSONELI" && item.permissions.includes("START_CASE");
  const canRecordResult = user?.role === "BIRIM_PERSONELI" && item.permissions.includes("RECORD_DEPARTMENT_ACTION");
  const hasDraft = item.drafts.length > 0;

  let next: NextAction;
  if (needsInfo) next = { title: "Eksik bilgiyi tamamlatın", body: item.clarification?.reason || "Dosyanın devamı için eksik bilgi gerekiyor.", label: informationActionLabel(item), action: "clarification" };
  else if (pendingInformationRequest) next = { title: "Bilgi yanıtını bekleyin", body: "Talep kaydedildi; yanıt geldiğinde dosya ilerleyecek.", done: true };
  else if (canReview) next = { title: "Ön incelemeyi doğrulayın", body: "Analizi kontrol edip dosyayı havale kararına hazırlayın.", label: "İncelemeyi Onayla", action: "review" };
  else if (canRoute) next = { title: "Dosyayı ilgili birime havale edin", body: `${item.routing_recommendation!.recommended_unit} önerisini kontrol edin.`, label: `${item.routing_recommendation!.recommended_unit} Birimine Havale Et`, action: "route" };
  else if (user?.role === "BIRIM_PERSONELI" && task?.status === "ASSIGNMENT_PENDING") next = { title: "Görevlendirmeyi inceleyin", body: "Ekip ve rol önerisi hazır; personel seçimi kullanıcı onayı gerektirir.", label: "Görevlendirmeyi İncele", action: "assignment" };
  else if (canStart) next = { title: "Dosyayı işleme alın", body: "Birim görevini kontrol ederek işlemi başlatın.", label: "İşleme Al", action: "start" };
  else if (canRecordResult) next = { title: "İşlem sonucunu kaydedin", body: "Doğrulanmış saha veya kurum sonucunu dosyaya ekleyin.", label: "İşlem Sonucunu Kaydet", action: "result" };
  else if (hasDraft) next = { title: "Cevap taslağını inceleyin", body: "Muhatap ve dayanak bilgilerini kontrol edin.", label: "Taslağı İncele", action: "draft" };
  else next = { title: item.workflow_status === "CLOSED" ? "Dosya kapatıldı" : "Yeni işlem beklenmiyor", body: item.workflow_status === "CLOSED" ? "Dosya yaşam döngüsü tamamlandı." : "Bu aşamada kullanıcı aksiyonu bulunmuyor.", done: true };

  return <section className="case-panel next-action next-action-operational">
    <span className="section-kicker">Şimdi ne yapmalıyım?</span>
    <h2>Sonraki Adım</h2><h3>{next.title}</h3><p>{next.body}</p>
    {next.action && next.label
      ? <button className="btn btn-primary" onClick={() => onAction(next.action!)}>{next.label}<ArrowRight size={16}/></button>
      : <div className="next-action-done"><CheckCircle2 size={18}/> {next.done ? "Bekleyen kullanıcı işlemi yok" : "İşlem bekleniyor"}</div>}
  </section>;
}
