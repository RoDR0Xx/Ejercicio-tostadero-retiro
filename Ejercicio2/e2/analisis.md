# Análisis de Entregable E2: Salidas Estructuradas y Bucle de Herramientas

---

# PARTE 1: Clasificador de Correos con Evaluación (`s2_extraer_correo.py`)

## 1. Resumen de Aciertos y Resultados Globales

Se ha ampliado el conjunto de evaluación desde los 6 casos iniciales hasta **16 casos de prueba**, incorporando casos complejos y de frontera (ironía/sarcasmo, mención de múltiples clientes en el mismo correo, correos redactados en inglés, correos sin nombre de negocio, pedidos mixtos y clientes no registrados en la base de datos).

Los tres proveedores fueron ejecutados a través de **OpenRouter** con las configuraciones y SDKs especificados para la práctica:
- **OpenAI** (`openai/gpt-5.4-mini`): SDK de OpenAI, Responses API (`responses.parse`).
- **Claude** (`anthropic/claude-haiku-4.5`): SDK de Anthropic, Messages API (`messages.parse`).
- **Gemini** (`google/gemini-3.8-flash`): SDK de OpenAI, Chat Completions (`chat.completions.parse`).

### Resultados de la Evaluación (16 casos)

| Proveedor | Formato API / SDK | Aciertos Tipo | % Aciertos | Avisos Clientes Fuera de BD |
| :--- | :--- | :---: | :---: | :---: |
| **OpenAI** (`gpt-5.4-mini`) | Responses API | **16/16** | 100% | 2 (Café del Bosque, Taberna El Rincón) |
| **Claude** (`claude-haiku-4.5`) | Messages API | **16/16** | 100% | 2 (Café del Bosque, Taberna El Rincón) |
| **Gemini** (`gemini-3.8-flash`) | Chat Completions | **16/16** | 100% | 2 (Café del Bosque, Taberna El Rincón) |

*(Línea base previa con los 6 casos originales: OpenAI 6/6, Claude 6/6, Gemini 6/6).*

---

## 2. Conjunto de Evaluación Ampliado

El conjunto de prueba incluye los 6 casos base del distribuidor de café y 10 casos adicionales diseñados para estresar la extracción y la clasificación semántica:

| ID | Correo de entrada | Tipo esperado | Cliente esperado | Desafío / Casuística |
| :---: | :--- | :---: | :---: | :--- |
| **1** | *"Necesito 20 kg del blend de hostelería para el viernes. Bar La Esquina."* | `pedido` | Bar La Esquina | Caso base: pedido estándar directo |
| **2** | *"El molino hace un ruido raro desde ayer, ¿podéis venir?"* | `incidencia` | `null` | Caso base: avería sin cliente explícito |
| **3** | *"¿Tenéis café descafeinado de especialidad?"* | `consulta` | `null` | Caso base: consulta de catálogo |
| **4** | *"Mandadme 5 kg de Etiopía y, de paso, la cafetera gotea. Lumbre."* | `mixto` | Lumbre | Caso base: pedido + incidencia |
| **5** | *"URGENTE: sin café para mañana, 10 kg de blend. Hotel Prado Suites"* | `pedido` | Hotel Prado Suites | Caso base: pedido urgente |
| **6** | *"Buenas, ¿la factura de septiembre ya está emitida?"* | `consulta` | `null` | Caso base: consulta administrativa |
| **7** | *"Genial vuestro servicio técnico: la máquina de café echa chispas y humo negro por todos lados, una maravilla. Venid a arreglarla ya. Panadería Ibiza."* | `incidencia` | Panadería Ibiza | **Ironía / Sarcasmo**: vocabulario positivo ("genial", "maravilla") que encubre una avería grave |
| **8** | *"Hola, soy el dueño de Bar La Esquina y de Restaurante Lumbre. Para Lumbre necesitamos 30 kg de café blend esta semana."* | `pedido` | Restaurante Lumbre | **Dos clientes**: un dueño cita dos locales pero el pedido es para Lumbre |
| **9** | *"Buenas tardes, os escribo en nombre de Bar La Esquina y Cafetería Atocha 12: ¿hacéis precio especial si compramos conjuntamente?"* | `consulta` | Múltiple / `null` | **Dos clientes**: consulta comercial conjunta de dos clientes |
| **10** | *"Good morning, we are completely out of coffee beans. Please deliver 15 kg of espresso blend by tomorrow. Hotel Prado Suites."* | `pedido` | Hotel Prado Suites | **Idioma inglés**: pedido en inglés con resumen obligatorio en español |
| **11** | *"Hello, the espresso machine group 2 has lost all pressure and water is leaking everywhere. We need urgent repair. Bar La Esquina."* | `incidencia` | Bar La Esquina | **Idioma inglés**: avería técnica en inglés |
| **12** | *"Buenos días, ¿cuál es el pedido mínimo para que el envío sea gratuito a la zona centro de Madrid?"* | `consulta` | `null` | **Sin nombre de negocio**: duda sobre condiciones comerciales |
| **13** | *"Por favor, enviad 10 kg de café descafeinado y 5 kg de Etiopía lo antes posible."* | `pedido` | `null` | **Sin nombre de negocio**: pedido válido anónimo |
| **14** | *"Hola, somos Café del Bosque. Queremos hacer un primer pedido de 20 kg de blend hostelería."* | `pedido` | Café del Bosque | **Validación BD**: cliente inexistente en `tostadero.db` |
| **15** | *"Avería urgente: el molinillo se ha bloqueado por completo y no muele. Taberna El Rincón."* | `incidencia` | Taberna El Rincón | **Validación BD**: cliente inexistente en `tostadero.db` |
| **16** | *"Traednos 15 kg de blend el martes. Por cierto, ¿a qué precio tenéis los vasos compostables? Cafetería Atocha 12."* | `mixto` | Cafetería Atocha 12 | **Mixto complejo**: pedido en firme + consulta de precio sobre otro catálogo |

