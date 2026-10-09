# Traspaso al integrador (PROVISIONAL): un sobre caduca, y se puede alargar su vida

| | |
|---|---|
| **Origen** | TASK-049 (caducidad del sobre, dentro del paquete ADR-0073) |
| **Medido en** | `f5sign-backend` rama `feat/envelope-expiry` @ `01e77681` (2026-09-29). Sin mergear en `develop`, sin desplegar; `dashboard-sf` rama `feat/waybill-pdf-pagination`. Los nombres pueden cambiar hasta que el paquete aterrice |
| **Repos afectados** | `dashboard-sf` (integración de Factor5). El signer tiene su propio traspaso: `11-049-signer.md` |
| **Status** | **PROVISIONAL, accionable contra mocks.** El traspaso oficial llegará en `f5sign-backend/docs/frontend-handoff/` cuando el paquete ADR-0073 aterrice |

## Qué cambió (commiteado, no planeado)

1. **`POST /api/v1/envelopes` acepta `expires_in_days`** (opcional, entero de 1 a 180, por defecto 30). Fuera de
   rango responde 422. Es la vida del sobre en días **contados desde el envío**, no desde la creación.
2. **`GET /api/v1/envelopes/{id}`**:
   - `expires_at` es **`null` mientras el sobre es `DRAFT`**. Se resuelve al enviar: `sent_at + expires_in_days`.
     Antes era creación + 30 días. **No mostréis fecha para un borrador.**
   - Campo nuevo **`expires_in_days`**, siempre presente (la vida elegida al crear; una prórroga mueve
     `expires_at` y no lo toca).
3. **Ruta nueva `POST /api/v1/envelopes/{id}/expiry-extensions`**, cuerpo `{"expires_at": "<RFC 3339>"}`
   (fecha absoluta, no días a sumar). Éxito: **200** `{"expires_at": "..."}`. Se puede repetir, siempre hacia
   delante, hasta 180 días después del envío. Refusos:
   - 409 `ENVELOPE_NOT_SENT`: es un borrador; no hay nada que prorrogar.
   - 409 `ENVELOPE_NO_LONGER_LIVE`: el sobre ya cerró.
   - 409 `ENVELOPE_EXPIRED`: la fecha ya pasó (el barrido lo cierra en menos de un minuto y nada lo mueve antes).
   - 409 `EXPIRY_NOT_FORWARD`: la fecha pedida no es posterior a la actual. ⚠ Un reintento tras perder un 200 recibe también
     este 409 (la primera ya se aplicó): tratadlo releyendo el sobre, no como un fallo.
   - 409 `EXPIRY_BEYOND_LIMIT`: más de 180 días después del envío.
   - 422: fecha malformada o vacía.
   - ⚠ El enlace de firma vive siete días desde su invitación, sea cual sea la vida del sobre: un firmante con el
     enlace caducado necesita un reenvío para actuar en el tiempo añadido.
4. **`ProblemCode` nuevos**: `ENVELOPE_EXPIRED`, `EXPIRY_NOT_FORWARD`, `EXPIRY_BEYOND_LIMIT`.
   `ENVELOPE_EXPIRED` sale también en el 409 de **anular** (`/void`), **corregir destinatario**
   (`/recipients/{id}/corrections`), **reenviar** (`/recipients/{id}/resends`) y **reclamar** (`/recipients/{id}/claim`):
   rutas del emisor pasada la fecha, hasta que el barrido cierra el sobre (en torno a un minuto). Es un
   "léelo de nuevo", no un "reintenta".
5. **El `status` pierde `EXPIRED`.** Un sobre caducado se lee `status: COMPLETED`, `outcome: NOT_AGREED`,
   `end_cause: EXPIRED` y `ended_by: null` (ninguna parte lo decidió), o `outcome: AGREED` si su acuerdo ya estaba
   asegurado. Los miembros sin firmar quedan `RELEASED` con `released_by: EXPIRY`.
   `COMPLETED` solo no significa acordado: leed `outcome`.
6. **Evento nuevo `ENVELOPE_EXPIRY_EXTENDED`** (cada prórroga es un hecho registrado). **No se entrega a
   integradores como webhook**: su efecto os llega por `expires_at` y, con el tiempo, por el fin del sobre.
7. ⚠ **Consecuencia operativa al desplegar.** Todo sobre enviado y aún abierto cuya antigua fecha (anclada a la
   creación + 30 días) ya haya pasado **lo caduca el barrido en su primera pasada, en menos de un minuto**. Esos
   sobres terminan `NOT_AGREED` / `EXPIRED` (o `AGREED`) y, por el aviso de fin sin acuerdo (TASK-040), sus
   destinatarios ya invitados reciben email. Revisad antes qué sobres abiertos tenéis con más de 30 días.

## Qué tiene que hacer el dashboard-sf

1. **Tratar `EXPIRED` como final: quitarlo del enum de `status`** y derivar "caducada" de
   `outcome` / `end_cause`. Cualquier `match`/`switch` o mapa de estados que lo nombre hay que reescribirlo.
2. **Mostrar la caducidad como fin sin acuerdo** (`end_cause: EXPIRED`, sin actor), distinta de la anulación del
   emisor. Y tratar `RELEASED` + `released_by: EXPIRY` como "no llegó a firmar".
3. **`expires_at` nulo en borrador**: no pintar fecha ni cuenta atrás hasta que el sobre se envía.
4. **Decidir si exponéis `expires_in_days`** al crear la carta de porte (por defecto 30, como hoy; no hace falta
   enviarlo). Si lo hacéis, validad 1 a 180 y avisad de que cuenta desde el envío.
5. **Opcional, decisión de producto: acción "Prorrogar"** sobre `expiry-extensions`, enviando una fecha absoluta.
   Manejar los cinco 409 por `code` y el 422. Un `ENVELOPE_EXPIRED` en anular/reenviar/corregir/reclamar se resuelve
   releyendo el sobre, no reintentando.
6. **`F5SignApiGateway`**: añadir `ENVELOPE_EXPIRED`, `EXPIRY_NOT_FORWARD` y `EXPIRY_BEYOND_LIMIT` al mapeo de
   errores si clasificáis por código.
7. **Avisar a operaciones del punto 7 de arriba** antes del despliegue.

Nada de esto rompe una creación que no envíe `expires_in_days`: el campo es opcional. Lo que rompe es el enum de
`status` si lo cerráis con `EXPIRED`, y la sorpresa de la primera pasada del barrido.
