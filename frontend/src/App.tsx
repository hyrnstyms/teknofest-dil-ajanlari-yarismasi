import React, { useState } from "react";
import { AlertCircle, FilePlus2, FileSearch } from "lucide-react";
import { AdminDashboard } from "./components/AdminDashboard";
import { ChatWidget } from "./components/chat/ChatWidget";
import { DocumentWorkspace } from "./components/DocumentWorkspace";
import { HomeDashboard } from "./components/HomeDashboard";
import { InputPanel } from "./components/InputPanel";
import { InstitutionSelector } from "./components/InstitutionSelector";
import { DraftsPage, IncomingDocumentsPage, ReviewQueuePage } from "./components/RecordViews";
import { Sidebar, type AppView } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { api, type InstitutionOption } from "./services/api";
import type { DocumentState } from "./types";
import "./index.css";

function App() {
  const [appState, setAppState] = useState<DocumentState | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [institution, setInstitution] = useState<InstitutionOption | null>(null);
  const [view, setView] = useState<AppView>("home");

  const prepareAnalysis = (): boolean => {
    setError(null);
    if (!institution) {
      setError("Analize başlamadan önce bir kurum seçin.");
      return false;
    }
    setAppState(null);
    setIsLoading(true);
    return true;
  };

  const handleAnalyzeText = async (text: string) => {
    if (!prepareAnalysis() || !institution) return;
    try {
      setAppState(await api.analyzeText(text, institution.id));
      setView("document-workspace");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Analiz sırasında bir hata oluştu.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleUploadFile = async (file: File) => {
    if (!prepareAnalysis() || !institution) return;
    try {
      setAppState(await api.uploadDocument(file, institution.id));
      setView("document-workspace");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Dosya yüklenirken bir hata oluştu.");
    } finally {
      setIsLoading(false);
    }
  };

  const refreshAnalysis = async () => {
    if (!appState?.analysis_id) return;
    try {
      setAppState(await api.getAnalysis(appState.analysis_id));
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "Analiz güncellenemedi.");
    }
  };

  const handleOpenAnalysis = async (analysisId: string) => {
    setError(null);
    try {
      const result = await api.getAnalysis(analysisId);
      setAppState(result);
      setView("document-workspace");
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Analiz kaydı açılamadı.");
    }
  };

  const handleChatDraftUpdated = (updatedDraft: DocumentState["draft"]) => {
    setAppState((previous) => previous ? { ...previous, draft: updatedDraft } : previous);
    void refreshAnalysis();
  };

  return (
    <div className="app-shell">
      <Sidebar
        activeView={view}
        onViewChange={setView}
      />

      <div className="app-main">
        <TopBar institutionSelector={(
          <InstitutionSelector
            topbar
            value={institution?.id ?? ""}
            onChange={(selected) => {
              setInstitution(selected);
              setAppState(null);
              setError(null);
            }}
            disabled={isLoading}
          />
        )} />
        <div className="app-content">
          {error && (
            <div className="inline-error no-print" role="alert">
              <AlertCircle size={20} /><div><strong>İşlem tamamlanamadı</strong><span>{error}</span></div>
            </div>
          )}

          {view === "admin" ? (
            <AdminDashboard onOpenAnalysis={handleOpenAnalysis} />
          ) : view === "incoming" ? (
            <IncomingDocumentsPage onOpenAnalysis={handleOpenAnalysis} />
          ) : view === "drafts" ? (
            <DraftsPage onOpenAnalysis={handleOpenAnalysis} />
          ) : view === "reviews" ? (
            <ReviewQueuePage onOpenAnalysis={handleOpenAnalysis} />
          ) : view === "new-document" ? (
            <section className="upload-view no-print">
              <div className="view-heading">
                <span className="section-kicker">Yeni işlem</span>
                <h1>Yeni Evrak Yükle</h1>
                <p>Dosya yükleyin veya evrak metnini yapıştırın. Analiz seçili kurum profiliyle çalıştırılır.</p>
                <span className="selected-context">Kurum: <strong>{institution?.label || "Seçilmedi"}</strong></span>
              </div>
              <InputPanel
                onAnalyzeText={handleAnalyzeText}
                onUploadFile={handleUploadFile}
                isLoading={isLoading}
                uploadLabel={institution?.ui_config.upload_label}
              />
            </section>
          ) : view === "document-workspace" ? (
            appState ? (
              <DocumentWorkspace state={appState} onUpdate={refreshAnalysis} />
            ) : (
              <div className="workspace-empty no-print">
                <FileSearch size={38} />
                <h2>Henüz analiz edilmiş evrak yok</h2>
                <p>Resmî yazı çalışma alanını açmak için yeni bir evrak yükleyin.</p>
                <button type="button" className="btn btn-primary" onClick={() => setView("new-document")}>
                  <FilePlus2 size={17} /> Yeni Evrak Yükle
                </button>
              </div>
            )
          ) : (
            <HomeDashboard
              institution={institution}
              onNewDocument={() => setView("new-document")}
              onOpenAnalysis={handleOpenAnalysis}
            />
          )}
        </div>
      </div>

      <ChatWidget
        analysisId={appState?.analysis_id}
        currentDraft={appState?.draft}
        onDraftUpdated={handleChatDraftUpdated}
      />
    </div>
  );
}

export default App;
