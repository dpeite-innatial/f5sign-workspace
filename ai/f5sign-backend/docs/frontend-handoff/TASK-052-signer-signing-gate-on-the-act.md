# Traspaso al frontal — la puerta de firma se contesta en el acto, y el rechazo también la pasa

| | |
|---|---|
| **Origen** | rama `fix/signing-gate-on-the-act` (desde `develop` `50a9e45e`), **sin mergear, sin desplegar** · commit: ver `git log fix/signing-gate-on-the-act` — el último que toca `src/` es el que manda · [ADR-0075](../adr/ADR-0075-the-signing-gate-is-answered-on-the-act.md) (`Accepted` el 2026-10-06) · [TASK-052](../tasks/TASK-052-the-signing-gate-is-answered-on-the-act.md) |
| **Fecha** | 2026-10-06 |
| **Repos afectados** | **signer** |
| **Naturaleza** | ⛔ **rompedor** detrás de una puerta de firma declarada: la ruta 5 deja de contestar la puerta de firma y el código viaja en el acto. Sin puerta de firma, nada cambia |
| **Acción requerida** | mandar el código como `code` en el commit y en el rechazo · pedir el código a la ruta 4 con `act` · dejar de llamar a la ruta 5 para la puerta de firma · abrir el modal del código también en el rechazo |
| **Despliegue** | ⛔ **en la misma ventana que el backend** (ADR-0075 §2.8): ninguno funciona con la versión anterior del otro detrás de una puerta de firma. La superficie sigue en `/v1` |
| **Desplegado** | not yet |
| **Status** | Pending |

## Lo que cambió en el contrato

- **`POST /api/v1/signing/commit` y `POST /api/v1/signing/decline` aceptan `code`** (string, opcional, como
  mucho 256). Si el destinatario tiene puerta de firma declarada, el código es obligatorio y se comprueba y
  se gasta **en esa misma petición**. Si no la tiene, `code` se ignora y no se registra nada.
- **La ruta 5 (`POST /api/v1/signing/session/auth`) contesta solo la puerta de acceso.** Si la puerta abierta
  es la de firma responde **409 `SIGNING_GATE_ANSWERED_ON_THE_ACT`** sin registrar nada. Si lo veis, el cliente
  está ejecutando el flujo antiguo. La respuesta 200 solo puede traer `gate_passed: ACCESS` y siempre trae el
  par de credenciales.
- **La ruta 4 (`POST /api/v1/signing/session/auth/otp/send`) acepta `act`**: `SIGN` (por defecto, si no lo
  mandáis) o `DECLINE`. Cada acto tiene su propio código: un código para firmar nunca vale para rechazar ni al
  revés; pedir el del otro acto **no** retira el abierto; el intervalo mínimo de 60 s y `resend: true` cuentan
  **por acto**. La respuesta 200 añade **`act`** (`SIGN`, `DECLINE`, o `null` en la puerta de acceso, donde el
  `act` que mandéis se ignora). ⚑ **La respuesta de la ruta 4 siempre trae `act`**: el campo
  está presente en toda 200, con `null` en la puerta de acceso; no lo tratéis como ausente.
- **El correo y el SMS del rechazo dicen *rechazar*** («Su código para rechazar es …»), no *firmar*.
- **La ruta 3 (`GET /api/v1/signing/session/auth`) no cambia**: sigue diciendo `gate: SIGNING` con su método;
  esa puerta se contesta en el acto.

### Respuestas del commit y del rechazo detrás de una puerta de firma

