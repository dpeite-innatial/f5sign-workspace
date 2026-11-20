# Traspaso al frontal — un destinatario puede quedar como inalcanzable, y el remitente puede corregirlo

| | |
|---|---|
| **Origen** | rama `feat/recipient-delivery-failure-2` · el contrato lo cambian `3323161` (el estado y la ruta) y `0ee1444` (el cuerpo del 409 y la puerta de activación) · sin PR todavía |
| **Fecha** | 2026-08-18 |
| **Repos afectados** | **dashboard** (ve el estado nuevo y necesita la acción de corregir) · **signer** (ninguna acción, ver abajo) |
| **Naturaleza** | additive — ningún campo cambia de tipo ni desaparece · **pero un enum cerrado gana un valor**, y ese es el punto que rompe si se ignora |
| **Acción requerida** | **handle a new state** — `recipients[].outcome` puede valer `DELIVERY_FAILED`, que hasta hoy era imposible · y exponer la corrección de contacto cuando se decida el UX |
| **Status** | Pending |

## Lo que cambió en el contrato

Las formas exactas están en el spec (`GET /api/doc.json`); aquí va **qué cambió y qué hacer**.

1. **`recipients[].outcome` gana un sexto valor: `DELIVERY_FAILED`.** Era un enum cerrado de cinco
   (`PENDING`, `COMPLETED`, `DECLINED`, `DELEGATED`, `SKIPPED`). ⛔ **Éste es el cambio que importa**: si el
   dashboard tipa ese enum, un `switch` exhaustivo o un `Record<Outcome, …>` deja de compilar, y si no lo
   tipa, caerá en su rama por defecto — que probablemente diga "Pendiente", que es exactamente la lectura
   equivocada. Significa *"no hemos podido hacerle llegar la invitación"*, no *"aún no ha firmado"*.

2. **Ruta nueva: `POST /api/v1/envelopes/{id}/recipients/{recipientId}/corrections`.** Corrige el contacto
   del destinatario, lo devuelve a `PENDING` y dispara una entrega nueva. Cuerpo: solo `email`.

3. **El 409 de esa ruta trae `application/problem+json`** con un `code` sobre el que discriminar. El caso
   que hay que dibujar es `RECIPIENT_CORRECTION_BUDGET_EXHAUSTED`: **hay un máximo de 3 correcciones por
   destinatario** y la cuarta se rechaza.

## Lo que el frontal tiene que hacer

- **Dashboard:** distinguir `DELIVERY_FAILED` de `PENDING` en la lista de destinatarios — son estados
  distintos con acciones distintas, y confundirlos es el fallo que esta task existe para evitar: hasta hoy
  un sobre con un correo rebotado se veía idéntico a uno esperando a que alguien se decidiera. Y ofrecer la
  corrección de contacto, discriminando el 409 por `code` y no por texto.
- **Signer:** ⚑ **nada, y es deliberado.** Un destinatario `DELIVERY_FAILED` **sigue pudiendo firmar** si
  tiene el enlace: `GET /api/v1/signing/session` le devuelve `AUTH_PASSED` igual que a un `PENDING`. El
  token se acuña *antes* de intentar la entrega, así que el credencial es el token y no el buzón — que le
  rebotara el correo no le quita el derecho a firmar. No hay `SessionStatus` nuevo y no hay que tocar nada.

## Lo que NO está listo todavía

- ⚠ **Solo se detecta el rechazo síncrono en la entrega.** Un rebote duro real suele ser **asíncrono** —el
  servidor acepta el mensaje y el destinatario lo rechaza minutos u horas después—, y de eso **no hay
  ninguna señal**: ese destinatario se queda `PENDING` para siempre, exactamente como antes. El seam de
  recibos (webhook del proveedor) no existe. **No presentéis `DELIVERY_FAILED` como "todos los fallos de
  entrega"**, porque no lo es.
- **El presupuesto restante de correcciones no es legible.** No hay campo que diga cuántas quedan; el
  frontal se entera de que se agotó por el 409 y no antes. Si el UX necesita "te quedan 2", falta backend.
- **Solo se corrige el email.** No hay teléfono que corregir porque no existe columna de teléfono en el esquema ([TASK-023](../tasks/TASK-023-sms-codes-and-recipient-phone.md)). ⚑ Esta línea decía *"hasta que exista el canal SMS"*; el canal existe desde 2026-08-20 ([TASK-030](../tasks/TASK-030-sms-delivery-channel.md)) y la conclusión no cambia — lo que falta es el destino, no el transporte.
- **No hay reintento automático ni fallback de canal.** La recuperación es siempre del remitente.

## Cómo verificarlo desde el frontal

1. `POST /api/v1/envelopes/{id}/recipients` con un email que rebote, y enviar el sobre.
2. `GET /api/v1/envelopes/{id}` → ese destinatario sale con `outcome: "DELIVERY_FAILED"`.
3. `POST …/recipients/{recipientId}/corrections` con `{"email": "…"}` → 204.
4. `GET` otra vez → vuelve a `PENDING` con `outcome_recorded_at` a `null`, y sale una entrega nueva.
5. Repetir hasta la cuarta corrección → **409** con `code: RECIPIENT_CORRECTION_BUDGET_EXHAUSTED`.

⛑ **2026-10-13: the correction now answers `200 {"warnings": [...]}`, not `204`** ([TASK-031](TASK-031-notification-channels.md)). The steps above are the contract as this handoff shipped it.
