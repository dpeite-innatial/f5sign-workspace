# Traspaso al frontal — el firmante descarga el justificante sellado de su propio acto

| | |
|---|---|
| **Origen** | rama `feat/per-recipient-receipt`, **mergeada en `develop` el 2026-10-26, sin desplegar** · commit `f3bc315a`, la punta de la rama al escribir esto · TASK-047 · [ADR-0086](../adr/ADR-0086-a-recipient-who-acts-gets-a-sealed-receipt.md) (`Proposed`) |
| **Fecha** | 2026-10-26 |
| **Repos afectados** | **signer** |
| **Naturaleza** | aditivo: una ruta nueva bajo la credencial de sesión y dos códigos nuevos en `ProblemCode`; ninguna ruta existente cambia |
| **Acción requerida** | opcional: ofrecer la descarga del justificante tras firmar, aprobar o rechazar · tratar el 409 `RECEIPT_NOT_READY` como espera |
| **Desplegado** | not yet |
| **Status** | Pending |

## Lo que cambió en el contrato

- **`GET /api/v1/signing/session/receipt`** devuelve el justificante del acto del destinatario de la credencial: un
  PDF/A-3a sellado por la plataforma, con sus datos adjuntos en JSON. Nombra a la organización remitente y no dice
  nada de los demás participantes ni de quien envió el sobre. Una vez emitido no cambia. Se descarga como
  `justificante-<id del sobre>-<id del destinatario>.pdf`. Etiqueta `Signing` en el `doc.json`.

> ⚑ **2026-10-28:** el nombre cambió; ver [TASK-076](TASK-076-integrator-signer-download-names.md).

- **Autenticación:** la credencial de sesión (`Authorization: Bearer`, la misma de la lectura de sesión, el documento
  y el commit). La ruta no lleva id de destinatario: es el de la credencial. El enlace de firma por sí solo no la
  admite.
- **Quién recibe uno:** un firmante, un aprobador o quien rechaza. Se emite poco después del acto: con
  `SEQUENTIAL_PADES`, cuando su firma ya está en el PDF; con `SINGLE_SEAL`, en su commit; y en un rechazo, en los dos
  modos.
- **Respuestas:**
  - `200`: el PDF, con un `ETag` fuerte (el SHA-256 de los bytes) y `Cache-Control: private`.
  - `304`: con `If-None-Match` y ese mismo `ETag`.
  - `409 RECEIPT_NOT_READY`: actuó y su justificante aún no está emitido. Con `SEQUENTIAL_PADES` dura hasta que su
    firma está en el PDF. Volver a preguntar tras una espera breve; se levanta solo cuando se emite.
  - `409 RECEIPT_UNAVAILABLE`: el justificante consta, pero su PDF no se puede leer. Repetir da la misma respuesta,
    salvo que la plataforma restaure el PDF. No ofrecer reintento automático.
  - `404`: una sola respuesta para cuatro casos: aún no ha firmado, aprobado ni rechazado; el remitente retiró su
    credencial; o el sobre cerró y ya no le sirve (rechazó o fue liberado). Para distinguirlos, preguntar a
    `GET /api/v1/signing/session`.
  - `400`, `401`, `500`: como en las demás rutas de la credencial de sesión.
- **`ProblemCode`** gana `RECEIPT_NOT_READY` y `RECEIPT_UNAVAILABLE`. Ramificad por `code`, no por el texto.

Las formas exactas están en el `doc.json`; este documento no las copia.

## Lo que el frontal tiene que hacer

1. Tras el acto (commit o rechazo), si queréis ofrecer el justificante, pedid `GET /api/v1/signing/session/receipt`
   con la credencial de sesión.
> **2026-10-27, TASK-072:** the session read and the copy list now carry `receipt` (`PENDING` / `ISSUED` / null). Poll the read, not this route, and cap the polling: see [TASK-072's handoff](TASK-072-signer-copy-card-reads.md) §3. The steps below are TASK-047's and still describe what this route answers.

2. Ante `409 RECEIPT_NOT_READY`, esperad en la misma pantalla y repetid con una cadencia moderada. No lo mostréis
   como error.
3. Ante `409 RECEIPT_UNAVAILABLE`, mostrad un aviso de que no se puede descargar ahora, sin bucle de reintento.
4. Ante `404`, no asumáis un fallo: leed la sesión para saber si el destinatario no ha actuado o la credencial se
   retiró.
5. Guardad el `ETag` si cacheáis el PDF.

## Lo que NO está listo todavía

- Nada se ha desplegado. ADR-0086 está `Accepted` (2026-10-26).
- **No hay envío del justificante** por correo o SMS ni enlace que lo recupere después de salir de la ceremonia: la
  descarga exige la credencial de sesión viva (15 minutos, renovable). Lo recogen [BL-280](../BACKLOG.md) (la
  entrega) y [BL-188](../BACKLOG.md) (volver a la copia firmada). Quien rechaza pierde su sesión al cerrarse el
  sobre, y su justificante solo lo descarga el integrador.

## Cómo verificarlo desde el frontal

- Regenerad el `doc.json` y comprobad `paths./api/v1/signing/session/receipt` y los dos valores en
  `components.schemas.ProblemCode` (regla 4: comprobad primero que el stack que os sirven ya los tiene).
- Con una sesión que ya firmó en `SEQUENTIAL_PADES`, la petición da 409 `RECEIPT_NOT_READY` hasta que la firma entra
  en el PDF y después 200 con `Content-Type: application/pdf`.
