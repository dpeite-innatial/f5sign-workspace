# Traspaso al signer — política de paso, roles que no firman, plazos de paso, y qué lee cada destinatario cuando el sobre termina

| | |
|---|---|
| **Origen** | paquete [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md), TASK-050 etapas A, B, E, F y plazos de paso, en la rama `feat/task-048-how-an-envelope-ends` en `f48b14e2` (merge de `feat/step-policy`) · commits `8f42995d` (A), `1cc5ef0e` (B), `480faab9`, `21dc9a4a` y `901fd813` (E: `envelope_outcome` en `/auth` y en el modelo de lectura), `c8e404c4` y `70593ec2` (F), `9d4531ae` (corte síncrono de las lecturas), `eb686c5f` (acto pasado el plazo → `LEG_CLOSED`), `fb875674` (apertura y paso de puerta rechazados bajo el bloqueo de fila), `70a0e89d` (nuevo texto de `ENVELOPE_NO_LONGER_LIVE`) · aún no en `develop` |
| **Fecha** | 2026-09-29 |
| **Repos afectados** | `f5sign-signer`. El integrador tiene el suyo: [TASK-050-integrator-step-policy-and-close-now.md](TASK-050-integrator-step-policy-and-close-now.md) |
| **Naturaleza** | un código retirado, un código nuevo, un campo nuevo en dos respuestas, `LEG_CLOSED` en más sitios, y **cambia el significado** de `outcome`/`REVOKED` en `/auth` y el texto de `ENVELOPE_NO_LONGER_LIVE` |
| **Acción requerida** | quitar `DECLINE_NOT_OFFERED_IN_QUORUM_STEP`; no ofrecer commit a los roles informativos y mapear `COMMIT_NOT_OFFERED_TO_ROLE`; enrutar por `outcome` y `envelope_outcome` a la vez; vista de solo lectura `/copy`; tratar `VIEWER` como `REVIEWER`; tratar `LEG_CLOSED` en la lectura y en el paso de puerta |
| **Desplegado** | no — solo en la rama del paquete, ni en `develop` ni servido por ningún entorno (regla 4 del README) |
| **Status** | Pending. Sustituye a los traspasos provisionales 30 a 33 que circularon contra mocks el 2026-09-29. **Según informa la sesión del signer, sin verlo en su árbol desde aquí** (worktree `f5sign-signer-adr0073`, rama local `feat/prep-adr-0073-envelope-ending`, 2026-09-29): A en `fd7c137`, B en `055898d`, E en `810275a`, la vista `/copy` en `01d752e`, y sus puntos 51 y 80 en `a8372ea` |

## Lo que cambió en el contrato

Las formas exactas están en el `doc.json` que sirve el árbol; aquí solo qué cambió.

### A. Un rechazo en un paso de quórum se acepta

- `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` **ya no existe**: sale del enum de `ProblemCode` y de la descripción del 409
  de `POST /api/v1/signing/decline`. Nadie lo emite.
- Rechazar dentro de un paso `AT_LEAST n` responde 200 igual que en un paso `ALL`. Lo que el rechazo hace al sobre
  lo decide el paso al admitirlo: sigue si el mínimo aún se alcanza, y el sobre termina sin acuerdo
  (`MINIMUM_UNREACHABLE`) si ya no; en un paso con veto, el rechazo lo termina (`RECIPIENT_VETOED`).
- `DECLINE_NOT_OFFERED_TO_ROLE` no cambia.
- Los pasos `AT_LEAST` ya se crean por la API (traspaso del integrador, etapa C), y `StepPolicyDeliveryBarHttpTest`
  los ejerce de extremo a extremo con rechazos dentro de un `AT_LEAST 1`.

### B. Los roles informativos no hacen commit

- Código nuevo **`COMMIT_NOT_OFFERED_TO_ROLE`** (409), de `POST /api/v1/signing/commit` y del commit delegado
  `POST /api/v1/envelopes/{id}/recipients/{recipientId}/signature`, cuando quien lo hace es `VIEWER`, `REVIEWER` o
  `EDITOR`. No se admite nada ni se registra ningún acto, y el mismo commit **nunca** tiene éxito.
