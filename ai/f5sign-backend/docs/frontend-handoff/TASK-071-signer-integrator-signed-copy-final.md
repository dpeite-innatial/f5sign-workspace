# Traspaso al frontal — `signed_copy = FINAL` llega en cuanto todo lo que ve el destinatario está sellado

| | |
|---|---|
| **Origen** | rama `feat/recipient-notices`, **en `develop` desde el 2026-10-26, sin desplegar** · commit `cdbdfffa`, el que cambia `signed_copy` y su texto publicado · TASK-071 · [ADR-0089](../adr/ADR-0089-a-recipient-is-told-when-their-part-ends.md) §2.7 (Accepted 2026-10-26) |
| **Fecha** | 2026-10-26 |
| **Repos afectados** | **signer** y **dashboard** (integrador, solo informativo) |
| **Naturaleza** | aditivo en la forma (ningún campo ni ruta nuevos; **ocho valores nuevos** en el enum `purpose` de la historia de notificaciones, ver abajo); **cambia una garantía publicada**: `signed_copy = FINAL` puede llegar antes de que el sobre complete |
| **Acción requerida** | signer: tratar `FINAL` como «tu copia es definitiva» sin esperar a que el sobre complete · integrador: ninguna |
| **Desplegado** | not yet |
| **Status** | Pending |

Hermano de [TASK-068](TASK-068-signer-signed-copy-after-commit.md) (`signed_copy`) y de
[TASK-069](TASK-069-integrator-signer-early-document-seal.md) (el sello temprano). Este traspaso sustituye la
decisión que recogía TASK-069: «`FINAL` solo con la compleción».

## Lo que cambió en el contrato

### Signer

- **`GET /api/v1/signing/session`: `signed_copy = FINAL` ahora puede llegar con el sobre aún en `SENT`.** Ocurre
  solo con `SEQUENTIAL_PADES`, en cuanto el acto del destinatario aterrizó y todos los documentos que puede ver
  están sellados. Antes de esto, en ese mismo momento la lectura decía `CONTAINS_YOUR_SIGNATURE`.
- **Lo mismo tras el cierre sin `SEAL_PENDING`**: si el sobre cerró y todos los documentos que ve el destinatario ya
  se sellaron antes, la lectura contesta 200 con `FINAL` (antes, `AWAITING_ENVELOPE`).
- **Vale también para un rol que aprueba**: un aprobador cuyo acto aterrizó y cuyos documentos visibles están
  sellados lee `FINAL`.
- **Un acto admitido que aún se está aplicando nunca es `FINAL`**, aunque todo lo que ve esté sellado: sigue en
  `APPLYING`.
- **Con `SINGLE_SEAL`, sin cambios**: `FINAL` solo con la compleción.
- **Los bytes no cambian**: la descarga ya servía la revisión sellada; ahora la lectura lo dice.
- La `description` publicada de `signed_copy` y la del 200 de la descarga cambiaron: regenerad la especificación y
  comparad.

### Integrador

- **Solo informativo.** Ninguna ruta del integrador cambia por esto. `signed_copy` es del destinatario, no del
  sobre: un `FINAL` no dice nada sobre la compleción, cuyas señales siguen siendo `envelope.status` y
  `seal_pending_since`.
- **La historia de notificaciones del destinatario**
  (`GET /api/v1/envelopes/{id}/recipients/{recipientId}/notifications`) **trae propósitos nuevos**:
  `RECIPIENT_ACT_RECORDED`, `RECIPIENT_PART_COMPLETE`, `RECIPIENT_DECLINE_RECORDED` y los cinco
  `ENVELOPE_ENDED_SENDER_CANCELLED_YOUR_COPY`, `ENVELOPE_ENDED_SENDER_CANCELLED_WITH_REASON_YOUR_COPY`,
  `ENVELOPE_ENDED_DECLINED_YOUR_COPY`, `ENVELOPE_ENDED_TIME_RAN_OUT_YOUR_COPY` y
  `ENVELOPE_ENDED_OUT_OF_REACH_YOUR_COPY` (ocho en total). El conjunto es abierto: mostrad un propósito
  desconocido en vez de rechazarlo.
- **`notification_channels: []` cambia de alcance.** Con `[]` la plataforma no manda ningún aviso de parte
  (los ocho nuevos incluidos), y el integrador es quien entrega al destinatario su enlace de copia con
  `POST /api/v1/envelopes/{id}/recipients/{recipientId}/copy-links` (ver el traspaso de TASK-070).

## Lo que el frontal tiene que hacer

1. **Signer: tratad `FINAL` como «tu copia es definitiva»**, sin esperar a que el sobre complete ni deducir nada de
   su estado. La notificación `RECIPIENT_PART_COMPLETE` exige más (sobre abierto, parte registrada,
   recibo emitido): la pantalla puede leer `FINAL` antes de que esa notificación salga, nunca al revés. No deduzcáis
   de `FINAL` que el aviso ya se envió.
2. **Signer: no inferáis `FINAL` de un 200 en la ruta de bytes.** `CONTAINS_YOUR_SIGNATURE` sigue sirviendo la
   descarga sin ser definitiva.
3. **Integrador: nada que hacer**, salvo aceptar los propósitos nuevos en la historia de notificaciones.
