"""Sesión 4 (Variante de P2). Inyección de preferencias mediante middleware de prompt dinámico.

En lugar de que el modelo deba recordar llamar a la herramienta `ver_preferencias`,
las preferencias se leen del store y se inyectan dinámicamente en el system prompt
antes de cada llamada al LLM con el decorador `@dynamic_prompt` de LangChain.

Uso:  python s4_memoria_dinamica.py <cliente_id> <hilo>
      p. ej. "python s4_memoria_dinamica.py 1 lunes" y después "... 1 martes"."""
import os
import sqlite3
import sys
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelRequest,
    SummarizationMiddleware,
    dynamic_prompt,
)
from langchain.tools import ToolRuntime, tool
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.sqlite import SqliteStore

load_dotenv()
MODELO = f"anthropic:{os.environ['ANTHROPIC_MODEL']}"


@dataclass
class Contexto:
    cliente_id: str  # Fijado por la aplicación tras autenticar al cliente
    olvido_solicitado: bool = False


def _espacio(runtime: ToolRuntime[Contexto]) -> tuple[str, str]:
    return ("clientes", runtime.context.cliente_id)


@tool
def recordar_preferencia(clave: str, valor: str, runtime: ToolRuntime[Contexto]) -> str:
    """Guarda una preferencia estable del cliente (horario de entrega, producto habitual,
    forma de contacto). No guardes datos personales sensibles ni datos de pago."""
    runtime.store.put(_espacio(runtime), clave, {"valor": valor})
    return f"Preferencia '{clave}' guardada."


@tool
def olvidar_preferencias(runtime: ToolRuntime[Contexto]) -> str:
    """Borra todas las preferencias del cliente actual y todos sus hilos de conversación. Úsala si el cliente lo solicita."""
    # 1. Borrar memoria a largo plazo (store / memoria.db)
    for item in runtime.store.search(_espacio(runtime)):
        runtime.store.delete(_espacio(runtime), item.key)

    # 2. Borrar memoria a corto plazo (checkpointer / hilos.db)
    prefijo = f"{runtime.context.cliente_id}-"
    with checkpointer.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT thread_id FROM checkpoints WHERE thread_id LIKE ? "
            "UNION SELECT DISTINCT thread_id FROM writes WHERE thread_id LIKE ?",
            (f"{prefijo}%", f"{prefijo}%"),
        )
        hilos = [fila[0] for fila in cur.fetchall()]

    for tid in hilos:
        checkpointer.delete_thread(tid)

    runtime.context.olvido_solicitado = True
    return "Preferencias e hilos de conversación eliminados."


SISTEMA_BASE = """Eres el asistente comercial de Tostadero Retiro.
Cuando el cliente exprese una preferencia estable, guárdala con recordar_preferencia.
Si pide que olvides sus datos, usa olvidar_preferencias y confírmalo."""


@dynamic_prompt
def prompt_con_preferencias(request: ModelRequest[Contexto]) -> str:
    """Middleware que consulta el store antes de cada llamada al modelo e inyecta
    las preferencias del cliente directamente en las instrucciones del sistema."""
    preferencias = {}
    if request.runtime and request.runtime.store and request.runtime.context:
        espacio = ("clientes", request.runtime.context.cliente_id)
        preferencias = {
            item.key: item.value["valor"]
            for item in request.runtime.store.search(espacio)
        }

    if preferencias:
        lineas = "\n".join(f"- {k}: {v}" for k, v in preferencias.items())
        bloque = f"\n\nPreferencias conocidas de este cliente:\n{lineas}\nTenlas siempre en cuenta al responder."
    else:
        bloque = "\n\nEste cliente no tiene preferencias registradas todavía."

    return SISTEMA_BASE + bloque


# Almacenes persistentes
checkpointer = SqliteSaver(sqlite3.connect("hilos.db", check_same_thread=False))
store = SqliteStore(sqlite3.connect("memoria.db", check_same_thread=False, isolation_level=None))
store.setup()

agente = create_agent(
    model=MODELO,
    tools=[recordar_preferencia, olvidar_preferencias],  # ¡Ya no necesita ver_preferencias!
    context_schema=Contexto,
    checkpointer=checkpointer,
    store=store,
    middleware=[
        prompt_con_preferencias,
        SummarizationMiddleware(
            model=MODELO, trigger=("tokens", 3000), keep=("messages", 10)
        ),
    ],
)

if __name__ == "__main__":
    cliente_id, hilo = sys.argv[1], sys.argv[2]
    config = {"configurable": {"thread_id": f"{cliente_id}-{hilo}"}}
    contexto = Contexto(cliente_id=cliente_id)
    while texto := input("Cliente: ").strip():
        estado = agente.invoke(
            {"messages": [{"role": "user", "content": texto}]},
            config,
            context=contexto,
        )
        print("Asistente:", estado["messages"][-1].text)
        if contexto.olvido_solicitado:
            checkpointer.delete_thread(f"{cliente_id}-{hilo}")
