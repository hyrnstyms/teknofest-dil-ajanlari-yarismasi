import React from "react";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  User,
} from "lucide-react";
import type { ChatMode, ChatUiMessage } from "./chatTypes";

interface Props {
  message: ChatUiMessage;
}

const MODE_LABELS: Record<ChatMode, string> = {
  kilavuz: "Kılavuz",
  mevzuat: "Mevzuat",
  taslak_duzenleme: "Taslak Düzenleme",
};

export const ChatMessage: React.FC<Props> = ({ message }) => {
  const isBot = message.role === "bot";
  const showFailure =
    message.status === "rejected" || message.status === "error";

  return (
    <div className={`chat-message ${isBot ? "bot" : "user"}`}>
      <div className="chat-message-avatar" aria-hidden="true">
        {isBot ? <Bot size={16} /> : <User size={16} />}
      </div>

      <div className="chat-message-content">
        {isBot && message.mode && (
          <div className="chat-message-meta">
            <span className="chat-mode-label">
              {MODE_LABELS[message.mode]}
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

        <div className="chat-message-bubble">{message.text}</div>

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
