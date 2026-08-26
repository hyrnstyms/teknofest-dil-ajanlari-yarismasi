import React, { useCallback, useState } from 'react';
import { BrowserRouter, Navigate, Routes, Route, useMatch, useNavigate } from 'react-router-dom';
import { AdminDashboard } from './components/AdminDashboard';
import { DraftsPage, IncomingDocumentsPage, ReviewQueuePage } from './components/RecordViews';
import { Sidebar } from './components/Sidebar';
import { HomePage } from './pages/HomePage';
import { NewDocumentPage } from './pages/NewDocumentPage';
import { DocumentWorkspacePage } from './pages/DocumentWorkspacePage';
import { ChatWidget } from './components/chat/ChatWidget';
import { DocumentState } from './types';
import './index.css';

function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  );
}

function AppShell() {
  const navigate = useNavigate();
  // ChatWidget state — lives at App level, outside routes
  const [activeAnalysisId, setActiveAnalysisId] = useState<string | undefined>(undefined);
  const [activeDraft, setActiveDraft] = useState<DocumentState["draft"] | undefined>(undefined);
  const workspaceMatch = useMatch('/evrak/:id');

  const handleAnalysisLoaded = useCallback((state: DocumentState) => {
    setActiveAnalysisId(state.analysis_id);
    setActiveDraft(state.draft);
  }, []);

  const handleChatDraftUpdated = useCallback((updatedDraft: DocumentState["draft"]) => {
    setActiveDraft(updatedDraft);
  }, []);

  const handleOpenAnalysis = useCallback((analysisId: string) => {
    navigate(`/evrak/${analysisId}`);
  }, [navigate]);

  const chatAnalysisId = workspaceMatch?.params.id === activeAnalysisId
    ? activeAnalysisId
    : undefined;
  const chatDraft = chatAnalysisId ? activeDraft : undefined;

  return (
    <>
      <div className="app-layout">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route
              path="/yeni-evrak"
              element={
                <NewDocumentPage
                  onAnalysisLoaded={handleAnalysisLoaded}
                />
              }
            />
            <Route
              path="/evrak/:id"
              element={
                <DocumentWorkspacePage
                  onAnalysisLoaded={handleAnalysisLoaded}
                  externallyUpdatedDraft={chatDraft}
                />
              }
            />
            <Route path="/gelen-evraklar" element={<IncomingDocumentsPage onOpenAnalysis={handleOpenAnalysis} />} />
            <Route path="/taslaklar" element={<DraftsPage onOpenAnalysis={handleOpenAnalysis} />} />
            <Route path="/inceleme-bekleyenler" element={<ReviewQueuePage onOpenAnalysis={handleOpenAnalysis} />} />
            <Route path="/yonetici" element={<AdminDashboard onOpenAnalysis={handleOpenAnalysis} />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>

      {/* Route içeriklerinin dışında; bütün sayfalarda görünür. */}
      <ChatWidget
        analysisId={chatAnalysisId}
        currentDraft={chatDraft}
        onDraftUpdated={handleChatDraftUpdated}
      />
    </>
  );
}

export default App;
