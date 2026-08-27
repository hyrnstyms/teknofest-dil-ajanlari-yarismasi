import React from "react";
import { Eye, FileQuestion } from "lucide-react";
import type { CaseRecord } from "../../types/case";

const labels: Record<string, string> = { address: "Olay konumu / adres", location: "Olay konumu", event_location: "Olay konumu", attachment: "Eksik ek", identity: "Kimlik bilgisi", subject: "Belge konusu" };

export function MissingInformationSolution({ item, onRequest }: { item: CaseRecord; onRequest: () => void }) {
  if (!item.clarification?.needs_clarification) return null;
  const fields = item.clarification.requested_fields || [];
  const target = item.source_type === "VATANDAS" ? "Başvuru sahibi" : item.source_type === "DIS_KURUM" ? "Gönderen kurum" : "Gönderen iç birim";
  const action = item.source_type === "VATANDAS" ? "Vatandaştan adres / bilgi talep et" : item.source_type === "DIS_KURUM" ? "Gönderen kurumdan bilgi iste" : "Gönderen birimden eksik eki iste";
  return <section className="case-panel clarification-panel clarification-solution">
    <header><div><span className="eyebrow">EKSİK BİLGİ ÇÖZÜMÜ</span><h2>Dosyayı ilerletmek için gereken bilgi</h2></div><FileQuestion/></header>
    <dl><div><dt>Eksik</dt><dd>{fields.length ? fields.map((field) => labels[field] || field.replaceAll("_", " ")).join(", ") : "Backend alan bilgisi sağlamadı"}</dd></div><div><dt>Neden gerekli?</dt><dd>{item.clarification.question || "Kurumsal işlemin güvenle sürdürülebilmesi için."}</dd></div><div><dt>Kimden alınmalı?</dt><dd>{target}</dd></div><div><dt>Önerilen işlem</dt><dd>{action}</dd></div></dl>
    <div><button className="btn btn-secondary" disabled title="Talep taslağı oluşturulduğunda açılır"><Eye size={16}/> Talep Yazısını Gör</button>{item.permissions.includes("REQUEST_CITIZEN_INFO") && <button className="btn btn-primary" onClick={onRequest}>Bilgi Talebini Oluştur</button>}</div>
  </section>;
}
