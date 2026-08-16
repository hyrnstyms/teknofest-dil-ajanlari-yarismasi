import React, { useState } from 'react';
import { Upload, File } from 'lucide-react';

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
    <form onSubmit={handleSubmit} className="card">
      <div className="card-header">
        <h3 className="card-title">Dosya Yükle</h3>
      </div>
      
      <div className="form-group" style={{ 
        border: '2px dashed var(--border-color)', 
        padding: '3rem 2rem', 
        textAlign: 'center',
        borderRadius: '8px',
        backgroundColor: '#f8fafc'
      }}>
        <input 
          type="file" 
          id="file-upload" 
          accept=".pdf,.docx,.doc,.txt" 
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />
        <label htmlFor="file-upload" style={{ cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
          <Upload size={48} color="var(--text-muted)" />
          <span style={{ fontWeight: 500 }}>Bilgisayarınızdan dosya seçin veya sürükleyin</span>
          <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Desteklenen formatlar: PDF, DOCX, TXT</span>
        </label>
      </div>

      {selectedFile && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '1rem', backgroundColor: '#eff6ff', borderRadius: '6px', marginBottom: '1.5rem' }}>
          <File size={24} color="var(--accent)" />
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 500 }}>{selectedFile.name}</div>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>{(selectedFile.size / 1024).toFixed(1)} KB • {selectedFile.type || 'Bilinmeyen tür'}</div>
          </div>
        </div>
      )}

      <button 
        type="submit" 
        className="btn btn-primary" 
        style={{ width: '100%' }}
        disabled={!selectedFile || isLoading}
      >
        {isLoading ? 'Belge analiz ediliyor...' : 'Analizi Başlat'}
      </button>
    </form>
  );
}