- Un miembro informativo **ya no retiene su paso**: antes un `VIEWER` cerraba su participación haciendo commit y el
  paso le esperaba; ahora el paso avanza sin él, y uno formado solo por informativos se cierra al activarse. Al
  cerrar el sobre queda `RELEASED` con `released_by: ENVELOPE_CLOSED`.
- Con el sobre abierto, sigue pasando la puerta y leyendo el documento como antes.
- `GET /signing/session` publica `VIEWER` como **`REVIEWER`** en `signer.role` (el enum de ese campo es
  `SIGNER | APPROVER | REVIEWER | EDITOR`): el signer nunca ve el valor `VIEWER` ahí. Los otros dos roles sin
  ceremonia (`IN_PERSON_HOST`, `CERTIFIED_DELIVERY`) no llegan: 409 `ROLE_NOT_INTERACTIVE`.

### E. Qué le pasó a mi participación y cómo terminó el sobre

1. **`envelope_outcome`**, nuevo, en **`GET /api/v1/signing/session/auth`** y en **`GET /api/v1/signing/session`**
   (el modelo de lectura; `901fd813`): `AGREED | NOT_AGREED`, nullable, **la clave siempre está**. Es `null`
   mientras el sobre no ha cerrado (también cuando el acuerdo ya está asegurado pero el sobre sigue abierto); desde
   el cierre lleva valor. Las dos rutas lo leen de una sola regla (`RecipientEnvelopeContextView::publishedOutcome()`)
   y coinciden en cada fila de la tabla.
2. **`outcome` de `/auth`** (`COMPLETED | DECLINED | REVOKED | RELEASED`, nullable) nombra lo que le pasó a **esta
   participación**. Una sesión revocada cuya participación el sobre ya cerró responde con el nombre que el sobre da a
   la participación (`RELEASED` o `DECLINED`), **no `REVOKED`** (`SessionStatus::outcomeAtTheGate()`).
3. **`REVOKED` ya no significa «el sobre terminó sin acuerdo».** Según el docblock de
   `SessionStatus::outcomeAtTheGate()`, en `/auth` queda solo para una sesión revocada cuya participación el sobre no
   ha cerrado y para participaciones cerradas de formas que hoy nada escribe (`DELEGATED`, `SKIPPED`); ningún flujo
   de este árbol lleva ahí. En `POST /signing/session`, `status` muestra `REVOKED` solo para filas de sesión
   revocadas antes de este cambio; `GET /signing/session` nunca.
4. **Sesiones.** Al liberar a un miembro se revoca su sesión, de forma asíncrona, **salvo** que su puerta siga pasando
   (los informativos): esos la conservan, tanto al liberarse como con una anulación del emisor (`480faab9`).

**Cómo separar las situaciones solo con `/auth`:**

| `outcome` | `envelope_outcome` | Situación |
|---|---|---|
| `null` | `null` | participación abierta, sobre abierto: la ceremonia normal |
| `RELEASED` | `null` | participación cerrada sin actuar (un plazo de paso) y el sobre sigue: nada que hacer ni que leer |
| `null` | fijado | miembro informativo tras el cierre: mostrar la copia sellada |
| `RELEASED` | fijado | participación terminada, nada que leer |
| `COMPLETED` | fijado | ya firmaste |

**Tabla que fija el test de Acceptance** (`WhatEachRecipientReadsAfterTheCloseHttpTest`). Cada fila es un
destinatario que abre un **enlace nuevo** con el sobre ya `COMPLETED` y una copia sellada. Columnas: `outcome` y
`envelope_outcome` de `/auth`; el `status` de `POST /signing/session` (o su rechazo); el `status` de
`GET /signing/session` (o su rechazo; su `envelope_outcome` coincide con el de `/auth` en todas las filas); y qué
bytes sirve `GET /signing/session/documents/{id}`.

`AGREED` (un paso, un firmante que firma, un informativo de cada rol):

| Miembro | `outcome` | `envelope_outcome` | `POST` `status` | `GET` `status` | documento |
|---|---|---|---|---|---|
| SIGNER, firmó | `COMPLETED` | `AGREED` | `COMPLETED` | `COMPLETED` | sellado |
| VIEWER, REVIEWER, EDITOR (paso activado) | `null` | `AGREED` | `AUTH_PASSED` | `AUTH_PASSED` | sellado |

`NOT_AGREED` (el emisor anula tras la primera firma; el paso 2 no llegó a activarse):

