"""Sesión 2. Function calling con Gemini (Chat Completions vía OpenRouter)."""
import json
import os
from pathlib import Path

import openai
from dotenv import load_dotenv

from herramientas import FUNCIONES, para_chat
from s2_chat_herramientas import SISTEMA

load_dotenv()
if not os.getenv("OPENROUTER_API_KEY"):
    for p in [Path(".env"), Path("../.env"), Path(__file__).parent / ".env", Path(__file__).parent.parent / ".env"]:
        if p.exists():
            load_dotenv(p)
            break

cliente = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)


def preguntar_gemini(pregunta: str, max_vueltas: int = 5) -> str:
    mensajes: list = [
        {"role": "system", "content": SISTEMA},
        {"role": "user", "content": pregunta},
    ]
    for _ in range(max_vueltas):
        r = cliente.chat.completions.create(
            model=os.environ["GEMINI_MODEL"],
            messages=mensajes,
            tools=para_chat(),
        )
        print(f"  [tokens] entrada={r.usage.prompt_tokens}, salida={r.usage.completion_tokens}")
        msg = r.choices[0].message
        mensajes.append(msg)

        if not msg.tool_calls:
            return msg.content or ""

        for llamada in msg.tool_calls:
            args = json.loads(llamada.function.arguments)
            resultado = FUNCIONES[llamada.function.name](**args)
            print(f"  -> {llamada.function.name}({args}) = {str(resultado)[:80]}")
            mensajes.append({
                "role": "tool",
                "tool_call_id": llamada.id,
                "content": json.dumps(resultado, ensure_ascii=False),
            })

    return "No he podido completar la consulta en el número de pasos permitido."


if __name__ == "__main__":
    preguntas = [
        "¿Qué pedidos pendientes tiene el Bar La Esquina y cuánto suman?",
        "¿Cuánto stock queda de descafeinado?",
        "¿Qué pedidos tiene el Bar Inexistente?",
        "Borra el pedido 1003",
    ]
    for p in preguntas:
        print("=" * 60)
        print(f"PREGUNTA: {p}")
        print("-" * 60)
        resp = preguntar_gemini(p)
        print("RESPUESTA:")
        print(resp)
        print()

