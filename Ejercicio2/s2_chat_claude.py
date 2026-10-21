"""Sesión 2. Function calling con Claude (Messages API de Anthropic)."""
import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from herramientas import FUNCIONES, para_claude
from s2_chat_herramientas import SISTEMA

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    for p in [Path(".env"), Path("../.env"), Path(__file__).parent / ".env", Path(__file__).parent.parent / ".env"]:
        if p.exists():
            load_dotenv(p)
            break

cliente = anthropic.Anthropic()


def preguntar_claude(pregunta: str, max_vueltas: int = 5) -> str:
    mensajes: list = [{"role": "user", "content": pregunta}]
    for _ in range(max_vueltas):
        r = cliente.messages.create(
            model=os.environ["ANTHROPIC_MODEL"],
            max_tokens=1024,
            system=SISTEMA,
            tools=para_claude(),
            messages=mensajes,
        )
        print(f"  [tokens] entrada={r.usage.input_tokens}, salida={r.usage.output_tokens}")
        mensajes.append({"role": "assistant", "content": r.content})

        llamadas = [item for item in r.content if item.type == "tool_use"]
        if not llamadas:
            # Respuesta final: unir fragmentos de texto devueltos
            textos = [item.text for item in r.content if item.type == "text"]
            return "\n".join(textos)

        # Enviar resultados de herramientas en un turno de rol 'user'
        respuestas_herramientas = []
        for llamada in llamadas:
            resultado = FUNCIONES[llamada.name](**llamada.input)
            print(f"  -> {llamada.name}({llamada.input}) = {str(resultado)[:80]}")
            respuestas_herramientas.append({
                "type": "tool_result",
                "tool_use_id": llamada.id,
                "content": json.dumps(resultado, ensure_ascii=False),
            })
        mensajes.append({"role": "user", "content": respuestas_herramientas})

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
        resp = preguntar_claude(p)
        print("RESPUESTA:")
        print(resp)
        print()

