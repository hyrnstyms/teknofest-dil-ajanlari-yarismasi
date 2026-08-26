import React from 'react';
import { AlertCircle } from 'lucide-react';
import { ApiRequestError } from '../services/api';

interface Props {
  error: unknown;
  title?: string;
  onRetry?: () => void;
  retryLabel?: string;
}

const ERROR_MESSAGES: Record<string, string> = {
  ocr_error:
    'Belgenin optik karakter tanıması başarısız oldu. Lütfen daha net bir tarama yükleyin.',
  ocr_failed:
    'Belgenin optik karakter tanıması başarısız oldu. Lütfen daha net bir tarama yükleyin.',
  empty_document:
    'Belgeden okunabilir metin çıkarılamadı. Dosyanın boş, bozuk veya şifreli olmadığını kontrol edin.',
  pdf_read_error:
    'PDF dosyası okunamadı. Dosya bozuk veya şifrelenmiş olabilir.',
  analysis_timeout:
    'Analiz işlemi zaman aşımına uğradı. Belgeniz çok uzun olabilir; lütfen tekrar deneyin.',
  timeout:
    'Analiz işlemi zaman aşımına uğradı. Belgeniz çok uzun olabilir; lütfen tekrar deneyin.',
  evren_unavailable:
    'Yapay zekâ modeli şu anda erişilemiyor. Lütfen daha sonra tekrar deneyin.',
  llm_unavailable:
    'Yapay zekâ modeli şu anda erişilemiyor. Lütfen daha sonra tekrar deneyin.',
  qdrant_unavailable:
    'Mevzuat veritabanına erişilemiyor. Mevzuat analizi yapılamadı.',
  rag_unavailable:
    'Mevzuat veritabanına erişilemiyor. Mevzuat analizi yapılamadı.',
};

function getUserFacingError(error: unknown): string {
  const code = error instanceof ApiRequestError ? error.code.toLowerCase() : '';
  if (ERROR_MESSAGES[code]) return ERROR_MESSAGES[code];

  const message = error instanceof Error ? error.message : String(error || '');
  const normalized = message.toLocaleLowerCase('tr-TR');

  if (normalized.includes('ocr')) return ERROR_MESSAGES.ocr_error;
  if (normalized.includes('timeout') || normalized.includes('zaman aşımı')) {
    return ERROR_MESSAGES.analysis_timeout;
  }
  if (normalized.includes('pdf') || normalized.includes('şifreli')) {
    return ERROR_MESSAGES.pdf_read_error;
  }
  if (
    normalized.includes('evren') ||
    normalized.includes('llm') ||
    normalized.includes('yapay zekâ')
  ) {
    return ERROR_MESSAGES.evren_unavailable;
  }
  if (
    normalized.includes('qdrant') ||
    normalized.includes('rag') ||
    normalized.includes('mevzuat veritabanı')
  ) {
    return ERROR_MESSAGES.qdrant_unavailable;
  }

  return message || 'Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin.';
}

export const ErrorDisplay: React.FC<Props> = ({ error, title = 'İşlem Başarısız', onRetry, retryLabel = 'Tekrar Dene' }) => (
  <div className="card error-display" role="alert">
    <div className="card-body">
      <div className="flex items-center gap-4">
        <AlertCircle size={24} className="text-error" style={{ flexShrink: 0 }} />
        <div>
          <p className="font-medium text-error">{title}</p>
          <p className="text-secondary error-display-message">
            {getUserFacingError(error)}
          </p>
        </div>
        {onRetry && (
          <button type="button" className="btn btn-secondary" onClick={onRetry}>
            {retryLabel}
          </button>
        )}
      </div>
    </div>
  </div>
);
