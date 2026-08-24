import React, { useEffect, useRef, useState } from "react";
import { Send, X } from "lucide-react";
import { ChatMessage } from "./ChatMessage";
import type { ChatUiMessage } from "./chatTypes";

interface Props {
  messages: ChatUiMessage[];
  isLoading: boolean;
  hasAnalysis: boolean;
  hasDraft: boolean;
  onSend: (message: string) => Promise<void>;
  onClose: () => void;
}

export const ChatPanel: React.FC<Props> = ({
  messages,
  isLoading,
  hasAnalysis,
  hasDraft,
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
          <h2>KAMUAI Asistan</h2>
          <p>Kılavuz, mevzuat ve taslak desteği</p>
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
        {hasAnalysis
          ? hasDraft
            ? "Aktif analiz ve taslak bağlamı kullanılıyor."
            : "Aktif analizde düzenlenebilir taslak bulunmuyor."
          : "Taslak düzenlemek için önce bir evrak analiz edin."}
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
