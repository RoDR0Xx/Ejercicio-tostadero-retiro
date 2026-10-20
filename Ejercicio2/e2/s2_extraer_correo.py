"""Sesión 2. Salidas estructuradas: de un correo libre a un objeto validado."""
import os
import re
import sqlite3
from pathlib import Path
from typing import Literal

import anthropic
import openai
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field

load_dotenv()
# Respaldo por si se ejecuta desde subcarpetas o entornos sin variables heredadas
if not os.getenv("OPENROUTER_API_KEY"):
    for p in [Path(".env"), Path("../.env"), Path(__file__).parent / ".env", Path(__file__).parent.parent / ".env"]:
        if p.exists():
            load_dotenv(p)
            break


class Linea(BaseModel):
    producto: str = Field(description="Producto tal y como lo menciona el cliente")
    cantidad: int = Field(description="Unidades o kilos pedidos")


class CorreoClasificado(BaseModel):
    tipo: Literal["pedido", "incidencia", "consulta", "mixto"]
    cliente: str | None = Field(description="Nombre del negocio si aparece; si no, null")
    lineas: list[Linea] = Field(description="Vacía si no hay pedido")
    urgente: bool
    resumen: str = Field(description="Una sola frase en español")


SISTEMA = "Extraes información de correos de clientes de un distribuidor de café para hostelería."


def con_openai(correo: str) -> CorreoClasificado:
    r = openai.OpenAI().responses.parse(
        model=os.environ["OPENAI_MODEL"], instructions=SISTEMA, input=correo,
        text_format=CorreoClasificado,
    )
    return r.output_parsed


def con_claude(correo: str) -> CorreoClasificado:
    r = anthropic.Anthropic().messages.parse(
        model=os.environ["ANTHROPIC_MODEL"], max_tokens=1024, system=SISTEMA,
        messages=[{"role": "user", "content": correo}],
        output_format=CorreoClasificado,
    )
    return r.parsed_output


def con_gemini(correo: str) -> CorreoClasificado:
    if os.getenv("GEMINI_API_KEY"):  # opcional: API nativa de Gemini
        cliente = genai.Client()  # en una variable: si no, el SDK cierra el cliente antes de usarlo
        r = cliente.interactions.create(
            model=os.environ["GEMINI_MODEL"].removeprefix("google/"),
            system_instruction=SISTEMA, input=correo,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": CorreoClasificado.model_json_schema(),
            },
        )
        return CorreoClasificado.model_validate_json(r.output_text)
    # Por defecto, vía OpenRouter con Chat Completions
    cliente = openai.OpenAI(base_url="https://openrouter.ai/api/v1",
                            api_key=os.environ["OPENROUTER_API_KEY"])
    r = cliente.chat.completions.parse(
        model=os.environ["GEMINI_MODEL"],
        messages=[{"role": "system", "content": SISTEMA}, {"role": "user", "content": correo}],
        response_format=CorreoClasificado,
    )
    return r.choices[0].message.parsed


def buscar_cliente(nombre: str) -> dict | None:
    """Valida y busca un cliente en la base de datos tostadero.db.

    Soporta coincidencias directas, parciales y detección si se mencionan
    múltiples clientes válidos. Devuelve el registro del cliente o None si no existe.
    """
    if not nombre or not nombre.strip():
        return None

    rutas_bd = [
        Path(__file__).parent / "tostadero.db",
        Path("tostadero.db"),
        Path(__file__).parent.parent / "tostadero.db",
        Path(__file__).parent.parent / "EJERCICIO1" / "tostadero.db",
    ]
    ruta_bd = next((p for p in rutas_bd if p.exists()), None)
    if not ruta_bd:
        return None

    termino = nombre.strip().lower()
    with sqlite3.connect(ruta_bd) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM clientes")
        clientes_bd = [dict(row) for row in cur.fetchall()]

    # 1. Coincidencia directa o contenida (ej. "Lumbre" con "Restaurante Lumbre")
    for c in clientes_bd:
        nom_bd = c["nombre"].lower()
        if nom_bd == termino or nom_bd in termino or termino in nom_bd:
            return c

    # 2. Si el modelo extrajo varios nombres unidos por 'y', ',', etc.
    partes = [p.strip().lower() for p in re.split(r",|\s+y\s+|\s+e\s+|/|-", termino) if p.strip()]
    for p in partes:
        for c in clientes_bd:
            nom_bd = c["nombre"].lower()
            if nom_bd == p or nom_bd in p or p in nom_bd:
                return c

    return None


