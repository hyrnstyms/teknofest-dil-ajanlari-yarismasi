import type { DraftInfo } from "../../types";
import type { ChatApiResponse, ChatMode, ChatSource } from "./chatTypes";

const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL || "http://localhost:8000";

export async function sendChatMessage(
  message: string,
  analysisId?: string,
  institution?: string,
): Promise<ChatApiResponse> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 180_000);
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}/api/chat/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        analysis_id: analysisId || null,
        institution: institution || null,
      }),
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Sohbet isteği zaman aşımına uğradı. Lütfen tekrar deneyin.");
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail?.message || `HTTP Error: ${response.status}`);
  }
  return response.json();
}

export interface StreamCallbacks {
  onStart?: (data: { provider: string; mode: ChatMode }) => void;
  onDelta?: (text: string) => void;
  onSources?: (sources: ChatSource[]) => void;
  onDraftUpdate?: (draft: DraftInfo) => void;
  onPendingAction?: (action: import("./chatTypes").PendingAction) => void;
  onDone?: (data?: { ttft_ms?: number; total_ms?: number }) => void;
  onError?: (err: Error) => void;
}

export interface ParsedSseEvent {
  event: string;
  data: Record<string, unknown>;
}

export function parseSseBlock(block: string): ParsedSseEvent | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of block.split("\n")) {
    if (!line || line.startsWith(":")) continue;
    if (line.startsWith("event:")) event = line.slice(6).trim();
    if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
  }
  if (dataLines.length === 0) return null;
  const data = JSON.parse(dataLines.join("\n")) as Record<string, unknown>;
  if (event === "message" && typeof data.type === "string") event = data.type;
  return { event, data };
}

export function createSseParser(onEvent: (event: ParsedSseEvent) => void) {
  let buffer = "";
  const drain = (flush = false) => {
    buffer = buffer.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      if (block.trim()) {
        const parsed = parseSseBlock(block);
        if (parsed) onEvent(parsed);
      }
      boundary = buffer.indexOf("\n\n");
    }
    if (flush && buffer.trim()) {
      const parsed = parseSseBlock(buffer);
      buffer = "";
      if (parsed) onEvent(parsed);
    }
  };
  return {
    push(chunk: string) { buffer += chunk; drain(); },
    finish() { drain(true); },
  };
}

export async function streamChatMessage(
  message: string,
  history: { role: string; content: string }[],
  callbacks: StreamCallbacks,
  abortSignal: AbortSignal,
  analysisId?: string,
  institution?: string,
  caseId?: string,
  token?: string,
): Promise<void> {
  let completed = false;
  const complete = (data?: { ttft_ms?: number; total_ms?: number }) => {
    if (completed) return;
    completed = true;
    callbacks.onDone?.(data);
  };

  const dispatch = ({ event, data }: ParsedSseEvent) => {
    switch (event) {
      case "start":
        callbacks.onStart?.(data as unknown as { provider: string; mode: ChatMode });
        break;
      case "delta": {
        const text = typeof data.text === "string" ? data.text : typeof data.content === "string" ? data.content : "";
        if (text) callbacks.onDelta?.(text);
        break;
      }
      case "sources":
        callbacks.onSources?.(Array.isArray(data.sources) ? data.sources as ChatSource[] : []);
        break;
      case "draft_update":
        if (data.updated_draft && typeof data.updated_draft === "object") {
          callbacks.onDraftUpdate?.(data.updated_draft as DraftInfo);
        }
        break;
      case "pending_action":
        if (data.pending_action && typeof data.pending_action === "object") {
          callbacks.onPendingAction?.(data.pending_action as import("./chatTypes").PendingAction);
        }
        break;
      case "error":
        callbacks.onError?.(new Error(typeof data.message === "string" ? data.message : "Sohbet akışı tamamlanamadı."));
        break;
      case "done":
        complete(data as { ttft_ms?: number; total_ms?: number });
        break;
    }
  };

  try {
    const response = await fetch(`${API_BASE_URL}/api/copilot/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        message,
        history,
        analysis_id: analysisId || null,
        case_id: caseId || null,
        institution: institution || null,
      }),
      signal: abortSignal,
    });
    if (!response.ok) throw new Error(`Sohbet akışı başlatılamadı (${response.status}).`);
    if (!response.headers.get("content-type")?.includes("text/event-stream")) {
      throw new Error("Sunucu geçerli bir sohbet akışı döndürmedi.");
    }
    if (!response.body) throw new Error("Sohbet akışı alınamadı.");

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    const parser = createSseParser(dispatch);
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      parser.push(decoder.decode(value, { stream: true }));
    }
    parser.push(decoder.decode());
    parser.finish();
  } catch (error) {
    if (!(error instanceof DOMException && error.name === "AbortError")) {
      callbacks.onError?.(error instanceof Error ? error : new Error("Sohbet akışı tamamlanamadı."));
    }
  } finally {
    complete();
  }
}