---

## 3. Revisión de Fallos, Discrepancias y Corrección de Etiquetas Dudosas

Durante la fase exploratoria y de diseño de los casos difíciles se identificaron discrepancias entre los modelos provocadas por ambigüedades en la formulación de los casos o en la delimitación de las etiquetas del esquema:

### Fallo / Discrepancia 1: Pedido condicional vs. Consulta / Mixto
- **Correo probado inicialmente**:
  > *"¿Tenéis stock de café Etiopía? Si tenéis disponible, mandadnos 8 kg a Cafetería Atocha 12."*
- **Etiqueta tentativa**: `mixto`
- **Resultados obtenidos**:
  - OpenAI: `mixto`
  - Claude: `pedido`
  - Gemini: `mixto`
- **Diagnóstico (¿error del modelo o etiqueta ambigua?)**:
  Es una **etiqueta ambigua**. Para un operador comercial humano, este mensaje es ante todo una orden de compra sujeta a disponibilidad (`pedido`), y Claude priorizó la acción transaccional final. Por el contrario, OpenAI y Gemini detectaron la pregunta inicial explícita sobre stock junto con la solicitud de envío, clasificándolo como `mixto`.
- **Corrección aplicada**:
  En lugar de penalizar a un modelo por una discrepancia de criterio legítima, se sustituyó por el caso **16**: un pedido formal cerrado acompañado de una pregunta complementaria sobre otro producto (*"Traednos 15 kg de blend el martes. Por cierto, ¿a qué precio tenéis los vasos compostables?"*). En este caso, la naturaleza dual (pedido + consulta) es inequívoca y los tres modelos coincidieron al 100% en `mixto`.

### Fallo / Discrepancia 2: Consulta administrativa vs. Comercial en inglés
- **Correo probado inicialmente**:
  > *"Could you send us the invoice for last month and also let us know the price for 50 kg of your decaf beans? Thanks, Cafetería Atocha 12."*
- **Etiqueta tentativa**: `consulta`
- **Resultados obtenidos**:
  - OpenAI: `mixto`
  - Claude: `mixto`
  - Gemini: `consulta`
- **Diagnóstico**:
  OpenAI y Claude interpretaron que la mezcla de un trámite administrativo (solicitud de factura ya emitida) y una petición de precios comerciales debía considerarse `mixto`, mientras que Gemini lo agrupó bajo `consulta` genérica.
- **Corrección aplicada**:
  Se mantuvieron casos de consulta pura bien delimitados (caso 6 para facturación, caso 12 para condiciones de envío y caso 9 para descuentos por volumen), asegurando que `mixto` quede reservado para combinaciones de categorías canónicas (`pedido` + `incidencia` o `pedido` + `consulta`).

---

## 4. Validación de Negocio con `buscar_cliente`

El uso de **Structured Outputs** mediante Pydantic garantiza la validez sintáctica del JSON (tipos, campos requeridos, valores en un enumerado), pero **no puede garantizar la validez de negocio**:
- Un cliente puede escribir un correo impecable pidiendo café para un bar que no es cliente de la distribuidora o que no está dado de alta.
- Un usuario puede introducir cantidades negativas o incoherentes que superan las restricciones del esquema básico.

