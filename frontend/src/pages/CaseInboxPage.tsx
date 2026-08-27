import React, { useEffect, useState } from "react";
import { ArrowRight, CalendarClock, UserRound } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { EmptyState, StatusBadge } from "../components/case/CasePrimitives";
import { useAuth } from "../contexts/AuthContext";
import { caseApi } from "../services/caseApi";
import type { CaseRecord } from "../types/case";

const sourceLabels: Record<CaseRecord["source_type"], string> = { VATANDAS: "Vatandaş", DIS_KURUM: "Dış Kurum", KURUM_ICI: "Kurum İçi" };
const channelLabels: Record<CaseRecord["source_channel"], string> = { WEB_FORM: "Web Formu", FIZIKI_EVRAK: "Fiziksel Evrak", EPOSTA: "E-posta", KEP: "KEP", EBYS: "EBYS", KURUM_ICI: "Kurum İçi" };
const deadlineRiskLabels = { NORMAL: "Normal", APPROACHING: "Yaklaşıyor", CRITICAL: "Kritik", OVERDUE: "Süresi Geçti", UNKNOWN: "Belirsiz" };
const preRouteStatuses = new Set(["RECEIVED", "ANALYZING", "WAITING_INITIAL_REVIEW", "WAITING_CITIZEN_INFO", "READY_TO_ROUTE"]);

export function CaseInboxPage({ history = false }: { history?: boolean }) {
  const { token, user } = useAuth();
  const [params] = useSearchParams();
  const [items, setItems] = useState<CaseRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    const query = history ? "scope=history" : params.toString();
    setLoading(true);
    setError("");
    void caseApi.inbox(token, query)
      .then((response) => setItems(response.items))
      .catch((cause) => setError(cause.message))
      .finally(() => setLoading(false));
  }, [token, params, history]);

  return <div className="case-page">
    <header className="case-page-heading"><div><span className="eyebrow">{user?.role === "EVRAK_KAYIT" ? "Kurum evrak havuzu" : user?.department_name || "Birim dosyaları"}</span><h1>{history ? "İşlem Geçmişi" : user?.role === "EVRAK_KAYIT" ? "Gelen Evrak Havuzu" : "Birim Dosyaları"}</h1><p>{history ? "Havale edilmiş dosyalar dahil kurumun işlem ve denetim geçmişi." : "Liste backend tarafından kurum, rol ve birim yetkinize göre filtrelenir."}</p></div></header>
    {error && <div className="case-error" role="alert">{error}</div>}
    {loading
      ? <div className="case-loading">Dosyalar yükleniyor…</div>
      : error
        ? null
        : items.length === 0
          ? <EmptyState title="Bu görünümde dosya yok" text="Filtreye ve yetki kapsamınıza uygun bir kayıt bulunamadı."/>
          : <section className="case-card-grid">{items.map((item) => <article className="case-card" key={item.id}>
            <header><span>{item.tracking_code}</span><StatusBadge status={item.workflow_status}/></header>
            <h2>{item.title}</h2>
            <dl>
              <div><dt><UserRound/> Kaynak</dt><dd>{sourceLabels[item.source_type]} · {channelLabels[item.source_channel]}</dd></div>
              <div><dt>Başvuru sahibi</dt><dd>{item.originator_name}</dd></div>
              <div><dt>Mevcut sahip</dt><dd>{item.current_department_name}</dd></div>
              {item.routing_recommendation && preRouteStatuses.has(item.workflow_status) && <div className="ai-recommendation-row"><dt>Yönlendirme önerisi</dt><dd>{item.routing_recommendation.recommended_unit}</dd></div>}
              <div><dt><CalendarClock/> Alınma</dt><dd>{new Date(item.received_at).toLocaleDateString("tr-TR")}</dd></div>
              {item.deadline?.applicable && item.deadline.legal_basis?.verified && <div><dt>Yasal süre</dt><dd>{item.deadline.deadline_days} gün · {deadlineRiskLabels[item.deadline.risk_level]}</dd></div>}
            </dl>
            <Link to={`/dosya/${item.id}`}>Dosyayı aç <ArrowRight size={16}/></Link>
          </article>)}</section>}
  </div>;
}
