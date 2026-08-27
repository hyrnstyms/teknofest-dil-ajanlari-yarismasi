import React, { useMemo } from "react";
import { AlertCircle, ArrowRight, ClipboardCheck, Clock3, FileCheck2, Inbox, MapPin, Route, ShieldAlert } from "lucide-react";
import { Link } from "react-router-dom";
import type { CaseRecord, CurrentUser } from "../../types/case";
import { EmptyState, StatusBadge } from "./CasePrimitives";

const approaching = (item: CaseRecord) => ["APPROACHING", "CRITICAL", "OVERDUE"].includes(item.deadline?.risk_level || "");
const missing = (item: CaseRecord) => item.workflow_status === "WAITING_CITIZEN_INFO" || Boolean(item.clarification?.needs_clarification);

export function RoleOperationsDashboard({ user, items, loading }: { user: CurrentUser; items: CaseRecord[]; loading: boolean }) {
  const registry = user.role === "EVRAK_KAYIT";
  const stats = useMemo(() => registry ? [
    { label: "Yeni Evrak", value: items.filter((x) => ["RECEIVED", "ANALYZING"].includes(x.workflow_status)).length, icon: Inbox },
    { label: "Analizi Tamamlanan", value: items.filter((x) => !["RECEIVED", "ANALYZING"].includes(x.workflow_status)).length, icon: FileCheck2 },
    { label: "Havale Bekleyen", value: items.filter((x) => x.workflow_status === "READY_TO_ROUTE").length, icon: Route },
    { label: "Eksik Bilgi Bekleyen", value: items.filter(missing).length, icon: AlertCircle },
    { label: "Acil / Süreli", value: items.filter((x) => approaching(x) || /yüksek|acil/i.test(x.priority || "")).length, icon: Clock3 },
    { label: "Manuel Karar Gereken", value: items.filter((x) => x.routing_recommendation?.requires_human_review || x.workflow_status === "WAITING_INITIAL_REVIEW").length, icon: ShieldAlert },
  ] : [
    { label: "Yeni Gelen", value: items.filter((x) => x.workflow_status === "IN_DEPARTMENT").length, icon: Inbox },
    { label: "Personel Ataması Bekleyen", value: items.filter((x) => x.workflow_status === "IN_DEPARTMENT" && !x.assigned_user_id).length, icon: ClipboardCheck },
    { label: "Saha İncelemesi Gereken", value: items.filter((x) => /yol|bakım|kaldırım|saha/i.test(`${x.title} ${x.analysis_summary || ""}`)).length, icon: MapPin },
    { label: "Eksik Bilgi Bekleyen", value: items.filter(missing).length, icon: AlertCircle },
    { label: "İşlemde", value: items.filter((x) => x.workflow_status === "IN_PROGRESS").length, icon: FileCheck2 },
    { label: "Cevap Bekleyen", value: items.filter((x) => ["RESPONSE_DRAFTED", "WAITING_FINAL_APPROVAL"].includes(x.workflow_status)).length, icon: ClipboardCheck },
    { label: "Süresi Yaklaşan", value: items.filter(approaching).length, icon: Clock3 },
  ], [items, registry]);
  const routingItems = items.filter((item) => item.routing_recommendation).slice(0, 6);
  const tasks = items.filter((item) => !["COMPLETED", "CLOSED"].includes(item.workflow_status)).slice(0, 6);
  return <>
    <header className="case-page-heading product-identity"><div><span className="eyebrow">EVRAG — EVRAKTAN İŞLEME</span><h1>{registry ? "Yazı İşleri Operasyon Masası" : `${user.department_name || "Birim"} Çalışma Masası`}</h1><p>{registry ? "Bugün gelen evrakları doğru yere, doğru işleme ve doğru personele aktarın." : "Biriminize ulaşan dosyaları göreve dönüştürün ve sonuçlandırın."}</p></div><Link className="btn btn-primary" to="/dosyalar">Çalışma listesine git <ArrowRight size={17}/></Link></header>
    <section className="case-stat-grid operations-kpis">{stats.map((s) => <article key={s.label}><span><s.icon/></span><div><strong>{loading ? "—" : s.value}</strong><small>{s.label}</small></div></article>)}</section>
    {registry ? <section className="case-panel operations-table-panel"><header><div><span className="eyebrow">AI HAVALE ÖNERİLERİ</span><h2>İnsan kararı bekleyen dosyalar</h2></div><Link to="/dosyalar?status=READY_TO_ROUTE">Tümünü gör</Link></header>{loading ? <div className="case-loading">Öneriler yükleniyor…</div> : routingItems.length ? <div className="operations-table" role="table"><div className="operations-table-head" role="row"><span>Evrak / Konu</span><span>Önerilen birim</span><span>Gerekçe</span><span>Öncelik</span><span>Aksiyon</span></div>{routingItems.map((item) => <div role="row" key={item.id}><span><b>{item.tracking_code}</b><small>{item.title}</small></span><strong>{item.routing_recommendation!.recommended_unit}</strong><p>{item.routing_recommendation!.reason}</p><em>{item.priority || "Normal"}</em><Link className="btn btn-secondary" to={`/dosya/${item.id}`}>{item.routing_recommendation!.recommended_unit} birimine havale</Link></div>)}</div> : <EmptyState title="Havale önerisi bekleyen dosya yok" text="Yalnız backend tarafından üretilmiş gerçek yönlendirme önerileri burada görünür."/>}</section>
      : <section className="case-panel operations-table-panel"><header><div><span className="eyebrow">BUGÜNÜN İŞLERİ</span><h2>Evrak değil, tamamlanacak görevler</h2></div><Link to="/dosyalar?view=assigned">Tümünü gör</Link></header>{loading ? <div className="case-loading">Birim işleri yükleniyor…</div> : tasks.length ? <div className="department-task-list">{tasks.map((item) => <Link to={`/dosya/${item.id}`} key={item.id}><span className="task-icon"><ClipboardCheck/></span><div><strong>{item.title}</strong><small>{item.analysis_summary || item.tracking_code}</small></div><div><b>{item.workflow_status === "IN_DEPARTMENT" ? "Dosyayı işleme al" : item.workflow_status === "IN_PROGRESS" ? "Kurum işlemini tamamla" : "Cevabı incele"}</b><StatusBadge status={item.workflow_status}/></div></Link>)}</div> : <EmptyState title="Bugün bekleyen iş yok" text="Biriminize atanmış açık bir görev bulunmuyor."/>}</section>}
    <section className="case-panel evrag-today"><header><div><span className="eyebrow">EVRAG BUGÜN</span><h2>İnsan emeğini doğru karara odaklayan işlemler</h2></div></header><div><span><strong>{items.length}</strong> yetkili dosya</span><span><strong>{items.filter((x) => x.routing_recommendation).length}</strong> havale önerisi</span><span><strong>{items.filter(missing).length}</strong> erken eksik bilgi tespiti</span><span><strong>{items.filter((x) => x.drafts?.length).length}</strong> resmî yazı süreci</span></div><small>Yalnız mevcut Case API verilerinden hesaplanır.</small></section>
  </>;
}
