# Traspaso al integrador — la política de paso al crear pasos, los plazos de paso, cuatro rechazos nuevos al enviar, y cerrar ya un sobre con acuerdo asegurado

| | |
|---|---|
| **Origen** | paquete [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md), TASK-050, en la rama `feat/task-048-how-an-envelope-ends` en `f48b14e2` (merge de `feat/step-policy`). Commits: política del paso `a3a524b2` y `b4fce49f`; cerrar ya `6717d021`, `859b36ce` y la ruta `dceeaeb7`; plazos de paso `3be2c390` (plazo guardado al activar, barrido) y `5b5212e7` (motivos juzgados en el instante del reloj, `STEP_DEADLINE_PASSED`); aviso de fin (F) `c8e404c4`. Aún no en `develop` |
| **Fecha** | 2026-09-29 |
| **Repos afectados** | `dashboard-sf` (integración de Factor5) y cualquier consumidor de `/api/v1/**`. El signer tiene el suyo: [TASK-050-signer-step-policy-and-what-a-recipient-reads.md](TASK-050-signer-step-policy-and-what-a-recipient-reads.md) |
| **Naturaleza** | **aditivo** en `POST /steps`, en la lectura del paso y en `send`; ruta nueva `POST /envelopes/{id}/close`; código nuevo `STEP_DEADLINE_PASSED` en `/void` y `/close`; **cambia el significado de `ended_by`**, que ya no implica anulación |
| **Acción requerida** | ninguna obligatoria para los flujos de hoy. No leer `ended_by` como «anulado»; mapear los códigos nuevos si se clasifica por código |
| **Desplegado** | no — solo en la rama del paquete, ni en `develop` ni servido por ningún entorno (regla 4 del README) |
| **Status** | Pending. Sustituye a los traspasos provisionales 34 (etapa C) y 50 (etapa D) que circularon contra mocks el 2026-09-29; todo lo de abajo está re-verificado contra el árbol en `f48b14e2` |

## Lo que cambió en el contrato

Las formas exactas están en el `doc.json` que sirve el árbol; aquí solo qué cambió.

### C. Política del paso

1. **`POST /api/v1/envelopes/{id}/steps`** acepta la política del paso. Todo es aditivo:
   - `ordinal`: entero ≥ 1, obligatorio, como hoy.
   - `completion`: `"ALL"` | `"AT_LEAST"`, por defecto `"ALL"`.
   - `min_signatures`: entero ≥ 1 o `null`. Obligatorio con `AT_LEAST`, rechazado con `ALL`.
   - `veto`: booleano, por defecto `false`. Solo con `AT_LEAST`; con `ALL` se rechaza.
   - `deadline_hours`: entero ≥ 24 o `null`, contado **desde la activación del paso**, no desde ahora.
   - Una política mal formada es 422 `VALIDATION_ERROR` que nombra el campo.
   - Reenviar el mismo `ordinal` con la misma política devuelve 201; con otra política, 409 `CONFLICT`.
   - Vuestra llamada de hoy, `{"ordinal": N}`, significa exactamente lo que significaba: `ALL`, sin veto, sin plazo.
2. **Avisos documentados en esa ruta** (ambas configuraciones se aceptan): un paso `AT_LEAST` sin plazo espera a
   **todos** sus miembros, así que uno que no sea el último debería llevarlo; un paso con veto y sin plazo solo se
   resuelve al vencer el sobre, y hasta entonces cerrar ya se rechaza.
3. **La unanimidad tiene una sola codificación:** `AT_LEAST n` con `n` igual o mayor que los miembros bloqueantes del
   paso (SIGNER/APPROVER) se rechaza al enviar. Usad `ALL`.
4. **`GET /api/v1/envelopes/{id}`**: cada elemento de `steps[]` gana `completion`, `veto`, `deadline_hours` y
   `deadline_at` (`activated_at` más las horas; `null` antes de la activación o sin plazo). `min_signatures` pasa a
   publicarse como nullable (siempre fue `null` con `ALL`; el esquema anterior decía entero, y era incorrecto).
