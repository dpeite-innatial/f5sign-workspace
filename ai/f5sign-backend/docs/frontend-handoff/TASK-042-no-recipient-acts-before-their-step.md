# Traspaso al frontal — nadie actúa antes de que el flujo llegue a su paso

<!-- OFFREPO: todos los hechos del lado cliente de este documento se leyeron en `f5sign-signer`, rama
`develop`, commit `c894f88`, el 2026-09-15: `app/composables/useSignFlow.ts` (`mapError`),
`app/composables/useSignerNavigation.ts` (`errorCodeToPath`), `app/middleware/session.global.ts` (el
`catch` de la apertura y del read-model), `app/pages/s/[token]/auth.vue` (el `catch` del descriptor),
`app/pages/s/[token]/view.vue` (`askSessionAfterMissingBytes`), `app/composables/useAuthChallenge.ts`
(envío de código y respuesta) e `i18n/locales/{es,en}.json` (`status.unavailable`). Están reescritos en
línea donde se usan, así que nada aquí exige tener ese repo delante; y ninguno se puede volver a medir
desde este. -->
<!-- OFFREPO: la fila *Status* se escribió el 2026-09-16 leyendo el clon de `f5sign-signer`, no su
sesión: `639a788` está en su `develop` y sale en `git log origin/develop..develop`, o sea sin push. Lo que
ese commit hace se leyó en su diff (`app/composables/useSignFlow.ts`, `app/composables/useAuthChallenge.ts`,
`app/pages/s/[token]/click-sign.vue`); el verde que cita está en su mensaje de commit y no se volvió a correr
desde aquí. Actualizado el 2026-09-16, más tarde, leyendo el mismo clon: `origin/develop` = `develop` =
`7ce2958`, y `git log c894f88..origin/develop` lista seis commits, `639a788` el primero; o sea, pusheado. -->
<!-- OFFREPO: la viñeta de despliegue restata hechos de `f5sign-signer` leídos en su clon el 2026-09-16:
`app/composables/useSignFlow.ts` en `c894f88` (el commit manda a `/done` solo un 409 con `ALREADY_SIGNED` o
`CONFLICT`, y cualquier otro 409 cae en la rama de último recurso, que llama a `reportError`), y el diff de
`01ffece`, que quita `code === 'CONFLICT'` de esa condición. -->


