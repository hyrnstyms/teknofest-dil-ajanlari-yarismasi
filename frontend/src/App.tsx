import React, { useState } from 'react';
import { Header } from './components/Header';
import { InputPanel } from './components/InputPanel';
import { ProcessingTimeline } from './components/ProcessingTimeline';
import { Dashboard } from './components/Dashboard';
import { api } from './services/api';
import { DocumentState } from './types';
import './index.css';
import { AlertCircle } from 'lucide-react';
import { ChatWidget } from './components/chat/ChatWidget';

function App() {
  const [appState, setAppState] = useState<DocumentState | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyzeText = async (text: string) => {
    resetState();
    setIsLoading(true);
    try {
      const result = await api.analyzeText(text);
      setAppState(result);
    } catch (err: any) {
      setError(err.message || "Analiz sırasında bir hata oluştu.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleUploadFile = async (file: File) => {
    resetState();
    setIsLoading(true);
    try {
      const result = await api.uploadDocument(file);
      setAppState(result);
    } catch (err: any) {
      setError(err.message || "Dosya yüklenirken bir hata oluştu.");
    } finally {
      setIsLoading(false);
    }
  };

  const resetState = () => {
    setAppState(null);
    setError(null);
  };

  // Mock a refresh action for the HumanReviewPanel if needed
  // In a real app we might fetch the specific analysis ID again
  const handleUpdate = () => {
    // A simple hack to force re-render, assuming local state mutation in API was handled 
    // or we can just update the state locally since we know it succeeded
    if (appState) {
      // For MVP, just refreshing the page or leaving it as is might be enough, 
      // but let's just create a new object reference to force render
      setAppState({ ...appState });
    }
  };

  const handleChatDraftUpdated = (updatedDraft: DocumentState["draft"]) => {
    setAppState((previous) =>
      previous ? { ...previous, draft: updatedDraft } : previous
    );
  };

  return (
    <div className="container">
      <Header />
      
      <InputPanel 
        onAnalyzeText={handleAnalyzeText} 
        onUploadFile={handleUploadFile} 
        isLoading={isLoading} 
      />

      {error && (
        <div className="card mb-6" style={{ borderColor: 'var(--error-color)' }}>
          <div className="card-body bg-red-50 flex items-center gap-3 text-error">
            <AlertCircle />
            <div>
              <p className="font-medium">İşlem Başarısız</p>
              <p className="text-sm">{error}</p>
            </div>
          </div>
        </div>
      )}

      {(isLoading || appState) && (
        <ProcessingTimeline 
          nodeTimings={appState?.node_timings || {}} 
          isLoading={isLoading} 
        />
      )}

      {appState && (
        <Dashboard state={appState} onUpdate={handleUpdate} />
      )}

      <ChatWidget
        analysisId={appState?.analysis_id}
        currentDraft={appState?.draft}
        onDraftUpdated={handleChatDraftUpdated}
      />
    </div>
  );
}

export default App;
