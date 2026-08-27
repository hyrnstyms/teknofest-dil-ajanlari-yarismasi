import React from "react";
import { Eye, FileQuestion } from "lucide-react";
import type { CaseRecord } from "../../types/case";

const labels: Record<string, string> = { address: "Olay konumu / adres", location: "Olay konumu", event_location: "Olay konumu", attachment: "Eksik ek", identity: "Kimlik bilgisi", subject: "Belge konusu" };
const departmentLabels: Record<string, string> = { yazi_isleri: "Yazı İşleri Müdürlüğü", fen_isleri: "Fen İşleri Müdürlüğü", imar_sehircilik: "İmar ve Şehircilik Müdürlüğü", zabita: "Zabıta Müdürlüğü", temizlik_isleri: "Temizlik İşleri Müdürlüğü" };
const actionLabels: Record<string, string> = { CITIZEN_INFORMATION_REQUESTED: "Vatandaştan eksik bilgi talep et", INTERNAL_INFORMATION_REQUESTED: "Gönderen iç birimden eksik bilgi talep et", EXTERNAL_INFORMATION_REQUESTED: "Gönderen kurumdan eksik bilgi talep et", REQUEST_INFORMATION: "Eksik bilgi talebi oluştur" };

export function MissingInformationSolution({ item, onRequest }: { item: CaseRecord; onRequest: () => void }) {
  if (!item.clarification?.needs_clarification) return null;
  const fields = item.clarification.requested_fields || [];
  const targetType = item.clarification.target_type || item.source_type;
  const targetDepartment = item.clarification.target_department ? departmentLabels[item.clarification.target_department] || item.clarification.target_department.replaceAll("_", " ") : undefined;
  const target = item.clarification.target_name
    || (targetType === "VATANDAS" ? "Başvuru sahibi" : targetType === "DIS_KURUM" ? "Gönderen kurum" : targetDepartment || "Gönderen iç birim");
  const action = actionLabels[item.clarification.recommended_action || ""] || "Eksik bilgi talebi oluştur";
  const isLocation = fields.some((field) => ["address", "location", "event_location"].includes(field));
  const buttonLabel = targetType === "VATANDAS"
    ? isLocation ? "Vatandaştan Konum Bilgisi İste" : "Vatandaştan Eksik Bilgi İste"
    : targetType === "DIS_KURUM"
      ? "Gönderen Kurumdan Eksik Bilgi İste"
      : `${targetDepartment || target}nden Eksik Bilgi İste`;
  return <section className="case-panel clarification-panel clarification-solution">
    <header><div><span className="eyebrow">EKSİK BİLGİ ÇÖZÜMÜ</span><h2>Dosyayı ilerletmek için gereken bilgi</h2></div><FileQuestion/></header>
    <dl><div><dt>Eksik</dt><dd>{fields.length ? fields.map((field) => labels[field] || field.replaceAll("_", " ")).join(", ") : "Backend alan bilgisi sağlamadı"}</dd></div><div><dt>Neden gerekli?</dt><dd>{item.clarification.reason || item.clarification.question || "Kurumsal işlemin güvenle sürdürülebilmesi için."}</dd></div><div><dt>Kimden alınmalı?</dt><dd>{target}</dd></div><div><dt>Önerilen işlem</dt><dd>{action}</dd></div></dl>
    <div><button className="btn btn-secondary" disabled title="Talep taslağı oluşturulduğunda açılır"><Eye size={16}/> Talep Yazısını Gör</button><button className="btn btn-primary" onClick={onRequest}>{buttonLabel}</button></div>
  </section>;
}
