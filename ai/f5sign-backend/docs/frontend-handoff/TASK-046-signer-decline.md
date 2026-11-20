# Traspaso al frontal — un destinatario puede rechazar, y el rechazo tiene su ruta

| | |
|---|---|
| **Origen** | rama `feat/recipient-decline` (desde `develop` `6d081d1`), **mergeada en `develop` en `26ed0d7`, sin desplegar** · commit: ver `git log feat/recipient-decline` — el último que toca `src/` es el que manda · [ADR-0070](../adr/ADR-0070-an-envelope-ends-in-agreement-or-is-voided-and-sealed.md) (`Proposed`, texto aprobado por el mantenedor el 2026-09-23) · [TASK-046](../tasks/TASK-046-a-recipient-may-decline.md) |
| **Fecha** | 2026-09-23 |
| **Repos afectados** | **signer** |
| **Naturaleza** | **aditivo**: una ruta nueva, un estado de sesión nuevo (que ya publicábamos como literal), cuatro códigos nuevos. ⚠ **Y un cambio de comportamiento en lectura**: un sobre `VOIDED` vuelve a servir su documento **sellado** a quien firmó o rechazó |
| **Acción requerida** | volver a mostrar el botón *Rechazar* contra el backend real, con confirmación explícita · enviar `{ "reason": string }` y nada más · ramificar los `code` nuevos · tratar `DECLINED` como estado terminal propio |
| **Desplegado** | not yet |
| **Status** | Pending |

## Lo que cambió en el contrato

- **`POST /api/v1/signing/decline`**, con la **credencial de sesión** (la misma que el commit). Cuerpo:
  `{ "reason": "<texto>" }` — obligatorio, no vacío, **como mucho 500 caracteres**, sin caracteres de
  control salvo tabulador y saltos de línea. ⛔ **Sin `session_id`**: vuestro borrador de `DeclineRequest` lo
  llevaba, pero la credencial ya nombra la sesión; si lo mandáis se ignora. 200 →
  `{ "session_id": "…", "status": "DECLINED" }`.
- **Es irreversible.** Si el destinatario es bloqueante (`SIGNER`, `APPROVER`), su rechazo **anula el sobre
  para todos** (`VOIDED`, `void_cause: RECIPIENT_DECLINED`) cuando el backend lo registra; las demás
  sesiones vivas se cierran. Si no es bloqueante (`CERTIFIED_DELIVERY`), solo cierra su tramo.
- **Pide el acceso superado, no el código de firma.** Un rechazo exige haber pasado la puerta de acceso (como
  cualquier acto), pero **no** consume un reto de la puerta de firma ni pide consentimiento: no firma nada.
- **`DECLINED` es ahora un miembro de `SessionStatus`** y lo veis en tres sitios:
  `GET /signing/session` → `status` (ya lo publicábamos como literal; el valor no cambia),
  `GET /signing/session/auth` → `outcome`, y `POST /signing/session` → `status`.
- **Códigos nuevos en el 409 de `/signing/decline`:** `SESSION_ALREADY_DECLINED`,
  `DECLINE_NOT_OFFERED_TO_ROLE`, `DECLINE_NOT_OFFERED_IN_QUORUM_STEP`. Y los de siempre, con el mismo
  significado que en el commit: `SESSION_ALREADY_COMPLETED`, `SESSION_CLOSED`, `ENVELOPE_NO_LONGER_LIVE`,
  `STEP_NOT_ACTIVE`. 401: `CREDENTIAL_RETIRED`, `AUTH_REAUTH_REQUIRED`. 422: `VALIDATION_ERROR` (el motivo).
  ⛑ **2026-09-29**: `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` se retiró con TASK-050 (`8f42995d`): rechazar en un paso de
  quórum responde 200 y lo juzga el sobre. Ver [TASK-050 signer](TASK-050-signer-step-policy-and-what-a-recipient-reads.md).
- **El commit gana un código:** firmar después de haber rechazado devuelve 409 `SESSION_ALREADY_DECLINED`
  (antes no podía ocurrir).
