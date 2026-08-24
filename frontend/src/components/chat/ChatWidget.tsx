import React, { useEffect, useRef, useState } from "react";
import { MessageCircle } from "lucide-react";
import type { DraftInfo } from "../../types";
import { ChatPanel } from "./ChatPanel";
import { sendChatMessage } from "./chatApi";
import type { ChatUiMessage } from "./chatTypes";
import "./chat.css";

interface Props {
  analysisId?: string;
  currentDraft?: DraftInfo;
  onDraftUpdated: (draft: DraftInfo) => void;
}

function messageId(): string {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function welcomeMessage(hasAnalysis: boolean): ChatUiMessage {
  return {
    id: messageId(),
    role: "bot",
    mode: "kilavuz",
    status: "answered",
    text: hasAnalysis
      ? "Aktif evrak analiziyle çalışıyorum. Sistem kullanımı, mevzuat veya taslak düzenleme hakkında sorabilirsiniz."
      : "Merhaba. Sistem kullanımı hakkında soru sorabilirsiniz. Taslak düzenlemek için önce bir evrak analiz etmeniz gerekir.",
  };
}

export const ChatWidget: React.FC<Props> = ({
  analysisId,
  currentDraft,
  onDraftUpdated,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const isOpenRef = useRef(isOpen);
  const [messages, setMessages] = useState<ChatUiMessage[]>([
    welcomeMessage(Boolean(analysisId)),
  ]);

  useEffect(() => {
    isOpenRef.current = isOpen;
  }, [isOpen]);

  useEffect(() => {
    setMessages([welcomeMessage(Boolean(analysisId))]);
    setUnreadCount(analysisId && !isOpenRef.current ? 1 : 0);
  }, [analysisId]);

  const handleSend = async (text: string) => {
    setMessages((previous) => [
      ...previous,
      { id: messageId(), role: "user", text },
    ]);
    setIsLoading(true);

    try {
      const result = await sendChatMessage(text, analysisId);
      setMessages((previous) => [
        ...previous,
        {
          id: messageId(),
          role: "bot",
          text: result.sohbet_yaniti,
          mode: result.mode,
          status: result.status,
          validationErrors: result.validation_errors,
        },
      ]);

      if (result.status === "applied" && result.updated_draft) {
        onDraftUpdated(result.updated_draft);
      }
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        {
          id: messageId(),
          role: "bot",
          mode: "kilavuz",
          status: "error",
          text:
            error instanceof Error
              ? error.message
              : "Sohbet isteği tamamlanamadı. Lütfen tekrar deneyin.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleWidget = () => {
    setIsOpen((previous) => {
      const next = !previous;
      if (next) setUnreadCount(0);
      return next;
    });
  };

  return (
    <div className="chat-widget">
      {isOpen && (
        <ChatPanel
          messages={messages}
          isLoading={isLoading}
          hasAnalysis={Boolean(analysisId)}
          hasDraft={Boolean(currentDraft)}
          onSend={handleSend}
          onClose={() => setIsOpen(false)}
        />
      )}

      <button
        type="button"
        className={`chat-launch-button ${isOpen ? "active" : ""}`}
        onClick={toggleWidget}
        aria-label={isOpen ? "Sohbeti kapat" : "Sohbeti aç"}
        aria-expanded={isOpen}
      >
        <MessageCircle size={26} />
        {unreadCount > 0 && (
          <span className="chat-unread-badge">{unreadCount}</span>
        )}
      </button>
    </div>
  );
};
