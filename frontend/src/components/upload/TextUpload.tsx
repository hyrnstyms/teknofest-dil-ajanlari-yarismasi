import React, { useState } from 'react';
import { Button } from '../ui/Button';

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
    <form onSubmit={handleSubmit} className="card flex flex-col gap-6 h-full min-h-[400px]">
      
      <div className="flex flex-col gap-2 flex-1">
        <label className="text-sm font-medium text-text-heading">Belge Metni</label>
        <textarea 
          className="form-control text-sm font-serif leading-relaxed resize-none flex-1"
          style={{ minHeight: '280px' }}
          placeholder="Analiz etmek istediğiniz evrak metnini buraya yapıştırın..."
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
      </div>

      <Button 
        type="submit" 
        variant="primary"
        size="lg"
        className="w-full justify-center"
        disabled={!text.trim() || isLoading}
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


