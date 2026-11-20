# Traspaso al frontal — un sobre anulado dice quién lo anuló, y queda sellado

| | |
|---|---|
| **Origen** | rama `feat/recipient-decline` (desde `develop` `6d081d1`), **mergeada en `develop` en `26ed0d7`, sin desplegar** · commit: ver `git log feat/recipient-decline` · [ADR-0070](../adr/ADR-0070-an-envelope-ends-in-agreement-or-is-voided-and-sealed.md) (`Proposed`, texto aprobado por el mantenedor el 2026-09-23) · [TASK-046](../tasks/TASK-046-a-recipient-may-decline.md) |
| **Fecha** | 2026-09-23 |
| **Repos afectados** | **dashboard** y **integradores con clave de máquina** (`dashboard-sf`) |
| **Naturaleza** | **aditivo en el esquema** (campos nuevos) · **rompe el contrato en un enum** (`EnvelopeStatus.DECLINED` desaparece; nunca se emitió) · ⚠ **dos cambios de comportamiento en una ruta viva**: `POST /envelopes/{id}/void` ahora **sella**, y **se rechaza en `READY_TO_SEAL`** |
| **Acción requerida** | leer `void_cause` para distinguir las dos anulaciones · quitar `DECLINED` de vuestro tipo de estado de sobre · manejar `ENVELOPE_REACHED_AGREEMENT` en el void · mostrar el motivo del rechazo desde el destinatario |
| **Desplegado** | not yet |
| **Status** | Pending |

## Lo que cambió en el contrato

- **Un sobre termina `COMPLETED` (acuerdo) o `VOIDED` (sin acuerdo).** `EnvelopeStatus.DECLINED` se retira del
  enum publicado: nada lo escribía nunca, así que ningún integrador puede haberlo recibido. Quién terminó un
  sobre sin acuerdo es su **causa**:
  - `void_cause`: `SENDER_VOIDED` | `RECIPIENT_DECLINED` (null mientras no está anulado). Todos los sobres
    anulados antes de este cambio son `SENDER_VOIDED`.
  - `voided_by_recipient_id`: el destinatario que rechazó, cuando la causa es `RECIPIENT_DECLINED`.
    `voided_by` (el actor del remitente) queda **null** en ese caso, y `void_reason` es solo el texto del
    remitente — nunca el del rechazo.
- **En cada destinatario:** `declined_at`, `decline_reason` (el texto del destinatario, tal como lo escribió)
  y `decline_access_method` (el método con el que había pasado la puerta de acceso al rechazar).
  `outcome: DECLINED` ya existía en el enum; ahora algo lo escribe.
- **`POST /envelopes/{id}/void` sella.** Anular —por cualquiera de las dos causas— sella cada documento tal
  como está con el sello de la plataforma, de forma asíncrona: sobre las firmas que tenga, o sobre el
  original si nadie firmó. `GET …/documents/{id}/sealed` sirve ese PDF cuando el sello ha llegado (404
  antes). No se emite `COMPLETED`: un sobre anulado sigue `VOIDED`.
- **`POST /envelopes/{id}/void` se rechaza en `READY_TO_SEAL`** con 409 `ENVELOPE_REACHED_AGREEMENT`: todos
  los bloqueantes firmaron, el sobre ha llegado a acuerdo y se completa solo. Antes se aceptaba.

## Lo que el frontal tiene que hacer

1. Distinguir en la UI *«anulado por el remitente»* de *«rechazado por <destinatario>»* con `void_cause` y
   `voided_by_recipient_id` — no derivarlo de otros campos.
2. Quitar `DECLINED` de cualquier `switch` sobre el estado del sobre.
3. En el void: tratar `ENVELOPE_REACHED_AGREEMENT` como *ya no se puede anular, está terminando*; releer el
   sobre en vez de reintentar.
4. Mostrar al remitente `decline_reason` del destinatario que rechazó.

## Lo que NO está listo todavía

- **El documento de evidencias** de un sobre anulado (con la causa, quién rechazó y el motivo): es del trabajo
  del audit trail; hasta entonces el motivo solo se lee aquí, en el sobre.
- **El PDF sellado no dice que está anulado**: el sello es invisible y sin `/Reason` (EU DSS 6.4 no puede
  escribirlo por REST — BL-281). Lo dice la plataforma: `status: VOIDED` + `void_cause`.
- **Un sello que falla** se reintenta y, agotados los reintentos, queda aparcado para un operador; el sobre no
  cambia de estado y nada lo muestra al cliente (BL-15, igual que el sello de compleción).
- **Webhooks**: `envelope.voided` con causa es el nombre al que apunta ADR-0070; nada de eso existe todavía
  (ADR-0064).

## Lo que NO existirá, y por qué

- **Un estado de sobre `DECLINED`.** Dos finales sin acuerdo exigirían dos caminos vinculantes —dos sellos,
  dos evidencias, dos avisos— para un solo hecho (ADR-0070 §7.1).
- **Rechazo delegado por el integrador** en esta tarea: es el primer seguimiento (ADR-0070 §2.8), no una idea
  descartada. Para la carta de porte, un cargador que no firma es un transporte cancelado: `void`.

## Cómo verificarlo desde el frontal

Anular un sobre `SENT` → 204; `GET /envelopes/{id}` → `status: VOIDED`, `void_cause: SENDER_VOIDED`; tras el
worker, `…/sealed` sirve un PDF. Un sobre en que un firmante bloqueante rechaza → `void_cause:
RECIPIENT_DECLINED`, `voided_by_recipient_id` = ese destinatario, y en él `outcome: DECLINED`, `declined_at`,
`decline_reason`, `decline_access_method`. Void de un sobre `READY_TO_SEAL` → 409 `ENVELOPE_REACHED_AGREEMENT`.