| | |
|---|---|
| **Origen** | rama `fix/step-order-at-every-door`, **mergeada en `develop` en `f490218` y pusheada** el 2026-09-16, sin PR — y **sin desplegar**: `develop` no es un despliegue (regla 4 del README); lo que manda es la fila *Desplegado* · commit `5143466` (el último de la rama que toca `src/`) · [ADR-0066](../adr/ADR-0066-no-recipient-acts-before-their-step.md) (**`Accepted (exercised)`** desde el 2026-09-16) · [TASK-042](../tasks/TASK-042-no-recipient-acts-before-their-step.md). ⛑ **Corregido el 2026-09-16, al mergear**: la fila abría *«rama `fix/step-order-at-every-door` · commit `5143466`»*, sin decir nada del merge, y acababa en *«sin PR todavía»*. ⛑ **Actualizado el 2026-09-16**: esta fila decía `37ffe1b` *“el último que toca `src/`”* y el ADR en `Proposed`. `5143466` tocó `src/` después, y es el commit que cambia la fila de la firma delegada en la tabla de rutas de máquina ([`BL-263`](../BACKLOG.md)) |
| **Fecha** | 2026-09-16 (los hechos del lado firmante se leyeron el 2026-09-15; ver el comentario de arriba) |
| **Repos afectados** | **signer** — una rama nueva en la respuesta del commit, y nada más obligatorio · **quien acuñe enlaces o firme por la superficie de máquina** (dashboard o integrador con clave de máquina) |
| **Naturaleza** | **rompe comportamiento, no esquema**: llamadas que hoy admiten al destinatario pasan a responder 409. Ninguna ruta, campo ni código nuevo — los dos códigos ya son miembros de `ProblemCode`. ⚑ **Y corrige el spec de paso**: tres rutas (el descriptor y las dos gemelas de máquina) publican una 409 que no publicaban, y la apertura nombra un código que ya emitía |
| **Acción requerida** | signer: **enrutar 409 `STEP_NOT_ACTIVE` en `POST /api/v1/signing/commit`** · máquina: tratar 409 `RECIPIENT_STEP_NOT_ACTIVE` del mint y 409 `STEP_NOT_ACTIVE` de las rutas de ceremonia como *esperar*, no como *reintentar* |
| **Desplegado** | not yet — ni el backend (mergeado en `develop` en `f490218` y pusheado, **sin desplegar**) ni el signer (pusheado en `develop` hasta `7ce2958`, **sin desplegar**). Y el mismo `develop` lleva [TASK-043](TASK-043-a-refused-commit-names-its-condition.md), que sale **en el mismo despliegue que el signer** (su *El orden de salida*). ⛑ **Corregido el 2026-09-16, al mergear y al pushear el signer**: decía *«ni la rama backend (sin merge y sin push) ni la del signer (sin push)»*; antes aún, solo *«la rama no está mergeada»* |
| **Status** | **Applied en `f5sign-signer` `develop`, pusheado** (2026-09-16; rango `c894f88..7ce2958`, seis commits: `639a788`, `2f4e721`, `eb5ac02`, `1638c6b`, `01ffece`, `7ce2958`). El que aplica este traspaso es `639a788`: un 409 `STEP_NOT_ACTIVE` en el commit guarda el error en el store y navega por `errorCodeToPath` a `/unavailable`, dejando rastro y no evento de Sentry; el mismo commit lo cubre en la página MVP y en las dos llamadas de la puerta de código, y enruta también el traspaso de [TASK-043](TASK-043-a-refused-commit-names-its-condition.md). ⚑ **Escrito desde su árbol y no desde su sesión** (*El punto débil* del README). ⛑ **Actualizado el 2026-09-16, al pushear el signer**: esta fila decía *«Applied en `f5sign-signer` `develop`, sin push (`639a788`, 2026-09-16)»* y *«dice sin push porque es lo que ese árbol dice»*; el mismo árbol dice ahora `origin/develop` = `develop` = `7ce2958`. ⛑ **Actualizado el 2026-09-16**: esta fila decía `Pending` |

> ⛔ **Qué arregla: un sobre se selló con una firma de tres.** En preprod, el 2026-08-27, el
> destinatario del paso 3 de un sobre `SIGN_ORDERED` de tres pasos firmó mientras el paso activo era el
> 1. Tenía un enlace acuñado por `POST /api/v1/signing-tokens`, y ninguna ruta preguntaba si el flujo
> había llegado a su paso: abrió, se autenticó, leyó y firmó. El sobre llegó a `COMPLETED` con los
> pasos 1 y 2 sin firmar.

## Lo que cambió en el contrato

**La pregunta nueva es una sola: *¿ha llegado el flujo al paso de este destinatario?*** — o sea, *¿se ha
activado alguna vez su paso?* Si no, se le rechaza en el mint y en cada ruta de la ceremonia.

⚑ **Es *activado*, no *abierto*, y la diferencia os importa.** Un paso ya **completado** sigue
contestando que sí: quien firmó y vuelve a por su copia sigue entrando exactamente igual que hoy. Y hoy
nada desactiva un paso que ya se activó, así que si una ruta admitió a alguien por este motivo, las
siguientes también lo harán.

### Rutas del firmante (`f5sign-signer`)

Para un destinatario cuyo paso no se ha activado:

| Ruta | Respuesta nueva | Lo que ya no ocurre |
|---|---|---|
| `POST /api/v1/signing/session` | **409** `STEP_NOT_ACTIVE` | no se crea sesión ni se emite credencial |
| `GET /api/v1/signing/session/auth` | **409** `STEP_NOT_ACTIVE` — ⚠ esta ruta **no publicaba ningún 409** hasta ahora | — |
| `POST /api/v1/signing/session/auth/otp/send` | **409** `STEP_NOT_ACTIVE` | no se envía código — tampoco SMS, que se paga |
| `POST /api/v1/signing/session/auth` | **409** `STEP_NOT_ACTIVE` | no se gasta intento |
| `GET /api/v1/signing/session` | **409** `STEP_NOT_ACTIVE` | — |
| `GET /api/v1/signing/session/documents/{documentId}` | **404**, igual que cualquier otro rechazo de esa ruta | no se sirven bytes |
| `POST /api/v1/signing/commit` | **409** `STEP_NOT_ACTIVE` | no se firma ni se registra nada |