- **`SEAL_PENDING` (409) en `GET /signing/session`.** Un sobre anulado se sella tal como está, de forma
  asíncrona. Quien firmó o rechazó puede leer ese documento sellado — pero hasta que el sello llega, la
  lectura se rechaza con este código, y la descarga del documento contesta 404. Se levanta sola.

## Lo que el frontal tiene que hacer

1. **Botón *Rechazar* visible otra vez** en la ceremonia, **detrás de una confirmación explícita** que diga
   que es irreversible, con un campo de motivo obligatorio (máx. 500).
2. **Ocultar el botón por `code`, no por rol en vuestro lado:** `DECLINE_NOT_OFFERED_TO_ROLE` y
   `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` significan *esta persona no puede rechazar aquí*; el backend es quien
   decide qué roles pueden (hoy `SIGNER`, `APPROVER`, `CERTIFIED_DELIVERY`). ⛑ **2026-09-29**: desde TASK-050 solo
   queda `DECLINE_NOT_OFFERED_TO_ROLE`; el otro código ya no se emite.
3. **`DECLINED` es un estado terminal propio**: ni pantalla de *firmado*, ni pantalla de *el remitente anuló*.
   `SESSION_ALREADY_DECLINED` es el éxito que llega tarde (doble clic, segunda pestaña): mostrad el estado
   rechazado.
4. **Un sobre `VOIDED` ya no es siempre *nada que ver*.** Para quien firmó o rechazó, `GET /signing/session`
   vuelve a contestar 200 (con `status` `COMPLETED` o `DECLINED`) cuando el sello de anulación ha llegado, y
   la descarga sirve el PDF sellado; antes de eso, `SEAL_PENDING`. Quien no actuó sigue recibiendo
   `ENVELOPE_NO_LONGER_LIVE`.

## Lo que NO está listo todavía

- ~~**Ningún aviso por correo** del rechazo ni de la anulación (TASK-040).~~ ⛑ **2026-09-29**: llega con [TASK-040](TASK-040-integrator-ending-notice.md): cada destinatario invitado recibe un correo, sin enlace, cuando el sobre termina sin acuerdo. El signer no cambia.
- **El PDF no dice que está anulado.** El sello de anulación es invisible y no lleva `/Reason` (EU DSS 6.4 no
  puede escribirlo por REST — BL-281); lo dice la plataforma (el estado del sobre) y, cuando llegue, el
  documento de evidencias.
- **`CERTIFIED_DELIVERY` no tiene read model**: `GET /signing/session` lo rechaza con `ROLE_NOT_INTERACTIVE`
  como siempre, aunque la ruta de rechazo sí lo admite.
- **Volver a entrar con una puerta de acceso declarada** a un sobre anulado: pasar la puerta otra vez se
  rechaza (el sobre ya no está vivo), igual que hoy en un sobre `COMPLETED`. Con la puerta neutra, el enlace
  basta.

## Lo que NO existirá, y por qué

- **Deshacer un rechazo.** Es terminal como una firma: el remitente crea un sobre nuevo (TASK-046 §4 D6).
- ~~**Rechazar en un paso de quórum**, hasta que los pasos de quórum se puedan crear: la regla está escrita y
  no se construye código que ningún flujo alcanza (ADR-0070 §2.3).~~ ⛑ **2026-09-29**: ya existe. TASK-050 permite
  crear pasos `AT_LEAST` y un rechazo dentro de ellos se acepta (`8f42995d`); ver
  [TASK-050 signer](TASK-050-signer-step-policy-and-what-a-recipient-reads.md).

## Cómo verificarlo desde el frontal

Con un sobre de dos firmantes bloqueantes en pasos distintos: el primero firma; el segundo abre, rechaza
con motivo → 200 `DECLINED`. `GET /signing/session/auth` del segundo → `outcome: DECLINED`. El primero, en
su sesión, recibe `SEAL_PENDING` hasta que el sello llega y después 200 con `status: COMPLETED` y el PDF
descargable. Un tercer destinatario que no actuó → `ENVELOPE_NO_LONGER_LIVE`.