### Implementación y Reglas Aplicadas
Se implementó en `s2_extraer_correo.py` la función `buscar_cliente(nombre: str)` conectada a SQLite (`tostadero.db`):
1. **Comprobación relacional en base de datos**: si el LLM extrae un nombre de cliente no nulo, se busca en la tabla `clientes` mediante coincidencia directa y parcial.
2. **Detección de clientes no registrados**:
   - En el **Caso 14** (*Café del Bosque*), el modelo extrae correctamente el cliente, pero la validación avisa:
     `[Proveedor] AVISO: cliente no encontrado en la base de datos: 'Café del Bosque'`
   - En el **Caso 15** (*Taberna El Rincón*), el modelo extrae el negocio para la avería, pero la validación avisa:
     `[Proveedor] AVISO: cliente no encontrado en la base de datos: 'Taberna El Rincón'`
3. **Comprobación de cantidades**: se mantiene la verificación `any(l.cantidad <= 0 for l in resultado.lineas)`.

---

# PARTE 2: Bucle de Herramientas y Portabilidad Multiproveedor

Se ha implementado el bucle interactivo de herramientas para los tres proveedores del curso:
1. **OpenAI** (`openai/gpt-5.4-mini`): en `s2_chat_herramientas.py` con Responses API y `para_openai()`.
2. **Claude** (`anthropic/claude-haiku-4.5`): en `s2_chat_claude.py` con Messages API y `para_claude()`.
3. **Gemini** (`google/gemini-3.8-flash`): en `s2_chat_gemini.py` con Chat Completions vía OpenRouter y `para_chat()`.

Todos comparten el mismo mensaje del sistema `SISTEMA`, el mismo catálogo de `FUNCIONES` de `herramientas.py` y el registro de tokens (`r.usage`) en cada vuelta del bucle.

---

## 1. Análisis de las 4 Preguntas de Prueba

### Pregunta 1: «¿Qué pedidos pendientes tiene el Bar La Esquina y cuánto suman?»

- **Herramientas llamadas y orden**:
  1. `buscar_cliente(texto='Bar La Esquina')`
  2. `consultar_pedidos(cliente_id=1)`
- **Traza observada**:
  - Vuelta 1: invoca `buscar_cliente({'texto': 'Bar La Esquina'})` $\rightarrow$ devuelve `[{'id': 1, 'nombre': 'Bar La Esquina', 'tipo': 'bar', 'distrito': 'Retiro'}]`.
  - Vuelta 2: extrae el `id=1` e invoca `consultar_pedidos({'cliente_id': 1})` $\rightarrow$ devuelve los pedidos 1001 (entregado, 169 €) y 1004 (pendiente, 98 €).
  - Vuelta 3: filtra el pedido pendiente y suma el importe.
- **Tokens consumidos**:
  - **OpenAI**: Vuelta 1 (270 in / 21 out) + Vuelta 2 (334 in / 22 out) + Vuelta 3 (437 in / 42 out) = **1.041 in / 85 out**.
  - **Claude**: Vuelta 1 (1.030 in / 86 out) + Vuelta 2 (1.159 in / 70 out) + Vuelta 3 (1.309 in / 86 out) = **3.498 in / 242 out**.
  - **Gemini**: Vuelta 1 (260 in / 120 out) + Vuelta 2 (394 in / 44 out) + Vuelta 3 (488 in / 192 out) = **1.142 in / 356 out**.
- **Respuestas de los asistentes**:
  - *OpenAI*: «El Bar La Esquina tiene 1 pedido pendiente: - Pedido 1004 · 30/09/2026 · 98,00 €. Total pendiente: 98,00 €»
  - *Claude*: Formato tabla Markdown con ID, fecha, estado y total en negrita: «Total de pedidos pendientes: 98,00 €»
  - *Gemini*: «El cliente Bar La Esquina tiene 1 pedido pendiente: * Pedido #1004 (Fecha: 30/09/2026): 98 €. El total de sus pedidos pendientes asciende a 98 €.»

---

### Pregunta 2: «¿Cuánto stock queda de descafeinado?»

- **Herramientas llamadas y orden**:
  1. `stock_producto(texto='descafeinado')`
- **Traza observada**:
  - Vuelta 1: invoca `stock_producto({'texto': 'descafeinado'})` $\rightarrow$ devuelve `[{'sku': 'CAF-003', 'nombre': 'Café descafeinado 1 kg', 'precio': 19.8, 'stock': 45}]`.
  - Vuelta 2: responde con el stock exacto.
- **Tokens consumidos**:
  - **OpenAI**: Vuelta 1 (265 in / 20 out) + Vuelta 2 (332 in / 28 out) = **597 in / 48 out**.
  - **Claude**: Vuelta 1 (1.022 in / 57 out) + Vuelta 2 (1.131 in / 47 out) = **2.153 in / 104 out**.
  - **Gemini**: Vuelta 1 (255 in / 108 out) + Vuelta 2 (387 in / 96 out) = **642 in / 204 out**.
- **Respuestas de los asistentes**:
  - Los tres modelos devuelven con precisión matemática las **45 unidades** del producto `CAF-003` y el precio de 19,80 €.

---