5. **`POST /api/v1/envelopes/{id}/send`** gana cuatro 422 con `ProblemCode` propio. Si aplican varios, `code` es el
   primero y `detail` los nombra todos:
   - `STEP_MINIMUM_NOT_BELOW_MEMBERS`: el `detail` indica enviar `completion: ALL`.
   - `STEP_MIXES_BLOCKING_ROLES`: un paso `AT_LEAST` con SIGNER y APPROVER a la vez (partid el paso en dos; los
     informativos a su lado no molestan).
   - `ENVELOPE_HAS_NO_BLOCKING_MEMBER`: ningún SIGNER/APPROVER en todo el sobre.
   - `RECIPIENT_ROLE_NOT_BUILT`: hay un destinatario `IN_PERSON_HOST` o `CERTIFIED_DELIVERY`.
6. **Reclamar una plaza** (`POST /envelopes/{id}/recipients/{recipientId}/claim`) pasado el plazo de su paso devuelve
   409 `RECIPIENT_CAN_NO_LONGER_ACT` (código que ya existía; se juzga en el instante de la llamada, aunque el paso aún
   no se haya cerrado).
7. El evento `EnvelopeRosterDeclared` gana `veto` y `deadline_hours` en sus pasos. Solo afecta a quien consuma
   eventos; no hay emisor de webhooks.

### D. Cerrar ya (`POST /api/v1/envelopes/{id}/close`)

1. **Primero, `ended_by` con valor ya no significa «anulado».** Hasta ahora solo lo tenía un sobre anulado por el
   emisor (`outcome: NOT_AGREED`, `end_cause: SENDER_VOIDED`). Ahora también lo tiene uno que el emisor cerró con
   acuerdo (`outcome: AGREED`, `end_cause: null`). **Para saber cómo terminó, leed `outcome`, nunca `ended_by` solo.**
   `closed_at` también puede llegar antes: se fija cuando el emisor cierra, no solo cuando se cierra el último paso.
2. **Ruta nueva**, `POST`, con la clave de máquina y la cabecera `DeclaredSubject`, sin cuerpo, como `/void`. Cierra
   un sobre **cuyo acuerdo ya está asegurado** (`agreed_at` con valor) sin esperar a los que faltan.
   - **204:** cerrado con `outcome: AGREED`. Cada destinatario pendiente pasa a `RELEASED` con
     `released_by: SENDER_CLOSED`. `status` sigue en `SENT` hasta que aterrizan las firmas ya admitidas y luego pasa
     a `COMPLETED`. Repetir la llamada da otro 204 y no cambia nada.
   - **409, ramificad sobre `code`.** Si aplican varios, el backend nombra el primero de este orden:
     1. `ENVELOPE_NO_LONGER_LIVE`: el sobre ya terminó de otra forma; haced `GET` para ver cómo.
     2. `ENVELOPE_EXPIRED`: su `expires_at` ha pasado y desde ese instante solo lo cierra su caducidad, en un
        minuto. No reintentéis: volved a leerlo.
     3. `STEP_DEADLINE_PASSED` (`ProblemCode` nuevo): ha vencido el plazo del paso abierto y el barrido aún no lo ha
        cerrado. **Reintentad pasado un minuto** (detalle en *Plazos*). Se nombra antes que el siguiente porque el
        barrido todavía puede asegurar el acuerdo.
     4. `ENVELOPE_AGREEMENT_NOT_SECURED` (`ProblemCode` nuevo): el acuerdo aún no está asegurado. Esperad a
        `agreed_at`, o anulad. Un paso con veto solo se asegura al cerrarse, así que no se puede cerrar antes.
     - `CONFLICT` (sin código propio) en un borrador: se descarta, no se cierra.
   - 404 y 503 `ENVELOPE_BUSY`, como en `/void`.
3. **Solo hay ventana para el 204 con un paso `AT_LEAST`.** Con pasos `ALL`, el acuerdo solo se asegura cuando firma
   el último bloqueante, y en ese momento el sobre ya se cierra solo. `CloseEnvelopeNowHttpTest` fija el 204 con un
   paso `AT_LEAST 1` de tres firmantes: firma uno, el emisor cierra y los otros dos quedan `RELEASED` ·
   `SENDER_CLOSED` · `SENT_NO_RESPONSE`.
4. **Evento `EnvelopeClosedBySender`**: interno, **no se entrega como webhook**. El final os llega como cualquier otro,
   como una terminación con `outcome: AGREED`.

### `STEP_DEADLINE_PASSED` también en `POST /api/v1/envelopes/{id}/void`