`STEP_NOT_ACTIVE` no es nuevo en el read-model: ya lo publicaba para una pierna **saltada**. Pero nada en
el backend escribe nunca ese estado, así que hasta hoy **ningún cliente lo había recibido**. A partir de
este cambio es cuando llega de verdad, y significa *aún no te toca*.

⚑ **Y de paso una corrección del spec, no del comportamiento.** La 409 publicada de
`POST /api/v1/signing/session` decía que su `code` **era** `ENVELOPE_NO_LONGER_LIVE`, cuando la ruta ya
emitía además `RECIPIENT_SIGNS_ELSEWHERE` desde antes de esta rama. Ahora publica los tres. La ruta hace
lo mismo que hacía; lo que cambia es lo que el `doc.json` os promete — y una enumeración cerrada de uno es
justo lo que hace que un cliente no ramifique.

**Qué contesta primero, cuando hay más de un motivo:**

- **Los rechazos de legitimidad conservan su respuesta de hoy y ganan**: sobre sin enviar (404),
  enlace o credencial retirados, sobre que ya no está vivo (`ENVELOPE_NO_LONGER_LIVE`), destinatario que
  firma desde su organización (`RECIPIENT_SIGNS_ELSEWHERE`). Un sobre anulado sobre un paso dormido sigue
  diciendo *anulado*. ⚠ **Con una excepción, y es el descriptor**: esa ruta no rechaza por sobre
  muerto — lo terminal viaja en el `outcome` del cuerpo del 200
  ([ADR-0056](../adr/ADR-0056-terminal-state-on-pre-credential-routes.md)) —, así que ahí el paso
  contesta primero y un destinatario dormido de un sobre anulado ve *aún no te toca*. Su paso no se
  activará nunca; el read-model sigue siendo quien explica el motivo.
- **`STEP_NOT_ACTIVE` gana a los rechazos sobre *cómo* actuar**: los `AUTH_*` de puerta, el enfriamiento
  del código y, en el read-model, los del resultado de la pierna y del rol (`RECIPIENT_DELEGATED`,
  `ROLE_NOT_INTERACTIVE`). Los tres van ya a `/unavailable` en vuestro mapa, así que el destino no cambia.
- ⚠ **Un residuo**: quien firmó fuera de turno **antes** de este cambio, sobre un sobre todavía vivo, y
  reintenta el commit, recibe ahora `STEP_NOT_ACTIVE` y no el `CONFLICT` pelado. Hoy ese reintento os
  llevaba a `/done`. Ese sobre es uno de los ya corrompidos (*Lo que NO está listo*).

### Rutas de máquina (integrador, `machineApiKey`)

| Ruta | Respuesta nueva |
|---|---|
| `POST /api/v1/signing-tokens` | **409** `RECIPIENT_STEP_NOT_ACTIVE`, sin acuñar nada. Contesta **después** de `ENVELOPE_NOT_SENT`, `RECIPIENT_SLOT_NOT_CLAIMED` y `RECIPIENT_SIGNS_ELSEWHERE`, así que no enmascara ninguno |
| `POST /api/v1/envelopes/{id}/recipients/{recipientId}/auth/otp/send` | **409** `STEP_NOT_ACTIVE` — ⚠ no publicaba ningún 409 |
| `POST /api/v1/envelopes/{id}/recipients/{recipientId}/auth` | **409** `STEP_NOT_ACTIVE` — ⚠ no publicaba ningún 409 |
| `POST /api/v1/envelopes/{id}/recipients/{recipientId}/signature` | **409** `STEP_NOT_ACTIVE`, **por detrás de las comprobaciones de la aserción**. ⛑ **Corregido el 2026-09-16, y la respuesta cambia para un caso** ([`BL-263`](../BACKLOG.md), ADR-0066 §2.6): esta celda decía *“por delante de las comprobaciones de la aserción: un acto que lleva aserción recibe el paso y no `ASSERTION_NOT_ACCEPTED`”*, y el código hacía eso. Ahora un destinatario `SIGNING_PLATFORM` que **lleva** aserción sobre un paso dormido recibe `ASSERTION_NOT_ACCEPTED` y no `STEP_NOT_ACTIVE`, porque esperar a su paso no le arregla nada: esa ruta nunca es suya con aserción, y antes gastaba dos viajes para acabar en el mismo rechazo. `STEP_NOT_ACTIVE` sigue siendo la respuesta para todo acto cuya **forma** sí acepta la ruta: un destinatario `MACHINE_KEY` que asierta correctamente, y un acto **relevado** (ceremonia nuestra, sin aserción) sobre una sesión ya abierta. ⚠ Una llamada **sin** aserción no llega a esa guarda mientras no exista ya una sesión para ese destinatario — sin aserción la ruta no abre ninguna, y un destinatario delegado contesta `ASSERTION_REQUIRED` desde la rama de *no hay sesión*, que está por encima de todo |