| Miembro | `outcome` | `envelope_outcome` | `POST` `status` | `GET` `status` | documento |
|---|---|---|---|---|---|
| SIGNER, firmó | `COMPLETED` | `NOT_AGREED` | `COMPLETED` | `COMPLETED` | sellado |
| SIGNER liberado en silencio (había abierto) | `RELEASED` | `NOT_AGREED` | 409 `ENVELOPE_NO_LONGER_LIVE` | 409 `ENVELOPE_NO_LONGER_LIVE` | 404 `NOT_FOUND` |
| VIEWER, REVIEWER, EDITOR (paso activado) | `null` | `NOT_AGREED` | `AUTH_PASSED` | `AUTH_PASSED` | sellado |
| VIEWER, REVIEWER, EDITOR (paso nunca activado) | `null` | `NOT_AGREED` | `AUTH_PASSED` | `AUTH_PASSED` | sellado |
| VIEWER que abrió antes de la anulación | `null` | `NOT_AGREED` | `AUTH_PASSED` | `AUTH_PASSED` | sellado |

**Filas que ya pueden ocurrir y ese test no recorre.** Con cerrar ya y los plazos construidos, las dos filas que antes
eran inalcanzables existen; lo que está fijado de cada una, y a qué nivel:

| Fila | Cómo se llega | Qué está fijado | Sobre HTTP, en las rutas del signer |
|---|---|---|---|
| `AGREED` × SIGNER liberado en silencio | cerrar ya (`released_by: SENDER_CLOSED`, `CloseEnvelopeNowHttpTest`) o el plazo del último paso bloqueante (`STEP_DEADLINE`, `StepDeadlineBarsGhHttpTest`), ambos sobre HTTP **en la lectura del sobre del emisor** | `/auth` responde `RELEASED` + `AGREED` con o sin sesión, viva o revocada (`GetAuthDescriptorControllerTest`, nivel controlador); un SIGNER liberado nunca pasa la puerta (`ReleasedMemberReadsFollowTheRoleTest`, unitario) | **pendiente**: ningún test recorre `POST`/`GET /signing/session` ni los bytes para esta fila. Por la regla, lo esperado es lo mismo que la fila `NOT_AGREED` equivalente: 409 `ENVELOPE_NO_LONGER_LIVE`, 409 `ENVELOPE_NO_LONGER_LIVE`, 404 |
| `AGREED` × paso nunca activado | cerrar ya con un paso posterior sin activar (o la caducidad con el acuerdo ya asegurado) | los dos lectores sirven la copia sellada a un informativo de ese paso y la niegan a un bloqueante, para ambos desenlaces (`SigningReadersCannotDisagreeTest`, nivel aplicación) | **pendiente**: sin test HTTP |

⚠ Tras un cierre `NOT_AGREED` los informativos de un paso nunca activado **no reciben aviso** (punto F), así que
esa fila existe en el backend pero ningún enlace real lleva a ella. Tras un cierre `AGREED` sí lo reciben, así que
la fila `AGREED` × paso nunca activado **sí** tiene un enlace real: el de `SEALED_COPY_READY`.

### F. Aviso de «copia sellada lista» y lectura tras el cierre

1. **Aviso nuevo `SEALED_COPY_READY`** (correo, en/es) para los miembros informativos cuando el sobre se completa y hay
   documento sellado:
   - sobre `AGREED`: todos los informativos, se haya activado su paso o no;
   - sobre `NOT_AGREED`: solo aquellos cuyo paso llegó a activarse;
   - sin nada sellado: nadie.

   Lleva un **enlace de firma nuevo, emitido al completarse el sobre**, no el de la invitación. Abre `/s/{token}` como
   cualquier otro enlace.

   ⚑ **Actualizado 2026-10-26 (TASK-071, ADR-0089 §2.6, sin desplegar): ese enlace ya no es de firma, es el enlace de
   copia de solo lectura** (`{NOTIFICATION_COPY_BASE_URL}/<enlace>`, ver el traspaso de TASK-070), y el aviso también
   llega a los miembros delegados. Lo de arriba describe el estado anterior.
