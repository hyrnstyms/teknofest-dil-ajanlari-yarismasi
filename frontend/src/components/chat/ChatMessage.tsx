import React from "react";
import {
  AlertTriangle,
  FileText,
  CheckCircle2,
  User,
  BookOpen,
  ChevronDown,
  ChevronRight,
  Copy,
} from "lucide-react";
import type { ChatMode, ChatUiMessage } from "./chatTypes";

interface Props {
  message: ChatUiMessage;
}

const MODE_LABELS: Record<ChatMode, string> = {
  kilavuz: "Kılavuz",
  mevzuat: "Mevzuat",
  kucuk_sohbet: "Sohbet",
  taslak_duzenleme: "Taslak Düzenleme",
  active_document: "Aktif Evrak",
  institution: "Kurum İşleyişi",
};

export const ChatMessage: React.FC<Props> = ({ message }) => {
  const [sourcesExpanded, setSourcesExpanded] = React.useState(false);
  const isBot = message.role === "bot";
  const showFailure =
    message.status === "rejected" || message.status === "error";

  const copyToClipboard = () => {
    navigator.clipboard.writeText(message.text);
  };

  return (
    <div className={`chat-message ${isBot ? "bot" : "user"}`}>
      <div className="chat-message-avatar" aria-hidden="true">
        {isBot ? <FileText size={15} /> : <User size={15} />}
      </div>

      <div className="chat-message-content">
        {isBot && message.mode && (
          <div className="chat-message-meta">
            <span className="chat-mode-label">
              {MODE_LABELS[message.mode] || "Copilot"}
            </span>
            {message.status === "applied" && (
              <span className="chat-status-success">
                <CheckCircle2 size={14} /> Uygulandı
              </span>
            )}
            {showFailure && (
              <span className="chat-status-failure">
                <AlertTriangle size={14} />
                {message.status === "rejected" ? "Reddedildi" : "Hata"}
              </span>
            )}
          </div>
        )}

        {message.sources && message.sources.length > 0 && (
          <div className="chat-message-sources">
            <button
              className="sources-toggle"
              onClick={() => setSourcesExpanded(!sourcesExpanded)}
            >
              <BookOpen size={14} />
              <span>Mevzuat Kaynakları ({message.sources.length})</span>
              {sourcesExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </button>

            {sourcesExpanded && (
              <div className="sources-list">
                {message.sources.map((src, i) => (
                  <div key={i} className="source-card">
                    <div className="source-header">
                      <strong>{src.law_number} sayılı Kanun</strong>
                      {src.madde_no && <span>Madde {src.madde_no}</span>}
                    </div>
                    <div className="source-title">{src.title}</div>
                    <div className="source-excerpt">"{src.excerpt}"</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="chat-message-bubble">
          {message.text || (message.isStreaming ? "Yanıt hazırlanıyor…" : "")}
          {message.isStreaming && message.text && <span className="streaming-cursor"></span>}
        </div>

        {isBot && !message.isStreaming && message.text && (
          <div className="chat-message-actions">
            <button className="chat-action-btn" onClick={copyToClipboard} title="Kopyala">
              <Copy size={14} /> Kopyala
            </button>
          </div>
        )}

        {message.validationErrors &&
          message.validationErrors.length > 0 && (
            <div className="chat-validation-errors">
              <strong>Biçim doğrulama ayrıntıları</strong>
              <ul>
                {message.validationErrors.map((error, index) => (
                  <li key={`${error.kural_kodu || "kural"}-${index}`}>
                    {error.kural_kodu && `[${error.kural_kodu}] `}
                    {error.mesaj || "Bilinmeyen biçim doğrulama hatası"}
                  </li>
                ))}
              </ul>
            </div>
          )}
      </div>
    </div>
  );
};