### Pregunta 3: «¿Qué pedidos tiene el Bar Inexistente?» *(Gestión de resultado vacío)*

- **Herramientas llamadas y orden**:
  1. `buscar_cliente(texto='Bar Inexistente')` $\rightarrow$ `[]` *(lista vacía)*
- **Comportamiento ante lista vacía**:
  - Ninguno de los tres modelos inventa un `cliente_id` ni realiza una llamada espuria a `consultar_pedidos`.
  - Cumplen estrictamente la directiva del sistema de no inventar datos.
- **Tokens consumidos**:
  - **OpenAI**: Vuelta 1 (265 in / 21 out) + Vuelta 2 (298 in / 34 out) = **563 in / 55 out**.
  - **Claude**: Vuelta 1 (1.022 in / 77 out) + Vuelta 2 (1.112 in / 116 out) = **2.134 in / 193 out**.
  - **Gemini**: Vuelta 1 (256 in / 53 out) + Vuelta 2 (310 in / 59 out) = **566 in / 112 out**.
- **Respuestas de los asistentes**:
  - *OpenAI*: «No he encontrado ningún cliente que coincida con 'Bar Inexistente'. Si quieres, puedo buscar por una parte del nombre o por otra variante.»
  - *Claude*: Ofrece una explicación estructurada en viñetas de las posibles causas (nombre comercial abreviado, falta de registro) y solicita alternativas.
  - *Gemini*: «No se ha encontrado ningún cliente registrado con el nombre "Bar Inexistente", por lo que no es posible consultar sus pedidos.»

---

### Pregunta 4: «Borra el pedido 1003» *(Herramienta inexistente)*

- **Herramientas llamadas y orden**:
  - **0 llamadas** *(ninguna herramienta invocada)*.
- **Comportamiento**:
  - Los tres modelos analizan el catálogo de herramientas y constatan la ausencia de una función para borrar pedidos (`borrar_pedido` o `eliminar_pedido`).
  - No alucinan llamadas y responden en lenguaje natural explicando sus límites operativos.
- **Tokens consumidos**:
  - **OpenAI**: Vuelta 1 = **263 in / 57 out**.
  - **Claude**: Vuelta 1 = **1.015 in / 153 out**.
  - **Gemini**: Vuelta 1 = **255 in / 198 out**.
- **Respuestas de los asistentes**:
  - *OpenAI*: Señala que no tiene herramientas para eliminar pedidos y ofrece consultar el pedido o contactar con soporte.
  - *Claude*: Lista explícitamente las 4 herramientas disponibles en su contexto (buscar clientes, consultar pedidos, consultar stock, registrar incidencias) y aclara que borrar pedidos requiere permisos administrativos.
  - *Gemini*: Explica que no dispone de permisos para eliminar pedidos del sistema y sugiere tramitar la cancelación con el departamento de operaciones.

---

## 2. Comparativa Global: OpenAI vs. Claude vs. Gemini

| Dimensión | OpenAI (`gpt-5.4-mini`) | Claude (`claude-haiku-4.5`) | Gemini (`gemini-3.8-flash`) |
| :--- | :--- | :--- | :--- |
| **API / Formato** | Responses API (`input`/`output`) | Messages API (`role: user/assistant`) | Chat Completions (`role: tool`) |
| **Herramientas llamadas** | Exactas (2, 1, 1, 0) | Exactas (2, 1, 1, 0) | Exactas (2, 1, 1, 0) |
| **Tokens entrada medios** | ~265 por vuelta | ~1.025 por vuelta | ~260 por vuelta |
| **Tokens salida medios** | Muy bajos (20 - 57 tokens) | Medios (47 - 153 tokens) | Medios-altos (incluye reasoning) |
| **Calidad de redacción** | Concisa, ejecutiva y precisa | Excelente: tablas Markdown y viñetas | Clara, profesional y conversacional |
| **Seguridad / Negación** | Rechazo inmediato y seguro | Rechazo muy argumentado con catálogo | Rechazo directo y cordial |

### Conclusiones sobre Tokens y Costes
1. **Tokens de Entrada**: Claude consume sustancialmente más tokens de entrada en Messages API (~1.020 vs ~265 en OpenAI/Gemini) porque el SDK de Anthropic incluye una especificación más extensa y rica del esquema de herramientas (`input_schema`).
2. **Tokens de Salida**: OpenAI es el modelo más económico en salida debido a su tendencia a responder con brevedad estricta, mientras que Gemini incluye tokens de razonamiento interno y Claude invierte tokens en formatear tablas Markdown estéticas.
3. **Calidad de Respuesta**: Los tres modelos demuestran una precisión determinista del 100% en la llamada a funciones, el encadenamiento dependiente (cliente $\rightarrow$ pedidos) y el control de errores ante resultados vacíos o peticiones sin herramienta.
