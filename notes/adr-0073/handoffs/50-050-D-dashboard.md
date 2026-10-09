# Traspaso al integrador (PROVISIONAL): cerrar ya un sobre cuyo acuerdo está asegurado

| | |
|---|---|
| **Origen** | TASK-050 §3.5 (ADR-0073 §2.2, §2.11), etapa D (close-now) |
| **Medido en** | `f5sign-backend` rama `feat/close-now` @ `da3d3071` (2026-09-29), sin mergear en `develop` ni desplegar; `dashboard-sf` rama `feat/waybill-pdf-pagination` @ `a4d8637ac` (2026-09-23) |
| **Repos afectados** | `dashboard-sf` (integración de Factor5). El signer no se ve afectado: no cambia ninguna ruta de firma ni nada que lea |
| **Status** | **PROVISIONAL, accionable contra mocks.** El traspaso oficial llegará en `f5sign-backend/docs/frontend-handoff/` cuando aterrice el paquete ADR-0073 |

## 1. Primero: `ended_by` con valor ya no significa "anulado"

- Hasta ahora `ended_by` solo tenía valor en un sobre anulado por el emisor (`outcome: NOT_AGREED`,
  `end_cause: SENDER_VOIDED`). **Ahora también lo tiene un sobre que el emisor cerró con acuerdo**
  (`outcome: AGREED`, `end_cause: null`).
- Para saber cómo terminó un sobre, leed **`outcome`**, nunca `ended_by` solo. El spec ya lo dice en la
  descripción de `ended_by`.
- En el árbol medido **no leéis `ended_by`** (`F5SignApiGateway` no lo menciona), así que hoy no se rompe nada.
  El aviso es para que no nazca una lectura "`ended_by` ≠ null ⇒ anulado".
- `closed_at` también puede llegar antes: se fija cuando el emisor cierra, no solo cuando se cierra el último
  paso.

## 2. Qué se añadió (commiteado)

- **`POST /api/v1/envelopes/{id}/close`.** Sin cuerpo, con la clave de máquina y la cabecera
  `DeclaredSubject`, igual que `/void`. Cierra un sobre **cuyo acuerdo ya está asegurado** (`agreed_at` con
  valor) sin esperar a los que faltan.
  - **204:** el sobre queda cerrado con `outcome: AGREED`. Cada destinatario pendiente pasa a `RELEASED` con
    `released_by: SENDER_CLOSED` y su `release_reason`. `status` sigue en `SENT` hasta que aterrizan las
    firmas ya admitidas, y luego pasa a `COMPLETED`. Repetir la llamada da otro 204 y no cambia nada.
  - **409 `ENVELOPE_AGREEMENT_NOT_SECURED`** (código nuevo): el acuerdo aún no está asegurado. Esperad a
    `agreed_at` y cerrad entonces, o anulad. Un paso con veto solo se asegura al cerrarse, así que no se
    puede cerrar antes.
  - **409 `ENVELOPE_NO_LONGER_LIVE`** (código ya publicado): el sobre ya terminó de otra forma. Haced
    `GET` para ver cómo.
  - **409 `CONFLICT`** en un borrador. **404** y **503 `ENVELOPE_BUSY`**, como en `/void`.
- **Evento `EnvelopeClosedBySender`**, interno. **No se publica como webhook**: el final os llega igual que
  cualquier otro, como la terminación con `outcome: AGREED`.

## 3. Para qué os sirve (decisión vuestra)

En la carta de porte, el paso de destinatarios es `AT_LEAST 1`. En cuanto firma uno, el acuerdo queda
asegurado, pero el paso esperaría a los demás o a su plazo. Con `/close`, el operador puede darla por
cerrada en ese momento. Es opcional: si no lo usáis, nada cambia.

⚠ **Hoy no se puede probar de extremo a extremo.** Los pasos `AT_LEAST n` todavía no se crean por la API: eso
llega con otra etapa de TASK-050, que tendrá su propio traspaso. Sin ellos, un sobre solo se asegura cuando
firma el último firmante bloqueante, y entonces se cierra solo. Por eso, en la práctica, hoy solo veréis
los dos 409. Mockead el 204.

## 4. Si lo adoptáis

1. Un método `close(string $envelopeId): void` en `F5SignApiGateway`, junto a `void()`.
2. Mapear `ENVELOPE_AGREEMENT_NOT_SECURED` a "todavía no se puede cerrar" y `ENVELOPE_NO_LONGER_LIVE` a "ya
   terminó, refrescad".
3. Para decidir si ofrecer el botón, usad `agreed_at` con valor y `closed_at` vacío.
