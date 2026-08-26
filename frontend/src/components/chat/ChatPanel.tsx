import React, { useEffect, useRef, useState } from "react";
import { Send, X } from "lucide-react";
import { ChatMessage } from "./ChatMessage";
import type { ChatUiMessage } from "./chatTypes";

interface Props {
  messages: ChatUiMessage[];
  isLoading: boolean;
  hasAnalysis: boolean;
  hasDraft: boolean;
  institutionLabel?: string;
  onSend: (message: string) => Promise<void>;
  onClose: () => void;
}

export const ChatPanel: React.FC<Props> = ({
  messages,
  isLoading,
  hasAnalysis,
  hasDraft,
  institutionLabel,
  onSend,
  onClose,
}) => {
  const [input, setInput] = useState("");
  const messageEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const submit = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    setInput("");
    await onSend(trimmed);
  };

  return (
    <section
      className="chat-panel"
      aria-label="KAMUAI yardım sohbeti"
    >
      <header className="chat-panel-header">
        <div>
          <h2>KAMUAI Kurumsal Copilot</h2>
          <p>Evrak, mevzuat, yönlendirme ve taslak desteği</p>
        </div>
        <button
          type="button"
          className="chat-close-button"
          onClick={onClose}
          aria-label="Sohbeti kapat"
        >
          <X size={20} />
        </button>
      </header>

      <div className="chat-context-hint">
        <span className="chat-context-badge">Kurum: {institutionLabel || "Seçilmedi"}</span>
        <span className={`chat-context-badge ${hasAnalysis ? "active" : "idle"}`}>
          {hasAnalysis ? "Aktif Evrak" : "Aktif evrak yok"}
        </span>
        <span>
          {hasAnalysis
            ? hasDraft
              ? "Analiz ve taslak bağlamı kullanılıyor."
              : "Aktif analizde düzenlenebilir taslak bulunmuyor."
            : "Evrak işlemleri için önce bir analiz açın."}
        </span>
      </div>

      <div className="chat-quick-actions" aria-label="Hızlı sorular">
        {(hasAnalysis
          ? ["Bu evrakı özetle", "Eksikleri göster", "Neden bu birim?", "Bu evraka hangi mevzuat uygulanıyor?"]
          : ["KAMUAI ne yapıyor?", "Nasıl evrak yüklerim?"]
        ).map((label) => (
          <button key={label} type="button" onClick={() => void onSend(label)} disabled={isLoading}>
            {label}
          </button>
        ))}
        {hasDraft && (
          <button type="button" onClick={() => void onSend("Taslak metni daha resmî yap")} disabled={isLoading}>
            Taslağı iyileştir
          </button>
        )}
      </div>

      <div className="chat-message-list" aria-live="polite">
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}

        {isLoading && (
          <div className="chat-typing" aria-label="Asistan yazıyor">
            <span />
            <span />
            <span />
            <span className="chat-typing-label">yazıyor...</span>
          </div>
        )}
        <div ref={messageEndRef} />
      </div>

      <form
        className="chat-input-row"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void submit();
            }
          }}
          placeholder="Mesajınızı yazın..."
          aria-label="Sohbet mesajı"
          rows={2}
          disabled={isLoading}
        />
        <button
          type="submit"
          className="chat-send-button"
          disabled={isLoading || !input.trim()}
          aria-label="Mesajı gönder"
        >
          <Send size={18} />
        </button>
      </form>
    </section>
  );
};
