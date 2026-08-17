# HANDOFF → `f5sign-infra` — dead-letter exchange para las colas de eventos

**Estado:** decidido, sin implementar. Repo que ejecuta: **`f5sign-infra`**.
**Contraparte en backend:** `f5sign-backend/docs/tasks/TASK-026-event-path-silent-drops.md` §3.3 y §4 D4–D6.
**Fecha:** 2026-08-17. Todas las medidas de abajo son contra el árbol de esa fecha; re-comprueba antes de tocar.

---

## Por qué existe esto

Hoy, un mensaje que el worker **no puede descifrar** entra en un bucle infinito y va tumbando workers.
Verificado contra el vendor instalado, no deducido:

- `Symfony\Component\Messenger\Bridge\Amqp\Transport\AmqpReceiver::get()` descifra dentro de un `try` que
  captura **exactamente un tipo**: `MessageDecodingFailedException`. Solo con ese rechaza el mensaje.
- Nuestro códec (`SelfSerializingMessageSerializer::decode()`) lanza `RuntimeException`, `JsonException` o
  lo que lance el `fromPayload()` del evento. **Ninguna es ese tipo**, y `MessageDecodingFailedException`
  aparece **cero veces** en `src/` y `tests/` del backend.
- `Symfony\Component\Messenger\Worker::run()` itera el receiver **fuera de todo `try`**. Su único
  `try/catch` está en `handleMessage()`, que solo se alcanza con un `Envelope` ya descifrado.

Resultado: la excepción mata el proceso con el mensaje **ni confirmado ni rechazado**, el broker lo
reentrega al siguiente worker, y así indefinidamente. No llega a `retry_strategy` ni a
`failure_transport`, porque ambos operan sobre un `Envelope` que nunca llega a existir.

## Por qué infra va PRIMERO, y no es un detalle de estilo

El arreglo de backend es envolver esos lanzamientos en `MessageDecodingFailedException` para que
`AmqpReceiver` **rechace**. Pero en AMQP *rechazar sin desvío configurado es tirar a la basura*.

Medido el 2026-08-17 sobre `docker/rabbitmq/definitions.json`: **ninguna de las 14 colas declaradas lleva
`x-dead-letter-exchange`**, y `policies` está vacío. El `alternate-exchange` de `f5sign.events` es otra
cosa — captura lo **no enrutable**, no lo rechazado por un consumidor.

⛔ **Si el PR de backend se mergea antes de que esto esté desplegado, es una regresión, no una mejora
parcial:** se cambia un fallo escandaloso (bucle, worker caído, mensaje aún en el broker) por uno callado
(mensaje descartado en silencio). Quien revise el PR de backend debe comprobar que esto está **desplegado**,
no meramente abierto.

*Consuelo, y es real:* `platform.event_log` sigue siendo la fuente de verdad, así que un hecho perdido en el
broker se puede volver a publicar. Esa es la otra mitad de TASK-026 (§3.1, comando de replay).

## Qué hay que hacer

1. **Un exchange de descartes** y **una sola cola de descartes compartida** para las cuatro colas de eventos
   (decisión D4 de TASK-026: el lector es un humano durante un incidente, cuatro sitios donde mirar no
   compran nada, y RabbitMQ estampa la cola de origen en la cabecera `x-death`).
2. **`x-dead-letter-exchange` como argumento en cada una de las cuatro colas de eventos**:
   `queue.envelope.events`, `queue.session.events`, `queue.signatureexecution.events`,
   `queue.notification.events`.

**Argumentos por cola, no una *policy*** (decisión D6). Razón: en `definitions.json` todo lo demás se declara
explícitamente por objeto, y el fichero es JSON puro sin comentarios, así que el efecto de una policy sería
invisible para quien lea la lista de colas.

## ⚠ La trampa: los argumentos de una cola son inmutables

Volver a declarar una cola existente con argumentos distintos falla con `PRECONDITION_FAILED`. Es decir:
**hay que borrar y recrear las cuatro colas de eventos** para que el argumento entre.

- **Hoy es gratis**: en dev es un reset de volumen.
- **El día que haya un entorno de vida larga es una operación de verdad**, y hay que drenar antes:
  `make worker-down` → profundidad 0 (`make worker-status`) → recrear → `make worker-up`.
- **Drenar es seguro** porque el log es la fuente de verdad, no la cola.
- Si algún día recrear resulta inaceptable, la salida es la *policy*, que sí se aplica sobre colas vivas.
  Está registrado como escotilla en TASK-026 §6.3; cambiar a ella no es un rediseño.

## Cómo se verifica

- `make worker-status` corre `rabbitmqctl list_queues name messages consumers`, que lista **todas** las
  colas con su profundidad — así que la cola de descartes nueva se reporta sola, sin comando nuevo. Por eso
  TASK-026 §4 D7 decide **no** construir un lector: es superficie de diagnóstico, no de recuperación.
- La prueba de verdad es cruzada y vive en el backend (TASK-026 §5): con esto desplegado y el wrap de
  backend puesto, un mensaje indescifrable debe **aparecer en la cola de descartes** en vez de desaparecer;
  y con el wrap puesto pero este cambio revertido, debe **descartarse** — que es la comprobación que hace
  observable el orden de arriba, y la aserción más importante de toda la tarea.

## Qué NO entra

- Clasificar fallos de *handler* permanentes vs transitorios — ADR-0015 lo tiene fichado aparte como
  *"refinement, queued"*.
- Tocar el transport `failed` ni `queue.failed`. ⚠ Y **no reutilices `queue.failed` como cola de descartes**:
  lleva `Envelope`s serializados en PHP con metadatos del framework, mientras que un mensaje desviado por el
  broker llega en crudo (cuerpo JSON + cabeceras). Mezclarlos rompe `messenger:failed:retry`.
- Un comando lector para la cola nueva (arriba, D7).
