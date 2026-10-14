# P2. El mismo encargo a tres proveedores

## Estado de la ejecución

La primera ejecución de `python s1_hola_tres.py` se detuvo en la llamada inicial. La petición configurada para OpenAI se envía a través de OpenRouter (`OPENAI_BASE_URL`) y el servicio respondió `402`: la cuenta no tiene créditos comprados. El script no llegó a consultar Claude ni Gemini. No se repitió la ejecución porque volvería a detenerse en el mismo punto.

Las respuestas siguientes son orientativas para preparar la puesta en común; no son resultados observados en esta máquina.

## Preguntas

1. **¿Qué proveedor responde antes? ¿La diferencia se mantiene entre ejecuciones?**

   No se puede saber de antemano: depende del modelo elegido, la carga del servicio, la red y la ruta hasta el proveedor. Puede cambiar qué proveedor queda primero entre ejecuciones; habría que comparar los tiempos medidos en ambas rondas.

2. **Para el mismo texto, ¿por qué no coinciden los tokens de entrada?**

   Cada modelo utiliza su propio tokenizador. Por eso el mismo correo, las instrucciones del sistema y la estructura de los mensajes pueden convertirse en cantidades distintas de tokens.

3. **El correo es mixto: incidencia y pedido. ¿Lo clasifican bien los tres?**

   Una respuesta correcta debería reconocer ambas partes: la cafetera que pierde presión es una incidencia y el pedido 1004 sigue pendiente. Lo ideal es que los tres lo clasifiquen como mixto; para saber si realmente lo hacen hay que revisar sus respuestas.

4. **¿Cambia la redacción entre la primera y la segunda ejecución?**

   Es posible que cambie: los modelos generativos pueden producir formulaciones diferentes para la misma petición. También podrían responder casi igual; la comparación real depende de las dos salidas.



