import React, { useEffect, useState } from "react";
import { RoleOperationsDashboard } from "../components/case/RoleOperationsDashboard";
import { DemoScenarioCenter } from "../components/demo/DemoScenarioCenter";
import { useAuth } from "../contexts/AuthContext";
import { caseApi } from "../services/caseApi";
import type { CaseRecord } from "../types/case";

export function RoleOperationsPage() {
  const { user, token } = useAuth();
  const [items, setItems] = useState<CaseRecord[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!token) return;
    void caseApi.inbox(token).then((response) => setItems(response.items)).catch((cause) => setError(cause.message)).finally(() => setLoading(false));
  }, [token]);
  if (!user) return null;
  return <div className="case-page role-operations-home">
    <RoleOperationsDashboard user={user} items={items} loading={loading || Boolean(error)}/>
    {error && <div className="case-error" role="alert">{error}</div>}
    {user.role === "EVRAK_KAYIT" && token && <DemoScenarioCenter token={token}/>} 
  </div>;
}
