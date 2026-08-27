import assert from "node:assert/strict";
import test from "node:test";
import { createSseParser } from "../src/components/chat/chatApi.ts";
import { restoreChatThread } from "../src/components/chat/chatStorage.ts";

function collect(chunks: string[], finish = true) {
  const events: Array<{ event: string; data: Record<string, unknown> }> = [];
  const parser = createSseParser((event) => events.push(event));
  chunks.forEach((chunk) => parser.push(chunk));
  if (finish) parser.finish();
  return events;
}

test("SSE event split across stream chunks is buffered", () => {
  const events = collect(["event: del", "ta\ndata: {\"text\":\"Mer", "haba\"}\n\n"]);
  assert.deepEqual(events, [{ event: "delta", data: { text: "Merhaba" } }]);
});

test("multiple SSE events in one chunk are emitted in order", () => {
  const events = collect(["event: start\ndata: {\"mode\":\"kilavuz\"}\n\nevent: delta\ndata: {\"text\":\"Yanıt\"}\n\n"]);
  assert.equal(events.length, 2);
  assert.equal(events[0].event, "start");
  assert.equal(events[1].data.text, "Yanıt");
});

test("CRLF framing and Turkish UTF-8 text are preserved", () => {
  const events = collect(["event: delta\r\ndata: {\"text\":\"Dilekçe süresi\"}\r\n\r\n"]);
  assert.equal(events[0].data.text, "Dilekçe süresi");
});

test("delta text can be accumulated without replacement", () => {
  const events = collect(["event: delta\ndata: {\"text\":\"Otuz \"}\n\nevent: delta\ndata: {\"text\":\"gün\"}\n\n"]);
  assert.equal(events.map((event) => String(event.data.text || "")).join(""), "Otuz gün");
});

test("final complete event is flushed without trailing blank line", () => {
  const events = collect(["event: done\ndata: {\"total_ms\":12}"]);
  assert.equal(events[0].event, "done");
});
test("chat storage migration removes only stale blank assistant messages", () => {
  const valid = { id: "valid", role: "bot", text: "Görünür yanıt", isStreaming: false };
  const blank = { id: "blank", role: "bot", text: "", isStreaming: false };
  const restored = restoreChatThread(JSON.stringify([valid, blank]));
  assert.deepEqual(restored?.map((message) => message.id), ["valid"]);
});

test("versioned chat storage preserves a valid active thread", () => {
  const message = { id: "answer", role: "bot", text: "30 gün", isStreaming: false };
  const restored = restoreChatThread(JSON.stringify({ version: 2, messages: [message] }));
  assert.equal(restored?.[0]?.text, "30 gün");
});