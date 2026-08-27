import type { ChatUiMessage } from "./chatTypes";

export const CHAT_STORAGE_VERSION = 2;

export interface StoredChatThread {
  version: number;
  messages: ChatUiMessage[];
}

function isMeaningfulMessage(message: ChatUiMessage): boolean {
  if (message.role === "user") return Boolean(message.text?.trim());
  return Boolean(message.text?.trim() || message.isStreaming || message.status === "error" || message.status === "rejected" || message.sources?.length);
}

export function restoreChatThread(raw: string | null): ChatUiMessage[] | null {
  if (!raw) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    const messages = Array.isArray(parsed) ? parsed : (parsed as Partial<StoredChatThread>)?.messages;
    return Array.isArray(messages) ? (messages as ChatUiMessage[]).filter(isMeaningfulMessage) : null;
  } catch {
    return null;
  }
}