En las dos gemelas y en la firma delegada, un sobre muerto sobre un paso dormido conserva también la
respuesta de hoy.

⛑ **Nada de esto añade trabajo al frontal** (añadido el 2026-09-16 con la corrección de la fila
anterior): la ruta delegada es de integrador, no del signer, y los dos códigos que se intercambian en
ese caso — `STEP_NOT_ACTIVE` y `ASSERTION_NOT_ACCEPTED` — ya estaban publicados en ella. Lo que cambia
es **cuál** de los dos llega, y solo cuando la llamada lleva una aserción que esa ruta no acepta.

⚑ **Dos códigos, uno por audiencia, y los dos ya existían.** `RECIPIENT_STEP_NOT_ACTIVE` es el del lado
del emisor y es **el mismo string** que ya devuelve el reenvío de invitación
([TASK-041](TASK-041-invitation-resend.md)) para el mismo hecho: quien ya ramifica sobre él allí no tiene
que aprender otro. `STEP_NOT_ACTIVE` es el de la ceremonia, y las gemelas de máquina lo comparten porque
ejecutan exactamente los mismos casos de uso que las rutas del navegador.

## Lo que el frontal tiene que hacer

### Signer

1. **El commit — obligatorio.** En `useSignFlow`, `mapError` manda un 409 cuyo `code` es `CONFLICT` o
   `ALREADY_SIGNED` a `/done`, y **cualquier otro 409 cae a la rama genérica**: pantalla de fallo
   (`kind: 'failed'`) **y** `reportError` a Sentry como *un firmante que no pudo firmar*. Hoy un 409
   `STEP_NOT_ACTIVE` acaba ahí, aunque el comentario encima de esa rama diga que esos códigos *"are
   handled below"* — no hay ninguna rama más abajo que los trate.
   - Añadid una rama para 409 `STEP_NOT_ACTIVE` **antes** de la genérica que haga lo que ya hacen
     `auth.vue` y `view.vue`: guardar el error en el store de sesión (`session.setError`) y **después**
     navegar a `errorCodeToPath(token, code, status)`, que ya lleva `STEP_NOT_ACTIVE` a `/unavailable`.
     Guardarlo antes importa: las pantallas de estado exigen un veredicto para ese enlace y, sin él,
     rebotan al índice.
   - **No lo reportéis a Sentry.** Es un resultado de negocio con pantalla propia, el mismo criterio con
     el que ese fichero ya excluye las ramas de arriba.
   - ⚠ Ese comentario nombra también `RECIPIENT_DELEGATED` y `ROLE_NOT_INTERACTIVE`, que tienen la misma
     caída. Si esta ruta los publica, miradlo en el spec. No es de esta tarea, pero la rama que añadáis
     puede cubrirlos a la vez.
   - **Cuándo se alcanza después del despliegue**: casi nunca, porque la apertura y el descriptor
     rechazan antes. Hace falta una credencial emitida **antes** del despliegue, o una pestaña que ya
     estaba en `/sign`. Mientras no esté vuestra rama, ese firmante ve un fallo genérico en vez de *"aún
     no te toca"*.
