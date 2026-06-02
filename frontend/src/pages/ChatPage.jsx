import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Chat } from "../components/Chat";
import { useAuth } from "../context/AuthContext";

// Genera un id de sesión legible (bonus: varias conversaciones).
function newSessionId() {
  return `sesion-${Date.now().toString(36)}`;
}

// Recuperamos las sesiones guardadas para no perderlas al recargar.
function loadSessions() {
  try {
    const raw = localStorage.getItem("sessions");
    const parsed = raw ? JSON.parse(raw) : [];
    if (Array.isArray(parsed) && parsed.length) return parsed;
  } catch {
    // ignoramos JSON corrupto
  }
  return [newSessionId()];
}

export function ChatPage() {
  const [sessions, setSessions] = useState(loadSessions);
  const [current, setCurrent] = useState(sessions[0]);
  const { logout } = useAuth();
  const navigate = useNavigate();

  function persist(list) {
    setSessions(list);
    localStorage.setItem("sessions", JSON.stringify(list));
  }

  // Bonus: botón "Nueva conversación".
  function handleNew() {
    const id = newSessionId();
    persist([id, ...sessions]);
    setCurrent(id);
  }

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="chat-page">
      <header className="chat-header">
        <h2>Agente de Soporte IA</h2>

        {/* Bonus: selector de session_id */}
        <select value={current} onChange={(e) => setCurrent(e.target.value)}>
          {sessions.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <button onClick={handleNew}>+ Nueva</button>
        <button className="logout" onClick={handleLogout}>
          Salir
        </button>
      </header>

      {/* key=current → al cambiar de sesión, Chat se remonta y recarga su historial */}
      <Chat key={current} sessionId={current} />
    </div>
  );
}
