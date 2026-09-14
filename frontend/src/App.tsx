import { FormEvent, useState } from "react";
import { MessageOut, sendMessage } from "./api";
import "./index.css";

export default function App() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [history, setHistory] = useState<MessageOut[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!input.trim() || loading) return;

    setLoading(true);
    setError(null);
    try {
      const result = await sendMessage(input, conversationId);
      setConversationId(result.conversation_id);
      setHistory(result.history);
      setInput("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <h1>toolloop-agent</h1>
      <p className="subtitle">
        Fase 1: loop de chat sin herramientas todavía (Sprint 2+ agrega tool
        calling y traza en vivo).
      </p>

      <div className="chat">
        {history.map((msg, i) => (
          <div key={i} className={`bubble ${msg.role}`}>
            <span className="role">{msg.role}</span>
            <p>{msg.content}</p>
          </div>
        ))}
      </div>

      {error && <p className="error">{error}</p>}

      <form onSubmit={handleSubmit} className="composer">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Escribí un mensaje..."
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          {loading ? "Enviando..." : "Enviar"}
        </button>
      </form>
    </div>
  );
}
