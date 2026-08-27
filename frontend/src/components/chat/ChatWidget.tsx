import React, { useEffect, useRef, useState } from "react";
import { MessageCircle } from "lucide-react";
import type { DraftInfo } from "../../types";
import { ChatPanel } from "./ChatPanel";
import { streamChatMessage } from "./chatApi";
import type { ChatUiMessage, ChatMode } from "./chatTypes";
import { CHAT_STORAGE_VERSION, restoreChatThread, type StoredChatThread } from "./chatStorage";
import { useAuth } from "../../contexts/AuthContext";
import { createCaseActionAdapter } from "../../services/copilotCaseApi";
import "./chat.css";

interface Props {
  analysisId?: string;
  caseId?: string;
  currentDraft?: DraftInfo;
  institutionId?: string;
  institutionLabel?: string;
  onDraftUpdated: (draft: DraftInfo) => void;
  openSignal?: number;
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
      ? "Aktif evrak bağlamını kullanıyorum. Özeti, eksikleri, mevzuatı, yönlendirme gerekçesini sorabilir veya taslak üzerinde kontrollü değişiklik isteyebilirsiniz."
      : "Merhaba, ben EVRAG Copilot. Kamu evrakı, mevzuat, yönlendirme ve resmî yazışma süreçlerinde yardımcı olabilirim.",
  };
}

