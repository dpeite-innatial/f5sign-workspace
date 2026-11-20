# Traspaso al dashboard y al integrador — el reenvío de un destinatario por SMS tiene tope

| | |
|---|---|
| **Origen** | rama `feat/sms-spend-guards`, **sin mergear** · [TASK-057](../tasks/TASK-057-sms-spend-guards.md) |
| **Fecha** | 2026-10-15 |
| **Repos afectados** | **dashboard** del remitente (botón de reenviar) e **integradores** que reenvían por la API (`factor5-dashboard`) |
| **Naturaleza** | aditivo: un `code` nuevo en el 409 de `POST /api/v1/envelopes/{id}/recipients/{recipientId}/resends`. Ninguna ruta nueva, ninguna clave nueva en ninguna lectura |
| **Acción requerida** | mostrar el motivo en el botón de reenviar y deshabilitarlo para ese destinatario · tolerar valores de `code` desconocidos en esta ruta |
| **Desplegado** | not yet |
| **Status** | Pending |

> **Actualización 2026-10-19 (TASK-060, ADR-0080, aceptado).** El tope ya no se aplica a todo destinatario cuyos canales incluyen `SMS`: cuenta los reenvíos que pueden salir por SMS. Un reenvío que nombra `"channel": "SMS"`, o que no nombra canal para un destinatario que declaró `SMS`, cuenta; uno que nombra `"channel": "EMAIL"` no cuenta ni se rechaza por el tope. El resto de este traspaso sigue vigente.

## Lo que cambió en el contrato

### Escritura: `POST /api/v1/envelopes/{id}/recipients/{recipientId}/resends`

El 409 de esta ruta gana un `code`:

| `code` | Cuándo | ¿Reintentar sirve? |
|---|---|---|
| `RECIPIENT_RESEND_CAP_REACHED` | Los `notification_channels` del destinatario incluyen `SMS` y ya se le ha reenviado **5 veces** (más las que haya concedido un operador) | **No, nunca**. Hace falta que un operador lo desbloquee |
| `RECIPIENT_RESENT_TOO_RECENTLY` | Ya salió un reenvío hace menos de un minuto | Sí, esperando |

El cuerpo del 409 de `RECIPIENT_RESEND_CAP_REACHED` **no lleva `next_resend_at`**, a diferencia del de
`RECIPIENT_RESENT_TOO_RECENTLY`: esperar no lo cura, así que no hay instante que dar. Quien vea un 409 sin
`next_resend_at` no debe programar un reintento.

Se aplica por destinatario y solo cuando sus canales incluyen `SMS` (aunque también tenga `EMAIL`). Un destinatario
cuyos canales son solo `EMAIL`, o ninguno, **no tiene tope**: sigue acotado únicamente por el minuto entre reenvíos.

Si la participación del destinatario ya está cerrada, la respuesta sigue siendo `RECIPIENT_LEG_CLOSED`, aunque el
tope se hubiera alcanzado: esa comprobación va primero.

## Qué tiene que hacer el dashboard

- Ante `RECIPIENT_RESEND_CAP_REACHED`, mostrar algo como «Se ha alcanzado el máximo de reenvíos para este
  destinatario; contacta con soporte» (o la redacción propia del dashboard) y **deshabilitar el botón de reenviar
  para ese destinatario**, en lugar de dejar que el usuario reintente.
- Distinguirlo de `RECIPIENT_RESENT_TOO_RECENTLY` («espera un minuto»): son dos mensajes distintos, y solo el
  segundo se resuelve esperando.
- Solo desbloquea un operador del servidor, con `app:envelope:unblock-resends`. **No hay API para ello** y la
  lectura del sobre **no expone** ni el número de reenvíos ni cuántos se han concedido de más. Tras un desbloqueo, el
  mismo botón vuelve a funcionar sin cambiar nada en el cliente.
- Como la lectura no publica el recuento, el dashboard **no puede anticiparse** a la negativa: tiene que tratar el
  409.
- `code` es un conjunto abierto en esta ruta: tolerar uno desconocido (mostrar el mensaje genérico del 409), no
  romper.

## Para la app del firmante y el integrador: el 429 del código puede durar hasta una hora

El envío de un código de un solo uso (`POST /api/v1/signing/session/auth/otp/send` en la app del firmante, y la ruta
de máquina del integrador) gasta ahora **cuatro contadores** en vez de tres: la sesión, el destino **en este sobre**,
el destino **en todos los sobres** (nuevo, 30 por hora) y el origen (la dirección o, en la ruta de máquina, el cliente
de API). El contrato en el cable **no cambia**: el mismo 429, el mismo `code` `OTP_SEND_COOLING_DOWN`, el mismo
cuerpo, `Retry-After` y `retry_at`, sea cual sea el contador que se negó.

Lo que sí cambia es la espera: el contador nuevo es por hora, así que `Retry-After` / `retry_at` puede llegar a cerca
de una hora. **No supongas 60 segundos**: pinta la cuenta atrás desde `retry_at`, como ya hace la app del firmante
desde TASK-022. Si un operador restablece los contadores de un destinatario atascado, el siguiente envío pasa sin
cambiar nada en el cliente.