`/void` gana el mismo 409 `STEP_DEADLINE_PASSED`, con la misma causa y el mismo remedio. En `/void`, un acuerdo ya
asegurado se nombra antes que nada (`ENVELOPE_REACHED_AGREEMENT`, como hasta ahora); si no lo está y han vencido a
la vez la caducidad y el plazo del paso, se nombra `ENVELOPE_EXPIRED`. Texto publicado de este código, idéntico en
las dos rutas:

> `STEP_DEADLINE_PASSED` — the open step's deadline has passed and the scheduled sweep has not closed it yet (it
> runs every minute). The envelope cannot be voided or closed in that window, because the sweep decides how the
> step ended (ADR-0073 §2.12). Retry after a minute. The envelope will then either have ended, or have moved on to
> a later step.

### F. Qué cambia en los avisos por correo

- `ENVELOPE_COMPLETED` («firmado») solo se manda ya a los **firmantes de un sobre `AGREED`**, nunca a quien rechazó ni a
  quien fue liberado, y su texto ya no dice «firmado por todos». Un sobre que termina sin acuerdo no lo manda.
- Los miembros informativos reciben `SEALED_COPY_READY` con un enlace nuevo (detalle en el traspaso del signer). ⚑ Desde TASK-071 (2026-10-26, sin desplegar) el enlace es el de copia de solo lectura, no uno de firma, y el aviso alcanza también a los delegados. No
  hay nada que hacer por vuestra parte: no mandéis un aviso propio.

## Plazos

Construido en este árbol. Qué ocurre cuando vence el plazo de un paso:

1. **El instante.** `deadline_hours` se autoriza en el paso; al activarse el paso se guarda `deadline_at`
   (`activated_at` + horas) y se publica en `steps[].deadline_at`. Es un instante fijo: nada lo recalcula después.
2. **El barrido.** Un comando programado (`app:envelope:sweep-clocks`, `SweepEnvelopeClocksCommand`, con el
   calendario `EnvelopeClockSchedule`) corre **cada minuto** y busca los sobres con un paso abierto cuyo
   `deadline_at` ha pasado según el reloj de la base de datos. Es el mismo barrido que cierra la caducidad de
   TASK-049: primero cierra el plazo de paso vencido y después la caducidad. Lo consume el worker ordinario (no el
   custodio), por el transporte `scheduler_envelope_clocks`. Correr dos veces no registra nada nuevo.
3. **Qué hace con el paso.** Libera a los miembros **bloqueantes** que siguen pendientes, cada uno `RELEASED` con
   `released_by: STEP_DEADLINE`. Los informativos no se liberan ahí: siguen abiertos hasta que se cierra el sobre.
   Después juzga el paso con su política:
   - `ALL` con alguien liberado: el sobre termina `NOT_AGREED`, `end_cause: STEP_DEADLINE_MISSED`.
   - `AT_LEAST n` con veto y algún liberado que la plataforma nunca alcanzó (`release_reason` `DELIVERY_FAILED`,
     `UNCLAIMED` o `NOT_REACHED`; ⛑ 2026-10-09: también `NO_REACHABLE_CHANNEL` e `INTEGRATOR_DELIVERED_NOT_OPENED`;
     ver el traspaso de TASK-056): `NOT_AGREED`, `end_cause: MEMBER_NOT_REACHED`.
   - `AT_LEAST n` con menos de `n` firmas: `NOT_AGREED`, `end_cause: STEP_DEADLINE_MISSED`.
   - `AT_LEAST n` con `n` firmas o más: el paso se cierra con acuerdo; se activa el siguiente, o, si era el último
     paso, el sobre termina `AGREED`.
4. **Quién más queda liberado.** Si el sobre termina en ese momento, todo miembro que siga abierto (pasos
   posteriores, informativos) queda `RELEASED` con `released_by: ENVELOPE_CLOSED`, como en cualquier otro final.
5. **`release_reason` se juzga en el instante del reloj, no en el del barrido.** Para los liberados por el plazo,
   los motivos son los que valían en `deadline_at` (y, para la caducidad, en `expires_at`), por tarde que corra el
   barrido: el mismo sobre da los mismos motivos siempre. Por ejemplo, un enlace que caduca entre el plazo y el
   barrido deja al miembro en `SENT_NO_RESPONSE`, no `LINK_EXPIRED`; y una apertura registrada después del plazo no
   cuenta como `OPENED_NO_ACT`. Los liberados por el cierre que resulta (`ENVELOPE_CLOSED`) se juzgan en el
   instante en que ocurre.
