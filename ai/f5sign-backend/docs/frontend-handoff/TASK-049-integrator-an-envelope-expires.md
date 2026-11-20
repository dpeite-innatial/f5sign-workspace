# Traspaso al integrador — un sobre caduca en la fecha que eligió el emisor, y se puede prorrogar

| | |
|---|---|
| **Origen** | rama `feat/task-048-how-an-envelope-ends` (paquete [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md)) · TASK-049 cerrada en `67626bce` · sin mergear en `develop` |
| **Fecha** | 2026-09-29 |
| **Repos afectados** | `dashboard-sf` (integración de Factor5) y cualquier consumidor de `/api/v1/**`. El signer tiene su propio traspaso: [TASK-049-signer-an-envelope-expires.md](TASK-049-signer-an-envelope-expires.md) |
| **Naturaleza** | **aditivo** en la creación y la lectura del sobre, más una ruta nueva; **rompe un enum**: `EnvelopeStatus` pierde `EXPIRED` |
| **Acción requerida** | quitar `EXPIRED` del enum de `status` y derivar la caducidad de `outcome`/`end_cause`; no pintar `expires_at` en un borrador; avisar a operaciones de la primera pasada del barrido (punto 7) |
| **Desplegado** | no — sin mergear en `develop` ni servido por ningún entorno (regla 4 del README) |
| **Status** | Pending. Sustituye al traspaso provisional que circuló contra mocks el 2026-09-29; los nombres de abajo están re-verificados contra el código de esta rama |

## Lo que cambió en el contrato

Las formas exactas están en el `doc.json` que sirve la rama; aquí solo qué cambió.

1. **`POST /api/v1/envelopes` acepta `expires_in_days`**: opcional, entero de 1 a 180, por defecto 30; fuera de
   rango responde 422. Es la vida del sobre **contada desde el envío**, no desde la creación.
2. **`GET /api/v1/envelopes/{id}`**:
   - `expires_at` es **`null` mientras el sobre es `DRAFT`**; el envío lo resuelve como `sent_at + expires_in_days`.
     Antes era creación + 30 días. No mostréis fecha para un borrador.
   - Campo nuevo **`expires_in_days`**, siempre presente: la vida elegida al crear. Una prórroga mueve
     `expires_at` y no lo toca.
3. **Ruta nueva `POST /api/v1/envelopes/{id}/expiry-extensions`**, cuerpo `{"expires_at": "<RFC 3339>"}` (fecha
   **absoluta**, no días a sumar). Éxito: 200 `{"expires_at": "…"}`. Repetible, siempre hacia delante, hasta 180 días
   después del envío. Rechazos, todos 409 con `code` salvo el último:
   - `ENVELOPE_NOT_SENT`: es un borrador; su vida son los días de `expires_in_days`, no hay nada que prorrogar.
   - `ENVELOPE_NO_LONGER_LIVE`: el sobre ya cerró.
   - `ENVELOPE_EXPIRED`: la fecha ya pasó; el barrido lo cierra en torno a un minuto y nada lo mueve antes.
   - `EXPIRY_NOT_FORWARD`: la fecha pedida no es posterior a la actual. ⚠ Un reintento tras perder el 200 recibe
     también este 409 (la primera ya se aplicó y nada se aplica dos veces): releed `expires_at` del sobre para
     distinguirlos.
   - `EXPIRY_BEYOND_LIMIT`: más de 180 días después del envío.
   - 422: fecha malformada o vacía. Y 503 `ENVELOPE_BUSY` como en cualquier escritura del sobre.
   - ⚠ El enlace de firma vive siete días desde su invitación, sea cual sea la vida del sobre: un firmante con el
     enlace caducado necesita un reenvío (`…/resends`) para actuar en el tiempo añadido.
4. **`ProblemCode` nuevos**: `ENVELOPE_EXPIRED`, `EXPIRY_NOT_FORWARD`, `EXPIRY_BEYOND_LIMIT`. `ENVELOPE_EXPIRED`
   sale también en el 409 de **anular** (`/void`), **corregir destinatario** (`/recipients/{id}/corrections`),
   **reenviar** (`/recipients/{id}/resends`) y **reclamar** (`/recipients/{id}/claim`): rutas del emisor usadas
   pasada la fecha y antes de que el barrido cierre el sobre. Es un «léelo de nuevo», no un «reintenta».
