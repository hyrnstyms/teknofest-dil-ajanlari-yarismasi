import React from "react";
import { AlertTriangle, Building2, Check, Circle, ClipboardList, MapPin, Route, UserRound } from "lucide-react";
import type { CaseRecord } from "../../types/case";

const statusRank: Record<string, number> = { RECEIVED: 0, ANALYZING: 1, WAITING_INITIAL_REVIEW: 2, WAITING_CITIZEN_INFO: 2, READY_TO_ROUTE: 3, IN_DEPARTMENT: 4, IN_PROGRESS: 5, RESPONSE_DRAFTED: 6, WAITING_FINAL_APPROVAL: 6, COMPLETED: 7, CLOSED: 7 };
const sourceLabels = { VATANDAS: "Vatandaş", DIS_KURUM: "Dış Kurum", KURUM_ICI: "Kurum İçi" };
const channelLabels: Record<string, string> = { WEB_FORM: "Web", FIZIKI_EVRAK: "Fiziki", EPOSTA: "E-posta", KEP: "KEP", EBYS: "EBYS", KURUM_ICI: "Kurum İçi" };
const departmentLabels: Record<string, string> = { yazi_isleri: "Yazı İşleri Müdürlüğü", fen_isleri: "Fen İşleri Müdürlüğü", imar_sehircilik: "İmar ve Şehircilik Müdürlüğü", zabita: "Zabıta Müdürlüğü", temizlik_isleri: "Temizlik İşleri Müdürlüğü" };
const taskLabels: Record<string, string> = { YOL_BAKIM_INCELEME: "Yol bakım / saha incelemesi", SAHA_INCELEMESI: "Saha incelemesi", GENEL_INCELEME: "Genel inceleme", BELGE_KONTROLU: "Belge kontrolü", SAHA_EKIBI: "Saha Ekibi", BIRIM_PERSONELI: "Birim Personeli", INSAAT_MUHENDISI: "İnşaat Mühendisi", TEKNIKER: "Tekniker" };

function readableCode(value?: string | null) {
  if (!value) return undefined;
  return departmentLabels[value] || taskLabels[value] || value.replaceAll("_", " ").toLocaleLowerCase("tr-TR").replace(/(^|\s)\p{L}/gu, (letter) => letter.toLocaleUpperCase("tr-TR"));
}

function field(item: CaseRecord, ...names: string[]): string | undefined {
  const fields = item.analysis_details?.extraction?.fields || {};
  for (const name of names) {
    const value = fields[name]?.value;
    if (typeof value === "string" && value.trim()) return value.trim();
  }
}