| Situación | Respuesta |
|---|---|
| Sin `code` | **401 `AUTH_CODE_REQUIRED`** (nuevo) — no se cobra |
| No hay código vivo **para este acto** (no se pidió, o ya se gastó; uno del otro acto no cuenta). ⚑ **Un código de rechazo adivinado, sin ningún código `DECLINE` vivo, contesta esto** | 401 `AUTH_NO_OPEN_CHALLENGE` — **no se cobra** |
| El código de este acto caducó | 401 `AUTH_CHALLENGE_EXPIRED` — no se cobra |
| Código incorrecto | 401 `AUTH_CODE_INCORRECT` — **se cobra el intento**; el código sigue vivo. No hay contador de intentos restantes |
| Bloqueo temporal | **429 `AUTH_COOLING_DOWN`** con `Retry-After` — igual que en la ruta 5, antes de leer el código; también es la respuesta al código incorrecto que lo arma |
| Bloqueo definitivo | **423 `AUTH_HARD_LOCKED`** — igual que en la ruta 5, antes de leer el código; solo lo levanta el remitente |
| El código vivo de este acto está ligado a otro conjunto de documentos | 409 `SIGNING_CHALLENGE_MISBOUND` — **no se cobra y no se gasta**; pedid uno nuevo con la ruta 4, **`act` del acto y `resend: true`** (con `resend: false` os devolvería el mismo) |
| Sin verificador (`ACCESS_CODE` sin código guardado) | 401 `AUTH_GATE_MISCONFIGURED` — el remitente tiene que reiniciar el código |

### El orden, que decide lo que cuesta cada rechazo (ADR-0075 §2.4)

1. **Lo propio del acto, antes del código.** Un reintento tras un commit con éxito contesta
   **`SESSION_ALREADY_COMPLETED`** (y tras un rechazo con éxito, **`SESSION_ALREADY_DECLINED`**) antes de leer el
   código, con el código ya gastado o sin código. Falta de consentimiento, o un rol que no puede rechazar
   (`DECLINE_NOT_OFFERED_TO_ROLE`), se dicen por su nombre y no cobran.
2. **El bloqueo** (429 / 423).
3. **El código.** Un código incorrecto da **401 `AUTH_CODE_INCORRECT` y se cobra aunque los campos también
   estén mal**: el código se comprueba antes que los valores.
4. **La admisión en el sobre.** Con el código **correcto** y valores inválidos: **422 `FIELD_VALUES_INVALID`**,
   **no se cobra nada y el código sigue vivo** — corregís el formulario y repetís con **el mismo código**.
   **503 `ENVELOPE_BUSY`**: no se gasta ni se cobra nada; reintentad con el mismo código. Lo mismo para los 409
   que nombra la admisión (`LEG_CLOSED`, `STEP_NOT_ACTIVE`, `ENVELOPE_NO_LONGER_LIVE`).

## Lo que el frontal tiene que hacer

1. **Commit.** El modal sobre `/sign` se queda donde está y **deja de llamar a la ruta 5**: pide el código a la
   ruta 4 con `act: SIGN` (o se apoya en el ya enviado) y el commit lleva `code`. Abrid el modal ante
   `AUTH_CODE_REQUIRED`, `AUTH_NO_OPEN_CHALLENGE` y `AUTH_CHALLENGE_EXPIRED`; `AUTH_CODE_INCORRECT` deja el modal
   abierto para reescribirlo.
2. **Rechazo.** El mismo modal en el rechazo, con `act: DECLINE`, **pedido cuando el destinatario confirma el
   rechazo, no al abrir el diálogo**. Guardad en memoria el motivo escrito mientras está el modal y mandad
   motivo y código juntos.
3. **Ruta 5 solo para la puerta de acceso.** `SIGNING_GATE_ANSWERED_ON_THE_ACT` desde ella significa que el
   cliente está ejecutando el flujo antiguo (por ejemplo, una pestaña abierta durante el despliegue): recargad.
4. **`ACCESS_CODE`**: no hay nada que enviar y la ruta 4 contesta `409 AUTH_METHOD_NOT_DELIVERED` como hoy. El
   modal pide el código que el firmante ya tiene y lo manda en el acto directamente, sin llamar a la ruta 4.
   Leed el método de la ruta 3.
5. **El bloqueo llega también al rechazo**: 429 con cuenta atrás, 423 sin reintento, como en la ruta 5.
6. **Cada acto tiene su código**: cambiar de idea (de firmar a rechazar) cuesta un mensaje nuevo para el otro
   acto y ninguna espera.
7. **Esto vale para todos los roles que pueden rechazar** — `SIGNER`, `APPROVER` y `CERTIFIED_DELIVERY` — si su
   puerta de firma está declarada.
