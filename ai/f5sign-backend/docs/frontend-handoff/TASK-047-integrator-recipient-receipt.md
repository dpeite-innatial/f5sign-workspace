# Traspaso al frontal — un integrador descarga el justificante sellado de un destinatario

| | |
|---|---|
| **Origen** | rama `feat/per-recipient-receipt`, **mergeada en `develop` el 2026-10-26, sin desplegar** · commit `f3bc315a`, la punta de la rama al escribir esto · TASK-047 · [ADR-0086](../adr/ADR-0086-a-recipient-who-acts-gets-a-sealed-receipt.md) (`Proposed`) · la forma de los textos cifrados: rama `feat/encrypt-the-other-members` ([ADR-0096](../adr/ADR-0096-key-management-encrypts-the-logs-free-text-under-erasable-keyrings.md) §2.9) |
| **Fecha** | 2026-10-26 · actualizado 2026-11-03 |
| **Repos afectados** | **integradores con clave de máquina** (`dashboard-sf`). El **dashboard** no: la ruta no acepta la sesión de usuario |
| **Naturaleza** | aditivo: una ruta nueva y dos códigos nuevos en `ProblemCode`; ninguna ruta existente cambia |
| **Acción requerida** | ninguna. Opcional: ofrecer la descarga del justificante de cada destinatario que ha actuado |
| **Desplegado** | not yet |
| **Status** | Pending |

## Lo que cambió en el contrato

- **`GET /api/v1/envelopes/{id}/recipients/{recipientId}/receipt`** devuelve el justificante del acto de ese
  destinatario: un PDF/A-3a sellado por la plataforma, con sus datos adjuntos en JSON. Recoge el acto del propio
  destinatario y el nombre de la organización remitente, y nada de los demás participantes ni de quien envió el
  sobre. Una vez emitido no cambia. Se descarga como `justificante-<id del sobre>-<id del destinatario>.pdf`.
  Etiqueta `Audit trail` en el `doc.json`.

> ⚑ **2026-10-28:** el nombre cambió; ver [TASK-076](TASK-076-integrator-signer-download-names.md).

- **Autenticación:** la clave de máquina y la cabecera `F5Sign-Declared-Subject`, como en las demás rutas de
  integrador. Cualquier clave del tenant descarga el justificante de cualquier destinatario del tenant.
- **Cuándo existe:** solo para un firmante, un aprobador o quien rechaza, y poco después de su acto: con
  `SEQUENTIAL_PADES`, cuando su firma ya está en el PDF; con `SINGLE_SEAL`, en su commit; y en un rechazo, en los
  dos modos.
- **Respuestas:**
  - `200`: el PDF, con un `ETag` fuerte (el SHA-256 de los bytes) y `Cache-Control: private`.
  - `304`: con `If-None-Match` y ese mismo `ETag`.
  - `404`: una sola respuesta para un sobre o destinatario que no existe, de otro tenant, que aún no ha actuado,
    con un rol que no recibe justificante, o cuyo justificante aún no se ha emitido. Para quien actuó, la misma
    petición un poco después puede dar 200.
  - `409 RECEIPT_UNAVAILABLE`: el justificante consta, pero su PDF no se puede leer. Repetir da la misma respuesta,
    salvo que la plataforma restaure el PDF, cosa que no puede hacer con uno destruido.
  - `400`: falta la cabecera `F5Sign-Declared-Subject`, o no es válida. `401`, `500`: como en las demás rutas.
- **`ProblemCode`** gana `RECEIPT_NOT_READY` y `RECEIPT_UNAVAILABLE`. Esta ruta solo emite el segundo;
  `RECEIPT_NOT_READY` lo emite la ruta de sesión del firmante.
- **El JSON adjunto al PDF** (`"schema": "f5sign.receipt/1"`) lleva datos personales del destinatario; tratadlo con el mismo
  cuidado que el PDF. Desde TASK-077 el JSON añade `recipient.personal.contacts[]` (cada código enviado, con su
  contacto enmascarado) y `act.signature_image_sha256`; sigue siendo `f5sign.receipt/1` y sus horas siguen en UTC.
  El PDF imprime la hora peninsular con su zona. No es la página «Anexo: datos técnicos de verificación» del PDF,
  que imprime parte de esos datos.
- **Cambia la forma de dos campos del JSON adjunto (2026-11-03, ADR-0096 §2.9).** El log guarda cifrado el texto que
  escribe una persona. `act.reason` y `act.reservation.text` pasan a ser una declaración, como ya lo era
  `envelope.title`: `{"stated": true, "value": ..., "source": ...}` o `{"stated": false, "reason": ...}`. Los tres pueden
  decir `ERASED`, cuando la clave del texto se destruyó, o `UNREADABLE`, cuando el valor está dañado. Hoy nada destruye
  una clave. Sigue siendo `f5sign.receipt/1`, porque nada está desplegado. El justificante no declara el motivo de una
  anulación.

Las formas exactas están en el `doc.json`; este documento no las copia.

## Lo que el frontal tiene que hacer

1. Nada es obligatorio. Para ofrecer la descarga, llamad a la ruta con la clave de máquina y la cabecera de sujeto.
2. Tratad el 404 de un destinatario que sí actuó como «todavía no», y repetid más tarde.
3. Ante `409 RECEIPT_UNAVAILABLE`, no reintentéis en bucle.

## Lo que NO está listo todavía

- Nada se ha desplegado. ADR-0086 está `Accepted` (2026-10-26).
- No hay ruta que liste los justificantes de un sobre: se piden de uno en uno, por destinatario.

## Cómo verificarlo desde el frontal

- Regenerad el `doc.json` y comprobad la ruta y los dos valores en `components.schemas.ProblemCode` (regla 4).
- Con un destinatario que ya firmó, la petición da 200 con `Content-Type: application/pdf` y un `ETag`; repetida con
  `If-None-Match` da 304.
