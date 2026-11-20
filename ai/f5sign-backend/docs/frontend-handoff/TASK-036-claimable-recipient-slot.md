# Traspaso al frontal — un destinatario puede declararse vacío y nombrarse una sola vez después

| | |
|---|---|
| **Origen** | `feat/claimable-recipient-slot` · commit `22328ad` (el merge de `origin/develop` sobre el que se corrió la lane; `3bef45f` era el primero de la ronda de arreglos) · sin PR todavía. ⚑ **Repuntado 2026-09-01**: esta fila decía `2b98b5c`, el commit 14 de 18 de la rama y **anterior** a `0802326` — un árbol en el que un claim que omitía `email` lo **borraba**, justo lo contrario de lo que promete el §2 de esta misma nota. Un sha de origen desfasado no envejece como una frase desfasada: se puede sacar y leer, y el contrato que se lee ahí de verdad se comportaba así |
| **Fecha** | 2026-08-28 |
| **Repos afectados** | **`f5sign-dashboard`** — es todo superficie de emisor. `f5sign-signer` no toca nada |
| **Naturaleza** | **aditivo** en el alta de destinatario y en la ruta nueva; **rompe** dos rutas que ya llamáis, que ganan un código de rechazo nuevo — **el mismo en las dos** |
| **Acción requerida** | dashboard: manejar **un** código nuevo en las dos rutas que ya usáis —el mismo en ambas, §3 y §4—, **más los tres de la ruta nueva** si la adoptáis (§2), y decidir si exponéis la declaración en el alta · signer: ninguna. ⚑ **Corregido 2026-09-01**: esta fila decía *"manejar **tres códigos nuevos** en rutas que ya usáis"*, y los títulos de §3 y §4 los contaban como *"segundo"* y *"tercer"* mientras el propio §4 admitía al final que era **el mismo** que §3. La cifra salía de contar dos veces un código compartido y de no contar en absoluto los de la ruta nueva, que ninguna versión anterior de esta nota enumeraba. Cada uno está ahora en su sección, y el conjunto vigente se lee del spec (`components.schemas.ProblemCode`), no de esta fila |
| **Desplegado** | not yet — la rama no está mergeada |
| **Status** | Pending |

## El caso que resuelve

El consignatario de un eCMR **no se conoce cuando se autoriza y se envía la carta de porte**. Hasta
ahora un destinatario podía crearse sin contacto y enviarse así — nadie lo impedía — pero era
completamente inerte: nada lo invitaba, nada podía, y **nada en ninguna parte decía si el vacío era
deliberado**. Un emisor que olvidó un campo y otro que dejó el hueco abierto a propósito producían
filas idénticas byte a byte.

Ahora el hueco se **declara**, y se rellena después con una operación propia.

## Lo que cambió en el contrato

### 1. `POST /api/v1/envelopes/{id}/recipients` — aditivo

Nuevo miembro opcional en el cuerpo:

```json
{ "claimable": true }
```

Declara que el hueco se autoriza **deliberadamente sin ocupante**. Por defecto `false`, así que
**ningún cliente actual cambia de comportamiento**.

⚑ **Lo que compra, y es lo que hace falta entender para usarlo:** con `claimable: true` se **difiere**
la comprobación de destinos. Hoy, declarar `OTP_EMAIL` sin email —o `OTP_SMS` sin teléfono, o contra
un fijo— se rechaza con **422 `RECIPIENT_CANNOT_RECEIVE_METHOD`**. Sobre un hueco declarado, esa
comprobación **no se hace en el alta**: se vuelve a hacer entera en el claim, contra lo que el claim
aporte, y falla allí con el mismo código.

⛔ **El diferimiento va atado a la declaración y a nada más.** Un destinatario ordinario sin contacto
se sigue rechazando exactamente igual que hoy. No es *"si no hay contacto, pasa"*.

### 2. `POST /api/v1/envelopes/{id}/recipients/{recipientId}/claim` — ruta nueva

Nombra a la parte. `Authn::MACHINE_KEY`, como el resto de la superficie de emisor.

```json
{ "full_name": "...", "email": "...", "phone": "...", "locale": "es" }
```

`full_name` es **obligatorio**; el resto opcional. Devuelve **204**.

⚑ **Y aquí está lo que importa para vuestra lógica de reintento: una repetición idéntica también
devuelve 204, indistinguible de la primera.** Un campo que la repetición **no** manda no se compara —
ausente significa *"no lo afirmo"*, no *"bórralo"*. Así que un reintento por timeout de red que omita
el `locale` que mandó la primera llamada es **idéntico**, no divergente. Esto es deliberado: es
justamente el caso donde un 409 sería peor.

Una repetición que **sí** manda un campo y difiere → **409 `RECIPIENT_ALREADY_CLAIMED`**, con el
mensaje nombrando qué campo. ⚑ **El código va nombrado desde 2026-09-01**: esta línea prometía el 409
sin decir con qué `code` llega, mientras el punto 1 de más abajo os pide ramificar por `code` y nunca
por el estado.