2. **Apertura, descriptor, read-model y bytes — nada que cambiar.** Medido en vuestro `develop`:
   - El `catch` del middleware global enruta los fallos de `start` y de `getSession` por
     `errorCodeToPath`.
   - El `catch` del descriptor en `auth.vue` también, y deja el error en el store antes de navegar.
   - Un 404 de bytes en el visor llama a `askSessionAfterMissingBytes`, que pregunta al read-model. El
     409 de éste enruta igualmente a `/unavailable`.
   - **No convirtáis el 404 de bytes en `/invalid`**: el read-model es quien explica el motivo.
3. **Envío de código y respuesta de código — opcional.** `useAuthChallenge` no tiene rama para este 409:
   - en el envío del montaje no pinta nada;
   - en reenviar o elegir canal pinta *"no se ha podido reenviar"*;
   - en la respuesta pinta el mensaje genérico.

   Solo lo ve una pantalla cargada antes del rechazo, porque la apertura y el descriptor contestan
   primero. Recargar lo arregla solo: el middleware reabre, recibe el 409 y va a `/unavailable`. Si os
   sale barato, enrutadlo por `errorCodeToPath` como el resto.
4. **La copy no se toca.** La variante por defecto de `/unavailable` dice *"No disponible aún — Tu turno
   para firmar aún no ha llegado."* (en: *"Not available yet — Your turn to sign has not arrived yet."*).
   Hasta hoy esa copy describía un caso que nunca llegaba; desde este cambio describe exactamente el que
   llega.

### Quien acuña enlaces o firma por máquina

1. **Mint → 409 `RECIPIENT_STEP_NOT_ACTIVE`: parad y esperad al paso.** Reintentar no lo cura. **Acuñar
   por adelantado enlaces para pasos posteriores deja de funcionar**: el destinatario recibe su invitación
   sola cuando su paso se activa.
2. **Gemelas de autenticación y firma delegada → 409 `STEP_NOT_ACTIVE`**: el mismo significado. No
   reenviéis el código ni la aserción en bucle.
3. **Los enlaces que ya acuñasteis antes del despliegue para pasos dormidos siguen existiendo, y no se
   revocan.** Cada uso se rechaza mientras el paso no se active; en cuanto se activa, **funcionan con
   normalidad**. No los descartéis ni los deis por muertos.

## Lo que NO está listo todavía

- **El despliegue, de los dos lados, y es uno solo.** La rama backend está mergeada en `develop` en `f490218` y
  pusheada, y **no está desplegada**; la del signer está pusheada en vuestro `develop` hasta `7ce2958` y tampoco
  está desplegada (fila *Status*). ⛑ Decía *«la del signer está commiteada en vuestro `develop` y sin push»* hasta
  que la pusheasteis, el 2026-09-16. ⛔ Ese `develop` lleva también [TASK-043](TASK-043-a-refused-commit-names-its-condition.md), y los dos lados salen
  **en el mismo despliegue** (*El orden de salida* de ese traspaso, enmendado el 2026-09-16). `STEP_NOT_ACTIVE`, por
  sí mismo, pesa poco: contra este backend, el signer viejo ya manda la apertura, el descriptor y el read-model a
  `/unavailable`, y únicamente el commit y las dos llamadas de código caen al fallo genérico. ⛑ **Corregido el
  2026-09-16, al mergear**: esta viñeta decía *«La rama backend no está mergeada, ni pusheada, ni desplegada»*; y
  antes aún, *«El cambio del signer, que es este traspaso. Y la rama backend, que no está mergeada ni desplegada»*.
- **Nada os avisa de que un paso se ha activado.** Los webhooks de integrador
  ([ADR-0064](../adr/ADR-0064-outbound-integrator-webhooks.md)) están `Proposed` y sin construir.
- **`POST /api/v1/signing/session/renew` no pregunta por el paso.** Quien tenga una credencial emitida
  antes del despliegue sobre un paso dormido puede seguir renovándola; todo lo que esa credencial compra
  lo rechaza. **Una renovación correcta no significa que el firmante esté admitido.**
