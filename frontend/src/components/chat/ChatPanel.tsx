import React, { useEffect, useRef, useState } from "react";
import { Send, X, Square, Trash2, RefreshCw } from "lucide-react";
import { ChatMessage } from "./ChatMessage";
import { EVRAGBrand } from "../EVRAGBrand";
import type { ChatUiMessage } from "./chatTypes";

interface Props {
  messages: ChatUiMessage[];
  isLoading: boolean;
  isStreaming?: boolean;
  hasAnalysis: boolean;
  institutionLabel?: string;
  failedMessage?: string | null;
  onSend: (message: string) => Promise<void>;
  onRetry?: () => void;
  onClose: () => void;
  onStop?: () => void;
  onClearHistory?: () => void;
  onConfirmAction?: (action: import("./chatTypes").PendingAction) => void;
}

export const ChatPanel: React.FC<Props> = ({
  messages,
  isLoading,
  isStreaming,
  hasAnalysis,
  institutionLabel,
  failedMessage,
  onSend,
  onRetry,
  onClose,
  onStop,
  onClearHistory,
  onConfirmAction,
}) => {
  const [input, setInput] = useState("");
  const messageEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const submit = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading || isStreaming) return;
    setInput("");
    await onSend(trimmed);
  };

  const isKaymakamlik = institutionLabel?.toLowerCase().includes("kaymakam");
  const isBelediye = institutionLabel?.toLowerCase().includes("belediye");

  let quickActions: string[] = [];
  if (hasAnalysis) {
    quickActions = ["Bu evrak ne hakkında?", "Hangi birime yönlendirilmeli?", "Eksik bilgi var mı?", "Hangi mevzuat uygulanıyor?"];
    // Dynamic based on last bot message
    const lastBot = messages.filter(m => m.role === "bot").pop();
    if (lastBot?.mode === "active_document") {
      quickActions = ["Neden bu birim?", "Sonraki adım ne?", "Mevzuatı göster", "Taslak oluştur"];
    } else if (lastBot?.mode === "mevzuat") {
      quickActions = ["Bu madde ne anlama geliyor?", "Süre var mı?", "Bu evraka nasıl uygulanıyor?"];
    } else if (lastBot?.mode === "taslak_duzenleme") {
      quickActions = ["Taslağı özetle", "Daha resmî hale getir", "Daha kısa hale getir"];
    }
  } else {
    if (isBelediye) {
      quickActions = ["Yol bakım talepleri hangi müdürlüğe gider?", "Bilgi edinme başvurularında mevzuat nedir?", "Bir dilekçenin cevap süresi nedir?"];
    } else if (isKaymakamlik) {
      quickActions = ["Dilekçe cevap süresi nedir?", "Sosyal yardım başvurusu nasıl yönlendirilir?", "Bilgi edinme başvurularında süreç nedir?"];
    } else {
      quickActions = ["KAMUAI ne yapıyor?", "Nasıl evrak yüklerim?", "Dilekçe cevap süresi nedir?"];
    }
  }

  return (
    <section className="kamuai-chat-panel" aria-label="KAMUAI Copilot">
      <header className="kamuai-chat-header">
        <div>
          <h2><EVRAGBrand variant="icon" theme="light" className="copilot-brand-mark" /><span>EVRAG Copilot</span></h2>
          <p>
            Kurum ve evrak asistanı
          </p>
        </div>
        <div className="chat-header-actions">
          {onClearHistory && (
            <button
              type="button"
              className="chat-header-action"
              onClick={onClearHistory}
              title="Sohbeti Temizle"
              aria-label="Sohbeti temizle"
            >
              <Trash2 size={16} />
            </button>
          )}
          <button
            type="button"
            className="chat-header-action"
            onClick={onClose}
            aria-label="Sohbeti kapat"
          >
            <X size={20} />
          </button>
        </div>
      </header>

      <div className="kamuai-chat-context-badges">
        <span className="context-badge primary">{institutionLabel || "Genel Kurum"}</span>
        {hasAnalysis && (
          <span className="context-badge active">Aktif Evrak</span>
        )}
      </div>

      <div className="kamuai-chat-quick-actions" aria-label="Önerilen sorular">
        {quickActions.slice(0, 4).map((label) => (
          <button key={label} type="button" onClick={() => void onSend(label)} disabled={isLoading || isStreaming}>
            {label}
          </button>
        ))}
      </div>

      <div className="kamuai-chat-messages" aria-live="polite">
        {messages.map((message) => (
          <ChatMessage 
            key={message.id} 
            message={message} 
            onConfirmAction={onConfirmAction}
          />
        ))}

        {isLoading && !isStreaming && (
          <div className="kamuai-chat-loading" aria-label="Düşünüyor">
            <span className="evrag-mark-small">◆</span> Yanıt hazırlanıyor<span className="dots">...</span>
          </div>
        )}

        {failedMessage && onRetry && (
          <div className="chat-retry-container">
            <p>Sohbet isteği tamamlanamadı.</p>
            <button onClick={onRetry} className="chat-retry-button">
              <RefreshCw size={14} /> Tekrar Dene
            </button>
          </div>
        )}
        <div ref={messageEndRef} />
      </div>

      <div className="kamuai-chat-composer">
        <textarea
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            e.target.style.height = 'auto';
            e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void submit();
            }
          }}
          placeholder="Mesajınızı yazın..."
          aria-label="Sohbet mesajı"
          disabled={isLoading && !isStreaming}
          rows={1}
        />
        {isStreaming ? (
          <button
            type="button"
            className="chat-stop-button"
            onClick={onStop}
            aria-label="Üretimi durdur"
          >
            <Square size={18} fill="currentColor" />
          </button>
        ) : (
          <button
            type="submit"
            className="chat-send-button"
            onClick={submit}
            disabled={isLoading || !input.trim()}
            aria-label="Mesajı gönder"
          >
            <Send size={18} />
          </button>
        )}
      </div>
    </section>
  );
};
