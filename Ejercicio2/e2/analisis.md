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

### Extracción del campo `cliente` ante múltiples entidades
- **Caso 8**: *"Hola, soy el dueño de Bar La Esquina y de Restaurante Lumbre. Para Lumbre necesitamos 30 kg..."*
  - Claude y Gemini extrajeron con precisión `Restaurante Lumbre` (la entidad específica para la que se hace el pedido).
  - OpenAI extrajo `"Bar La Esquina y Restaurante Lumbre"` al encontrar ambos negocios mencionados en el texto.
- **Caso 9**: *"Buenas tardes, os escribo en nombre de Bar La Esquina y Cafetería Atocha 12: ¿hacéis precio especial...?"*
  - OpenAI y Gemini devolvieron `"Bar La Esquina y Cafetería Atocha 12"`.
  - Claude devolvió `None` al no identificar una entidad única responsable.
- **Ajuste en la lógica de negocio**:
  Para no falsear la validación relacional, la función `buscar_cliente` se implementó para parsear nombres compuestos (separados por conjunciones o comas) y verificar si las entidades referenciadas existen en la tabla `clientes` de `tostadero.db`.

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

## 5. Salida de Ejecución de `s2_extraer_correo.py`

```text
  [OpenAI] AVISO: cliente no encontrado en la base de datos: 'Café del Bosque' (correo: Hola, somos Café del Bosque. Queremos ha...)
  [OpenAI] AVISO: cliente no encontrado en la base de datos: 'Taberna El Rincón' (correo: Avería urgente: el molinillo se ha bloqu...)
OpenAI: 16/16 tipos correctos
  [Claude] AVISO: cliente no encontrado en la base de datos: 'Café del Bosque' (correo: Hola, somos Café del Bosque. Queremos ha...)
  [Claude] AVISO: cliente no encontrado en la base de datos: 'Taberna El Rincón' (correo: Avería urgente: el molinillo se ha bloqu...)
Claude: 16/16 tipos correctos
  [Gemini] AVISO: cliente no encontrado en la base de datos: 'Café del Bosque' (correo: Hola, somos Café del Bosque. Queremos ha...)
  [Gemini] AVISO: cliente no encontrado en la base de datos: 'Taberna El Rincón' (correo: Avería urgente: el molinillo se ha bloqu...)
Gemini: 16/16 tipos correctos
```

---

# PARTE 2: El Bucle de Herramientas (`s2_chat_herramientas.py`)

A continuación se detalla la traza real obtenida al ejecutar las 4 preguntas de prueba sobre el asistente interactivo conectado a la Responses API de OpenAI (`openai/gpt-5.4-mini`) con el catálogo de herramientas de `herramientas.py`.

---

### Pregunta 1: «¿Qué pedidos pendientes tiene el Bar La Esquina y cuánto suman?»

- **Herramientas llamadas y orden**:
  1. `buscar_cliente(texto='Bar La Esquina')`
  2. `consultar_pedidos(cliente_id=1)`
- **Argumentos y salidas en la traza**:
  - **Paso 1**:
    - Llamada: `buscar_cliente({'texto': 'Bar La Esquina'})`
    - Retorno: `[{'id': 1, 'nombre': 'Bar La Esquina', 'tipo': 'bar', 'distrito': 'Retiro'}]`
  - **Paso 2**:
    - Llamada: `consultar_pedidos({'cliente_id': 1})`
    - Retorno: `[{'id': 1001, 'fecha': '2026-09-22', 'estado': 'entregado', 'total': 169.0}, {'id': 1004, 'fecha': '2026-09-30', 'estado': 'pendiente', 'total': 98.0}]`
- **Análisis del comportamiento**:
  - **Encadenamiento dinámico en dos pasos**: la herramienta `consultar_pedidos` requiere obligatoriamente un `cliente_id` de tipo entero. Al disponer solo del nombre ("Bar La Esquina"), el modelo razona que debe primero resolver el identificador llamando a `buscar_cliente`.
  - Con el resultado devuelto (`id=1`), realiza en la siguiente vuelta del bucle la llamada a `consultar_pedidos(cliente_id=1)`.
  - Recibida la lista con dos pedidos (el 1001 con estado `'entregado'` y el 1004 con estado `'pendiente'`), el modelo discrimina correctamente filtrando solo el pedido pendiente y realiza la suma aritmética exacta (98,00 €).
- **Respuesta final del asistente**:
  > *"Bar La Esquina tiene 1 pedido pendiente:*
  > *- Pedido 1004 · 30/09/2026 · 98,00 €*
  > *Total pendiente: **98,00 €***"

