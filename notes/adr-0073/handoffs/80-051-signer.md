# Traspaso al signer (PROVISIONAL): un sobre o una participación cerrados responden igual antes y después de la revocación

| | |
|---|---|
| **Origen** | TASK-051 (ADR-0074, aceptado 2026-09-29; §2.5 enmendado el mismo día a dos ramas) |
| **Medido en** | `f5sign-backend` rama `feat/envelope-answers-first` (worktree `f5sign-backend-answer-order`), 2026-09-29. Sin mergear en `develop`, sin desplegar. Aterriza **después** del paquete ADR-0073 |
| **Repos afectados** | signer (`f5sign-signer`). Integradores: las rutas máquina `/envelopes/{id}/recipients/{recipientId}/auth/otp/send`, `/auth` y `/signature` cambian igual (lo recoge el traspaso de integradores) |
| **Status** | **PROVISIONAL, accionable contra mocks.** El traspaso oficial irá en `f5sign-backend/docs/frontend-handoff/` |

## Qué cambió (commiteado, no planeado)

El código que recibe un destinatario ante un sobre cerrado o una participación cerrada ya **no depende de si la
revocación de su sesión (que va por el relay) ha llegado o no**. Antes el mismo acto recibía un código antes de la
revocación y otro después.

**Ningún código nuevo en el catálogo.** Cambia qué código responde cada ruta:

| Ruta | Situación | Antes | Ahora |
|---|---|---|---|
| `POST /api/v1/signing/commit`, `POST /api/v1/signing/decline` | sobre cerrado, sesión ya revocada | 409 `SESSION_CLOSED` | 409 `ENVELOPE_NO_LONGER_LIVE` (igual que antes de la revocación) |
| mismas | participación liberada con el sobre abierto, sesión ya revocada | 409 `SESSION_CLOSED` | 409 `LEG_CLOSED` (igual que antes de la revocación) |
| mismas | sesión caducada por inactividad (`AWAITING_REAUTH`) sobre un sobre cerrado o una participación cerrada | 401 `AUTH_REAUTH_REQUIRED` | 409 `ENVELOPE_NO_LONGER_LIVE` / `LEG_CLOSED` |
| mismas | el plazo del paso ya pasó y el barrido aún no lo aplicó, **y ese plazo termina el sobre** | 409 `LEG_CLOSED` | 409 `ENVELOPE_NO_LONGER_LIVE` |
| mismas | ídem, y el sobre sigue sin este destinatario | 409 `LEG_CLOSED` | 409 `LEG_CLOSED` (sin cambio) |
| `POST /api/v1/signing/session/auth/otp/send`, `POST /api/v1/signing/session/auth` | sobre cerrado, sesión ya revocada | **401** `AUTH_NO_OPEN_CHALLENGE` | **409** `ENVELOPE_NO_LONGER_LIVE` |
| mismas | participación liberada con el sobre abierto, sesión viva | 409 `ENVELOPE_NO_LONGER_LIVE` (falso: el sobre seguía vivo) | 409 **`LEG_CLOSED`** (nuevo en estas rutas) |
| mismas | participación liberada con el sobre abierto, sesión ya revocada | **401** `AUTH_NO_OPEN_CHALLENGE` | **409** `LEG_CLOSED` |
| mismas | el destinatario ya firmó o ya rechazó | 401 `AUTH_NO_OPEN_CHALLENGE` | 401 `AUTH_NO_OPEN_CHALLENGE` (sin cambio) |
| commit y rechazo | un miembro informativo (`VIEWER`, `REVIEWER`, `EDITOR`) actúa pasado el plazo de su paso, antes del barrido | 409 `LEG_CLOSED` | 409 `COMMIT_NOT_OFFERED_TO_ROLE` (commit) / `DECLINE_NOT_OFFERED_TO_ROLE` (rechazo), igual que después del barrido |
| mismas | un miembro informativo actúa sobre un paso ya cerrado (por el barrido o porque el paso se completó), con el sobre abierto | 409 `STEP_NOT_ACTIVE` | 409 `COMMIT_NOT_OFFERED_TO_ROLE` / `DECLINE_NOT_OFFERED_TO_ROLE` |