⚠ **El mensaje dice *"differs from the one the slot holds"*, no *"from the claim already recorded"*, y
la diferencia os ahorra un diagnóstico falso:** un claim escribe **solo** los campos que trae, así que
el valor contra el que se compara puede haberse escrito **en el alta** y no en ningún claim. Un hueco
creado con `locale: es`, reclamado sin locale y re-enviado con `locale: fr` se rechaza aquí
—correctamente: el relleno es de una sola vez— pero ningún claim declaró jamás `es`. No mandéis al
operador a buscar una llamada anterior que no existe.

⛔ **Los otros dos rechazos de esta ruta, que ninguna versión anterior de esta nota enumeraba.** Los
tres van a pantallas distintas, así que el 409 pelado no os sirve para ninguno:

- **`RECIPIENT_NOT_CLAIMABLE`** — este destinatario nunca se declaró hueco: no hay ocupación abierta que
  rellenar. O tenéis el id equivocado, o estáis intentando editar a alguien nombrado en el alta, y para
  eso no hay ruta (abajo, en *Lo que NO existirá*).
- **`RECIPIENT_CAN_NO_LONGER_ACT`** — no queda nada que una parte nombrada pudiera hacer: su tramo se
  cerró, o el paso en el que está ya se completó. **Es una propiedad, no una lista de estados**: se
  dispara sobre cualquier desenlace terminal, y uno nuevo queda cubierto el día que exista. No lo
  cableéis contra una lista de desenlaces vuestra.

Y sigue habiendo un **409 `CONFLICT`** genérico cuando el sobre en sí no admite escritura, que no es de
esta rama y no tiene remedio propio.

⚑ **Y esto es lo que hay que hacer en vez de copiar la lista de arriba.** El conjunto vigente lo publica
el spec en `components.schemas.ProblemCode`, y `OpenApiSpecTest` lo mantiene **igual, en las dos
direcciones**, al conjunto de códigos que las excepciones emiten de verdad: uno nuevo sin publicar rompe
el build, y una entrada que ya nadie emite también. Leedlo de ahí. Si esta nota y el spec no coinciden,
manda el spec.

### 3. `POST /api/v1/signing-tokens` — ROMPE

Ya devolvía 409 `ENVELOPE_NOT_SENT`. Ahora puede devolver además **409 `RECIPIENT_SLOT_NOT_CLAIMED`**:
no se acuña enlace de firma para un hueco que nadie ha reclamado. Sin esto, cualquiera con el enlace
sería la parte, y la evidencia no podría decir quién firmó.

⚑ **Un hueco YA reclamado acuña con total normalidad** — es un destinatario ordinario.

### 4. `POST /api/v1/envelopes/{id}/recipients/{recipientId}/corrections` — ROMPE (el mismo código que §3)

Ahora puede devolver **409 `RECIPIENT_SLOT_NOT_CLAIMED`**. Una corrección cambia *dónde se alcanza a
una parte ya nombrada*, y un hueco sin reclamar no tiene parte a la que alcanzar. **La operación que
aplica es el claim**, y el cuerpo del error lo dice.

⚠ Es el mismo código que en el mint, a propósito: un estado, un remedio, dos superficies.

## Lo que el frontal tiene que hacer

**Dashboard:**

1. **Ramificad sobre `code`, no sobre el 409.** Las dos rutas rotas ya devolvían 409 por otros motivos,
   así que el estado por sí solo no os sirve. `RECIPIENT_SLOT_NOT_CLAIMED` significa *"reclama el hueco
   primero"* y tiene una acción concreta detrás; los demás 409 de esas rutas, no. Y lo mismo en la ruta
   nueva, donde **todos** sus rechazos de estado son 409 y cada uno lleva a un sitio distinto (§2).
2. **Si ofrecéis "copiar enlace de firma" por destinatario**, ocultadlo o deshabilitadlo en un hueco sin
   reclamar — igual que ya hacéis con el sobre en borrador desde TASK-035.
3. **Si ofrecéis "corregir contacto"**, en un hueco sin reclamar hay que ofrecer **reclamar** en su
   lugar, no un formulario de corrección que va a fallar.
4. **El claim es una operación de una sola vez.** Un botón que se pueda pulsar dos veces está bien
   (converge), pero un formulario que permita *cambiar* a quién nombrasteis no: eso es re-asignación y
   está deliberadamente fuera (abajo).
5. **Decidid si exponéis `claimable` en el alta.** Es opcional y por defecto `false`; si vuestro flujo
   no tiene el caso eCMR, podéis ignorarlo entero.

**Signer:** nada. Un hueco sin reclamar no tiene enlace, así que nunca llega a esa app.

## Lo que NO está listo todavía

