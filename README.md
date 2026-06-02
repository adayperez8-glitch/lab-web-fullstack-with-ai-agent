![logo_ironhack_blue 7](https://user-images.githubusercontent.com/23629340/40541063-a07a0a8a-601a-11e8-91b5-2f13e4e6b441.png)

# Lab | App Fullstack con Agente IA

## Objetivo

Conectar el agente LangGraph construido en el D1 con una interfaz React funcional. Al finalizar tendrás una app de chat completamente operativa en el navegador, con autenticación, streaming y gestión de estados.

## Punto de partida

- **Backend**: la API FastAPI del D1 (agente LangGraph + RAG + PostgreSQL)
- **Frontend**: app React nueva creada con Vite

```bash
# Crear el frontend (una sola vez)
npm create vite@latest frontend -- --template react
cd frontend
npm install axios react-router-dom
```

Estructura objetivo:
```
lab-web-fullstack-with-ai-agent/
├── backend/
│   ├── main.py            ← con CORS y endpoint de streaming
│   ├── agent/
│   └── .env
└── frontend/
    ├── src/
    │   ├── api/
    │   │   ├── auth.js
    │   │   └── client.js
    │   ├── context/
    │   │   └── AuthContext.jsx
    │   ├── components/
    │   │   ├── Chat.jsx
    │   │   └── ProtectedRoute.jsx
    │   ├── pages/
    │   │   ├── LoginPage.jsx
    │   │   └── ChatPage.jsx
    │   └── App.jsx
    ├── .env              ← VITE_API_URL=http://localhost:8000
    └── .env.example
```

## Paso 1 — CORS en el backend

En `main.py`, añade el middleware antes de las rutas:

```python
import os
from fastapi.middleware.cors import CORSMiddleware

ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

En `.env`:
```
ALLOWED_ORIGINS=http://localhost:5173
```

Verifica que `uvicorn main:app --reload` arranca y que la ruta `/api/chat` responde a OPTIONS desde el navegador.

## Paso 2 — Auth en el backend (si no la tienes)

Si tu backend del D1 no tiene autenticación JWT completa, añade este mínimo para poder conectar el frontend:

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

DEMO_TOKEN = os.getenv("DEMO_TOKEN", "demo-token-12345")
security = HTTPBearer()

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    if creds.credentials != DEMO_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")
    return {"user": "demo"}
```

Añade a `.env`:

```env
DEMO_TOKEN=demo-token-12345
```

En el frontend, el login simplemente guardará este token estático. Para el proyecto final implementarás JWT real.

## Paso 3 — Variables de entorno en el frontend

Crea `frontend/.env`:

```
VITE_API_URL=http://localhost:8000
```

Crea `frontend/.env.example` (este sí va al repositorio):
```
VITE_API_URL=http://localhost:8000
```

Añade a `frontend/.gitignore`:
```
.env
```

En el código React, accede con `import.meta.env.VITE_API_URL`.

## Paso 4 — Cliente API y auth en React

Implementa los archivos siguiendo las guías de los archivos `2_jwt-react.md` y `3_chat-ui-react.md`.

`src/api/auth.js`:
- `login(email, password)` → llama a `/auth/login` y guarda token en localStorage
- `logout()` → borra el token
- `getToken()` → lee el token

`src/api/client.js`:
- `axios.create({ baseURL: VITE_API_URL })`
- Interceptor de request: añade `Authorization: Bearer <token>`
- Interceptor de response: redirige a `/login` en 401

`src/context/AuthContext.jsx`:
- Provee `login`, `logout`, `isAuth`

## Paso 5 — Endpoint de streaming en el backend

Añade el endpoint SSE junto al que ya tenías:

```python
from fastapi.responses import StreamingResponse

@app.post("/api/chat/stream")
async def chat_stream(body: ChatInput, user=Depends(get_current_user)):
    async def generar():
        async for chunk in agente.astream(
            {"messages": [{"role": "user", "content": body.message}]},
            config={"configurable": {"thread_id": body.session_id}},
        ):
            if "messages" in chunk:
                content = chunk["messages"][-1].content
                if content:
                    safe = content.replace("\n", "\\n")
                    yield f"data: {safe}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generar(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

## Paso 6 — Chat con streaming en React

Implementa el componente `<Chat />` usando `fetch` con `getReader()` según `4_streaming-sse.md`.

El componente debe:
- Mostrar mensajes del usuario (derecha, azul) y del asistente (izquierda, gris)
- Mostrar el texto del asistente mientras se va generando (chunk a chunk)
- Desactivar el input mientras espera la respuesta
- Gestionar errores de red con un mensaje visible

## Paso 7 — Rutas y navegación

```jsx
// App.jsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { LoginPage } from "./pages/LoginPage";
import { ChatPage } from "./pages/ChatPage";

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/chat"
            element={
              <ProtectedRoute>
                <ChatPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/chat" />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
```

## Prueba manual completa

1. Arranca el backend: `uvicorn main:app --reload`
2. Arranca el frontend: `npm run dev` (desde `frontend/`)
3. Abre `http://localhost:5173` → debe redirigir a `/login`
4. Introduce cualquier email y el `DEMO_TOKEN` como contraseña → redirige a `/chat`
5. Envía un mensaje → el texto del asistente aparece token a token
6. Apaga el backend → intenta enviar → aparece mensaje de error (no pantalla en blanco)
7. Reinicia el backend → el chat vuelve a funcionar

## Entrega

Repositorio con esta estructura:
```
lab-web-fullstack-with-ai-agent/
├── backend/
│   ├── main.py       ← CORS + /api/chat + /api/chat/stream
│   ├── .env.example  ← variables de entorno documentadas (sin valores reales)
│   └── requirements.txt
└── frontend/
    ├── src/
    ├── .env.example  ← VITE_API_URL=http://localhost:8000
    └── package.json
```

## Checklist de entrega

- [ ] `POST /api/chat` acepta peticiones desde `localhost:5173` (sin error CORS)
- [ ] El login guarda un token y redirige al chat
- [ ] Las rutas protegidas redirigen a `/login` si no hay token
- [ ] El chat envía mensajes y muestra la respuesta del agente LangGraph
- [ ] Las respuestas se muestran en streaming (texto progresivo, no todo de golpe)
- [ ] El agente recuerda el contexto dentro de la misma sesión
- [ ] Si el backend está caído, el frontend muestra un error (no se rompe en blanco)
- [ ] Las API keys y tokens NO están en el código fuente (`.env` en `.gitignore`)

## Bonus

- Añade un selector de `session_id` para que el usuario pueda tener varias conversaciones
- Muestra el historial de conversaciones al volver a cargar la página (recuperar de `/api/chat/history`)
- Añade un botón "Nueva conversación" que limpie el estado y genere un nuevo `session_id`

---

## Cómo ejecutar este proyecto

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows (PowerShell: venv\Scripts\Activate.ps1)
pip install -r requirements.txt

# Configura el entorno
copy .env.example .env       # y rellena GROQ_API_KEY con una clave válida

# (Solo la primera vez, si no existe chroma_db/) indexa las políticas para el RAG:
python ingestar.py

uvicorn main:app --reload    # http://localhost:8000  (docs en /docs)
```

> **Nota:** el `chroma_db/` con las políticas ya viene indexado. Necesitas una
> `GROQ_API_KEY` **válida** en `backend/.env` para que el agente responda
> (la clave de ejemplo del D1 puede estar caducada).

### Frontend

```bash
cd frontend
npm install
copy .env.example .env       # VITE_API_URL=http://localhost:8000
npm run dev                  # http://localhost:5173
```

Abre `http://localhost:5173` → te redirige a `/login`. Entra con cualquier email
y la contraseña `demo-token-12345` (el `DEMO_TOKEN`).

### Endpoints del backend

| Método | Ruta                 | Auth | Descripción                                  |
|--------|----------------------|------|----------------------------------------------|
| POST   | `/auth/login`        | No   | Devuelve el token si la password = DEMO_TOKEN |
| POST   | `/api/chat`          | Sí   | Respuesta completa del agente                |
| POST   | `/api/chat/stream`   | Sí   | Respuesta en streaming (SSE), token a token  |
| GET    | `/api/chat/history`  | Sí   | Historial de una sesión (`?session_id=...`)  |

### Arquitectura

```
backend/
├── main.py            CORS + auth + endpoints (chat, stream, history, login)
├── agent/             agente LangGraph + RAG (Chroma) reutilizado del D1
│   ├── __init__.py
│   └── graph.py
├── chroma_db/         vector store ya indexado (políticas)
├── ingestar.py        re-indexa politicas.txt en chroma_db
├── politicas.txt      base de conocimiento del RAG
├── requirements.txt
└── .env.example

frontend/
├── src/
│   ├── api/{client.js, auth.js}        axios + interceptores + token
│   ├── context/AuthContext.jsx         login / logout / isAuth
│   ├── components/{Chat.jsx, ProtectedRoute.jsx}
│   ├── pages/{LoginPage.jsx, ChatPage.jsx}
│   └── App.jsx                          rutas
└── .env.example
```