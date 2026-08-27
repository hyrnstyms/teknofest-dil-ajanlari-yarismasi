import React, { useEffect, useMemo, useState } from "react";
import { FileText, Search } from "lucide-react";
import { Link } from "react-router-dom";
import { OfficialWritingWorkspace } from "../components/case/OfficialWritingWorkspace";
import { useAuth } from "../contexts/AuthContext";
import { caseApi } from "../services/caseApi";
import type { CaseRecord, OfficialWritingListItem } from "../types/case";
import { draftStatusLabels, draftTypeLabels, isResponseDraft, recipientKindLabels } from "../utils/caseDraftPresentation";

const filters = [["ALL", "Tümü"], ["DRAFT", "Taslak"], ["EDITED", "Onay Bekliyor"], ["APPROVED", "Gönderime Hazır"]] as const;

export function OfficialWritingsPage() {
  const { token, user } = useAuth();
  const [items, setItems] = useState<OfficialWritingListItem[]>([]);
  const [filter, setFilter] = useState("ALL");
  const [query, setQuery] = useState("");
  const [selectedCase, setSelectedCase] = useState<CaseRecord>();
  const [error, setError] = useState("");
  const load = () => token ? caseApi.officialWritings(token).then((response) => setItems(response.items)).catch((cause) => setError(cause.message)) : Promise.resolve();
  useEffect(() => { void load(); }, [token]);
  const queue = useMemo(() => {
    const latest = new Map<string, OfficialWritingListItem>();
    items.filter(isResponseDraft).sort((left, right) => String(right.updated_at).localeCompare(String(left.updated_at))).forEach((item) => {
      const key = `${item.case_id}:${item.draft_type}`;
      if (!latest.has(key)) latest.set(key, item);
    });
    return [...latest.values()];
  }, [items]);
  const shown = useMemo(() => queue.filter((item) => (filter === "ALL" || item.draft_status === filter) && `${item.tracking_code} ${item.subject} ${item.recipient}`.toLocaleLowerCase("tr-TR").includes(query.toLocaleLowerCase("tr-TR"))), [queue, filter, query]);
  async function open(item: OfficialWritingListItem) { if (token) setSelectedCase(await caseApi.get(token, item.case_id)); }

  return <div className="case-page official-center">
    <header className="case-page-heading"><div><span className="eyebrow">Case cevap kuyruğu</span><h1>{user?.role === "BIRIM_PERSONELI" ? "Cevaplar" : "Giden Evraklar"}</h1><p>Yetkili olduğunuz case’lere bağlı cevap taslakları, onaylar ve gönderime hazır kayıtlar.</p></div></header>
    <div className="writing-toolbar"><div>{filters.map(([key, label]) => <button className={filter === key ? "active" : ""} onClick={() => setFilter(key)} key={key}>{label}</button>)}</div><label><Search/><input placeholder="Case no, konu veya muhatap" value={query} onChange={(event) => setQuery(event.target.value)}/></label></div>
    {error && <div className="case-error">{error}</div>}
    <div className="official-center-grid"><section className="writing-card-list">{shown.map((item) => <article key={item.id}><span><FileText/></span><div><small>{item.tracking_code} · {item.current_department_name}</small><h2>{item.subject}</h2><p>{recipientKindLabels[item.recipient_kind || ""] || "Muhatap"}: {item.recipient || item.originator_name}</p><em>{draftTypeLabels[item.draft_type]} · {draftStatusLabels[item.draft_status]} · Son işlem {new Date(item.updated_at || item.created_at || Date.now()).toLocaleDateString("tr-TR")}</em></div><div><button className="btn btn-secondary" onClick={() => void open(item)}>İncele</button><Link className="btn btn-secondary" to={`/dosya/${item.case_id}`}>Dosyaya Git</Link></div></article>)}{!error && shown.length === 0 && <p className="case-empty">Bu durumda cevap taslağı bulunmuyor.</p>}</section>{selectedCase && token && <OfficialWritingWorkspace item={{ ...selectedCase, drafts: selectedCase.drafts.filter(isResponseDraft) }} token={token} onRefresh={async () => { setSelectedCase(await caseApi.get(token, selectedCase.id)); await load(); }} onNotice={() => undefined}/>}</div>
  </div>;
}
