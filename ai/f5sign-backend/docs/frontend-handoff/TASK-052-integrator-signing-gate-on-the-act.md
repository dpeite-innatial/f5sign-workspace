# Traspaso al integrador — la puerta de firma se contesta en el acto, también en la ceremonia por máquina

| | |
|---|---|
| **Origen** | rama `fix/signing-gate-on-the-act` (desde `develop` `50a9e45e`), **sin mergear, sin desplegar** · commit: ver `git log fix/signing-gate-on-the-act` — el último que toca `src/` es el que manda · [ADR-0075](../adr/ADR-0075-the-signing-gate-is-answered-on-the-act.md) (`Accepted` el 2026-10-06) · [TASK-052](../tasks/TASK-052-the-signing-gate-is-answered-on-the-act.md) · [ADR-0055](../adr/ADR-0055-delegated-signature.md) §2.11 |
| **Fecha** | 2026-10-06 |
| **Repos afectados** | **integradores** que conducen la ceremonia por la superficie de máquina |
| **Naturaleza** | ⛔ **rompedor** detrás de una puerta de firma declarada. La firma **delegada** (`signs_via: MACHINE_KEY`) no cambia: no tiene puerta de firma |
| **Acción requerida** | pedir el código con `act` · retransmitirlo **en el acto** como `code` · dejar de mandar el código de firma al gemelo de la ruta 5 |
| **Despliegue** | en la misma ventana que el backend (ADR-0075 §2.8); la superficie sigue en `/v1` mientras ningún integrador conduzca esta ceremonia contra un despliegue vivo |
| **Desplegado** | not yet |
| **Status** | Pending |

## Lo que cambió en el contrato

- **Gemelo de la ruta 4 — `POST /api/v1/envelopes/{id}/recipients/{recipientId}/auth/otp/send`** acepta
  **`act`**: `SIGN` (por defecto) o `DECLINE`; la respuesta 200 lo devuelve como `act` (`null` en la puerta de
  acceso, donde se ignora). Un código por acto, intervalo mínimo y `resend` por acto.
- **Gemelo de la ruta 5 — `POST /api/v1/envelopes/{id}/recipients/{recipientId}/auth`** contesta **solo la
  puerta de acceso**. Con la puerta de firma abierta responde **409 `SIGNING_GATE_ANSWERED_ON_THE_ACT`** sin
  registrar nada. ⚑ **Ahora abre la sesión del destinatario si no existe** (tras las mismas comprobaciones que
  el gemelo de la ruta 4), así que un código de acceso `ACCESS_CODE` se retransmite directamente, sin llamar
  antes al gemelo de la ruta 4.
  La respuesta 200 solo puede traer **`gate_passed: ACCESS`**. Declara además **423 `AUTH_HARD_LOCKED`** y
  **429 `AUTH_COOLING_DOWN`** (con `Retry-After`), como la ruta 5: el bloqueo no es un 401, y el 401 nombra
  tres rechazos (`AUTH_CODE_INCORRECT`, `AUTH_NO_OPEN_CHALLENGE`, `AUTH_CHALLENGE_EXPIRED`).
- **Ruta de firma por máquina — `POST /api/v1/envelopes/{id}/recipients/{recipientId}/signature`**, para un
  acto **retransmitido** (destinatario `SIGNING_PLATFORM`): el cuerpo **no lleva aserción** y, si hay puerta de
  firma, lleva **`code`** (emitido con `act: SIGN`, o el `ACCESS_CODE` precompartido). ⚑ Los tres miembros de
  la aserción (`asserted_subject`, `asserted_consented_at`, `asserted_document_hashes`) **dejan de ser
  obligatorios en el esquema**: hasta ahora lo eran, y eso rechazaba con 422 cualquier acto retransmitido
  antes de llegar al caso de uso. Un destinatario delegado sigue necesitándolos: sin ellos, 409
  `ASSERTION_REQUIRED`. ⚑ **Un miembro suelto de la aserción se rechaza**: si mandáis cualquiera de los tres
  (por ejemplo solo `asserted_document_hashes`), la llamada pasa a ser una aserción y se juzga por la forma del
  destinatario: **409 `ASSERTION_REQUIRED`** si es delegado y falta alguno, **409 `ASSERTION_NOT_ACCEPTED`**
  para cualquier otro (aunque mandéis los tres). No se descarta en silencio ni se confirma el acto: o no mandáis
  ninguno (acto retransmitido) o mandáis los tres (delegado).
- **Rechazo — `POST /api/v1/signing/decline`** con la **credencial de sesión** que devolvió el gemelo de la
  ruta 5: `{ "reason": "…", "code": "…" }`, el código emitido con `act: DECLINE`.
- **Para `ACCESS_CODE` no hay nada que enviar**: el código se retransmite en el acto (firma o rechazo) sin
  llamar al gemelo de la ruta 4, y el acto abre, verifica y gasta su propio reto.

### Respuestas en el acto (firma por máquina y rechazo)

Las mismas que en la superficie del destinatario: **401** `AUTH_CODE_REQUIRED` (sin código),
`AUTH_NO_OPEN_CHALLENGE` (sin código vivo para este acto), `AUTH_CHALLENGE_EXPIRED`, `AUTH_CODE_INCORRECT`
(**se cobra**, sin contador de intentos restantes), `AUTH_GATE_MISCONFIGURED`; **429** `AUTH_COOLING_DOWN` con
`Retry-After` y **423** `AUTH_HARD_LOCKED`, antes de leer el código; **409** `SIGNING_CHALLENGE_MISBOUND` (no se
cobra ni se gasta; pedid otro con `act` y `resend: true`). Un rechazo de la admisión (422 `FIELD_VALUES_INVALID`,
503 `ENVELOPE_BUSY`, los 409 del sobre) **no cobra ni gasta**: reintentad con el mismo código. Un reintento tras
un acto con éxito contesta `SESSION_ALREADY_COMPLETED` / `SESSION_ALREADY_DECLINED` antes de leer el código.

## Secuencias

**Firma retransmitida** (puerta de acceso y de firma por código): gemelo ruta 4 → código de acceso → gemelo
ruta 5 (`{code}`) → credencial; gemelo ruta 4 con `{"act":"SIGN"}` → código de firma → ruta de firma con
`{"code": "…"}` → 204.

**Rechazo retransmitido**: igual hasta la credencial; gemelo ruta 4 con `{"act":"DECLINE"}` → código de
rechazo → `POST /signing/decline` con la credencial y `{"reason": "…", "code": "…"}` → 200.

**`ACCESS_CODE` en las dos puertas**: gemelo ruta 5 con el código precompartido (abre la sesión) → credencial;
ruta de firma (o rechazo) con ese mismo código como `code`.
