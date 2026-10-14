# Análisis de proveedores

## Estado de los datos

No se completó la comparativa. La ejecución se detuvo en la primera petición, de OpenAI, con error `402` de OpenRouter por saldo insuficiente. Las URLs configuradas para OpenAI y Anthropic también apuntan a OpenRouter. Por tanto, `comparativa.csv` contiene solo la cabecera: no hay tiempos, recuentos de tokens, costes ni respuestas que puntuar.

## Diferencia de tokens

Con este CSV no se puede identificar qué modelo contabilizaría más tokens. En general, una misma respuesta visible puede dar recuentos distintos porque cada modelo usa su propio tokenizador. Además, el uso reportado puede incluir tokens de razonamiento interno que no aparecen en el texto mostrado; por eso una respuesta breve no siempre implica pocos tokens de salida.

## Elección para 2.000 correos al mes

La comparativa no aporta evidencia para elegir un proveedor: faltan coste por correo, latencia y puntuaciones de calidad de los tres. No sería responsable declarar un ganador basándose solo en impresiones o en las tarifas publicadas. Cuando haya saldo, hay que completar las 15 filas, puntuar la calidad y comparar por proveedor el coste medio por correo, la latencia y la calidad media. El coste mensual estimado será el coste medio por correo multiplicado por 2.000; elegiría una opción de calidad suficiente que ofrezca el mejor equilibrio entre coste y latencia.

## Cómo completar

Añadir saldo a OpenRouter y volver a ejecutar `python s1_comparativa.py`. Después, copiar el CSV generado a este directorio, puntuar `calidad_1a5` en equipo y actualizar este análisis con los resultados medidos.
