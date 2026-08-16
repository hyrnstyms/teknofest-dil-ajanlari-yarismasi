import React, { useState } from 'react';
import { Layout } from './components/layout/Layout';
import { NewDocumentPage } from './pages/NewDocumentPage';
import { AnalysisPage } from './pages/AnalysisPage';
import { SystemStatusPage } from './pages/SystemStatusPage';
import { PerformancePage } from './pages/PerformancePage';
import { DocumentsPage } from './pages/DocumentsPage';
import { ReviewQueuePage } from './pages/ReviewQueuePage';

function App() {
  const [currentPath, setCurrentPath] = useState('new');
  const [analysisId, setAnalysisId] = useState<string | null>(null);

  const handleNavigate = (path: string) => {
    setCurrentPath(path);
  };

  const handleAnalysisComplete = (id: string) => {
    setAnalysisId(id);
    setCurrentPath('analysis');
  };

  const navigateToAnalysis = (id: string) => {
    setAnalysisId(id);
    setCurrentPath('analysis');
  };

  return (
    <Layout currentPath={currentPath} onNavigate={handleNavigate}>
      {currentPath === 'new' && (
        <NewDocumentPage onAnalysisComplete={handleAnalysisComplete} />
      )}
      {currentPath === 'analysis' && analysisId && (
        <AnalysisPage analysisId={analysisId} />
      )}
      {currentPath === 'analysis' && !analysisId && (
        <div className="alert alert-warning">
          Lütfen önce bir evrak analiz edin.
        </div>
      )}
      {currentPath === 'documents' && <DocumentsPage onNavigateToAnalysis={navigateToAnalysis} />}
      {currentPath === 'review-queue' && <ReviewQueuePage onNavigateToAnalysis={navigateToAnalysis} />}
      {currentPath === 'status' && <SystemStatusPage />}
      {currentPath === 'performance' && <PerformancePage />}
    </Layout>
  );
}

export default App;