6. **El hueco entre el plazo y el barrido** (como mucho, un minuto si el barrido corre a su hora):
   - `/void` y `/close` responden 409 `STEP_DEADLINE_PASSED` (ver arriba): quién llegue primero no decide cómo
     terminó el paso.
   - Una firma o un rechazo del destinatario de ese paso se rechaza como 409 `LEG_CLOSED` (también la firma
     delegada, `POST …/recipients/{recipientId}/signature`); no se registra nada.
   - Reclamar una plaza de ese paso: 409 `RECIPIENT_CAN_NO_LONGER_ACT` (sección C, punto 6).

Lo fijan, sobre HTTP con el reloj de la base de datos fijado y el barrido real, `StepDeadlineBarsDeHttpTest` (un
consignatario callado liberado `SENT_NO_RESPONSE` · `STEP_DEADLINE` con el sobre abierto y el paso siguiente
activado; y una plaza sin reclamar liberada `UNCLAIMED` · `STEP_DEADLINE`, con `STEP_DEADLINE_MISSED` y el cerrador
`NOT_REACHED` · `ENVELOPE_CLOSED`) y `StepDeadlineBarsGhHttpTest` (un `AT_LEAST 1` último que termina `AGREED`
liberando al callado en el plazo, también con el barrido tarde; y una junta `AT_LEAST 3` con veto que termina
`MEMBER_NOT_REACHED`). `STEP_DEADLINE_PASSED` en `/void` y `/close` está fijado en tests de dominio y de caso de uso
(`EnvelopeStepDeadlineTest`, `StepDeadlineGapTest`, `VoidEnvelopeUseCaseTest`, `CloseEnvelopeNowUseCaseTest`),
**no sobre HTTP**.

## Lo que el frontal tiene que hacer

Nada obligatorio para los flujos de hoy. Recomendado:

1. **No leer `ended_by` como «anulado».** Si algún día lo leéis, hacedlo junto a `outcome`. En el árbol medido
   `F5SignApiGateway` no lo menciona, así que hoy no se rompe nada.
2. **`F5SignErrorMessages.php`**: mapear, si clasificáis por código, los cuatro 422 nuevos de `send` (al menos
   `RECIPIENT_ROLE_NOT_BUILT` y `ENVELOPE_HAS_NO_BLOCKING_MEMBER`); `STEP_DEADLINE_PASSED` en `void` («reintentad en
   un minuto», solo alcanzable con pasos con plazo); y, si adoptáis cerrar ya, `ENVELOPE_AGREEMENT_NOT_SECURED`
   («todavía no se puede cerrar»), `ENVELOPE_NO_LONGER_LIVE` («ya terminó, refrescad») y `ENVELOPE_EXPIRED`.
   `RECIPIENT_CAN_NO_LONGER_ACT` ya tiene mensaje.
3. Si adoptáis cerrar ya: un método `close(string $envelopeId): void` en `F5SignApiGateway`, junto a `void()`; y para
   decidir si ofrecer el botón, `agreed_at` con valor y `closed_at` vacío.
4. Si algún día autoráis plazos: mostrad `steps[].deadline_at` (no lo calculéis vosotros) y leed `released_by` y
   `end_cause` para explicar el final.

## Decisiones del mantenedor para `dashboard-sf`

- **El paso de los destinatarios es `AT_LEAST 1` con un plazo de 72 horas** (decisión del mantenedor, 2026-09-30):
  `{"ordinal": N, "completion": "AT_LEAST", "min_signatures": 1, "deadline_hours": 72}`. ⚠ **Solo con dos
  destinatarios o más.** Con un único destinatario, `AT_LEAST 1` es unanimidad y `send` lo rechaza con 422
  `STEP_MINIMUM_NOT_BELOW_MEMBERS` (el mínimo tiene que quedar por debajo de los miembros bloqueantes del paso); ese
  paso se autoriza `{"ordinal": N, "completion": "ALL", "deadline_hours": 72}`. Los pasos del cargador y del
  transportista siguen `ALL`, y todos los destinatarios siguen siendo `SIGNER`. Antes de esa decisión autorizaba todos
  los pasos como `ALL`, así que el rechazo de un destinatario terminaba el sobre para todos (lo vio el mantenedor en
  local, sobre `01a0f2cf-fcd3-74bb-b23e-d44e2bfe87b8`). Con `AT_LEAST 1` dejan de ser inalcanzables
  `STEP_DEADLINE_PASSED` (anular entre el plazo y el barrido) y, en cuanto firma el primer destinatario,
  `ENVELOPE_REACHED_AGREEMENT` al anular. De los cuatro 422 nuevos de `send`, `STEP_MINIMUM_NOT_BELOW_MEMBERS` solo es
  inalcanzable si el paso de un único destinatario se autoriza `ALL` (arriba); los otros tres siguen inalcanzables: no
  hay destinatarios que no firmen.
