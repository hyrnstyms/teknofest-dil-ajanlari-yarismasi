import React, { useCallback, useState } from 'react';
import { BrowserRouter, Routes, Route, useMatch } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { HomePage } from './pages/HomePage';
import { NewDocumentPage } from './pages/NewDocumentPage';
import { DocumentWorkspacePage } from './pages/DocumentWorkspacePage';
import { InboxPage } from './pages/InboxPage';
import { AdminPage } from './pages/AdminPage';
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
            <Route path="/gelen-evraklar" element={<InboxPage />} />
            <Route path="/yonetici" element={<AdminPage />} />
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
