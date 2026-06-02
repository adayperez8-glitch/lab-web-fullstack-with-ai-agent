import { useEffect, useRef, useState } from "react";
import client, { API_URL } from "../api/client";
import { getToken } from "../api/auth";

export function Chat({ sessionId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  // Bonus: al cambiar de sesión, recuperamos el historial del backend.
  useEffect(() => {
    let cancelled = false;
    setError("");
    setMessages([]);
    client
      .get("/api/chat/history", { params: { session_id: sessionId } })
      .then(({ data }) => {
        if (!cancelled) setMessages(data.messages || []);
      })
      .catch(() => {
        // Si falla el historial (p.ej. backend caído) no rompemos la UI.
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  // Auto-scroll al último mensaje.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    setError("");
    setInput("");
    setLoading(true);

    // Añadimos el mensaje del usuario y un hueco para la respuesta.
    setMessages((prev) => [
      ...prev,
      { role: "user", content: text },
      { role: "assistant", content: "" },
    ]);

    try {
      const res = await fetch(`${API_URL}/api/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ message: text, session_id: sessionId }),
      });

      if (!res.ok) {
        throw new Error(`El servidor respondió ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      // Lectura del stream chunk a chunk.
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() || ""; // lo que quede incompleto se guarda

        for (const evt of events) {
          if (!evt.startsWith("data:")) continue;
          // Quitamos "data:" y SOLO el único espacio separador del protocolo SSE,
          // preservando los espacios propios del token (p. ej. " devolver").
          let payload = evt.slice(5);
          if (payload.startsWith(" ")) payload = payload.slice(1);

          if (payload === "[DONE]") continue;
          if (payload.startsWith("[ERROR]")) {
            throw new Error(payload.replace("[ERROR]", "").trim());
          }

          // Deshacemos el escape de saltos de línea del backend.
          const chunk = payload.replace(/\\n/g, "\n");
          setMessages((prev) => {
            const copy = [...prev];
            copy[copy.length - 1] = {
              role: "assistant",
              content: copy[copy.length - 1].content + chunk,
            };
            return copy;
          });
        }
      }
    } catch (err) {
      setError(
        "No se pudo conectar con el servidor. Comprueba que el backend está activo."
      );
      // Quitamos la burbuja vacía del asistente si no llegó nada.
      setMessages((prev) => {
        const copy = [...prev];
        const last = copy[copy.length - 1];
        if (last && last.role === "assistant" && last.content === "") {
          copy.pop();
        }
        return copy;
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="messages">
        {messages.length === 0 && (
          <p className="empty-state">
            Escribe un mensaje para empezar a hablar con el agente.
          </p>
        )}
        {messages.map((m, i) => {
          const isLast = i === messages.length - 1;
          const streaming = isLast && m.role === "assistant" && loading;
          return (
            <div
              key={i}
              className={`bubble ${m.role}${streaming ? " cursor" : ""}`}
            >
              {m.content}
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      {error && <div className="chat-error">{error}</div>}

      <form className="composer" onSubmit={sendMessage}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Escribe tu mensaje…"
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          {loading ? "…" : "Enviar"}
        </button>
      </form>
    </>
  );
}