export const ChatWidget: React.FC<Props> = ({
  analysisId,
  caseId,
  currentDraft: _currentDraft,
  institutionId,
  institutionLabel,
  onDraftUpdated,
  openSignal,
}) => {
  const { token } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [failedMessage, setFailedMessage] = useState<string | null>(null);

  const isOpenRef = useRef(isOpen);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [messages, setMessages] = useState<ChatUiMessage[]>([]);

  const sessionKey = `evrag_chat_${institutionId || "global"}_${caseId || analysisId || "no_doc"}`;

  useEffect(() => {
    isOpenRef.current = isOpen;
  }, [isOpen]);

  useEffect(() => {
    // Load history for this thread
    const restored = restoreChatThread(sessionStorage.getItem(sessionKey));
    setMessages(restored?.length ? restored : [welcomeMessage(Boolean(analysisId))]);
    setUnreadCount(analysisId && !isOpenRef.current ? 1 : 0);
    setFailedMessage(null);
  }, [sessionKey, analysisId]);

  useEffect(() => {
    if (openSignal) setIsOpen(true);
  }, [openSignal]);

  useEffect(() => {
    if (messages.length > 1) { // don't just save welcome message
      const stored: StoredChatThread = { version: CHAT_STORAGE_VERSION, messages };
      sessionStorage.setItem(sessionKey, JSON.stringify(stored));
    }
  }, [messages, sessionKey]);

  const handleClearHistory = () => {
    sessionStorage.removeItem(sessionKey);
    setMessages([welcomeMessage(Boolean(analysisId))]);
  };

  const stopStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };

  const handleConfirmAction = async (action: import("./chatTypes").PendingAction) => {
    const msgIndex = messages.findIndex(m => m.pendingAction === action);
    if (msgIndex < 0) return;
    
    const msg = messages[msgIndex];
    if (msg.actionStatus === "submitting" || msg.actionStatus === "resolved") {
      return; // Idempotent guard
    }
    
    const msgId = msg.id;
    
    // Set to submitting synchronously before the asynchronous confirmation call.
    setMessages(prev => prev.map(m => 
      m.id === msgId ? { ...m, actionStatus: "submitting" } : m
    ));

    try {
      if (!token) throw new Error("Oturum bulunamadı.");
      const result = await createCaseActionAdapter(token).executeAction(action);
      
      setMessages(prev => prev.map(m => 
        m.id === msgId ? { ...m, actionResult: result, actionStatus: "resolved" } : m
      ));
    } catch {
      setMessages(prev => prev.map(m => 
        m.id === msgId ? { ...m, actionResult: { success: false, message: "İşlem sırasında hata oluştu." }, actionStatus: "resolved" } : m
      ));
    }
  };

  const handleSend = async (text: string) => {
    setFailedMessage(null);
    const userMsg: ChatUiMessage = { id: messageId(), role: "user", text };

    // Extract history for API
    const history = messages
      .filter((m) => m.role === "user" || m.role === "bot")
      .map((m) => ({ role: m.role === "bot" ? "assistant" : "user", content: m.text }));

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setIsStreaming(true);

    const botMsgId = messageId();
    let currentBotMsg: ChatUiMessage = {
      id: botMsgId,
      role: "bot",
      text: "",
      isStreaming: true,
      mode: "kilavuz",
    };

    setMessages((prev) => [...prev, currentBotMsg]);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    await streamChatMessage(
      text,
      history,
      {
        onStart: (data) => {
          setIsLoading(false);
          currentBotMsg = { ...currentBotMsg, mode: data.mode as ChatMode };
          setMessages((prev) => prev.map((m) => (m.id === botMsgId ? currentBotMsg : m)));
        },
        onDelta: (deltaText) => {
          setIsLoading(false);
          currentBotMsg = { ...currentBotMsg, text: currentBotMsg.text + deltaText };
          setMessages((prev) => prev.map((m) => (m.id === botMsgId ? currentBotMsg : m)));
        },
        onSources: (sources) => {
          currentBotMsg = { ...currentBotMsg, sources };
          setMessages((prev) => prev.map((m) => (m.id === botMsgId ? currentBotMsg : m)));
        },
        onDraftUpdate: (draft) => {
          currentBotMsg = { ...currentBotMsg, status: "applied" };
          setMessages((prev) => prev.map((m) => (m.id === botMsgId ? currentBotMsg : m)));
          onDraftUpdated(draft);
        },
        onPendingAction: (action) => {
          currentBotMsg = { ...currentBotMsg, pendingAction: action };
          setMessages((prev) => prev.map((m) => (m.id === botMsgId ? currentBotMsg : m)));
        },
        onError: (err) => {
          setFailedMessage(text);
          currentBotMsg = {
            ...currentBotMsg,
            status: "error",
            text: currentBotMsg.text || err.message || "Sohbet isteği tamamlanamadı."
          };
          setMessages((prev) => prev.map((m) => (m.id === botMsgId ? currentBotMsg : m)));
        },
        onDone: () => {
          let updatedText = currentBotMsg.text;
          let status = currentBotMsg.status;
          if (!updatedText && !currentBotMsg.sources && status !== "error") {
            updatedText = "Yanıt üretilemedi. Tekrar deneyebilirsiniz.";
            status = "error";
          }
          currentBotMsg = { ...currentBotMsg, isStreaming: false, text: updatedText, status };
          setMessages((prev) => prev.map((m) => (m.id === botMsgId ? currentBotMsg : m)));
          setIsStreaming(false);
          setIsLoading(false);
          abortControllerRef.current = null;
        }
      },
      controller.signal,
      analysisId,
      institutionId,
      caseId,
      token || undefined,
    );
  };

  const handleRetry = () => {
    if (failedMessage) handleSend(failedMessage);
  };

  return (
    <>
      <button
        onClick={() => {
          setIsOpen(!isOpen);
          setUnreadCount(0);
        }}
        className={`kamuai-chat-fab ${isOpen ? "open" : ""}`}
        aria-label="Sohbet asistanını aç/kapat"
      >
        <MessageCircle size={24} />
        {unreadCount > 0 && !isOpen && (
          <span className="kamuai-chat-badge">{unreadCount}</span>
        )}
      </button>

      <div className={`kamuai-chat-container ${isOpen ? "open" : ""}`}>
        {isOpen && (
          <ChatPanel
            messages={messages}
            isLoading={isLoading}
            isStreaming={isStreaming}
            hasAnalysis={Boolean(analysisId)}
            institutionLabel={institutionLabel}
            onSend={handleSend}
            onClose={() => setIsOpen(false)}
            onRetry={handleRetry}
            failedMessage={failedMessage}
            onStop={stopStreaming}
            onClearHistory={handleClearHistory}
            onConfirmAction={handleConfirmAction}
          />
        )}
      </div>
    </>
  );
};