5. **`EnvelopeStatus` pierde `EXPIRED`.** Un sobre caducado se lee `status: COMPLETED`, `outcome: NOT_AGREED`,
   `end_cause: EXPIRED` y `ended_by: null` (ninguna parte lo decidió), o `outcome: AGREED` si su acuerdo ya estaba
   asegurado. Los miembros sin firmar quedan `RELEASED` con `released_by: EXPIRY`. `COMPLETED` solo no significa
   acordado: leed `outcome`.
6. **Evento nuevo `ENVELOPE_EXPIRY_EXTENDED`** (cada prórroga se registra). **No se entrega como webhook**: no
   existe emisor de webhooks en este backend; el efecto os llega por `expires_at` y, con el tiempo, por el fin del sobre.
7. ⚠ **Consecuencia operativa al desplegar.** Todo sobre enviado y aún abierto cuya antigua fecha (creación + 30
   días) ya haya pasado **lo caduca el barrido en su primera pasada, en menos de un minuto**. Terminan `NOT_AGREED` /
   `EXPIRED` (o `AGREED`) y, por el aviso de fin sin acuerdo ([TASK-040](TASK-040-integrator-ending-notice.md)), sus
   destinatarios ya invitados reciben un correo. Revisad antes qué sobres abiertos tenéis con más de 30 días.

## Lo que el frontal tiene que hacer

1. **Quitar `EXPIRED` del enum de `status`** y derivar «caducada» de `outcome`/`end_cause`. Cualquier
   `match`/`switch` o mapa de estados que lo nombre hay que reescribirlo.
2. **Mostrar la caducidad como fin sin acuerdo** (`end_cause: EXPIRED`, sin actor), distinta de la anulación del
   emisor, y tratar `RELEASED` + `released_by: EXPIRY` como «no llegó a firmar».
3. **`expires_at` nulo en borrador**: ni fecha ni cuenta atrás hasta que el sobre se envía.
4. **`F5SignApiGateway`**: añadir `ENVELOPE_EXPIRED`, `EXPIRY_NOT_FORWARD` y `EXPIRY_BEYOND_LIMIT` al mapeo de
   errores si clasificáis por código. Un `ENVELOPE_EXPIRED` en anular/reenviar/corregir/reclamar se resuelve
   releyendo el sobre.
5. **Avisar a operaciones del punto 7** antes del despliegue.

Nada de esto rompe una creación que no envíe `expires_in_days`. Lo que rompe es el enum de `status` si lo cerráis
con `EXPIRED`, y la sorpresa de la primera pasada del barrido.

## Decisiones del mantenedor para `dashboard-sf`

- **No expondrá `expires_in_days`** al crear la carta de porte: se queda el 30 por defecto, como hoy.
- **No habrá acción «Prorrogar» por ahora.** La ruta existe y está publicada, pero `dashboard-sf` no la consume;
  si se retoma, es decisión de producto nueva.

Consecuencia: para `dashboard-sf` los puntos 1 a 5 de arriba son todo el trabajo, y la ruta `expiry-extensions`
queda sin cliente por su parte. Otros integradores sí pueden usarla.

## Lo que NO está listo todavía

- Nada de este traspaso está desplegado ni en `develop`; comprobad el `doc.json` de vuestro entorno antes de
  construir (regla 4).
- **Caducar por política de paso** (`STEP_DEADLINE_MISSED` y compañía) es de TASK-050 y tiene su propio traspaso.

## Lo que NO existirá, y por qué

- **Webhook de la prórroga**: el backend no tiene emisor de webhooks y este cambio no lo crea; los integradores
  leen `expires_at`.

## Cómo verificarlo desde el frontal

- Crear un sobre sin `expires_in_days`: `GET` devuelve `expires_in_days: 30` y `expires_at: null`; tras enviarlo,
  `expires_at` es el envío más 30 días.
- Con `expires_in_days: 0` o `181`: 422.
- `POST …/expiry-extensions` sobre un borrador: 409 `ENVELOPE_NOT_SENT`; con una fecha anterior a la actual:
  409 `EXPIRY_NOT_FORWARD`.
- Un sobre caducado: `status: COMPLETED`, `end_cause: EXPIRED`, `ended_by: null`.