2. **Un informativo de un paso que nunca se activó ya puede entrar y leer una vez cerrado el sobre.** El paso solo se
   pregunta mientras el sobre está abierto; desde el cierre deciden las reglas de siempre: los informativos leen, sea
   cual sea el desenlace; los bloqueantes de ese paso siguen rechazados (`ENVELOPE_NO_LONGER_LIVE` al abrir y en el
   modelo de lectura, 404 en los bytes).
3. En consecuencia, tras el cierre **`GET /signing/session/auth` deja de responder 409 `STEP_NOT_ACTIVE`** a un
   miembro de un paso nunca activado: responde el descriptor normal (200).
4. Entre el cierre y `COMPLETED`, la lectura responde `SEAL_PENDING` como ya hacía; los bytes dan 404 hasta el sellado.
   ⛑ **2026-10-23, TASK-069**: solo mientras el destinatario vea algún documento con bytes aún sin sellar. Con
   `SEQUENTIAL_PADES` un documento puede quedar sellado antes del cierre
   ([ADR-0087](../adr/ADR-0087-a-document-is-sealed-once-it-is-final.md)); si todos los que puede ver lo están, la
   lectura responde 200 desde el cierre.
5. `ENVELOPE_COMPLETED` («firmado») solo llega ya a quien firmó un sobre `AGREED`, y su texto ya no dice «firmado por
   todos». Solo afecta al correo.

### G. `LEG_CLOSED`: dónde se publica ya

`LEG_CLOSED` (409) significa *el sobre sigue abierto, pero tu parte ya terminó*. Con el sobre cerrado se responde
`ENVELOPE_NO_LONGER_LIVE` antes que él. Ahora llega en:

| Ruta | Cuándo | Evidencia |
|---|---|---|
| `POST /signing/commit`, `POST /signing/decline` (y el commit delegado del integrador) | un acto ya admitido o una participación liberada, como desde TASK-048; **y ahora también** un acto en el hueco entre el plazo del paso y el barrido: el texto publicado añade *«including when this recipient's step has reached its deadline and is about to be closed without this act»* | `eb686c5f`; `AdmitRecipientActTest` (nivel aplicación). Sin test HTTP del hueco |
| `POST /signing/session` (abrir) | una participación liberada con el sobre abierto (un plazo de paso); **y ahora también** la que se cierra en el instante entre la lectura sin bloqueo y el registro de la apertura bajo el bloqueo de fila: no se emite credencial | `fb875674`; el primer caso, sobre HTTP en `StepDeadlineBarsDeHttpTest`. La carrera no se puede provocar por HTTP (lo dice ese test) |
| `POST /signing/session/auth` (y su relevo por clave de máquina) | **nuevo**: el código era correcto, pero la participación se cerró sin firma (un plazo de paso la liberó) en el instante antes de registrar el paso; no se emite credencial y el intento queda gastado | `fb875674`; texto publicado en `SubmitAuthResponseController`. Sin test HTTP |
| `GET /signing/session` con una credencial ya emitida | **nuevo en el texto publicado**: un bloqueante liberado con el sobre abierto recibe 409 `LEG_CLOSED` al momento, sin esperar a que la revocación asíncrona llegue a su sesión; y los bytes, 404. Un informativo liberado sigue leyendo | `9d4531ae`; `ClosedLegReadsOnAnOpenEnvelopeHttpTest` (la liberación se escribe en la fila, no la produce el barrido) |

**Quien rechazó, con el sobre abierto, no recibe `LEG_CLOSED` en la lectura:** `GET /signing/session` responde 200
con `status: DECLINED`, y `GET /signing/session/documents/{id}` responde 404 (la descarga ya no le sirve bytes con
una credencial emitida antes del rechazo; `9d4531ae`). Lo fijan `SigningSessionReaderTest` y
`SigningDocumentReaderTest` (nivel aplicación); el texto publicado de la descarga lo dice así.

`POST /signing/session/auth/otp/send` **no** publica `LEG_CLOSED`: para un liberado que nunca abrió sesión responde
404 `NOT_FOUND` y no envía código (`StepDeadlineBarsDeHttpTest`).

### H. `ENVELOPE_NO_LONGER_LIVE` ya no dice «cancelado»

`70a0e89d` cambió el texto publicado del 409 en `POST /signing/session` y en `GET /signing/session`. Antes pedía
llevar al firmante a una pantalla de *«this document was cancelled»*; ahora dice que su parte terminó y
**expresamente que no significa que el documento se cancelara**, porque un sobre también cierra con acuerdo sin su
parte (cerrar ya, o un plazo). Para decir cómo terminó, remite a `outcome` y `envelope_outcome` de
`GET /signing/session/auth`, que el mismo enlace sigue alcanzando.