- **Los dos campos NO se publican en el read model.** `GET /api/v1/envelopes/{id}` **no** os dice hoy si
  un destinatario es un hueco ni si está reclamado. Es de [TASK-037](../tasks/TASK-037-claimable-invitation-and-visibility.md),
  deliberadamente.

  ⚑ **Corregido 2026-08-28 con el argumento del equipo de dashboard, que es mejor que el que había aquí.**
  Esto decía que la consecuencia era no poder pintar *"esperando a que alguien lo reclame"* ni decidir en
  cliente qué botón ofrecer. **Eso no bloquea ninguna pantalla**: quien declara `claimable: true` es el
  propio frontal, así que sabe localmente qué destinatario es un hueco y lo persiste al crear el sobre; y
  para *"reclamado o no"*, el 204/409 basta para decidir **después de intentarlo**.

  ⚠ **Lo que la ausencia sí cuesta es RESINCRONIZACIÓN, no pintar un badge.** Ese flag local es una caché
  de escritura **sin ruta de lectura para cuadrarla**: si el claim responde 204 y el flush del frontal se
  cae después, las dos partes quedan divergentes de forma permanente **y sin forma de detectarlo**. Es un
  riesgo real y acotado, y es el argumento honesto para priorizar 037 — no la pantalla.
  ⛔ **Y no lo apañéis con un reintento a ciegas**: sin lectura no se puede distinguir *"no llegó"* de
  *"llegó y se perdió la confirmación"*, y el segundo caso reintentado con otros datos es un 409.
- **La invitación al reclamar tampoco existe todavía.** Nombrar a la parte no le manda nada por ahora;
  la ocasión de notificación es de TASK-037.

## Lo que NO existirá, y por qué

- **No hay forma de re-asignar un hueco ya reclamado.** Está diferido junto con editar la identidad de
  un destinatario ya nombrado, como **una sola** pregunta: el id de sesión de firma es determinista
  sobre `(tenant, sobre, destinatario)`, así que un segundo ocupante heredaría la sesión, el rastro de
  acceso y **la puerta ya pasada** del primero. No es un hueco de API, es una decisión de diseño con su
  camino de migración ya nombrado.
- **No hay forma de que la propia parte se identifique.** El auto-reclamo está excluido: un enlace al
  portador haría parte a *quien lo tenga*, que es exactamente lo que esto evita.
- **El claim no registra quién lo pidió.** La cabecera `F5Sign-Declared-Subject` se valida y se
  **descarta**; el evento no la lleva. Rechazamos `f5s:none` con un **400**, así que la llamada tiene que
  afirmar un humano — pero eso prueba que se **afirmó**, nunca que quedara **registrado**. Hoy nada en el
  backend puede responder *"¿qué operario nombró a este consignatario?"*. No construyáis UI que lo dé por
  hecho. **Corregido con [ADR-0097](../adr/ADR-0097-the-log-is-the-documents-one-source.md) §2.10:** el hecho
  `RECIPIENT_CLAIMED` registra ahora la cabecera, cifrada. Ningún documento la muestra todavía, y una
  repetición idéntica conserva la primera declaración, así que sigue sin haber UI que construir sobre ella.

## Cómo verificarlo desde el frontal

1. Crear sobre + documento, y añadir destinatario con
   `{"step_ordinal":1,"role":"SIGNER","claimable":true,"auth":{"access_method":"OTP_EMAIL"}}`
   **sin email** → **201**. (El mismo cuerpo **sin `claimable`** → **422
   `RECIPIENT_CANNOT_RECEIVE_METHOD`**: ese es el par que demuestra que el diferimiento va atado a la
   declaración.)

   ⚑ **Corregido 2026-09-01: el cuerpo iba sin `step_ordinal`, y el par no demostraba nada.**
   `step_ordinal` es obligatorio junto con `role` —el alta lo publica en su `required`—, así que las
   **dos** mitades daban **422 `VALIDATION_ERROR`**: la misma respuesta, por un motivo que no tiene nada
   que ver con el diferimiento, en el paso que esta nota presenta como la prueba de que sí. Un par
   discriminante tiene que diferir **solo** en lo que se está probando. Las formas exactas del cuerpo
   están en el spec (`GET /api/doc.json`), que es donde mirar si el alta gana algún obligatorio más.
2. Enviar el sobre.
3. `POST /api/v1/signing-tokens` con ese par → **409 `RECIPIENT_SLOT_NOT_CLAIMED`**.
4. `POST …/recipients/{id}/corrections` con un email → **409 `RECIPIENT_SLOT_NOT_CLAIMED`**.
5. `POST …/recipients/{id}/claim` con `full_name` + email → **204**. Repetir **la misma llamada** → **204**.
   Repetirla con otro `full_name` → **409 `RECIPIENT_ALREADY_CLAIMED`**.
6. `POST /api/v1/signing-tokens` otra vez → **201**. Ya es un destinatario ordinario.
7. `POST …/claim` con cabecera `F5Sign-Declared-Subject: f5s:none` → **400**.
8. `POST …/claim` sobre un destinatario **ordinario** (dado de alta sin `claimable`) → **409
   `RECIPIENT_NOT_CLAIMABLE`**. Es el par del punto 1 visto desde la otra ruta: sin la declaración no hay
   hueco que rellenar, y este no es el editor de destinatarios.

⚠ Estos pasos no ejercitan `RECIPIENT_CAN_NO_LONGER_ACT`, que necesita un tramo ya cerrado. Está
descrito en §2 como propiedad justamente porque no se reproduce con una secuencia corta; no deduzcáis de
su ausencia aquí que no llega.
