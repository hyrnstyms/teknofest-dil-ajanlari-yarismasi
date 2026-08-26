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
import type { InstitutionOption } from "./services/api";
import type { DocumentState } from "./types";
import "./index.css";

function App() { return <BrowserRouter><AppShell /></BrowserRouter>; }

function AppShell() {
  const navigate = useNavigate();
  const workspaceMatch = useMatch("/evrak/:id");
  const [hasEntered, setHasEntered] = useState(false);
  const [institution, setInstitution] = useState<InstitutionOption | null>(null);
  const [activeAnalysisId, setActiveAnalysisId] = useState<string>();
  const [activeDraft, setActiveDraft] = useState<DocumentState["draft"]>();
  const [contextNotice, setContextNotice] = useState<string | null>(null);

  const handleAnalysisLoaded = useCallback((state: DocumentState) => {
    setActiveAnalysisId(state.analysis_id || state.document_id);
    setActiveDraft(state.draft);
  }, []);
  const handleInstitutionChange = useCallback((selected: InstitutionOption | null) => {
    setInstitution((current) => {
      if (current?.id && current.id !== selected?.id) {
        setActiveAnalysisId(undefined); setActiveDraft(undefined);
        setContextNotice("Kurum profili değişti; önceki aktif evrak bağlamı temizlendi.");
      } else setContextNotice(null);
      return selected;
    });
  }, []);
  const handleOpenAnalysis = useCallback((analysisId: string) => navigate(`/evrak/${analysisId}`), [navigate]);
  const chatAnalysisId = workspaceMatch?.params.id === activeAnalysisId ? activeAnalysisId : undefined;
  const chatDraft = chatAnalysisId ? activeDraft : undefined;

  if (!hasEntered) return <EntryLanding onEnterDesk={() => setHasEntered(true)} onEnterAdmin={() => { setHasEntered(true); navigate("/yonetici"); }} />;

  return <>
    <div className="app-layout"><Sidebar /><div className="app-main">
      <TopBar institutionSelector={<InstitutionSelector topbar value={institution?.id ?? ""} onChange={handleInstitutionChange} disabled={false} />} />
      <main className="main-content">
        {contextNotice && <div className="context-notice no-print" role="status"><Building2 size={18} /><span>{contextNotice}</span></div>}
        <Routes>
          <Route path="/" element={<HomePage institution={institution} />} />
          <Route path="/yeni-evrak" element={<NewDocumentPage institution={institution} onAnalysisLoaded={handleAnalysisLoaded} />} />
          <Route path="/evrak/:id" element={<DocumentWorkspacePage onAnalysisLoaded={handleAnalysisLoaded} externallyUpdatedDraft={chatDraft} />} />
          <Route path="/gelen-evraklar" element={<IncomingDocumentsPage onOpenAnalysis={handleOpenAnalysis} />} />
          <Route path="/taslaklar" element={<DraftsPage onOpenAnalysis={handleOpenAnalysis} />} />
          <Route path="/inceleme-bekleyenler" element={<ReviewQueuePage onOpenAnalysis={handleOpenAnalysis} />} />
          <Route path="/yonetici" element={<AdminDashboard onOpenAnalysis={handleOpenAnalysis} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div></div>
    <ChatWidget analysisId={chatAnalysisId} currentDraft={chatDraft} institutionId={institution?.id} institutionLabel={institution?.label} onDraftUpdated={setActiveDraft} />
  </>;
}
export default App;
