import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud,
  FileText,
  X,
  FilePlus,
  Loader2,
  CircleDashed,
} from 'lucide-react';
import { api, type InstitutionOption } from '../services/api';
import { DocumentState } from '../types';
import { ErrorDisplay } from '../components/ErrorDisplay';
import { humanizeFilename } from '../utils/presentation';

interface Props {
  institution: InstitutionOption | null;
  onAnalysisLoaded?: (state: DocumentState) => void;
}

// Processing stage labels (no fake percentages)
const PROCESSING_STAGES = [
  'Belge okunuyor',
  'İçerik analiz ediliyor',
  'Mevzuat aranıyor',
  'Birim öneriliyor',
  'Taslak hazırlanıyor',
];
export const NewDocumentPage: React.FC<Props> = ({ institution, onAnalysisLoaded }) => {
  const navigate = useNavigate();
  const [text, setText] = useState('');
  const [inputMode, setInputMode] = useState<'file' | 'text'>('file');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files?.length > 0) {
      setSelectedFile(e.dataTransfer.files[0]);
      setInputMode('file');
      setText('');
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      setSelectedFile(e.target.files[0]);
      setInputMode('file');
      setText('');
    }
  };

  const handleClearFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleSubmit = async () => {
    setError(null);
    setIsLoading(true);
    try {
      let result: DocumentState;
      if (selectedFile) {
        result = await api.uploadDocument(selectedFile, institution?.id);
      } else {
        result = await api.analyzeText(text, institution?.id);
      }
      onAnalysisLoaded?.(result);
      const analysisId = result.analysis_id || result.document_id;
      if (!analysisId) {
        throw new Error('Backend yanıtında analiz kimliği bulunamadı.');
      }
      navigate(`/evrak/${analysisId}`);
    } catch (err: unknown) {
      setError(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="page-container">
      <h2 style={{ marginBottom: '1.5rem' }}>
        <FilePlus size={24} style={{ verticalAlign: 'middle', marginRight: '0.5rem' }} />
        Demo Evrak Girişi
      </h2>

      <p className="demo-ingress-note">
        Yarışma demosunda evrak girişi manuel olarak simüle edilmektedir.
        Üretim ortamında EVRAG mevcut EBYS / elektronik başvuru sistemleriyle
        entegre edilebilir.
      </p>

      {/* Kurum Seçimi */}
      <div className="selected-context institution-profile-badge mb-6">
        Aktif Kurum: <strong>{institution?.label || "Seçilmedi"}</strong>
      </div>

      <div className="document-mode-tabs" role="tablist" aria-label="Evrak giriş yöntemi">
        <button type="button" role="tab" aria-selected={inputMode === 'file'} className={inputMode === 'file' ? 'active' : ''} onClick={() => { setInputMode('file'); setText(''); }}>Dosya Yükle</button>
        <button type="button" role="tab" aria-selected={inputMode === 'text'} className={inputMode === 'text' ? 'active' : ''} onClick={() => { setInputMode('text'); handleClearFile(); }}>Metin Gir</button>
      </div>

      {/* Dosya + Metin Girişi */}
      <div className="card mb-6">
        <div className="card-header">
          <FileText size={18} /> Belge Girişi
        </div>
        <div className="card-body">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1.5rem' }}>
            {/* File Upload Dropzone */}
            <div className={inputMode === 'file' ? '' : 'input-mode-hidden'}>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                style={{ display: 'none' }}
                accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp"
              />

              {selectedFile ? (
                <div className="upload-area selected-document-paper flex flex-col items-center justify-center" style={{ background: '#f8fafc', borderColor: 'var(--primary-color)' }}>
                  <div className="badge badge-info mb-4" style={{ padding: '0.5rem 1rem', fontSize: '0.95rem' }}>
                    <FileText size={18} />
                    {humanizeFilename(selectedFile.name).title}
                  </div>
                  <div className="text-secondary mb-4" style={{ fontSize: '0.85rem' }}>
                    {humanizeFilename(selectedFile.name).extension || "DOSYA"} · {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </div>
                  <button
                    className="btn btn-secondary"
                    onClick={handleClearFile}
                    disabled={isLoading}
                  >
                    <X size={16} /> Dosyayı Kaldır
                  </button>
                </div>
              ) : (
                <div
                  className={`upload-area ${isDragging ? 'drag-over' : ''}`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  style={{ minHeight: '220px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}
                >
                  <div className="folded-document-icon" aria-hidden="true"><UploadCloud size={27} /></div>
                  <p className="font-medium" style={{ fontSize: '1.1rem', color: 'var(--text-primary)' }}>Dosyayı buraya sürükleyin veya tıklayarak seçin</p>
                  <p className="text-sm text-secondary" style={{ marginTop: '0.5rem' }}>
                    Desteklenen Formatlar: PDF, PNG, JPG, TIFF, BMP
                  </p>
                </div>
              )}
            </div>

            <div className="input-mode-hidden">VEYA</div>

            {/* Text Input */}
            <div className={inputMode === 'text' ? '' : 'input-mode-hidden'}>
              <textarea
                placeholder="Analiz edilecek metni doğrudan buraya yapıştırın..."
                value={text}
                onChange={(e) => {
                  setText(e.target.value);
                  if (selectedFile) handleClearFile();
                }}
                disabled={isLoading || selectedFile !== null}
                style={{ height: '100%', minHeight: '160px', backgroundColor: selectedFile ? '#f1f5f9' : '#ffffff' }}
              />
            </div>
          </div>

          {/* Submit */}
          <div className="flex justify-center" style={{ marginTop: '1.5rem' }}>
            <button
              className="btn btn-primary"
              style={{ padding: '0.75rem 2rem', fontSize: '1rem' }}
              disabled={isLoading || !institution || (!selectedFile && !text.trim())}
              onClick={handleSubmit}
            >
              {isLoading ? (
                <>
                  <Loader2 size={18} className="spinner" /> Analiz Ediliyor...
                </>
              ) : (
                'Evrakı Analiz Et'
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Processing Stage Indicator */}
      {isLoading && (
        <div className="card">
          <div className="card-body processing-state">
            <div className="flex items-center justify-center gap-2">
              <Loader2 size={24} className="text-primary spinner" />
              <p className="font-medium">Analiz devam ediyor</p>
            </div>
            <p className="text-secondary processing-disclaimer">
              Backend canlı aşama bilgisi sağlamadığından ilerleme yüzdesi veya
              tamamlandı işareti gösterilmez. İşlem hattı şu adımları yürütür:
            </p>
            <ol className="processing-stage-list">
              {PROCESSING_STAGES.map((stage) => (
                <li key={stage}><CircleDashed size={14} aria-hidden="true" /> {stage}</li>
              ))}
            </ol>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error ? <ErrorDisplay error={error} onRetry={() => void handleSubmit()} /> : null}
    </div>
  );
};

function formatInstitutionName(institution: string): string {
  return institution
    .split('_')
    .map((part) => part.charAt(0).toLocaleUpperCase('tr-TR') + part.slice(1))
    .join(' ');
}
