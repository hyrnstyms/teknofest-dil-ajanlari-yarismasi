import React, { useState } from 'react';

interface TextUploadProps {
  onAnalyze: (text: string) => void;
  isLoading: boolean;
}

export function TextUpload({ onAnalyze, isLoading }: TextUploadProps) {
  const [text, setText] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim()) {
      onAnalyze(text.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card">
      <div className="card-header">
        <h3 className="card-title">Metin ile Analiz</h3>
      </div>
      
      <div className="form-group">
        <label className="form-label">Belge Metni</label>
        <textarea 
          className="form-control"
          placeholder="Analiz etmek istediğiniz evrak metnini buraya girin."
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={12}
        />
      </div>

      <button 
        type="submit" 
        className="btn btn-primary" 
        style={{ width: '100%' }}
        disabled={!text.trim() || isLoading}
      >
        {isLoading ? 'Belge analiz ediliyor...' : 'Analizi Başlat'}
      </button>
    </form>
  );
}
