import React, { useCallback, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes, useMatch, useNavigate } from "react-router-dom";
import { Building2 } from "lucide-react";
import { AdminDashboard } from "./components/AdminDashboard";
import { ChatWidget } from "./components/chat/ChatWidget";
import { EntryLanding } from "./components/EntryLanding";
import { InstitutionSelector } from "./components/InstitutionSelector";
import { DraftsPage, IncomingDocumentsPage, ReviewQueuePage } from "./components/RecordViews";
import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { DocumentWorkspacePage } from "./pages/DocumentWorkspacePage";
import { HomePage } from "./pages/HomePage";
import { NewDocumentPage } from "./pages/NewDocumentPage";
import { AIOperationsPage } from "./pages/AIOperationsPage";
import { api, type InstitutionOption } from "./services/api";
import type { DocumentState } from "./types";
import "./index.css";

const ENTRY_SESSION_KEY = "kamuai:desk-entered";
const INSTITUTION_SESSION_KEY = "kamuai:institution";

function readStoredInstitution(): InstitutionOption | null {
  try {
    const value = window.sessionStorage.getItem(INSTITUTION_SESSION_KEY);
    return value ? JSON.parse(value) as InstitutionOption : null;
  } catch {
    return null;
  }
}

function canonicalInstitutionId(value: unknown): string {
  return String(value || "").trim().replace(/_v\d+$/i, "");
}

function App() {
  return <BrowserRouter><AppShell /></BrowserRouter>;
}

function AppShell() {
  const navigate = useNavigate();
  const workspaceMatch = useMatch("/evrak/:id");
  const [hasEntered, setHasEntered] = useState(
    () => window.sessionStorage.getItem(ENTRY_SESSION_KEY) === "true",
  );
  const [institution, setInstitution] = useState<InstitutionOption | null>(
    readStoredInstitution,
  );
  const [activeAnalysisId, setActiveAnalysisId] = useState<string>();
  const [activeDraft, setActiveDraft] = useState<DocumentState["draft"]>();
  const [contextNotice, setContextNotice] = useState<string | null>(null);
  const [copilotOpenSignal, setCopilotOpenSignal] = useState(0);

  const enterApplication = useCallback((target = "/") => {
    window.sessionStorage.setItem(ENTRY_SESSION_KEY, "true");
    setHasEntered(true);
    navigate(target);
  }, [navigate]);

  const handleAnalysisLoaded = useCallback((state: DocumentState) => {
    setActiveAnalysisId(state.analysis_id || state.document_id);
    setActiveDraft(state.draft);

    const institutionId = canonicalInstitutionId(state.kurum_profili_id);
    if (!institutionId) return;
    void api.listInstitutionOptions()
      .then((options) => {
        const matchingInstitution = options.find((option) => option.id === institutionId);
        if (!matchingInstitution) return;
        setInstitution(matchingInstitution);
        window.sessionStorage.setItem(
          INSTITUTION_SESSION_KEY,
          JSON.stringify(matchingInstitution),
        );
      })
      .catch(() => {
        // Analiz görünümü kurum listesi geçici olarak alınamasa da çalışmaya devam eder.
      });
  }, []);

  const handleInstitutionChange = useCallback((selected: InstitutionOption | null) => {
    setInstitution((current) => {
      const changed = Boolean(current?.id && current.id !== selected?.id);
      if (selected) {
        window.sessionStorage.setItem(INSTITUTION_SESSION_KEY, JSON.stringify(selected));
      } else {
        window.sessionStorage.removeItem(INSTITUTION_SESSION_KEY);
      }
      if (changed) {
        setActiveAnalysisId(undefined);
        setActiveDraft(undefined);
        setContextNotice("Kurum profili değişti; önceki aktif evrak bağlamı temizlendi.");
        if (workspaceMatch) navigate("/");
      } else {
        setContextNotice(null);
      }
      return selected;
    });
  }, [navigate, workspaceMatch]);

  const handleOpenAnalysis = useCallback((analysisId: string) => {
    navigate(`/evrak/${analysisId}`);
  }, [navigate]);

  const chatAnalysisId = workspaceMatch?.params.id === activeAnalysisId
    ? activeAnalysisId
    : undefined;
  const chatDraft = chatAnalysisId ? activeDraft : undefined;

  if (!hasEntered) {
    return (
      <EntryLanding
        onEnterDesk={() => enterApplication("/")}
        onEnterAdmin={() => enterApplication("/yonetici")}
      />
    );
  }

  return (
    <>
      <div className="app-layout">
        <Sidebar onOpenCopilot={() => setCopilotOpenSignal((value) => value + 1)} />
        <div className="app-main">
          <TopBar institutionSelector={(
            <InstitutionSelector
              topbar
              value={institution?.id ?? ""}
              onChange={handleInstitutionChange}
              disabled={false}
            />
          )} />
          <main className="main-content">
            {contextNotice && (
              <div className="context-notice no-print" role="status">
                <Building2 size={18} /><span>{contextNotice}</span>
              </div>
            )}
            <Routes>
              <Route path="/" element={<HomePage institution={institution} />} />
              <Route path="/yeni-evrak" element={<NewDocumentPage institution={institution} onAnalysisLoaded={handleAnalysisLoaded} />} />
              <Route path="/evrak/:id" element={<DocumentWorkspacePage onAnalysisLoaded={handleAnalysisLoaded} externallyUpdatedDraft={chatDraft} />} />
              <Route path="/gelen-evraklar" element={<IncomingDocumentsPage onOpenAnalysis={handleOpenAnalysis} />} />
              <Route path="/taslaklar" element={<DraftsPage onOpenAnalysis={handleOpenAnalysis} />} />
              <Route path="/inceleme-bekleyenler" element={<ReviewQueuePage onOpenAnalysis={handleOpenAnalysis} />} />
              <Route path="/yonetici" element={<AdminDashboard onOpenAnalysis={handleOpenAnalysis} />} />
              <Route path="/ai-operasyon" element={<AIOperationsPage institution={institution} onOpenAnalysis={handleOpenAnalysis} />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </div>
      <ChatWidget
        analysisId={chatAnalysisId}
        currentDraft={chatDraft}
        institutionId={institution?.id}
        institutionLabel={institution?.label}
        onDraftUpdated={setActiveDraft}
        openSignal={copilotOpenSignal}
      />
    </>
  );
}

export default App;
