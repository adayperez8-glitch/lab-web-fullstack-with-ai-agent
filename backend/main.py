"""API FastAPI que conecta el agente LangGraph del D1 con el frontend React.

Incluye:
- CORS para permitir peticiones desde el frontend (localhost:5173).
- Autenticación mínima por token estático (DEMO_TOKEN) vía Bearer.
- POST /auth/login    → valida credenciales y devuelve el token.
- POST /api/chat      → respuesta completa del agente (no streaming).
- POST /api/chat/stream → respuesta en streaming (SSE), token a token.
- GET  /api/chat/history → historial de una sesión (thread_id).
"""

import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from agent import agente

load_dotenv()

app = FastAPI(title="App Fullstack con Agente IA")

# --- Paso 1: CORS -----------------------------------------------------------
ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Paso 2: Auth mínima (token estático) -----------------------------------
DEMO_TOKEN = os.getenv("DEMO_TOKEN", "demo-token-12345")
security = HTTPBearer()


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    if creds.credentials != DEMO_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")
    return {"user": "demo"}


# --- Modelos de entrada -----------------------------------------------------
class LoginInput(BaseModel):
    email: str
    password: str


class ChatInput(BaseModel):
    message: str
    session_id: str


# --- Login ------------------------------------------------------------------
@app.post("/auth/login")
def login(body: LoginInput):
    """Login demo: cualquier email vale, la contraseña debe ser el DEMO_TOKEN.

    En el proyecto final esto se sustituye por JWT real.
    """
    if body.password != DEMO_TOKEN:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    return {"token": DEMO_TOKEN, "user": body.email}


# --- Chat (respuesta completa) ----------------------------------------------
@app.post("/api/chat")
def chat(body: ChatInput, user=Depends(get_current_user)):
    config = {"configurable": {"thread_id": body.session_id}}
    resultado = agente.invoke(
        {"messages": [HumanMessage(content=body.message)]},
        config=config,
    )
    return {"response": resultado["messages"][-1].content}


# --- Paso 5: Chat con streaming (SSE) ---------------------------------------
@app.post("/api/chat/stream")
async def chat_stream(body: ChatInput, user=Depends(get_current_user)):
    config = {"configurable": {"thread_id": body.session_id}}

    async def generar():
        try:
            # stream_mode="messages" emite los tokens del LLM uno a uno.
            async for msg, _meta in agente.astream(
                {"messages": [HumanMessage(content=body.message)]},
                config=config,
                stream_mode="messages",
            ):
                # Solo nos interesa el texto que genera el asistente,
                # no las llamadas a herramientas ni los ToolMessages.
                if isinstance(msg, AIMessage) and msg.content:
                    safe = msg.content.replace("\n", "\\n")
                    yield f"data: {safe}\n\n"
        except Exception as exc:  # noqa: BLE001 - queremos avisar al cliente
            err = str(exc).replace("\n", " ")
            yield f"data: [ERROR] {err}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generar(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --- Historial de una sesión ------------------------------------------------
@app.get("/api/chat/history")
def history(session_id: str, user=Depends(get_current_user)):
    config = {"configurable": {"thread_id": session_id}}
    state = agente.get_state(config)
    messages = []
    if state is not None:
        for m in state.values.get("messages", []):
            # Mapeamos el tipo de LangChain a un rol entendible por el frontend.
            if isinstance(m, HumanMessage):
                role = "user"
            elif isinstance(m, AIMessage):
                role = "assistant"
            else:
                role = "system"
            # Saltamos mensajes sin texto (p.ej. llamadas a herramientas vacías).
            if role in ("user", "assistant") and m.content:
                messages.append({"role": role, "content": m.content})
    return {"session_id": session_id, "messages": messages}


@app.get("/")
def root():
    return {"mensaje": "API del agente IA — usa /api/chat o /api/chat/stream"}
