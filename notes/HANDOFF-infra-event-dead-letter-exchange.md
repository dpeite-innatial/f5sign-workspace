# HANDOFF → `f5sign-infra` — dead-letter exchange para las colas de eventos

**Estado:** **implementado en `f5sign-infra` el 2026-08-18** (working tree, sin commitear al escribir esto) y
**aplicado al broker de dev**, verificado de punta a punta. Repo que ejecuta: **`f5sign-infra`**.
⚑ **La sección "La trampa" de abajo quedó falsificada al implementarlo** y está corregida in situ: el fallo
no es ruidoso como decía, es callado. Si solo vas a leer un párrafo de este documento, que sea ese.
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

## ⚠ La trampa: los argumentos de una cola son inmutables, y **nadie te lo dice**

⛔ **CORRECCIÓN, medida al implementarlo el 2026-08-18 contra RabbitMQ 4.0.** Este documento decía que
volver a declarar una cola existente con argumentos distintos *"falla con `PRECONDITION_FAILED`"*. **No
falla.** `rabbitmqctl import_definitions` se queda con los argumentos **viejos**, no emite warning y
reporta éxito, con el log del broker limpio (`Importing concurrently 15 queues...`, cero errores). Medido:
tras el import, el exchange nuevo y la cola nueva **sí** se habían creado, y el `x-dead-letter-exchange` de
las cuatro colas de eventos **no había entrado**.

*(`PRECONDITION_FAILED` es lo que devuelve un `queue.declare` de un cliente AMQP. El importador de
definiciones es otro camino y no se comporta igual — de ahí el error de este documento.)*

**Esto cambia la naturaleza del riesgo, no solo un detalle.** La premisa entera de arriba es que infra va
primero para no cambiar un fallo escandaloso por uno callado. Pero el propio despliegue de infra falla
callado: `make reload-rabbitmq` sale **en verde** con el desvío sin poner. Quien revise el PR de backend y
compruebe que "infra está desplegado" mirando el import, está mirando un verde que no significa nada.

Por eso el cambio implementado **no se queda en el fichero**:
- `make rabbit-check-dlx` afirma que las cuatro colas llevan el argumento y se pone rojo si no
  (`docker/scripts/check-event-dlx.sh`).
- `make reload-rabbitmq` lo ejecuta **después** de importar y falla si no está — así "desplegado" es
  comprobable en vez de declarativo.
- `make rabbit-recreate-event-queues` hace el borrado+recreado, con `--if-empty --if-unused` por defecto
  para que el broker impida perder mensajes, y `FORCE=1` como decisión explícita.

Sigue siendo cierto lo esencial: **hay que borrar y recrear las cuatro colas de eventos** para que el
argumento entre.

- **Hoy es gratis**: en dev es un reset de volumen.
- **El día que haya un entorno de vida larga es una operación de verdad**, y hay que drenar antes:
  `make worker-down` → profundidad 0 (`make worker-status`) → recrear → `make worker-up`.
- **Drenar es seguro** porque el log es la fuente de verdad, no la cola.
- Si algún día recrear resulta inaceptable, la salida es la *policy*, que sí se aplica sobre colas vivas.
  Está registrado como escotilla en TASK-026 §6.3; cambiar a ella no es un rediseño.

## Cómo se verifica

> **Resultado al implementarlo (2026-08-18), sobre el stack de dev.** Publicado en `f5sign.events` con
> `App.Session.Event.DlxSmoke` y rechazado sin requeue: aterriza en `queue.events.dead-letter` con
> `x-death: queue=queue.session.events, reason=rejected` — o sea, la procedencia que D4 daba por buena se
> conserva de verdad. **Control negativo**, que es lo que lo convierte en prueba: cola desechable *sin* el
> argumento, mismo rechazo, el mensaje **desaparece** y la cola de descartes no se mueve. El desvío es lo
> que lo captura, y no otra cosa.
>
> Coste real del recreado en dev: se descartaron **54** mensajes pendientes de `queue.session.events`
> (decisión explícita del usuario, `FORCE=1`); las otras tres estaban a 0.

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
