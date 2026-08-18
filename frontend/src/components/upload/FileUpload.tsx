import React, { useState } from 'react';
import { Upload, File, X } from 'lucide-react';
import { Button } from '../ui/Button';

interface FileUploadProps {
  onUpload: (file: File) => void;
  isLoading: boolean;
}

export function FileUpload({ onUpload, isLoading }: FileUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedFile) {
      onUpload(selectedFile);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card flex flex-col gap-6">
      
      <div className="dropzone">
        <input 
          type="file" 
          id="file-upload" 
          accept=".pdf,.docx,.doc,.txt" 
          onChange={handleFileChange}
          className="dropzone-input"
        />
        <div className="dropzone-icon">
          <Upload size={32} />
        </div>
        <div className="text-center">
          <span className="font-semibold text-text-heading block mb-1">Dosyanızı buraya sürükleyin</span>
          <span className="text-sm text-muted block mb-2">veya tıklayarak seçin</span>
          <span className="text-xs text-muted block mt-2">PDF, DOCX ve TXT • Maksimum 20MB</span>
        </div>
      </div>

      {selectedFile && (
        <div className="flex justify-between items-center p-4 bg-bg-color border border-border-color rounded-md">
          <div className="flex items-center gap-3 min-w-0">
            <File size={24} className="text-accent flex-shrink-0" />
            <div className="flex flex-col min-w-0">
              <span className="font-medium text-text-main truncate text-sm">{selectedFile.name}</span>
              <span className="text-xs text-muted">{(selectedFile.size / 1024).toFixed(1)} KB</span>
            </div>
          </div>
          <button 
            type="button" 
            onClick={() => setSelectedFile(null)}
            className="p-1.5 text-muted hover:text-danger rounded-md hover:bg-danger-light transition-colors"
          >
            <X size={18} />
          </button>
        </div>
      )}

      <Button 
        type="submit" 
        variant="primary" 
        size="lg"
        className="w-full justify-center"
        disabled={!selectedFile || isLoading}
      >
        {isLoading ? (
          <>
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
            Analiz Ediliyor...
          </>
        ) : 'Analizi Başlat'}
      </Button>
    </form>
  );
}