- `SESSION_CLOSED` sigue en el catálogo pero queda **reducido**: solo significa "la sesión se cerró sin que el
  destinatario actuara, con el sobre y su participación todavía abiertos". Hoy ninguna ruta de producción lo produce.
  En `otp/send` y `auth` no se responde nunca (una sesión terminada es el 401 `AUTH_NO_OPEN_CHALLENGE`).
  `SESSION_ALREADY_COMPLETED`, `SESSION_ALREADY_DECLINED` y `SESSION_CLOSED` solo llegan a esas dos rutas si la
  sesión se cierra entre dos lecturas de la misma petición; significan lo mismo: parar.
- En `otp/send` y `auth`, ante `ENVELOPE_NO_LONGER_LIVE` o `LEG_CLOSED` no se envía código, no se cobra nada y no se
  gasta intento.
- **Decisión del mantenedor (2026-09-29): el rol de un miembro informativo responde antes que el paso y que el plazo.**
  Su participación no la libera el barrido, así que la respuesta es su rechazo de rol antes y después del barrido.
  Si el plazo vencido termina el sobre, sigue respondiendo antes el sobre (`ENVELOPE_NO_LONGER_LIVE`).
- **Textos publicados (actualizados):** el 401 de `otp/send` dice ya que una sesión terminada (firmada, rechazada o
  cerrada con el sobre y la participación abiertos) cae ahí también con `recover: true`, y que un sobre o una
  participación cerrados responden el 409. El 401 `AUTH_REAUTH_REQUIRED` del rechazo dice que un sobre o una
  participación cerrados responden antes el 409. `SESSION_CLOSED` en commit, commit delegado y rechazo lleva
  «no se produce hoy».

## Qué tiene que hacer el signer

1. En `otp/send` y en el envío de la respuesta de `auth`: tratar **409 `LEG_CLOSED`** como en el commit y el rechazo
   (tu participación ha terminado; no reintentar, no volver a pedir el código). Si hoy cae en la rama de código
   desconocido, el spec ya dice "parar", que es el sentido seguro, pero conviene la pantalla propia.
2. En esas dos rutas, un sobre o una participación cerrados ya **no** llegan como 401 `AUTH_NO_OPEN_CHALLENGE` después
   de la revocación: llegan como 409. Revisar que el 401 `AUTH_NO_OPEN_CHALLENGE` quede solo para "no hay nada que
   probar" (ya firmado, ya rechazado, o ninguna puerta abierta), y que nada dependa de recibir el 401 para mostrar
   "sobre cancelado".
3. Commit y rechazo: `SESSION_CLOSED` y `ENVELOPE_NO_LONGER_LIVE` ya se pintaban igual; no hace falta cambio. Si
   algún texto decía que `SESSION_CLOSED` era "tu participación fue liberada", ahora esa situación llega como
   `LEG_CLOSED`.
4. Una sesión inactiva sobre un sobre cerrado ya no pide reautenticarse (401 `AUTH_REAUTH_REQUIRED`): recibe el 409 del
   cierre. Comprobar que la pantalla de reautenticación no se dispara en ese caso.
5. Tests: los `it.each` de `otp/send` y `auth` ganan `LEG_CLOSED`; los casos que esperaban 401 tras una anulación pasan
   a 409 `ENVELOPE_NO_LONGER_LIVE`.
6. Commit y rechazo de un miembro informativo: `COMMIT_NOT_OFFERED_TO_ROLE` / `DECLINE_NOT_OFFERED_TO_ROLE` ya estaban
   mapeados; ahora llegan también donde antes llegaba `LEG_CLOSED` (plazo vencido sin barrer) o `STEP_NOT_ACTIVE` (paso
   ya cerrado). Si el signer ya oculta Firmar y Rechazar para esos roles, no hay cambio visible.

## Orden de despliegue

**Backend primero es seguro** para el signer: ningún código cambia a otro con remedio distinto (todos dicen "parar,
no se hizo nada, no reintentar"), y un `LEG_CLOSED` sin mapear en `otp/send`/`auth` cae en la rama de código
desconocido, que el spec manda tratar como "parar". El único movimiento de estado es 401 → 409 en `otp/send`/`auth`
para un sobre o participación cerrados; los dos estados dicen que ahí ya no se puede hacer nada. ⚠ Verificar en el
signer que un 409 en esas dos rutas no se trate como error inesperado (Sentry) antes de desplegar el backend; si lo
hace, desplegar juntos.