export function CaseOperationPlan({ item, onRoute }: { item: CaseRecord; onRoute: () => void }) {
  const rank = statusRank[item.workflow_status] ?? 0;
  const operation = item.ai_operation;
  const task = item.assignment || item.tasks?.at(-1);
  const missing = item.clarification?.requested_fields || item.analysis_details?.missing_fields?.blocking_fields || [];
  const location = field(item, "address", "location", "event_location");
  const canRoute = item.permissions.includes("ROUTE_CASE") && Boolean(item.routing_recommendation);
  const recommendedDepartment = item.routing_recommendation?.recommended_unit
    || readableCode(operation?.recommended_department || operation?.department_code)
    || item.current_department_name;
  const team = operation?.team_name || readableCode(task?.team_code || operation?.recommended_team || operation?.team_code);
  const role = readableCode(task?.recommended_role || operation?.recommended_role);
  const taskType = readableCode(task?.task_type || operation?.recommended_task_type || operation?.task_type);
  const fieldDecision = operation?.requires_field_visit ?? operation?.field_visit_required;
  const priority = item.priority_assessment?.priority || item.priority || "Belirlenmedi";
  const priorityReason = item.priority_assessment?.priority_reason;
  const routePayload = item.timeline.filter((event) => event.event_type === "CASE_ROUTED").at(-1)?.payload || {};
  const levelOneFrom = readableCode(String(routePayload.from_department || "")) || item.current_department_name;
  const levelOneTo = readableCode(String(routePayload.to_department || "")) || recommendedDepartment;
  const stages = [
    ["Kuruma Geldi", sourceLabels[item.source_type]], ["Ön İnceleme", "EVRAG karar desteği"], ["Yazı İşleri", "İnsan kontrolü"],
    [recommendedDepartment, "Kurumsal havale"], ["Birim İçi Görev", task?.status || "Atama bekleniyor"],
    ["İşlem", taskType || "Backend önerisi bekleniyor"], ["Cevap / Onay", "Resmî yazı"], ["Tamamlandı", "Muhataba sonuç"],
  ];

  return <>
    <section className="operation-plan" aria-label="EVRAG Akıllı İşlem Planı">
      <header><div><span className="eyebrow">EVRAG AKILLI İŞLEM PLANI</span><h2>{recommendedDepartment}</h2><p>Backend kararlarından beslenen kurumsal işlem planı</p></div><ClipboardList/></header>
      <div className="operation-levels">
        <div><small>KURUMSAL HAVALE · LEVEL 1</small><strong>{levelOneFrom}</strong><span>→</span><strong>{levelOneTo}</strong></div>
        <div><small>BİRİM İÇİ İŞLEM · LEVEL 2</small><strong>{recommendedDepartment}</strong><span>→</span><strong>{team || "Ekip önerisi yok"}</strong><span>→</span><strong>{role || "Rol önerisi yok"}</strong></div>
      </div>
      <dl className="operation-facts">
        <div><dt>Öncelik</dt><dd className={`priority-${String(priority).toLowerCase()}`}>{priority}</dd></div>
        <div><dt>Görev / işlem</dt><dd>{taskType || "Backend önerisi yok"}</dd></div>
        <div><dt>Saha görevi</dt><dd>{fieldDecision === true ? "Gerekli" : fieldDecision === false ? "Gerekli değil" : "Backend kararı yok"}</dd></div>
        <div><dt>Eksik bilgi</dt><dd>{missing.length ? missing.join(", ") : "Yok"}</dd></div>
      </dl>
      <div className="operation-reason"><strong>Operasyon gerekçesi</strong><p>{operation?.reason || item.routing_recommendation?.reason || "Backend operasyon gerekçesi sağlamadı."}</p>{priorityReason && <p><b>Öncelik gerekçesi:</b> {priorityReason}</p>}</div>
      {canRoute && <button className="btn btn-primary operation-cta" onClick={onRoute}>{recommendedDepartment.toLocaleUpperCase("tr-TR")} BİRİMİNE HAVALE ET</button>}
    </section>
    <section className="municipal-chain" aria-label="Belediye evrak zinciri">
      {stages.map(([title, detail], index) => <React.Fragment key={`${title}-${index}`}><div className={index < rank ? "complete" : index === rank ? "current" : "future"}><span>{index < rank ? <Check/> : index === rank ? <Route/> : <Circle/>}</span><strong>{title}</strong><small>{detail}</small></div>{index < stages.length - 1 && <i>→</i>}</React.Fragment>)}
    </section>
    <section className="operation-support-grid">
      <article><span><UserRound/> Kaynak</span><strong>{sourceLabels[item.source_type]}</strong><small>{item.originator_name} · {channelLabels[item.source_channel] || item.source_channel}</small></article>
      <article id="case-assignment"><span><Building2/> Birim içi görevlendirme</span><strong>{task ? task.status : operation ? "ASSIGNMENT_PENDING" : "Görev oluşturulmadı"}</strong><small>{taskType || "Görev bilgisi yok"} · {team || "Ekip yok"} · {role || "Rol yok"}</small>{task && !task.assigned_user_id && <small>Personel seçimi için backend kullanıcı listesi sağlanmıyor; sahte personel gösterilmedi.</small>}</article>
      <article><span><MapPin/> Saha işlemi</span><strong>{fieldDecision === true ? "Gerekli" : fieldDecision === false ? "Gerekli değil" : "Belirlenmedi"}</strong><small>{location || "Doğrulanmış konum verisi bulunmuyor."}</small></article>
      <article><span><AlertTriangle/> Sorumluluk</span><strong>İnsan onayı zorunlu</strong><small>EVRAG ekip ve rol önerir; gerçek personeli otomatik seçmez.</small></article>
    </section>
  </>;
}