# Conjunto de evaluación ampliado con casos difíciles:
# ironía, dos clientes, inglés, sin nombre de negocio, clientes fuera de BD y casos mixtos.
CASOS = [
    # Casos base originales (6)
    ("Necesito 20 kg del blend de hostelería para el viernes. Bar La Esquina.", "pedido"),
    ("El molino hace un ruido raro desde ayer, ¿podéis venir?", "incidencia"),
    ("¿Tenéis café descafeinado de especialidad?", "consulta"),
    ("Mandadme 5 kg de Etiopía y, de paso, la cafetera gotea. Lumbre.", "mixto"),
    ("URGENTE: sin café para mañana, 10 kg de blend. Hotel Prado Suites", "pedido"),
    ("Buenas, ¿la factura de septiembre ya está emitida?", "consulta"),
    # Caso difícil 1: Ironía / Sarcasmo (apariencia positiva pero reporte de avería crítica)
    ("Genial vuestro servicio técnico: la máquina de café echa chispas y humo negro por todos lados, una maravilla. Venid a arreglarla ya. Panadería Ibiza.", "incidencia"),
    # Caso difícil 2: Dos clientes en el mismo correo (pedido para uno de ellos)
    ("Hola, soy el dueño de Bar La Esquina y de Restaurante Lumbre. Para Lumbre necesitamos 30 kg de café blend esta semana.", "pedido"),
    # Caso difícil 3: Dos clientes en el mismo correo (consulta conjunta)
    ("Buenas tardes, os escribo en nombre de Bar La Esquina y Cafetería Atocha 12: ¿hacéis precio especial si compramos conjuntamente?", "consulta"),
    # Caso difícil 4: Correo en inglés (pedido con resumen en español)
    ("Good morning, we are completely out of coffee beans. Please deliver 15 kg of espresso blend by tomorrow. Hotel Prado Suites.", "pedido"),
    # Caso difícil 5: Correo en inglés (incidencia técnica)
    ("Hello, the espresso machine group 2 has lost all pressure and water is leaking everywhere. We need urgent repair. Bar La Esquina.", "incidencia"),
    # Caso difícil 6: Sin nombre de negocio (consulta de transporte y condiciones)
    ("Buenos días, ¿cuál es el pedido mínimo para que el envío sea gratuito a la zona centro de Madrid?", "consulta"),
    # Caso difícil 7: Sin nombre de negocio (pedido explícito sin identificar cliente)
    ("Por favor, enviad 10 kg de café descafeinado y 5 kg de Etiopía lo antes posible.", "pedido"),
    # Caso difícil 8: Cliente que NO existe en la base de datos (dispara aviso de negocio)
    ("Hola, somos Café del Bosque. Queremos hacer un primer pedido de 20 kg de blend hostelería.", "pedido"),
    # Caso difícil 9: Avería con cliente que NO existe en la base de datos (dispara aviso de negocio)
    ("Avería urgente: el molinillo se ha bloqueado por completo y no muele. Taberna El Rincón.", "incidencia"),
    # Caso difícil 10: Mixto complejo (pedido en firme + consulta de precio sobre otro catálogo)
    ("Traednos 15 kg de blend el martes. Por cierto, ¿a qué precio tenéis los vasos compostables? Cafetería Atocha 12.", "mixto"),
]


if __name__ == "__main__":
    for nombre, extraer in [("OpenAI", con_openai), ("Claude", con_claude), ("Gemini", con_gemini)]:
        aciertos = 0
        for correo, esperado in CASOS:
            resultado = extraer(correo)
            aciertos += resultado.tipo == esperado

            # Validación de negocio 1: el esquema garantiza int, pero no cantidad positiva
            if any(l.cantidad <= 0 for l in resultado.lineas):
                print(f"  [{nombre}] cantidad no válida en: {correo[:40]}...")

            # Validación de negocio 2: comprobar si el cliente nombrado existe en la base de datos
            if resultado.cliente:
                cliente_bd = buscar_cliente(resultado.cliente)
                if not cliente_bd:
                    print(f"  [{nombre}] AVISO: cliente no encontrado en la base de datos: '{resultado.cliente}' (correo: {correo[:40]}...)")

        print(f"{nombre}: {aciertos}/{len(CASOS)} tipos correctos")

