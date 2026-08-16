import React, { useState } from 'react';
import { FileUpload } from '../components/upload/FileUpload';
import { TextUpload } from '../components/upload/TextUpload';
import { analyzeText, uploadDocument } from '../services/documents';
import { ApiError } from '../types/api';

interface NewDocumentPageProps {
  onAnalysisComplete: (analysisId: string) => void;
}

export function NewDocumentPage({ onAnalysisComplete }: NewDocumentPageProps) {
  const [activeTab, setActiveTab] = useState<'upload' | 'text'>('upload');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const handleUpload = async (file: File) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await uploadDocument(file);
      onAnalysisComplete(res.analysis_id);
    } catch (err: any) {
      setError(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnalyzeText = async (text: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await analyzeText(text);
      onAnalysisComplete(res.analysis_id);
    } catch (err: any) {
      setError(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.5rem', color: 'var(--primary)', marginBottom: '0.5rem' }}>Yeni Evrak İşlemi</h2>
        <p style={{ color: 'var(--text-muted)' }}>Sisteme yeni bir evrak yükleyin veya metnini yapıştırarak analiz edin.</p>
      </div>

      <div className="tabs">
        <button 
          className={`tab ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveTab('upload')}
        >
          Dosya Yükle
        </button>
        <button 
          className={`tab ${activeTab === 'text' ? 'active' : ''}`}
          onClick={() => setActiveTab('text')}
        >
          Metin ile Analiz
        </button>
      </div>

      {error && (
        <div className="alert alert-danger">
          <strong>Hata:</strong> {error.message}
        </div>
      )}

      {isLoading && (
        <div className="alert alert-warning" style={{ backgroundColor: '#eff6ff', borderColor: '#bfdbfe', color: '#1e40af' }}>
          <strong>Bilgi:</strong> Evrak sınıflandırma, bilgi çıkarma, mevzuat analizi ve taslak oluşturma adımları yürütülüyor. Lütfen bekleyin...
        </div>
      )}

      {activeTab === 'upload' ? (
        <FileUpload onUpload={handleUpload} isLoading={isLoading} />
      ) : (
        <TextUpload onAnalyze={handleAnalyzeText} isLoading={isLoading} />
      )}
    </div>
  );
}