- **No habrá un botón «Cerrar ya»**, aunque el acuerdo ya puede asegurarse antes de que firmen todos (con la primera
  firma de un destinatario). El sobre acuerda y sigue abierto hasta el plazo del paso, que es cuando se cierra solo.
- **«Anular carta de porte» usa `/close` cuando ya hay acuerdo** (decisión del mantenedor, 2026-09-30). La regla del
  backend no cambia: con el acuerdo asegurado, `/void` responde `ENVELOPE_REACHED_AGREEMENT`, y es lo correcto para
  otros dominios. En la carta de porte, el acuerdo de `AT_LEAST 1` es la herramienta que da independencia a los
  destinatarios, no un acuerdo de todas las partes, así que anular sigue siendo legítimo:
  - sin acuerdo (`agreed_at` nulo): `POST /void`, que termina `NOT_AGREED` / `SENDER_VOIDED`;
  - con acuerdo y el sobre abierto: `POST /close` y la anulación de la carta en el dashboard. El sobre termina `AGREED`,
    los destinatarios pendientes quedan `RELEASED` con `released_by: SENDER_CLOSED` y dejan de poder firmar;
  - con la firma terminada: solo la anulación en el dashboard, como antes.

  «Cancelar firma» se oculta en cuanto hay acuerdo. Así la plataforma y el registro de auditoría dicen quién firmó y
  que el remitente cerró el resto, y el dashboard dice que la carta está anulada: las dos cosas son ciertas.

## Lo que NO está listo todavía

- Está en `develop` desde 2026-09-30, pero no desplegado; comprobad el `doc.json` de vuestro entorno (regla 4).
- ⚠ Sin el transporte `scheduler_envelope_clocks` en el worker del despliegue, ni los plazos de paso ni la caducidad
  se cierran nunca, y `/void` y `/close` responderían `STEP_DEADLINE_PASSED` / `ENVELOPE_EXPIRED` indefinidamente
  pasado el instante. Es configuración de `f5sign-infra`, no de este repo: su `docker-compose.yml` ya lo consume en
  el worker (visto en el checkout principal de infra el 2026-09-29, el mismo transporte que usa la caducidad de
  TASK-049); lo que no se ha comprobado es la configuración de ningún entorno desplegado.

## Lo que NO existirá, y por qué

- **Webhook de `EnvelopeClosedBySender`**: el backend no tiene emisor de webhooks y este evento está expresamente
  excluido del censo; el integrador lee `outcome`, `closed_at` y `ended_by`.
- **Una segunda codificación de la unanimidad** (`AT_LEAST n` con `n` = todos): se rechaza al enviar para que un
  paso se lea de una sola manera.
- **Anular o cerrar ya en el minuto entre el plazo y el barrido**: se rechaza con `STEP_DEADLINE_PASSED` a propósito,
  para que el mismo sobre termine igual lo pida quien lo pida en ese minuto (ADR-0073 §2.12).

## Cómo verificarlo desde el frontal

- Crear un paso con `{"ordinal": 1}`: la lectura devuelve `completion: ALL`, `min_signatures: null`, `veto: false`,
  `deadline_hours: null`, `deadline_at: null`.
- `completion: AT_LEAST` sin `min_signatures`, o `completion: ALL` con `veto: true`: 422 `VALIDATION_ERROR`.
- Enviar un sobre con un `AT_LEAST` cuyo `n` iguala a los firmantes: 422 `STEP_MINIMUM_NOT_BELOW_MEMBERS`.
- Un paso con `deadline_hours: 48`: tras activarse, `deadline_at` = `activated_at` + 48 h.
- `POST …/close` sobre un sobre sin acuerdo asegurado: 409 `ENVELOPE_AGREEMENT_NOT_SECURED`; sobre uno ya anulado:
  409 `ENVELOPE_NO_LONGER_LIVE`; sobre un borrador: 409 `CONFLICT`; sobre un `AT_LEAST 1` con una firma: 204, y los
  pendientes `RELEASED` · `SENDER_CLOSED`.
