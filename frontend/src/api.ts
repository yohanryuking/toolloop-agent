export interface MessageOut {
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ChatResponse {
  conversation_id: string;
  reply: string;
  history: MessageOut[];
}

export type AgentStepEvent =
  | { type: "conversation_id"; conversation_id: string }
  | { type: "action"; tool: string; input: unknown }
  | { type: "observation"; tool: string; output: unknown; is_error: boolean }
  | { type: "final"; text: string }
  | { type: "error"; message: string }
  | { type: "done" };

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function sendMessage(
  message: string,
  conversationId: string | null
): Promise<ChatResponse> {
  const response = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });

  if (!response.ok) {
    throw new Error(`Error del servidor: ${response.status}`);
  }

  return response.json();
}

/**
 * Igual que `sendMessage`, pero consume `POST /api/chat/stream` (SSE) y
 * llama a `onEvent` por cada paso a medida que llega. Usa `fetch` +
 * `ReadableStream` en vez de `EventSource` porque el endpoint es POST (con
 * body), y `EventSource` nativo del browser solo soporta GET.
 */
export async function streamMessage(
  message: string,
  conversationId: string | null,
  onEvent: (event: AgentStepEvent) => void
): Promise<void> {
  const response = await fetch(`${API_URL}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`Error del servidor: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      const dataLine = rawEvent
        .split("\n")
        .find((line) => line.startsWith("data: "));
      if (dataLine) {
        onEvent(JSON.parse(dataLine.slice("data: ".length)));
      }

      boundary = buffer.indexOf("\n\n");
    }
  }
}