## Plazos

Lo que ve un destinatario cuyo paso tiene plazo (`deadline_hours`), con el backend de `f48b14e2`:

1. **Antes del plazo**: nada cambia.
2. **Entre el plazo y el barrido** (el barrido corre cada minuto): su firma y su rechazo se rechazan con 409
   `LEG_CLOSED` y no se registra nada. En el código de este árbol, abrir y leer **no** miran el plazo: la puerta y
   la lectura siguen pasando hasta que el barrido libera la participación; una apertura en ese hueco no cuenta como
   haber abierto. Esto último no tiene test HTTP.
3. **Tras el barrido, con el sobre abierto** (el paso cerró y el sobre siguió, p. ej. al paso siguiente): un
   bloqueante que no actuó queda `RELEASED` con `released_by: STEP_DEADLINE` en la lectura del emisor. En sus
   rutas: `/auth` → `outcome: RELEASED`, `envelope_outcome: null`; abrir → 409 `LEG_CLOSED` sin credencial; enviar
   código → no se envía; lectura con una credencial ya emitida → 409 `LEG_CLOSED`; bytes → 404. Su sesión se revoca
   de forma asíncrona. Los informativos del paso **no** se liberan en el plazo: siguen leyendo.
4. **Tras el barrido, si el plazo termina el sobre** (`NOT_AGREED` con `STEP_DEADLINE_MISSED` o
   `MEMBER_NOT_REACHED`, o `AGREED` si era el último paso bloqueante y tenía lo que necesitaba): `/auth` →
   `outcome: RELEASED` y `envelope_outcome` con el desenlace; abrir y leer → 409 `ENVELOPE_NO_LONGER_LIVE`; bytes →
   404. Los informativos, `outcome: null` + `envelope_outcome` fijado: la copia sellada (y el aviso
   `SEALED_COPY_READY` si les corresponde).

Sobre HTTP con el barrido real está fijado el punto 3 (`StepDeadlineBarsDeHttpTest`: `/auth`, abrir, enviar código)
y, para la lectura con credencial ya emitida, `ClosedLegReadsOnAnOpenEnvelopeHttpTest`. Del punto 4 están fijados
sobre HTTP los desenlaces en la lectura del emisor (`StepDeadlineBarsDeHttpTest`, `StepDeadlineBarsGhHttpTest`);
**las rutas del signer en el punto 4 están pendientes de test HTTP** y lo escrito sale de la misma regla que la
tabla `NOT_AGREED` de arriba.

## Lo que el frontal tiene que hacer

1. **A.** En `useSignerNavigation.ts`, quitar `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` del `case` que comparte con
   `DECLINE_NOT_OFFERED_TO_ROLE` y de `CODES_DECLINE_NOT_OFFERED`; quitarlo de `useSignerNavigation.spec.ts`,
   `useDecline.spec.ts` y del docblock de `decline()` del cliente. `declineNotOffered` sigue activándolo
   `DECLINE_NOT_OFFERED_TO_ROLE`. **No ocultar Rechazar por estar en un paso de quórum** (el signer no lo deducía por
   su cuenta: no lee `min_signatures`).
2. **B.** No ofrecer firmar/confirmar a `VIEWER`, `REVIEWER` ni `EDITOR`. Mapear `COMMIT_NOT_OFFERED_TO_ROLE` en el
   clasificador del commit, como `DECLINE_NOT_OFFERED_TO_ROLE` en el rechazo. Decisión del mantenedor: **el signer
   retira la acción sin distinguir rol** — ante el 409 la oculta y se queda en `/view`, no es reintentable. Un código
   desconocido ya cae en el `default` seguro, pero la rama explícita evita la pantalla de error genérica.
