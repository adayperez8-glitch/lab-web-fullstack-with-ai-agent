"""Paquete del agente LangGraph (reutilizado del D1).

Expone el grafo compilado `agente` y el `checkpointer` para que `main.py`
pueda invocarlo y consultar el estado de cada sesión (thread_id).
"""

from .graph import agente, checkpointer

__all__ = ["agente", "checkpointer"]
