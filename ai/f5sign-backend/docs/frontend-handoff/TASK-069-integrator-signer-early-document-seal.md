# Traspaso al frontal — un documento queda sellado en cuanto nadie más puede firmarlo, antes de que el sobre cierre

| | |
|---|---|
| **Origen** | rama `feat/early-document-seal`, **sin mergear, sin desplegar** · commit `839a4c5c`, la punta de la rama al escribir esto · TASK-069 · [ADR-0087](../adr/ADR-0087-a-document-is-sealed-once-it-is-final.md) (`Proposed`: la aceptación es del propietario) |
| **Fecha** | 2026-10-23 |
| **Repos afectados** | **dashboard** (integrador) y **signer** |
| **Naturaleza** | aditivo en la forma (ningún campo, ruta ni valor de enum nuevo); **cambia una garantía publicada**: `GET .../documents/{documentId}/sealed` puede contestar 200 con el sobre aún en `SENT`, y el 409 `SEAL_PENDING` pasa a ser por documento |
| **Acción requerida** | integrador: no tratar un primer 200 de `/sealed` como «completado» · signer: llevar la pantalla «preparando tu copia» con el 409 `SEAL_PENDING` y no inferir `FINAL` de un 200 en la descarga |
| **Desplegado** | not yet |
| **Status** | Pending |

> 2026-10-26, TASK-071: `FINAL` ya no espera a la compleción del sobre; ver [TASK-071](TASK-071-signer-integrator-signed-copy-final.md).

Hermano de [TASK-068](TASK-068-signer-signed-copy-after-commit.md) (`signed_copy`) y del punto 4 y la nota ⛑ del
traspaso al signer de TASK-050. Léelos juntos.

## Lo que cambió en el contrato

### Integrador

- **`GET /api/v1/envelopes/{id}/documents/{documentId}/sealed` puede contestar 200 mientras el sobre sigue en
  `SENT`.** Los bytes y el ETag fuerte son los mismos antes y después de que el sobre complete.
- **Cuándo ocurre**: solo con `SEQUENTIAL_PADES`, para un documento con al menos una firma, cuando ya nadie puede
  firmarlo **ni rellenar un campo en él**. Regla del propietario (2026-10-23): un documento queda retenido mientras
  esté pendiente cualquier destinatario que sea dueño de un campo colocado en él, **lo firme o no**, de cualquier
  tipo; un campo sin dueño no retiene nada; los destinatarios completados, rechazados o liberados ya no retienen.
  Motivo: un valor se registra en el commit de su dueño y lo dibuja la siguiente revisión del documento, y una
  cadena sellada solo admite una extensión (ADR-0085, ADR-0087 §2.3).
- **Cuándo se evalúa**: al aterrizar la compleción de un destinatario (los documentos que firma o en los que es
  dueño de un campo) y al asegurarse el acuerdo (todos los documentos). **Un rechazo o una liberación por sí solos no
  piden nada**: ese documento se sella en un aseguramiento posterior o al cierre.
- **404 para cualquier otro documento** hasta el cierre, y después hasta que corra el sello del sobre; es permanente
  para un sobre con el que nadie se comprometió. Un id de otro tenant también es 404.
- **`GET .../documents/{documentId}/current` sigue siendo la forma de pedir la punta a mitad de flujo.**
- ⚠ **Un primer 200 en `/sealed` NO es la compleción.** Las señales son `envelope.status` y `seal_pending_since`.
- **Anular desde el remitente se rechaza** en un sobre que ya tiene un sello temprano (está acordado).
- **El trail de auditoría** muestra el sello temprano bajo su documento, con su propio hecho `DOCUMENT_SEALED`.
- La `description` publicada de la ruta cambió (dos frases): regenerad la especificación y comparad.
- **Sin campo, ruta ni valor de enum nuevos.**

### Signer

- **`GET /api/v1/signing/session`: el 409 `SEAL_PENDING` es ahora por documento.** Tras el cierre, solo contesta 409
  mientras algún documento que el destinatario puede ver tenga bytes y no esté sellado; si todos se sellaron antes,
  contesta 200 desde el cierre.
- **La ruta de bytes sigue siendo un 404 sin cuerpo** para un documento sin sellar de un sobre cerrado. Pintad la
  pantalla «preparando tu copia» a partir del 409; se levanta sola.
- **Decisión del propietario (2026-10-23):** un firmante cuyo documento se selló antes lee
  `signed_copy = CONTAINS_YOUR_SIGNATURE`, **no `FINAL`**, hasta que el sobre completa. La descarga está lista y los
  bytes están sellados. **`FINAL` solo con la compleción; no deduzcáis `FINAL` de un 200 en la ruta de bytes.**
  TASK-071 decidirá la señal de «copia final».
- Un documento que el firmante comparte con un dueño de campo pendiente puede sellarse **después** de la compleción
  del propio firmante.

### Eventos

- `DOCUMENT_READY_TO_SEAL`: `envelope_id`, `document_id`, `occurred_at`; una vez por documento que una llamada dejó
  final, en orden de documento.
- `DOCUMENT_SEALED`: `execution_id`, `envelope_id`, `document_id`, `occurred_at`.
- `ENVELOPE_SEALED` conserva su forma pero puede cubrir menos documentos, o ninguno (ADR-0087 §2.4).

## Lo que el frontal tiene que hacer

1. **Integrador**: no uséis un 200 de `/sealed` como señal de que el sobre completó; leed `status` y
   `seal_pending_since`. Si ofrecíais la descarga sellada solo al completar, podéis ofrecerla antes por documento,
   sabiendo que no cambia después.
2. **Signer**: conducid la espera con el 409 `SEAL_PENDING` de la lectura de sesión (polling como en TASK-068) y no
   mostréis control de reintento sobre un 404 de bytes.
3. **Signer**: no mostréis «copia final» con `CONTAINS_YOUR_SIGNATURE` aunque la descarga ya sirva.
4. Si consumís eventos, tratad los dos tipos nuevos como aditivos y no asumáis que `ENVELOPE_SEALED` cubre todos los
   documentos.

## Lo que NO está listo todavía

- **La aceptación de ADR-0087** (propietario): hasta entonces el comportamiento es el de la rama, sin mergear.
- **La señal de «copia final» para el firmante** (TASK-071): hoy solo hay `FINAL` al completar el sobre.
- **Un `ENVELOPE_SEALED` duplicado** puede registrarse si cada documento se selló antes y llega una redelivery de
  `ENVELOPE_READY_TO_SEAL` antes de `COMPLETED` (desviación aceptada por el propietario; la compleción y el trail lo
  absorben). Si el integrador cuenta estos eventos, no los cuente como compleciones.
- `SINGLE_SEAL` no cambia: un solo sello al cierre.

## Cómo verificarlo desde el frontal

1. Regenerad la especificación OpenAPI y comparad la `description` de `GET .../documents/{documentId}/sealed`.
2. Con un sobre `SEQUENTIAL_PADES` cuyo último paso sea `AT_LEAST 1` con dos firmantes, X e Y, cada uno con su propio
   documento (A para X, B para Y; la forma del albarán): cuando X firma, el acuerdo queda asegurado y el sobre sigue en
   `SENT` porque Y está pendiente; esperad al worker y `GET .../documents/A/sealed` contesta 200 mientras `B` contesta 404.
3. El 200 de A tiene el mismo ETag después de que el sobre complete.

En el backend, `EarlyDocumentSealHttpTest` recorre estos pasos.
