import { FormEvent, useState } from "react";
import { AgentStepEvent, streamMessage } from "./api";
import "./index.css";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface TraceStep {
  turn: number;
  type: "action" | "observation" | "final" | "error";
  tool?: string;
  detail: string;
  isError?: boolean;
}

function describeStep(event: AgentStepEvent): TraceStep | null {
  switch (event.type) {
    case "action":
      return {
        turn: 0,
        type: "action",
        tool: event.tool,
        detail: `Llamando a \`${event.tool}\` con ${JSON.stringify(event.input)}`,
      };
    case "observation":
      return {
        turn: 0,
        type: "observation",
        tool: event.tool,
        detail:
          typeof event.output === "string"
            ? event.output
            : JSON.stringify(event.output),
        isError: event.is_error,
      };
    case "final":
      return { turn: 0, type: "final", detail: event.text };
    case "error":
      return { turn: 0, type: "error", detail: event.message };
    default:
      return null;
  }
}

export default function App() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [steps, setSteps] = useState<TraceStep[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [turn, setTurn] = useState(0);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!input.trim() || loading) return;

    const message = input;
    const currentTurn = turn + 1;
    setTurn(currentTurn);
    setHistory((prev) => [...prev, { role: "user", content: message }]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      await streamMessage(message, conversationId, (evt) => {
        if (evt.type === "conversation_id") {
          setConversationId(evt.conversation_id);
          return;
        }
        if (evt.type === "done") {
          return;
        }

        const step = describeStep(evt);
        if (step) {
          setSteps((prev) => [...prev, { ...step, turn: currentTurn }]);
        }

        if (evt.type === "final") {
          setHistory((prev) => [
            ...prev,
            { role: "assistant", content: evt.text },
          ]);
        } else if (evt.type === "error") {
          setHistory((prev) => [
            ...prev,
            { role: "assistant", content: `⚠️ ${evt.message}` },
          ]);
        }
      });
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
        Sprint 4: la traza (acción → observación → respuesta final) se
        transmite en vivo por SSE mientras el agente resuelve la tarea.
      </p>

      <div className="panels">
        <div className="panel">
          <h2>Chat</h2>
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
              {loading ? "Pensando..." : "Enviar"}
            </button>
          </form>
        </div>

        <div className="panel">
          <h2>Traza del agente</h2>
          <div className="trace">
            {steps.length === 0 && (
              <p className="trace-empty">
                Acá vas a ver cada acción y observación del agente en vivo.
              </p>
            )}
            {steps.map((step, i) => (
              <div key={i} className={`trace-step trace-${step.type}`}>
                <span className="trace-label">
                  {step.type === "action" && "🔧 acción"}
                  {step.type === "observation" &&
                    (step.isError ? "❌ observación" : "👀 observación")}
                  {step.type === "final" && "✅ respuesta final"}
                  {step.type === "error" && "⚠️ error"}
                  {step.tool ? ` · ${step.tool}` : ""}
                </span>
                <p>{step.detail}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