3. **E.** Añadir `envelope_outcome` (nullable) a los tipos de `/auth` **y** de `GET /signing/session`. Enrutar por
   `outcome` y `envelope_outcome` a la vez:
   - `outcome: null` con `envelope_outcome` fijado: vista de lectura de la copia sellada (ni «tu participación ha
     terminado» ni la pantalla `/done` de «ya habías firmado»);
   - `RELEASED`: participación terminada; con `envelope_outcome: null` el documento sigue su curso para otros; con
     valor, el texto puede decir si el documento siguió (`AGREED`: «el documento se completó»; `NOT_AGREED`: «no
     siguió adelante»);
   - `COMPLETED`: como hasta ahora.

   Dejar de tratar `REVOKED` como «el remitente canceló» y mantener una rama `default` segura para él.
4. **Vista nueva de solo lectura `/copy`** (decisión del mantenedor). Se enruta cuando la puerta pasa (`AUTH_PASSED`)
   **y** `envelope_outcome != null`, con `GET /signing/session` como fuente. Es la primera pantalla de un informativo
   que llega por el enlace de `SEALED_COPY_READY`: no puede suponer sesión previa, ni paso activo, ni haber pasado
   por «pendiente». Mientras el sello no está (`SEAL_PENDING`), la pantalla de espera que ya existe.
5. **No mostrar «todavía no es tu turno»** (`STEP_NOT_ACTIVE`) tras el cierre: el backend ya no lo emite ahí. Si el
   signer lo deducía de otro dato, revisadlo.
6. **`signer.role`**: tratar `VIEWER` como `REVIEWER`; el backend nunca manda `VIEWER` en ese campo.
7. **`ENVELOPE_NO_LONGER_LIVE` no es «cancelado».** El texto publicado ya no lo dice (punto H): para un liberado de un
   sobre `AGREED` (cerrar ya, o un plazo) también llega este 409. La pantalla no debe decir que el documento se
   canceló; para decir cómo terminó, apoyarse en `outcome` y `envelope_outcome` de `/auth`, no solo en el 409.
8. **`LEG_CLOSED` en más rutas** (punto G): añadirlo en el paso de puerta (`POST /signing/session/auth`) y en la
   lectura (`GET /signing/session`), con la misma pantalla terminal que en abrir, firmar y rechazar; no reintentar.
   Para el subtítulo de `/declined` cuando se llega por `LEG_CLOSED`, recomendamos reutilizar `legReleasedSubtitle`
   (cadena del signer, según su sesión; no existe en este repo).

## Lo que NO está listo todavía

- Nada de esto está en `develop` ni desplegado; comprobad el `doc.json` de vuestro entorno (regla 4).
- Las filas y rutas marcadas **pendiente** arriba (la tabla de filas sin recorrer, el punto 4 de *Plazos*, el hueco
  entre plazo y barrido) están escritas desde la regla del código, no desde un test HTTP.
- Los pasos `AT_LEAST`, cerrar ya y los plazos de paso solo aparecerán en vuestros flujos cuando un integrador los
  autorice; `dashboard-sf` ha decidido no hacerlo por ahora (traspaso del integrador).

## Lo que NO existirá, y por qué

- **Un código propio para «el paso es de quórum» al rechazar**: el rechazo es un acto como otro y lo juzga el sobre;
  por eso `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` desaparece en vez de convertirse en otro.
- **Un código propio para «tu paso venció»**: un acto pasado el plazo responde `LEG_CLOSED`, igual que la caducidad
  de TASK-049 no añadió código para el signer; decisión del mantenedor del 2026-09-29 (`eb686c5f`).

## Cómo verificarlo desde el frontal

- `POST /signing/commit` con un enlace de `VIEWER`, `REVIEWER` o `EDITOR`: 409 `COMMIT_NOT_OFFERED_TO_ROLE`.
- Con el sobre abierto, `GET /signing/session/auth` de un miembro pendiente: `outcome: null`, `envelope_outcome: null`.
- Tras un cierre, la tabla de arriba: `(null, X)` informativo lee; `(RELEASED, X)` terminado; `(COMPLETED, X)` firmó.
- `GET /signing/session` de un informativo tras el cierre: `status: AUTH_PASSED` y `envelope_outcome` fijado.
- `GET /signing/session/auth` de un informativo de un paso nunca activado, tras el cierre: 200, no 409 `STEP_NOT_ACTIVE`.
- Un paso `AT_LEAST 1` con plazo y un paso posterior: un firmante firma, otro no abre. Pasado el plazo y el barrido,
  el paso siguiente se activa y el que no abrió da `(RELEASED, null)` en `/auth` y 409 `LEG_CLOSED` al abrir.
