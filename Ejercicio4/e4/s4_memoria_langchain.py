"""Sesión 4. Memoria persistente con LangChain: hilos (corto plazo) y preferencias (largo plazo).

Uso:  python s4_memoria_langchain.py <cliente_id> <hilo>
      p. ej. "python s4_memoria_langchain.py 1 lunes" y después "... 1 martes"."""
import os
import sqlite3
import sys
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain.tools import ToolRuntime, tool
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.sqlite import SqliteStore

load_dotenv()
MODELO = f"anthropic:{os.environ['ANTHROPIC_MODEL']}"


@dataclass
class Contexto:
    cliente_id: str  # lo fija la aplicación tras identificar al cliente; el modelo no puede cambiarlo
    olvido_solicitado: bool = False


def _espacio(runtime: ToolRuntime[Contexto]) -> tuple[str, str]:
    return ("clientes", runtime.context.cliente_id)  # namespace: aísla la memoria de cada cliente


@tool
def recordar_preferencia(clave: str, valor: str, runtime: ToolRuntime[Contexto]) -> str:
    """Guarda una preferencia estable del cliente (horario de entrega, producto habitual,
    forma de contacto). No guardes datos personales sensibles ni datos de pago."""
    runtime.store.put(_espacio(runtime), clave, {"valor": valor})
    return f"Preferencia '{clave}' guardada."


@tool
def ver_preferencias(runtime: ToolRuntime[Contexto]) -> dict:
    """Devuelve las preferencias guardadas del cliente actual."""
    return {item.key: item.value["valor"] for item in runtime.store.search(_espacio(runtime))}


@tool
def olvidar_preferencias(runtime: ToolRuntime[Contexto]) -> str:
    """Borra todas las preferencias del cliente actual y sus hilos de conversación. Úsala si el cliente lo solicita."""
    # 1. Borrar preferencias en el store (memoria a largo plazo)
    for item in runtime.store.search(_espacio(runtime)):
        runtime.store.delete(_espacio(runtime), item.key)

    # 2. Borrar hilos del cliente en el checkpointer (memoria a corto plazo)
    prefijo = f"{runtime.context.cliente_id}-"
    with checkpointer.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT thread_id FROM checkpoints WHERE thread_id LIKE ? "
            "UNION SELECT DISTINCT thread_id FROM writes WHERE thread_id LIKE ?",
            (f"{prefijo}%", f"{prefijo}%")
        )
        hilos = [fila[0] for fila in cur.fetchall()]

    for tid in hilos:
        checkpointer.delete_thread(tid)

    runtime.context.olvido_solicitado = True
    return "Preferencias e hilos de conversación eliminados."


SISTEMA = """Eres el asistente comercial de Tostadero Retiro.
Al empezar cada conversación consulta ver_preferencias y tenlas en cuenta.
Cuando el cliente exprese una preferencia estable, guárdala con recordar_preferencia.
Si pide que olvides sus datos, usa olvidar_preferencias y confírmalo."""

# Dos almacenes distintos: hilos de conversación y memoria a largo plazo
checkpointer = SqliteSaver(sqlite3.connect("hilos.db", check_same_thread=False))
store = SqliteStore(sqlite3.connect("memoria.db", check_same_thread=False, isolation_level=None))
store.setup()

agente = create_agent(
    model=MODELO,
    tools=[recordar_preferencia, ver_preferencias, olvidar_preferencias],
    system_prompt=SISTEMA,
    context_schema=Contexto,
    checkpointer=checkpointer,
    store=store,
    middleware=[SummarizationMiddleware(model=MODELO, trigger=("tokens", 3000),
                                        keep=("messages", 10))],
)

if __name__ == "__main__":
    cliente_id, hilo = sys.argv[1], sys.argv[2]
    config = {"configurable": {"thread_id": f"{cliente_id}-{hilo}"}}
    contexto = Contexto(cliente_id=cliente_id)
    while texto := input("Cliente: ").strip():
        estado = agente.invoke({"messages": [{"role": "user", "content": texto}]},
                               config, context=contexto)
        print("Asistente:", estado["messages"][-1].text)
        if contexto.olvido_solicitado:
            # Resuelve la persistencia del hilo activo: LangGraph escribe un checkpoint
            # al terminar invoke(), por lo que purgamos el hilo actual aquí tras la invocación.
            checkpointer.delete_thread(f"{cliente_id}-{hilo}")