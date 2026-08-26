import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud,
  FileText,
  X,
  FilePlus,
  Building2,
  Loader2,
  CircleDashed,
} from 'lucide-react';
import { api } from '../services/api';
import { DocumentState } from '../types';
import { ErrorDisplay } from '../components/ErrorDisplay';

interface Props {
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
const ACTIVE_ANALYSIS_INSTITUTION = 'kaymakamlik';

export const NewDocumentPage: React.FC<Props> = ({ onAnalysisLoaded }) => {
  const navigate = useNavigate();
  const [text, setText] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Institutions
  const [institutions, setInstitutions] = useState<string[]>([
    ACTIVE_ANALYSIS_INSTITUTION,
  ]);
  const [selectedInstitution, setSelectedInstitution] = useState(
    ACTIVE_ANALYSIS_INSTITUTION,
  );

  useEffect(() => {
    const fetchInstitutions = async () => {
      try {
        const data = await api.getInstitutions();
        setInstitutions(
          Array.from(new Set([ACTIVE_ANALYSIS_INSTITUTION, ...data.institutions])),
        );
      } catch {
        // silently fail — institution picker is optional context
      }
    };
    fetchInstitutions();
  }, []);

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
      setText('');
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      setSelectedFile(e.target.files[0]);
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
        result = await api.uploadDocument(selectedFile);
      } else {
        result = await api.analyzeText(text);
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
        Yeni Evrak Analiz Et
      </h2>

      {/* Kurum Seçimi */}
      {institutions.length > 0 && (
        <div className="card mb-6">
          <div className="card-header">
            <Building2 size={18} /> Aktif Kurum Bağlamı
          </div>
          <div className="card-body">
            <select
              value={selectedInstitution}
              onChange={(e) => setSelectedInstitution(e.target.value)}
              disabled={isLoading}
              style={{
                width: '100%',
                padding: '0.6rem 0.75rem',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--border-radius)',
                fontSize: '0.9rem',
                backgroundColor: '#fff',
              }}
            >
              {institutions.map((institution) => (
                <option
                  key={institution}
                  value={institution}
                  disabled={institution !== ACTIVE_ANALYSIS_INSTITUTION}
                >
                  {formatInstitutionName(institution)}
                </option>
              ))}
            </select>
            <p className="text-secondary institution-context-note">
              Mevcut analiz API'si kurum parametresi kabul etmediği için analizler
              Kaymakamlık profiliyle yürütülür; ekranda seçilmiş fakat backend'e
              uygulanmayan bir kurum bağlamı gösterilmez.
            </p>
          </div>
        </div>
      )}

      {/* Dosya + Metin Girişi */}
      <div className="card mb-6">
        <div className="card-header">
          <FileText size={18} /> Belge Girişi
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
                accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp"
              />

              {selectedFile ? (
                <div className="upload-area flex flex-col items-center justify-center">
                  <div className="badge badge-info mb-4">
                    <FileText size={16} />
                    {selectedFile.name}
                  </div>
                  <div className="text-secondary mb-4" style={{ fontSize: '0.85rem' }}>
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </div>
                  <button
                    className="btn btn-secondary"
                    onClick={handleClearFile}
                    disabled={isLoading}
                  >
                    <X size={16} /> Kaldır
                  </button>
                </div>
              ) : (
                <div
                  className={`upload-area ${isDragging ? 'drag-over' : ''}`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <UploadCloud size={48} className="upload-icon" style={{ margin: '0 auto' }} />
                  <p className="font-medium">Dosyayı buraya sürükleyin veya tıklayarak seçin</p>
                  <p className="text-sm text-secondary" style={{ marginTop: '0.5rem' }}>
                    PDF, PNG, JPG, TIFF ve BMP desteklenir
                  </p>
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
                style={{ height: '100%', minHeight: '180px' }}
              />
            </div>
          </div>

          {/* Submit */}
          <div className="flex justify-center" style={{ marginTop: '1.5rem' }}>
            <button
              className="btn btn-primary"
              style={{ padding: '0.75rem 2rem', fontSize: '1rem' }}
              disabled={isLoading || (!selectedFile && !text.trim())}
              onClick={handleSubmit}
            >
              {isLoading ? (
                <>
                  <Loader2 size={18} className="spinner" /> Analiz Ediliyor...
                </>
              ) : (
                'Belgeyi Analiz Et'
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
      {error ? <ErrorDisplay error={error} /> : null}
    </div>
  );
};

function formatInstitutionName(institution: string): string {
  return institution
    .split('_')
    .map((part) => part.charAt(0).toLocaleUpperCase('tr-TR') + part.slice(1))
    .join(' ');
}
