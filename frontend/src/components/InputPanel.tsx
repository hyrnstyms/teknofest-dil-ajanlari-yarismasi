import React, { useEffect, useState, useRef } from "react";
import { UploadCloud, FileText, X } from "lucide-react";

interface InputPanelProps {
  onAnalyzeText: (text: string) => void;
  onUploadFile: (file: File) => void;
  isLoading: boolean;
  uploadLabel?: string;
}

export const InputPanel: React.FC<InputPanelProps> = ({
  onAnalyzeText,
  onUploadFile,
  isLoading,
  uploadLabel = "Belge Girişi",
}) => {
  const [text, setText] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const loadingMessages = [
    "Belge okunuyor...",
    "Bilgiler çıkarılıyor...",
    "Mevzuat kontrol ediliyor...",
    "Uygun birim değerlendiriliyor...",
    "Resmî yazı taslağı hazırlanıyor...",
  ];

  useEffect(() => {
    if (!isLoading) {
      setLoadingStep(0);
      return;
    }
    const timer = window.setInterval(() => {
      setLoadingStep((current) => Math.min(current + 1, loadingMessages.length - 1));
    }, 7000);
    return () => window.clearInterval(timer);
  }, [isLoading, loadingMessages.length]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setSelectedFile(e.dataTransfer.files[0]);
      setText("");
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
      setText("");
    }
  };

  const handleSubmit = () => {
    if (selectedFile) {
      onUploadFile(selectedFile);
    } else if (text.trim()) {
      onAnalyzeText(text);
    }
  };

  const handleClearFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="card mb-6">
      <div className="card-header">
        <FileText size={20} className="text-primary" />
        {uploadLabel}
      </div>
      <div className="card-body">
        <div className="dashboard-grid" style={{ marginTop: 0 }}>
          {/* File Upload */}
          <div className="flex-col">
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileChange} 
              style={{ display: 'none' }}
              accept=".pdf,.png,.jpg,.jpeg,.tiff"
            />
            
            {selectedFile ? (
              <div className="upload-area flex flex-col items-center justify-center">
                <div className="badge badge-info mb-4">
                  <FileText size={16} />
                  {selectedFile.name}
                </div>
                <div className="text-secondary mb-4 text-sm">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </div>
                <button className="btn btn-secondary" onClick={handleClearFile} disabled={isLoading}>
                  <X size={16} /> Kaldır
                </button>
              </div>
            ) : (
              <div 
                className={`upload-area ${isDragging ? "drag-over" : ""}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <UploadCloud size={48} className="upload-icon mx-auto" />
                <p className="font-medium">Dosyayı buraya sürükleyin veya tıklayarak seçin</p>
                <p className="text-sm text-secondary mt-2">PDF, PNG, JPG desteklenir</p>
              </div>
            )}
          </div>

          {/* Text Input */}
          <div className="flex-col">
            <textarea 
              placeholder="Veya analiz edilecek metni doğrudan buraya yapıştırın..."
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                if (selectedFile) handleClearFile();
              }}
              disabled={isLoading || selectedFile !== null}
              style={{ height: '100%', minHeight: '160px' }}
            />
          </div>
        </div>

        <div className="flex justify-center mt-6">
          <button 
            className="btn btn-primary" 
            style={{ padding: '0.75rem 2rem', fontSize: '1rem' }}
            disabled={isLoading || (!selectedFile && !text.trim())}
            onClick={handleSubmit}
          >
            {isLoading ? (
              <>
                <span className="spinner"></span> EVRAK ANALİZ EDİLİYOR
              </>
            ) : (
              <>
                EVRAKI ANALİZ ET
              </>
            )}
          </button>
        </div>
        {isLoading && (
          <div className="analysis-loading-status" role="status" aria-live="polite">
            <span className="spinner dark" />
            <div>
              <strong>{loadingMessages[loadingStep]}</strong>
              <small>Gösterilen aşamalar bekleme deneyimidir; gerçek zamanlı backend ilerleme yüzdesi değildir.</small>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
