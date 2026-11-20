# Traspaso al frontal — una ceremonia de firma exige un sobre que ya se haya enviado

| | |
|---|---|
| **Origen** | `fix/signature-requires-readable-envelope` · commit `687886d` (+ correcciones de auditoría) · sin PR todavía |
| **Fecha** | 2026-08-25 |
| **Repos afectados** | **ambos** — `f5sign-dashboard` (el mint) y `f5sign-signer` (las rutas de destinatario) |
| **Naturaleza** | **rompe el contrato** en `POST /api/v1/signing-tokens`; corrige la especificación publicada en el resto |
| **Acción requerida** | dashboard: **manejar dos estados nuevos** en el mint · signer: ninguna, salvo confirmar que un 404 se trata como enlace inválido |
| **Desplegado** | not yet — la rama no está mergeada |
| **Status** | Pending |

## Lo que cambió en el contrato

**Un sobre que no se ha enviado ya no admite ceremonia.** El predicado es `sent_at IS NOT NULL`, no
`status != 'DRAFT'`.

### `POST /api/v1/signing-tokens` (dashboard) — esto es lo que rompe

Antes respondía **siempre 201**. Ahora puede responder:

| Código | Cuándo | `code` |
|---|---|---|
| **409** | el sobre no se ha enviado | `ENVELOPE_NOT_SENT` |
| **404** | el sobre no existe, es de otro tenant, o ese destinatario no está en él | — |

Ambas llevan `application/problem+json` con el esquema `ProblemDetails`, así que el `code` es legible.

⚠ **El 404 es nuevo y no solo cubre el caso "sin enviar".** Antes se acuñaba un token válido para un
`recipient_id` que no estaba en el sobre, o para un sobre de otro tenant. Eso ya no ocurre. Si vuestro
flujo depende de que el mint nunca falle, esa suposición ya no se sostiene.

⛔ **Lo que el 409 NO cubre:** un sobre **anulado, completado o caducado** sigue acuñando. La credencial
resultante no sirve para nada (ambas puertas de firma la rechazan), pero la llamada devuelve 201. No
leáis un mint correcto como prueba de que el sobre está vivo.

### Rutas de destinatario (signer) — corrige la especificación, no la rompe

Cinco rutas pasan a responder **404** para un sobre sin enviar, en lugar de servir contenido:
`POST /signing/session`, `GET /signing/session/auth`, `POST /signing/session/auth/otp/send`,
`POST /signing/session/auth`, `GET /signing/session` y `GET /signing/session/documents/{documentId}`.

El 404 es **indistinguible** de un id equivocado, y eso es deliberado: decir *"este sobre existe pero
aún no se ha enviado"* revelaría a quien solo tiene un enlace que existe un sobre sin enviar y —en el
descriptor pre-puerta— **cómo se titula**.

## Lo que el frontal tiene que hacer

**Dashboard:**

1. **Enviar antes de acuñar.** Si vuestro flujo ofrece "copiar enlace de firma" en un sobre en borrador,
   ese botón ahora falla con 409. Ocultadlo o deshabilitadlo hasta que el sobre esté enviado.
2. **Ramificad sobre `code === 'ENVELOPE_NOT_SENT'`** para dar el mensaje útil (*"envía el sobre primero"*)
   en vez de un error genérico.
3. Tratad el **404** como *"ese par sobre/destinatario ya no es válido"*, no como un fallo de red.

**Signer:** nada que cambiar. Un 404 en cualquier ruta de `/signing/` ya debería llevar a la pantalla de
enlace inválido; esto solo añade un motivo más por el que puede darse.

## Lo que NO está listo todavía

- ⛑ **CERRADO desde 2026-08-28 — este punto ya no aplica.** Decía: *«La dirección terminal sigue
  abierta. Un token de firma sobrevive a un sobre anulado hasta su caducidad (7 días). Lo que cambia es
  que no compra nada: ambas puertas rechazan.»* Las dos mitades eran falsas o quedaron obsoletas:
  `BL-87` está cerrado por [ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md), que
  cierra también las **lecturas** (no solo las puertas), y desde 2026-09-01 una **corrección de
  contacto** revoca el enlace superseded en vez de dejarlo vivo siete días
  ([ADR-0060](../adr/ADR-0060-retiring-a-credential-whose-holder-changed.md) §2.6 enmendado).
  ⚠ Un sobre `COMPLETED` **sí** sigue sirviendo el read-model y los bytes al firmante: es su copia.
- **Nada de esto está desplegado.** La rama no se ha mergeado.

## Lo que NO existirá, y por qué

**No habrá un código distinto para "sobre anulado" en el mint.** Se decidió no cubrir la dirección
terminal aquí: lo que necesita es una credencial que se pueda invalidar, y eso es una decisión sobre el
formato de credencial (ADR-0045), no sobre la legibilidad del sobre.

**El 404 de las rutas de destinatario no se va a desglosar.** Distinguir "no existe" de "sin enviar" es
justamente la divulgación que el 404 evita.

## Cómo verificarlo desde el frontal

1. Crear un sobre, añadir documento y destinatario, **sin enviar**.
2. `POST /api/v1/signing-tokens` con ese par → **409**, cuerpo `application/problem+json`,
   `code: "ENVELOPE_NOT_SENT"`.
3. `POST /api/v1/signing-tokens` con un `recipient_id` aleatorio sobre un sobre enviado → **404**.
4. Enviar el sobre, repetir el paso 2 → **201** con el `token`, exactamente como antes.
