# Traspaso al integrador y al dashboard — un reenvío puede nombrar uno de los canales que el destinatario declaró

| | |
|---|---|
| **Origen** | rama `feat/resend-channel` · commit `ffcd0b94` · [TASK-060](../tasks/TASK-060-a-resend-may-name-one-declared-channel.md) · [ADR-0080](../adr/ADR-0080-a-resend-may-name-one-declared-channel.md) (**Aceptado** por el propietario el 2026-10-19) |
| **Fecha** | 2026-10-19 |
| **Repos afectados** | **integradores** que reenvían por la API y **dashboard** del remitente (`factor5-dashboard`) |
| **Naturaleza** | aditivo: un cuerpo opcional en `POST /api/v1/envelopes/{id}/recipients/{recipientId}/resends` y dos `code` nuevos en su 409. Ninguna ruta nueva, ninguna clave nueva en ninguna lectura |
| **Acción requerida** | ninguna para quien no nombra canal · para ofrecer «reenviar por X»: enviar `channel` y tratar los dos 409 nuevos · tolerar valores de `code` desconocidos en esta ruta |
| **Desplegado** | not yet |
| **Status** | Pending |

## Lo que cambió en el contrato

### Escritura: `POST /api/v1/envelopes/{id}/recipients/{recipientId}/resends`

1. **Cuerpo opcional** `{"channel": "EMAIL" | "SMS"}`. Sin cuerpo, `{}` o `null` se comporta exactamente como hasta ahora: el reenvío va por los canales declarados.
2. **El canal nombrado debe ser uno de los que el destinatario declaró y que lo alcanzan ahora.** Sale **una sola entrega** por ese canal, **sin caer al otro**. `notification_channels` y `notification_mode` del destinatario **no cambian**; los avisos posteriores siguen la declaración.
3. Dos `code` nuevos en el 409:

   | `code` | Cuándo | ¿Reintentar sirve? |
   |---|---|---|
   | `RESEND_CHANNEL_NOT_DECLARED` | El canal nombrado no está en los `notification_channels` del destinatario | No: nombrar un canal declarado, o cambiar los canales con `PUT` |
   | `RESEND_CHANNEL_UNREACHABLE` | Está declarado pero hoy no alcanza: falta el contacto o está rechazado, el teléfono no es móvil o su país no está soportado, el SMS no está conectado o el interruptor del tenant está apagado | **No**: reintentar igual no ayuda |

4. **422 `VALIDATION_ERROR`** si `channel` no es una cadena o no es un valor conocido.
5. Un destinatario con `notification_channels: []` sigue recibiendo `RECIPIENT_NOTIFIED_BY_INTEGRATOR`, **aunque se nombre un canal**.
6. `RECIPIENT_HAS_NO_REACHABLE_CHANNEL` **no se responde nunca cuando se nombra un canal**: ese caso es `RESEND_CHANNEL_UNREACHABLE`.
7. **El tope cuenta los reenvíos que pueden salir por SMS** (supersede la condición de [TASK-057](TASK-057-dashboard-resend-cap.md)): un reenvío que nombra `SMS` cuenta; uno que no nombra canal cuenta si el destinatario declaró `SMS`; uno que nombra `EMAIL` **ni cuenta ni se rechaza por el tope**. La concesión de un operador sube el mismo techo. El código y el cuerpo del 409 `RECIPIENT_RESEND_CAP_REACHED` no cambian.
8. El historial de notificaciones (`GET …/recipients/{recipientId}/notifications`, [TASK-058](TASK-058-dashboard-integrator-notification-history.md)) muestra la **única** entrega, en el canal nombrado.

## Qué tiene que hacer el cliente

1. Si se quiere ofrecer «reenviar por correo» / «reenviar por SMS», enviar `channel` y tratar `RESEND_CHANNEL_NOT_DECLARED` y `RESEND_CHANNEL_UNREACHABLE` con mensajes distintos: el primero se cura nombrando otro canal o cambiando la declaración; el segundo, arreglando el contacto o la configuración, no reintentando.
2. Si no se quiere, no hacer nada: el cuerpo vacío sigue valiendo.
3. Seguir tratando `code` como conjunto abierto en esta ruta.

## Lo que NO está listo

- La lectura del sobre **no publica** qué canales alcanzan hoy a un destinatario ni el recuento del tope: el cliente no puede anticipar los dos 409; tiene que tratarlos.
- **Aviso**: cambiar los canales con `PUT` de forma que **no** vuelva a invitar **no cancela** un reenvío con canal nombrado ya creado (solo lo paran las cancelaciones existentes).
- ADR-0080 está **Aceptado** (2026-10-19): el propietario ya lo aceptó.

## Cómo verificarlo desde el cliente

- Regenerar el OpenAPI y comparar: la ruta de reenvíos gana el `requestBody` opcional con `channel` y los dos `code` en el 409.
- `POST …/resends` con `{"channel":"EMAIL"}` sobre un destinatario que declaró solo `SMS` debe dar 409 `RESEND_CHANNEL_NOT_DECLARED`; con `{"channel":1}`, 422.