- **Un destinatario con la pierna `DELEGATED` o `SKIPPED` sigue siendo invisible** a la apertura, al
  descriptor y al envío de código ([`BL-183`](../BACKLOG.md), su mitad de *resultado*). Esto cruza el
  paso, no el resultado. Hoy nada escribe esos dos estados.
- **Los sobres de preprod ya corrompidos no se diagnostican ni se reparan.** Puede haber sobres
  `COMPLETED` con pasos que nunca se activaron, y este cambio no altera lo que un cliente lee de ellos.

## Lo que NO existirá, y por qué

⛔ **No habrá un código distinto para *aún no* y para *saltado*** (un `STEP_NOT_YET_ACTIVE`). Nada escribe
`SKIPPED`, así que el código tiene hoy un único significado vivo. Un código nuevo caería en vuestro
`default` hasta que saliera a la vez un cambio vuestro. El día que `SKIPPED` tenga quien lo escriba y un
remedio distinto, ése es el momento de partirlo
([ADR-0066](../adr/ADR-0066-no-recipient-acts-before-their-step.md) §7.4).

⛔ **No se revocarán los enlaces ya acuñados.** Emitir es aditivo y el enlace se guarda solo como digest.
La revocación se descartó sobre el registro
([ADR-0045](../adr/ADR-0045-issued-credential-format.md) §2.6,
[TASK-028](../tasks/TASK-028-opaque-signing-token.md) §4.3), y la única retirada que existe es la de una
corrección de contacto
([ADR-0060](../adr/ADR-0060-retiring-a-credential-whose-holder-changed.md) §2.6). Por eso se rechaza cada
uso en vez del enlace.

⛔ **El firmante no recibirá un 404 por esto, salvo en los bytes.** Un destinatario dormido está en un
sobre **enviado**, figura en él y el flujo va a llegar a él. Su ceremonia existe y todavía no ha
empezado. *Enlace equivocado* y *vuelve más tarde* no comparten remedio, y una respuesta
indistinguible de un id erróneo le haría abandonar un enlace bueno
([ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md) §2.4,
[ADR-0056](../adr/ADR-0056-terminal-state-on-pre-credential-routes.md) §2.5). Los bytes siguen en 404
porque esa ruta contesta 404 por cualquier motivo y el read-model es quien lo explica
([ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md) §2.5).

⛔ **No se apretará a *activado y sin completar*.** Parecería más estricto, y le cerraría la puerta a
quien vuelve a un paso ya completado a por la copia que firmó.

## Cómo verificarlo desde el frontal

1. `GET /api/doc.json` → `GET /api/v1/signing/session/auth` publica una respuesta **409**, y lo mismo las
   dos gemelas de máquina. Si no la publican, ese despliegue es anterior a este cambio. ⚠ **No sirve
   buscar los códigos en `components.schemas.ProblemCode`**: los dos ya estaban, así que su presencia no
   dice nada del despliegue. ⚑ **Corregido 2026-09-16**: esto decía que la prosa de *esas* 409 se reescribió al
   final de la rama, y no es cierto — el descriptor y las dos gemelas no se han tocado desde que ganaron su
   409. Las que sí se reescribieron al final (`ac3152c`) son otras tres: `POST /signing/commit`,
   `GET /signing/session/documents/{id}` y `POST /signing-tokens`. En cualquier caso la versión que vale es
   la del `doc.json` que os sirvan, que por la regla 1 del README esta nota no copia.
2. Sobre `SIGN_ORDERED` de tres pasos, enviado; solo el paso 1 activo.
3. `POST /api/v1/signing-tokens` para el destinatario del paso 3 → **409**
   `code: "RECIPIENT_STEP_NOT_ACTIVE"`. Para el del paso 1 → **201**, como siempre.
4. El destinatario del paso 1 firma → **200**. Es el control positivo: sin él, el paso anterior pasaría
   también en un sistema que rechaza a todo el mundo.
5. **La rama del commit se prueba en vuestros tests unitarios**, contra un 409 `STEP_NOT_ACTIVE` simulado:
   `/unavailable`, sin evento de Sentry. Contra el backend es difícil de provocar, justo porque el mint y
   la apertura rechazan antes. Hace falta un enlace acuñado antes del despliegue, o uno emitido
   directamente en una pila de pruebas.
