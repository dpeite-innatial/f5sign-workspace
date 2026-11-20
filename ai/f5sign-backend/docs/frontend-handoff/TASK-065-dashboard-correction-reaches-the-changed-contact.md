# Traspaso al dashboard — una corrección solo alcanza al contacto que cambió

| | |
|---|---|
| **Origen** | rama `feat/correction-reaches-the-changed-contact` · commit `cf6dff0a` · [TASK-065](../tasks/TASK-065-a-correction-reaches-only-the-contact-it-changed.md) · [ADR-0084](../adr/ADR-0084-a-correction-reaches-only-the-contact-it-changed.md) |
| **Fecha** | 2026-10-21 |
| **Repos afectados** | **dashboard** |
| **Naturaleza** | comportamiento: misma ruta, mismos códigos |
| **Acción requerida** | dashboard: sí, el flujo de añadir un contacto |
| **Desplegado** | not yet |
| **Status** | Pending |

La forma exacta de la petición y de las respuestas está en el `doc.json` de la ruta y **no cambia**: ni cuerpo, ni
códigos, ni claves nuevas. Cambia lo que el servidor hace con el cuerpo.

## Lo que cambió

`POST /api/v1/envelopes/{id}/recipients/{recipientId}/corrections` compara ahora cada campo enviado con lo guardado
(el email sin distinguir mayúsculas; el teléfono por su forma E.164) y decide el resultado él mismo:

- **Un contacto que cambia es una corrección.** Gasta una de las 3 correcciones del destinatario y lo reinvita **solo
  por el canal declarado de cada contacto que cambió** (`email` → `EMAIL`, `phone` → `SMS`), y por ningún otro. Si el
  contacto cambiado es el destino de un canal declarado, los enlaces enviados antes dejan de valer y se cancela
  cualquier invitación aún no entregada.
- **Un contacto que el destinatario no tenía es una adición.** No gasta correcciones, no cierra ningún enlace y solo
  reinvita si el canal de ese contacto está declarado. Se sigue aceptando con las 3 correcciones gastadas.
- Una llamada que cambia un contacto y añade el otro es **una** corrección, y reinvita por los canales declarados de los dos.
- **Un cuerpo igual a lo guardado responde 200 y no hace nada**: no gasta, no envía, no registra. Para reenviar sobre un
  contacto que está bien existe `POST …/resends`.

La respuesta es siempre `200 {warnings}`, igual que antes.

## Qué hacer: añadir un contacto a un firmante

El flujo del dashboard para «añadir un contacto» (por ejemplo, el email de quien se dio de alta solo con teléfono) es:

1. `POST …/corrections` con el contacto que falta (es una adición: no gasta ni envía por canales no declarados).
2. `PUT …/notification-channels` para declarar el canal del contacto nuevo, para que los avisos lleguen también por él.
   Si el destinatario ya recibió su invitación, declarar el canal no la reenvía: añadir el paso `POST …/resends` con
   ese canal.
3. `PUT …/auth` si el destinatario **aún no ha abierto su enlace** (ADR-0083) y se quiere una puerta que use ese
   contacto.

No hay una ruta aparte para añadir, ni se puede vaciar un contacto. Este flujo solo **añade** canales, así que no
cambia con lo de la sección siguiente.

## Quitar un canal declarado cuando el enlace ya pudo enviarse

`PUT …/notification-channels` no cambia de ruta, de cuerpo ni de códigos, pero ahora distingue (ADR-0084 §2.11):

- **Quitar un canal** que el destinatario tenía declarado, en un sobre enviado y con su participación abierta, **en cuanto
  se le haya podido enviar el enlace** (su paso está activo y no está delegado ni es un slot sin reclamar), aunque la
  invitación aún no haya llegado: los enlaces enviados antes **dejan de abrir** y se envía una invitación nueva por los
  canales que quedan. Con `[]` no se envía nada y la invitación queda a cargo de quien integra.
- **Cualquier otro cambio** (solo añadir canales, cambiar antes del envío, con el paso aún sin activar, o sobre un
  destinatario delegado o un slot sin reclamar): no anula nada y solo cambian los avisos siguientes; reinvita únicamente
  a quien nunca fue invitado con éxito, como antes.

Si el dashboard permite quitar un canal, conviene avisar de que el enlace anterior dejará de funcionar.

## Antes y después, caso por caso

| Caso | Antes | Ahora |
|---|---|---|
| Incidente: destinatario con solo `SMS` declarado y teléfono; se envía su email | gasta 1 corrección, reenvía el SMS sin que el teléfono cambie, retira el enlace vivo y el email no recibe nada | adición: no gasta, no reenvía, no retira el enlace; declarar `EMAIL` hace que los avisos siguientes vayan también al email, y para mandarle ya la invitación allí, `POST …/resends` nombrando `EMAIL` (ADR-0080) |
| Cambia el email con `[EMAIL, SMS]` declarados | gasta 1, reinvita por `EMAIL` y por `SMS` | gasta 1, reinvita **solo por `EMAIL`**; el enlace que llevó el `SMS` también deja de valer (la retirada es por destinatario), y no se reenvía por `SMS` |
| Cambia el teléfono | gasta 1, reinvita por todos los canales declarados | gasta 1, reinvita **solo por `SMS`** (si está declarado) |
| Cuerpo igual a lo guardado (mismo email aunque cambie la capitalización, mismo teléfono en otra grafía) | gasta 1 y reinvita | 200, no gasta, no envía, no registra |
| Se quita un canal declarado (p. ej. `["SMS"]` → `["EMAIL"]`) en cuanto se le ha podido enviar el enlace (paso activo) | los enlaces enviados seguían abriendo y no se reenviaba nada | los enlaces anteriores dejan de abrir y se invita por `EMAIL`; así una corrección posterior del teléfono ya no deja un enlace vivo en el número equivocado |
| Se añade un canal (p. ej. `["SMS"]` → `["SMS","EMAIL"]`) | solo cambian los avisos siguientes | igual: no anula nada |
| Correcciones agotadas (3 gastadas) y se añade un contacto que faltaba | 409 `RECIPIENT_CORRECTION_BUDGET_EXHAUSTED` | 200, es una adición; solo una corrección sigue recibiendo este 409 |

Los 409 y 422 existentes se mantienen, en el mismo orden y con los mismos `code`; un cuerpo igual a lo guardado sobre
una participación cerrada, un slot sin reclamar o un sobre sin enviar sigue recibiendo la negativa de siempre.

## Lo que NO existirá

- Una ruta distinta para añadir un contacto, o vaciar un contacto.
- Reenviar desde esta ruta sobre un contacto sin cambios: eso es `POST …/resends`.

## Cómo verificarlo desde el frontal

El contador de correcciones no se publica en el sobre; se verifica por lo observable. Destinatario con
`notification_channels: ["SMS"]` y sin email, ya invitado: `POST …/corrections` con `{"email": "a@x.com"}` → 200, el
enlace anterior por SMS sigue abriendo y no sale ningún SMS. Repetir con el mismo cuerpo → 200 sin efecto. Tras tres
correcciones reales (cambios de contacto), una cuarta responde 409 `RECIPIENT_CORRECTION_BUDGET_EXHAUSTED`, mientras
que una adición sigue respondiendo 200.
