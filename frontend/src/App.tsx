import React, { useCallback, useMemo, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes, useMatch, useNavigate } from "react-router-dom";
import { ChatWidget } from "./components/chat/ChatWidget";
import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { AIOperationsPage } from "./pages/AIOperationsPage";
import { CaseInboxPage } from "./pages/CaseInboxPage";
import { CaseWorkspacePage } from "./pages/CaseWorkspacePage";
import { CitizenTracePage } from "./pages/CitizenTracePage";
import { QrVerifyPage } from "./pages/QrVerifyPage";
import { AdminPage } from "./pages/AdminPage";
import { DemoLoginPage } from "./pages/DemoLoginPage";
import { DocumentWorkspacePage } from "./pages/DocumentWorkspacePage";
import { InstitutionDirectoryPage } from "./pages/InstitutionDirectoryPage";
import { NewDocumentPage } from "./pages/NewDocumentPage";
import { RoleHomePage } from "./pages/RoleHomePage";
import type { DocumentState } from "./types";
import type { InstitutionOption } from "./services/api";
import "./index.css";
import "./case-ui.css";
function App() { return <BrowserRouter><AuthProvider><Routes><Route path="/takip/:trackingCode" element={<CitizenTracePage/>}/><Route path="/dogrulama/:id" element={<QrVerifyPage/>}/><Route path="*" element={<AuthenticatedShell/>}/></Routes></AuthProvider></BrowserRouter>; }
function AuthenticatedShell() { const { user, loading } = useAuth(); if (loading) return <div className="app-boot">EVRAG güvenli oturumu doğrulanıyor…</div>; if (!user) return <DemoLoginPage/>; return <WorkspaceShell/>; }
function WorkspaceShell() { const { user } = useAuth(); const navigate = useNavigate(); const legacyMatch = useMatch("/evrak/:id"); const caseMatch = useMatch("/dosya/:id"); const [activeAnalysisId, setActiveAnalysisId] = useState<string>(); const [activeDraft, setActiveDraft] = useState<DocumentState["draft"]>(); const [copilotOpenSignal, setCopilotOpenSignal] = useState(0); const institution = useMemo<InstitutionOption>(() => ({ id: user!.institution_id, label: user!.institution_id === "belediye" ? "Belediye" : user!.institution_id, ui_config: { description: user!.department_name || user!.department_code } }), [user]); const handleAnalysisLoaded = useCallback((state: DocumentState) => { setActiveAnalysisId(state.analysis_id || state.document_id); setActiveDraft(state.draft); }, []); const chatAnalysisId = legacyMatch?.params.id === activeAnalysisId ? activeAnalysisId : undefined; return <><div className="app-layout"><Sidebar role={user!.role} onOpenCopilot={() => setCopilotOpenSignal((v) => v + 1)}/><div className="app-main"><TopBar user={user!}/><main className="main-content"><Routes><Route path="/" element={<RoleHomePage/>}/><Route path="/dosyalar" element={<CaseInboxPage/>}/><Route path="/gecmis" element={<CaseInboxPage history/>}/><Route path="/dosya/:id" element={<CaseWorkspacePage/>}/><Route path="/kurum-rehberi" element={<InstitutionDirectoryPage/>}/><Route path="/yeni-evrak" element={<NewDocumentPage institution={institution} onAnalysisLoaded={handleAnalysisLoaded}/>}/><Route path="/evrak/:id" element={<DocumentWorkspacePage onAnalysisLoaded={handleAnalysisLoaded} externallyUpdatedDraft={activeDraft}/>}/><Route path="/ai-operasyon" element={<AIOperationsPage institution={institution} onOpenAnalysis={(id) => navigate(`/evrak/${id}`)}/>}/><Route path="/yonetici" element={<AdminPage/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Routes></main></div></div><ChatWidget analysisId={chatAnalysisId} caseId={caseMatch?.params.id} currentDraft={chatAnalysisId ? activeDraft : undefined} institutionId={user!.institution_id} institutionLabel={institution.label} onDraftUpdated={setActiveDraft} openSignal={copilotOpenSignal}/></>; }
export default App;
