import React from "react";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import type { CaseRecord, CurrentUser } from "../../types/case";

type Action = "review" | "route" | "start" | "clarification";

export function OperationalNextAction({ item, user, onAction }: { item: CaseRecord; user?: CurrentUser | null; onAction: (action: Action) => void }) {
  const needsInfo = Boolean(item.clarification?.needs_clarification && item.permissions.includes("REQUEST_CITIZEN_INFO"));
  const canReview = user?.role === "EVRAK_KAYIT" && item.permissions.includes("ACCEPT_REVIEW");
  const canRoute = user?.role === "EVRAK_KAYIT" && item.permissions.includes("ROUTE_CASE") && Boolean(item.routing_recommendation);
  const canStart = user?.role === "BIRIM_PERSONELI" && item.permissions.includes("START_CASE");
  const next = needsInfo
    ? { title: "Eksik bilgiyi tamamlatın", body: "Dosyanın devam edebilmesi için doğrulanmış eksik bilgi talebini gönderin.", label: "Bilgi talebi oluştur", action: "clarification" as const }
    : canReview
      ? { title: "Ön incelemeyi doğrulayın", body: "EVRAG analizini kontrol ederek dosyayı havale kararına hazırlayın.", label: "İncelemeyi onayla", action: "review" as const }
      : canRoute
        ? { title: "Havale kararını verin", body: `${item.routing_recommendation!.recommended_unit} önerisini ve gerekçesini kontrol edin.`, label: "Havaleyi onayla", action: "route" as const }
        : canStart
          ? { title: "Dosyayı işleme alın", body: "Birim sorumluluğunu kabul ederek kurum veya saha işlemini başlatın.", label: "İşleme al", action: "start" as const }
          : { title: item.workflow_status === "CLOSED" ? "Dosya kapatıldı" : "Mevcut aşamayı inceleyin", body: item.workflow_status === "CLOSED" ? "Bu dosyada yeni bir operasyon adımı beklenmiyor." : "Yeni işlem yetkisi oluştuğunda burada doğrudan eylem gösterilir." };

  return <section className="case-panel next-action next-action-operational">
    <span className="eyebrow">ŞİMDİ NE YAPMALIYIM?</span>
    <h2>{next.title}</h2><p>{next.body}</p>
    {"action" in next
      ? <button className="btn btn-primary" onClick={() => onAction(next.action as Action)}>{next.label}<ArrowRight size={16}/></button>
      : <div className="next-action-done"><CheckCircle2 size={18}/> Bekleyen işlem yok</div>}
  </section>;
}
