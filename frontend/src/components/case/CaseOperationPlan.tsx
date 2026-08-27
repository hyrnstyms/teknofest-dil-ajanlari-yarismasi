import React from "react";
import { AlertTriangle, Building2, Check, Circle, ClipboardList, MapPin, Route, UserRound } from "lucide-react";
import type { CaseRecord } from "../../types/case";

const statusRank: Record<string, number> = { RECEIVED: 0, ANALYZING: 1, WAITING_INITIAL_REVIEW: 2, WAITING_CITIZEN_INFO: 2, READY_TO_ROUTE: 3, IN_DEPARTMENT: 4, IN_PROGRESS: 5, RESPONSE_DRAFTED: 6, WAITING_FINAL_APPROVAL: 6, COMPLETED: 7, CLOSED: 7 };
const sourceLabels = { VATANDAS: "Vatandaş", DIS_KURUM: "Dış Kurum", KURUM_ICI: "Kurum İçi" };
const channelLabels: Record<string, string> = { WEB_FORM: "Web", FIZIKI_EVRAK: "Fiziki", EPOSTA: "E-posta", KEP: "KEP", EBYS: "EBYS", KURUM_ICI: "Kurum İçi" };

function field(item: CaseRecord, ...names: string[]): string | undefined {
  const fields = item.analysis_details?.extraction?.fields || {};
  for (const name of names) {
    const value = fields[name]?.value;
    if (typeof value === "string" && value.trim()) return value.trim();
  }
}

function sourceLabel(item: CaseRecord) { return sourceLabels[item.source_type]; }
function channelLabel(item: CaseRecord) { return channelLabels[item.source_channel] || item.source_channel; }

export function CaseOperationPlan({ item, onRoute }: { item: CaseRecord; onRoute: () => void }) {
  const rank = statusRank[item.workflow_status] ?? 0;
  const missing = item.clarification?.requested_fields || item.analysis_details?.missing_fields?.blocking_fields || [];
  const location = field(item, "address", "location", "event_location");
  const canRoute = item.permissions.includes("ROUTE_CASE") && Boolean(item.routing_recommendation);
  const fieldRequired = Boolean(location) || /yol|bakım|kaldırım|saha/i.test(`${item.title} ${item.analysis_summary || ""}`);
  const stages = [
    ["Kuruma Geldi", sourceLabel(item)], ["Ön İnceleme", "EVRAG karar desteği"], ["Yazı İşleri", "İnsan kontrolü"],
    [item.routing_recommendation?.recommended_unit || item.current_department_name, "Sorumlu birim"], ["Personel Ataması", "Birim içi görev"],
    ["İşlem", fieldRequired ? "Saha / kurum işlemi" : "Kurum işlemi"], ["Cevap / Onay", "Resmî yazı"], ["Tamamlandı", "Vatandaşa sonuç"],
  ];
  return <>
    <section className="operation-plan" aria-label="EVRAG Akıllı İşlem Planı">
      <header><div><span className="eyebrow">EVRAG AKILLI İŞLEM PLANI</span><h2>{item.routing_recommendation?.recommended_unit || item.current_department_name}</h2><p>Evraktan işleme dönüşen kurumsal yol haritası</p></div><ClipboardList/></header>
      <div className="operation-route"><strong>{item.routing_recommendation?.recommended_unit || "İlk inceleme sürüyor"}</strong><span>→</span><strong>{fieldRequired ? "Saha / Yerinde İnceleme" : "Kurumsal İnceleme"}</strong></div>
      <dl className="operation-facts">
        <div><dt>Öncelik</dt><dd className={`priority-${String(item.priority || "normal").toLowerCase()}`}>{item.priority || "Normal"}</dd></div>
        <div><dt>Saha görevi</dt><dd>{fieldRequired ? "Gerekli" : "Belirlenmedi"}</dd></div>
        <div><dt>Eksik bilgi</dt><dd>{missing.length ? missing.join(", ") : "Yok"}</dd></div>
        <div><dt>Konum</dt><dd>{location || "Doğrulanmış konum yok"}</dd></div>
      </dl>
      <div className="operation-reason"><strong>Neden?</strong><p>{item.routing_recommendation?.reason || item.analysis_summary || "İşlem planı için insan incelemesi bekleniyor."}</p></div>
      {canRoute && <button className="btn btn-primary operation-cta" onClick={onRoute}>{item.routing_recommendation!.recommended_unit.toLocaleUpperCase("tr-TR")} BİRİMİNE HAVALE ET</button>}
    </section>
    <section className="municipal-chain" aria-label="Belediye evrak zinciri">
      {stages.map(([title, detail], index) => <React.Fragment key={title}><div className={index < rank ? "complete" : index === rank ? "current" : "future"}><span>{index < rank ? <Check/> : index === rank ? <Route/> : <Circle/>}</span><strong>{title}</strong><small>{detail}</small></div>{index < stages.length - 1 && <i>→</i>}</React.Fragment>)}
    </section>
    <section className="operation-support-grid">
      <article><span><UserRound/> Kaynak</span><strong>{sourceLabel(item)}</strong><small>{item.originator_name} · {channelLabel(item)}</small></article>
      <article><span><Building2/> Birim içi görevlendirme</span><strong>Henüz oluşturulmadı</strong><small>Görevli ve ekip bilgisi backend tarafından sağlandığında burada gösterilir.</small></article>
      <article><span><MapPin/> Saha işlemi</span><strong>{fieldRequired ? "Gerekli" : "Belirlenmedi"}</strong><small>{location || "Gerçek konum verisi bulunmuyor; harita gösterilmedi."}</small></article>
      <article><span><AlertTriangle/> Sorumluluk</span><strong>İnsan onayı zorunlu</strong><small>EVRAG önerir; kurumsal sorumluluk personel kararıyla aktarılır.</small></article>
    </section>
  </>;
}
