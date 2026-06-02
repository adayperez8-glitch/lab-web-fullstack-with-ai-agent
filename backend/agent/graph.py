from typing import TypedDict, Annotated, Sequence
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
import operator
import json
from datetime import datetime
import os

load_dotenv()

class EstadoSoporte(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
retriever = vectordb.as_retriever(search_kwargs={"k": 3})

@tool
def buscar_pedido(pedido_id: str) -> str:
    """Busca el estado de un pedido por su ID. Ejemplo: buscar_pedido('PED-1234')"""
    pedidos = {
        "PED-1234": {"estado": "enviado", "fecha_entrega": "15/05/2026", "total": 89.99},
        "PED-5678": {"estado": "en preparación", "fecha_entrega": "18/05/2026", "total": 45.50},
    }
    pedido = pedidos.get(pedido_id.upper())
    return str(pedido) if pedido else f"Pedido {pedido_id} no encontrado"

@tool
def calcular_reembolso(total: float, porcentaje: float) -> str:
    """Calcula el importe de un reembolso parcial."""
    reembolso = round(total * porcentaje / 100, 2)
    return f"Reembolso del {porcentaje}% sobre {total}€: {reembolso}€"

@tool
def escalar_a_humano(motivo: str) -> str:
    """Escala un caso a un agente humano cuando el asistente no puede resolverlo."""
    caso = {
        "fecha": datetime.now().isoformat(),
        "motivo": motivo,
        "estado": "pendiente"
    }
    try:
        with open("casos_escalados.json", "r", encoding="utf-8") as f:
            casos = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        casos = []
    casos.append(caso)
    with open("casos_escalados.json", "w", encoding="utf-8") as f:
        json.dump(casos, f, ensure_ascii=False, indent=2)
    return f"Caso escalado a humano correctamente. Motivo: {motivo}. ID de caso: CASO-{len(casos):04d}"

tools = [buscar_pedido, calcular_reembolso, escalar_a_humano]
modelo = ChatOpenAI(
    model="llama-3.3-70b-versatile",
    temperature=0,
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY")
)
modelo_con_tools = modelo.bind_tools(tools)

def nodo_llm(estado: EstadoSoporte) -> dict:
    ultimo_humano = next(
        (m.content for m in reversed(estado["messages"]) if isinstance(m, HumanMessage)),
        ""
    )
    docs = retriever.invoke(ultimo_humano)
    contexto = "\n".join(d.page_content for d in docs)

    system = SystemMessage(content=f"""Eres un asistente de soporte amable y preciso.
Usa las herramientas disponibles para consultar pedidos y calcular reembolsos.
Responde preguntas sobre políticas usando este contexto:

{contexto}

Si no tienes información, dilo claramente. No inventes datos.""")

    mensajes_con_system = [system] + list(estado["messages"])
    respuesta = modelo_con_tools.invoke(mensajes_con_system)
    return {"messages": [respuesta]}

def debe_continuar(estado: EstadoSoporte) -> str:
    ultimo = estado["messages"][-1]
    if hasattr(ultimo, "tool_calls") and ultimo.tool_calls:
        return "usar_tool"
    return END

nodo_tools = ToolNode(tools)

grafo = StateGraph(EstadoSoporte)
grafo.add_node("llm", nodo_llm)
grafo.add_node("tools", nodo_tools)
grafo.set_entry_point("llm")
grafo.add_conditional_edges("llm", debe_continuar, {"usar_tool": "tools", END: END})
grafo.add_edge("tools", "llm")

checkpointer = MemorySaver()
agente = grafo.compile(checkpointer=checkpointer)
