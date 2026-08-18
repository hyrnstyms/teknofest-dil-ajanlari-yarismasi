import React, { useState } from 'react';
import { FileUpload } from '../components/upload/FileUpload';
import { TextUpload } from '../components/upload/TextUpload';
import { analyzeText, uploadDocument } from '../services/documents';
import { ApiError } from '../types/api';
import { FileText, Type } from 'lucide-react';
import { Card } from '../components/ui/Card';

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
    <div className="page-container flex flex-col gap-6 h-full pb-8">
      
      {error && (
        <div className="p-4 bg-danger-light text-danger rounded-md border border-danger">
          <strong>Hata:</strong> {error.message}
        </div>
      )}

      {isLoading && (
        <div className="p-4 bg-info-light text-info rounded-md border border-info flex items-center gap-3">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-info flex-shrink-0"></div>
          <span><strong>Bilgi:</strong> Evrak sınıflandırma, bilgi çıkarma, mevzuat analizi ve taslak oluşturma adımları yürütülüyor. Lütfen bekleyin...</span>
        </div>
      )}

      <div className="flex justify-center mb-4">
        <div className="segmented-control">
          <button 
            className={`segmented-btn flex items-center justify-center gap-2 ${activeTab === 'upload' ? 'active' : ''}`}
            onClick={() => setActiveTab('upload')}
          >
            <FileText size={18} />
            Dosya Yükle
          </button>
          <button 
            className={`segmented-btn flex items-center justify-center gap-2 ${activeTab === 'text' ? 'active' : ''}`}
            onClick={() => setActiveTab('text')}
          >
            <Type size={18} />
            Metin ile Analiz
          </button>
        </div>
      </div>

      <div className="flex justify-center">
        <div className="w-full" style={{ maxWidth: '600px' }}>
          {activeTab === 'upload' ? (
            <FileUpload onUpload={handleUpload} isLoading={isLoading} />
          ) : (
            <TextUpload onAnalyze={handleAnalyzeText} isLoading={isLoading} />
          )}
        </div>
      </div>
    </div>
  );
}