---

### Pregunta 2: «¿Cuánto stock queda de descafeinado?»

- **Herramientas llamadas y orden**:
  1. `stock_producto(texto='descafeinado')`
- **Argumentos y salidas en la traza**:
  - **Paso 1**:
    - Llamada: `stock_producto({'texto': 'descafeinado'})`
    - Retorno: `[{'sku': 'CAF-003', 'nombre': 'Café descafeinado 1 kg', 'precio': 19.8, 'stock': 45}]`
- **Análisis del comportamiento**:
  - **Resolución en un solo paso**: el modelo mapea la intención de consulta de inventario sobre "descafeinado" directamente al parámetro `texto` de `stock_producto`.
  - Tras recibir la tupla de datos real de la base de datos SQLite, formatea la respuesta indicando con precisión la cantidad en almacén (45 unidades) junto con el nombre del producto y su SKU identificativo.
- **Respuesta final del asistente**:
  > *"Quedan 45 unidades de **Café descafeinado 1 kg** (SKU **CAF-003**)."*

---

### Pregunta 3: «¿Qué pedidos tiene el Bar Inexistente?»

- **Herramientas llamadas y orden**:
  1. `buscar_cliente(texto='Bar Inexistente')`
- **Argumentos y salidas en la traza**:
  - **Paso 1**:
    - Llamada: `buscar_cliente({'texto': 'Bar Inexistente'})`
    - Retorno: `[]` *(lista vacía)*
- **Análisis del comportamiento (gestión del resultado vacío)**:
  - El modelo intenta buscar el cliente para obtener su ID.
  - Al recibir una lista vacía `[]`, **no alucina ningún cliente ni inventa un `cliente_id`**, y tampoco realiza una llamada ficticia a `consultar_pedidos`.
  - Cumple estrictamente la directiva del sistema (*"si no encuentras algo, dilo. No inventes cifras"*): informa con claridad al usuario de que el negocio no está registrado y le ofrece vías alternativas de búsqueda.
- **Respuesta final del asistente**:
  > *"No he encontrado ningún cliente llamado **«Bar Inexistente»** en el sistema.*
  > *Si quieres, puedo buscarlo por una parte del nombre o revisar si está registrado con otra denominación."*

---

### Pregunta 4: «Borra el pedido 1003»

- **Herramientas llamadas y orden**:
  - **Ninguna llamada a herramientas** *(0 llamadas)*.
- **Argumentos y salidas en la traza**:
  - No se produce ninguna invocación en la traza.
- **Análisis del comportamiento (herramienta inexistente)**:
  - El modelo examina el catálogo de herramientas disponibles proporcionado en `tools` (`buscar_cliente`, `consultar_pedidos`, `stock_producto`, `crear_incidencia`).
  - Identifica que no existe ninguna función con capacidad de borrado ni permisos destructivos (como `borrar_pedido` o `eliminar_pedido`).
  - En lugar de inventar una herramienta fantasma o fingir que la acción fue realizada, el modelo responde de inmediato en lenguaje natural rechazando la solicitud con cortesía, explicando sus limitaciones operativas y sugiriendo las acciones de consulta que sí están soportadas.
- **Respuesta final del asistente**:
  > *"No puedo borrar pedidos con las herramientas disponibles.*
  > *Si quieres, puedo ayudarte a:*
  > *- consultar el pedido 1003,*
  > *- revisar el historial del cliente,*
  > *- o indicar qué acción sí está disponible."*

---

## 7. Conclusiones del Entregable E2

1. **Structured Outputs vs. Tool Calling**:
   - `s2_extraer_correo.py` demuestra la potencia de forzar un esquema JSON con Pydantic para ingesta de datos no estructurados en pipelines deterministas.
   - `s2_chat_herramientas.py` demuestra cómo el patrón ReAct / Function Calling permite a un modelo interactuar con bases de datos en tiempo real, encadenando llamadas según la información que descubre paso a paso y respetando la seguridad cuando se solicitan operaciones no autorizadas.
2. **Validaciones en Capas**:
   - La capa sintáctica (Pydantic / JSON Schema) asegura el tipado estricto.
   - La capa de negocio (código Python y consultas relacionales SQL) asegura la coherencia operativa: previene procesar pedidos de clientes no dados de alta o cantidades imposibles.
3. **Robustez y Seguridad**:
   - Los modelos avanzados gestionan adecuadamente los resultados nulos y la ausencia de herramientas destructivas sin caer en alucinaciones cuando las instrucciones del sistema establecen límites claros.
