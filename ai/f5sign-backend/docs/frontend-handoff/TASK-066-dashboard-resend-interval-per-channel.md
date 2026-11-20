# Traspaso al dashboard — el intervalo entre reenvíos cuenta por canal

| | |
|---|---|
| **Origen** | rama `feat/resend-interval-per-channel` · commit `50cb6435` · [TASK-066](../tasks/TASK-066-the-resend-interval-counts-per-channel.md) |
| **Fecha** | 2026-10-21 |
| **Repos afectados** | **dashboard** del remitente (`factor5-dashboard`) e **integradores** que reenvían por la API |
| **Naturaleza** | **sin cambio de contrato**: misma ruta, mismo cuerpo, mismos `code`. Cambia cuándo se responde `RECIPIENT_RESENT_TOO_RECENTLY` |
| **Acción requerida** | ninguna para seguir funcionando · las dos llamadas que el dashboard ya hace (`EMAIL` y luego `SMS`) pasan a salir las dos |
| **Desplegado** | not yet |
| **Status** | Pending |

## Lo que cambió

`POST /api/v1/envelopes/{id}/recipients/{recipientId}/resends`

1. **El intervalo mínimo (60 s) se cuenta por canal**, no por destinatario. `{"channel":"EMAIL"}` y, acto seguido, `{"channel":"SMS"}` responden **204 y 204**, y salen un correo y un SMS. Antes, la segunda daba 409 `RECIPIENT_RESENT_TOO_RECENTLY`.
2. El mismo canal dos veces dentro de 60 s sigue dando 409 `RECIPIENT_RESENT_TOO_RECENTLY` con `next_resend_at`.
3. **Un reenvío sin canal** cuenta para **todos** los canales declarados que hoy alcanzan al destinatario (con `IN_ORDER`, el siguiente es el de respaldo). Por eso:
   - sin canal y, acto seguido, `{"channel":"SMS"}` → **409**, aunque solo saliera el correo;
   - `{"channel":"EMAIL"}` (o `SMS`) y, acto seguido, sin canal → **409**.
4. `next_resend_at` es el instante en que **ese mismo reenvío** se admitirá: el de su canal si lo nombra; si no nombra ninguno, el más tardío de los canales por los que saldría.
5. No cambian el tope de SMS (`RECIPIENT_RESEND_CAP_REACHED`), el resto de `code`, ni el historial de notificaciones.

## Qué tiene que hacer el cliente

1. Para «reenviar por correo y por SMS», nombrar `EMAIL` y luego `SMS` (o al revés). No mezclar un reenvío sin canal con uno con canal en el mismo minuto.
2. Seguir mostrando `next_resend_at` tal cual; no calcular la espera a partir de otra llamada.

## Cómo verificarlo desde el cliente

- Destinatario `["EMAIL","SMS"]` `IN_ORDER`: `POST …/resends` con `{"channel":"EMAIL"}` → 204; inmediatamente `{"channel":"SMS"}` → 204; el historial (`GET …/recipients/{recipientId}/notifications`) muestra dos reenvíos, uno por correo y uno por SMS.
- Repetir `{"channel":"SMS"}` dentro del minuto → 409 `RECIPIENT_RESENT_TOO_RECENTLY` con `next_resend_at`.
