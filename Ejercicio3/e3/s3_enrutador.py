"""Sesión 3. Enrutador Híbrido: Clasificador (Sesión 2) + Agente (Sesión 3).

Optimización de costes y latencia:
- Consultas sencillas -> Camino barato y directo (LLM directo con Gemini Flash o GPT-5.4-nano).
- Pedidos, incidencias y mixtos -> Camino agéntico completo con herramientas (Claude Haiku 4.5).
"""
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Asegurar codificación UTF-8 en consola de Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Carga de variables de entorno buscando en múltiples rutas
load_dotenv()
if not os.getenv("OPENROUTER_API_KEY"):
    for p in [Path(".env"), Path("../.env"), Path(__file__).parent / ".env", Path(__file__).parent.parent / ".env"]:
        if p.exists():
            load_dotenv(p)
            break

import openai
from llm_client import LLM
from s2_extraer_correo import CorreoClasificado, con_openai, SISTEMA as SISTEMA_CLASIFICADOR
from s3_agente import Agente, Herramienta, SISTEMA as SISTEMA_AGENTE
from herramientas import DEFINICIONES, FUNCIONES

# 1. Instrucciones para responder consultas sencillas sin herramientas
SISTEMA_CONSULTAS = """Eres el asistente comercial y de atención al cliente de Tostadero Retiro S.L.
Tu cometido es resolver consultas generales de clientes y hosteleros de forma breve, profesional y cordial en español.

Catálogo y precios de referencia:
- Café de especialidad Etiopía 1 kg: 24,50 €
- Café blend hostelería 1 kg: 16,90 €
- Café descafeinado 1 kg: 19,80 €
- Máquinas y consumibles: Cafetera espresso 2 grupos (2.890 €), Molino on-demand (640 €), Vasos compostables 8 oz (pack 1.000 u. a 54 €).

Condiciones comerciales y de servicio:
- Envíos: entrega en 24-48 horas laborables. Envío gratuito en la Comunidad de Madrid a partir de 50 € de pedido.
- Facturación: las facturas mensuales se emiten y envían por correo electrónico durante los primeros 5 días hábiles del mes siguiente.
- Mantenimiento y revisiones: nuestro servicio técnico opera todo el año (incluido agosto) con cobertura de urgencias.

Si el cliente solicita tramitar un pedido en firme o reportar una avería de una máquina, recuérdale amablemente que indique el nombre de su establecimiento para que podamos procesarlo inmediatamente."""

# 2. Construcción del agente de la Sesión 3 con sus herramientas
herramientas = [
    Herramienta(d["name"], d["description"], d["parameters"], FUNCIONES[d["name"]],
                requiere_aprobacion=(d["name"] == "crear_incidencia"))
    for d in DEFINICIONES
]
agente = Agente(SISTEMA_AGENTE, herramientas, max_pasos=8, aprobador=lambda n, a: True)


def clasificar_con_metricas(correo: str) -> tuple[CorreoClasificado, int, int]:
    """Ejecuta la clasificación estructurada midiendo el consumo de tokens."""
    r = openai.OpenAI().responses.parse(
        model=os.environ["OPENAI_MODEL"],
        instructions=SISTEMA_CLASIFICADOR,
        input=correo,
        text_format=CorreoClasificado,
    )
    return r.output_parsed, r.usage.input_tokens, r.usage.output_tokens


def atender(correo: str, modelo_barato: str = "gemini") -> str:
    """Función de enrutado solicitada en el enunciado."""
    clasificacion = con_openai(correo)        # sesión 2: salida estructurada
    if clasificacion.tipo == "consulta":      # camino barato y predecible
        if modelo_barato == "gemini":
            return LLM("gemini").responder(SISTEMA_CONSULTAS, correo).texto
        else:
            return LLM("openai", modelo=modelo_barato).responder(SISTEMA_CONSULTAS, correo).texto
    return agente.ejecutar(correo)            # camino agéntico para lo complejo


def atender_con_metricas(correo: str, modelo_barato: str = "gemini") -> dict:
    """Ejecuta el enrutador midiendo tiempos, tokens y llamadas exactas."""
    t0 = time.perf_counter()
    clasificacion, t_in_clas, t_out_clas = clasificar_con_metricas(correo)
    
    if clasificacion.tipo == "consulta":
        if modelo_barato == "gemini":
            r_llm = LLM("gemini").responder(SISTEMA_CONSULTAS, correo)
        else:
            r_llm = LLM("openai", modelo=modelo_barato).responder(SISTEMA_CONSULTAS, correo)
            
        return {
            "tipo": "consulta",
            "camino": f"barato ({modelo_barato})",
            "texto": r_llm.texto,
            "llamadas": 2,  # 1 clasificación + 1 generación directa
            "tokens_entrada": t_in_clas + r_llm.tokens_entrada,
            "tokens_salida": t_out_clas + r_llm.tokens_salida,
            "segundos": time.perf_counter() - t0,
        }
    else:
        texto = agente.ejecutar(correo)
        return {
            "tipo": clasificacion.tipo,
            "camino": "agéntico (Claude con herramientas)",
            "texto": texto,
            "llamadas": 1 + agente.ultimo_consumo["llamadas"],  # 1 clasificación + N vueltas agente
            "tokens_entrada": t_in_clas + agente.ultimo_consumo["tokens_entrada"],
            "tokens_salida": t_out_clas + agente.ultimo_consumo["tokens_salida"],
            "segundos": time.perf_counter() - t0,
        }


def evaluar_solo_agente(correo: str) -> dict:
    """Ejecuta el correo directamente en el agente (camino caro 100%) para comparar."""
    t0 = time.perf_counter()
    texto = agente.ejecutar(correo)
    return {
        "camino": "agéntico 100%",
        "texto": texto,
        "llamadas": agente.ultimo_consumo["llamadas"],
        "tokens_entrada": agente.ultimo_consumo["tokens_entrada"],
        "tokens_salida": agente.ultimo_consumo["tokens_salida"],
        "segundos": time.perf_counter() - t0,
    }


if __name__ == "__main__":
    # Los 6 casos base de la Sesión 2
    CASOS_S2 = [
        ("Necesito 20 kg del blend de hostelería para el viernes. Bar La Esquina.", "pedido"),
        ("El molino hace un ruido raro desde ayer, ¿podéis venir?", "incidencia"),
        ("¿Tenéis café descafeinado de especialidad?", "consulta"),
        ("Mandadme 5 kg de Etiopía y, de paso, la cafetera gotea. Lumbre.", "mixto"),
        ("URGENTE: sin café para mañana, 10 kg de blend. Hotel Prado Suites", "pedido"),
        ("Buenas, ¿la factura de septiembre ya está emitida?", "consulta"),
    ]

    print("=" * 80)
    print("COMPARATIVA DE ENRUTADO: TODO AGENTE vs. ENRUTADOR (GEMINI) vs. ENRUTADOR (NANO)")
    print("=" * 80)

    for i, (correo, tipo_esperado) in enumerate(CASOS_S2, 1):
        print(f"\n[Caso {i}] ({tipo_esperado}) '{correo}'")
        res_nano = atender_con_metricas(correo, modelo_barato="openai/gpt-5.4-nano")
        print(f"  -> Enrutado a: {res_nano['camino']} | Llamadas={res_nano['llamadas']} | Tokens: in={res_nano['tokens_entrada']}, out={res_nano['tokens_salida']}")
        print(f"     Respuesta breve: {res_nano['texto'].strip().replace(chr(10), ' ')[:90]}...")
