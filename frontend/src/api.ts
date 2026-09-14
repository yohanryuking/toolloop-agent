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
