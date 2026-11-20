# Traspaso al frontal — un commit rechazado dice por qué

<!-- OFFREPO: lo que este documento afirma sobre el lado cliente viene del informe de la sesión de
`f5sign-signer` del 2026-09-16 (`app/composables/useSignFlow.ts`, `mapError`, leído por ellos en
`develop` `c894f88`) y de lo que esa misma sesión dice haber construido ya. Está reescrito en línea
donde se usa; nada de aquí exige tener ese repo delante, y nada de aquí se puede volver a medir desde
este. La columna «lo que hacéis con cada código» es **vuestra decisión, recogida**, no una
instrucción nuestra. -->
<!-- OFFREPO: la fila *Status* se escribió el 2026-09-16 leyendo el clon de `f5sign-signer`, no su
sesión: `639a788`, `2f4e721`, `eb5ac02` y `1638c6b` están en su `develop` y los cuatro salen en
`git log origin/develop..develop`, o sea sin push. El verde que citan (lint + typecheck + 2938 unit) está
en sus mensajes de commit y no se volvió a correr desde aquí. Actualizado el 2026-09-16, más tarde, leyendo el
mismo clon: `origin/develop` = `develop` = `7ce2958`, y `git log c894f88..origin/develop` lista seis commits —
los cuatro de arriba, `01ffece` y `7ce2958` —; o sea, pusheado. -->
<!-- OFFREPO: *El orden de salida* se enmendó el 2026-09-16 con hechos de `f5sign-signer` leídos ese día en
su clon: `app/composables/useSignFlow.ts` en `c894f88` (`mapError` manda un 409 a la página de hecho solo con
`ALREADY_SIGNED` o `CONFLICT`, su rama de último recurso llama a `reportError`, y `retry()` repite el flujo
entero); el diff de `01ffece`, que quita `code === 'CONFLICT'` de esa condición; y
`.output/public/_nuxt/builds/latest.json` en un build local (solo las claves `id` y `timestamp`). Que los dos
lados salen en el mismo despliegue es decisión de los dos mantenedores tal como se nos transmitió ese día, no
algo leído en un árbol. El sha de `01ffece` cambió antes del push (enmendaron su mensaje): cualquier otro sha
para ese commit está obsoleto. -->

| | |
|---|---|
| **Origen** | rama `fix/conflict-taxonomy`, **mergeada en `develop` en `acb20d0`** (encima del merge de TASK-042, `f490218`) **y pusheada** el 2026-09-16, sin PR — y **sin desplegar**: `develop` no es un despliegue (regla 4 del README); lo que manda es la fila *Desplegado* · commit `117f7d3` (el último que cambia código o prosa publicada en `src/`; por encima hay documentación y la corrección de un docblock que no llega al `doc.json`, así que no era la punta de la rama. ⛑ Hasta el 2026-09-16 decía *«el último que toca `src/`; por encima solo hay documentación»*) · [ADR-0067](../adr/ADR-0067-a-refused-commit-names-its-condition.md) (**`Accepted (exercised)`** desde el 2026-09-16) · [TASK-043](../tasks/TASK-043-a-refused-commit-names-its-condition.md). ⛑ **Corregido el 2026-09-16, al mergear**: la fila abría *«rama `fix/conflict-taxonomy` · commit `117f7d3`»*, sin decir nada del merge, acababa en *«sin PR todavía»* y el paréntesis decía *«así que no es la punta»*. ⛑ **Actualizado el 2026-09-16**: esta fila decía `8e99f33` *“el último que toca `src/` — los posteriores son tests y este documento”* y el ADR en `Proposed`. `360cbfc` y `117f7d3` tocaron `src/` después: los dos cambian el texto de los 409 que este documento describe, y ninguno cambia comportamiento; y el mantenedor aceptó el ADR ese mismo día. ⚠ **Aceptado no es desplegado**: lo que manda es la fila *Desplegado* |
| **Fecha** | 2026-09-16 |
| **Repos afectados** | **signer** — obligatorio, y **en el mismo despliegue** que nosotros (ver *El orden de salida*; ⛑ decía *«y **antes** que nosotros»* hasta el 2026-09-16) · **integradores con clave de máquina** — la firma delegada gana los mismos códigos |
| **Naturaleza** | **aditivo en el esquema, y aun así rompe comportamiento para un consumidor**: ninguna ruta, campo ni estado nuevo; tres códigos nuevos en `ProblemCode` y un `CONFLICT` pelado que deja de llegar donde antes llegaba. ⚑ **Y corrige el spec de paso**: seis bloques `#[OA\*]` publicaban un `code` ausente como afirmación positiva |
| **Acción requerida** | **ramificar cuatro `code` en el 409 de `POST /api/v1/signing/commit`** · quitar la rama de `CONFLICT` (hecho: `01ffece`) · **desplegar en el mismo despliegue que este backend**, ni antes ni después (*El orden de salida*). ⛑ **Cambiado el 2026-09-16, confirmado por el mantenedor**: decía *«conservar la rama de `CONFLICT` hasta que esto esté **desplegado**»* |
| **Desplegado** | not yet — ni el backend (mergeado en `develop` en `acb20d0` y pusheado, **sin desplegar**) ni el signer (pusheado en `develop` hasta `7ce2958`, **sin desplegar**). Y los dos salen **en el mismo despliegue** (*El orden de salida*). ⛑ **Corregido el 2026-09-16, al mergear y al pushear el signer**: decía *«ni la rama backend (sin merge y sin push) ni la del signer (sin push)»*; antes aún, solo *«la rama no está mergeada»* |
| **Status** | **Applied en `f5sign-signer` `develop`, pusheado** (2026-09-16; rango `c894f88..7ce2958`, seis commits): `639a788` enruta los dos traspasos, este y el de [TASK-042](TASK-042-no-recipient-acts-before-their-step.md); `2f4e721` fuerza un código nuevo solo ante `SIGNING_CHALLENGE_MISBOUND`; `eb5ac02` deja como hecho leído lo que asumían del reto caducado; `1638c6b` mueve sus citas a nuestra 409 publicada; **`01ffece` quita la rama de `CONFLICT`** de `mapError` y alinea `click-sign.vue` con la partición; `7ce2958` regenera su snapshot del contrato desde nuestro `develop`. ⚑ **Escrito desde su árbol y no desde su sesión** (*El punto débil* del README). ⚠ **No queda ninguna pieza de código; queda el despliegue conjunto** (fila *Desplegado*). ⛑ **Actualizado el 2026-09-16, al pushear el signer**: esta fila decía *«Applied en `f5sign-signer` `develop`, sin push»* con cuatro commits, *«dice sin push porque es lo que ese árbol dice»* y *«Queda una pieza, y todavía no le toca a nadie: quitar la rama de `CONFLICT`, que espera a que esto esté **desplegado**»*. ⛑ **Actualizado el 2026-09-16**: esta fila decía `Pending` |

> ⛔ **Qué arregla: la pantalla de «firmado» sobre una firma que no ocurrió.** `POST /api/v1/signing/commit`
> contestaba el mismo `409 CONFLICT` para *ya estaba firmado*, *el sobre fue anulado* y *el código de
> firma no autoriza estos documentos*. Vuestro `mapError` manda un 409 `CONFLICT` a `/s/{token}/done`,
> que pinta su variante de éxito — así que en dos de los tres casos **no se firmó nada** y la única
> pantalla que un firmante se cree sin dudar le decía lo contrario. Lo reportasteis vosotros, y
> demostrasteis que no se podía cerrar por vuestro lado: los tres eran idénticos byte a byte, y
> ramificar sobre `status` es justo lo que nuestra propia prosa publicada prohíbe. [`BL-259`](../BACKLOG.md).

## Lo que cambió en el contrato

**Cuatro condiciones que contestaban un solo término pasan a contestar cuatro.** La excepción de
dominio que hay detrás (`SigningSessionStateException`) ahora lleva su propio `code`, uno por
condición. Ni el status ni la forma del cuerpo se mueven: sigue siendo un `409` con
`application/problem+json` y `code` sigue siendo un string abierto en el esquema, así que ningún
cliente generado rechaza un valor que no conocía.

### Los tres códigos nuevos

| `code` | Qué pasó | Qué NO pasó |
|---|---|---|
| **`SESSION_ALREADY_COMPLETED`** | Esta pierna ya estaba cerrada **por el acto de este mismo destinatario**. Un segundo commit con la credencial todavía viva aterriza aquí en vez de firmar dos veces | — es el único de los cuatro en el que **sí hay firma** |
| **`SESSION_CLOSED`** | La sesión de firma se cerró **sin que este destinatario actuara**. Hoy solo ocurre porque el remitente anuló el sobre | no se firmó nada y no se va a firmar |
| **`SIGNING_CHALLENGE_MISBOUND`** | Había un código de **firma** verificado, y autoriza un conjunto de documentos **distinto** del acto que se está confirmando | no se firmó nada; y **volver a pedir el mismo código no arregla nada**. ⚠ Un código ya **gastado** es otra respuesta y no ésta: cae en un `401`, porque la prueba ya no está en vez de no encajar |

Y un cuarto, **que no es nuevo**: **`ENVELOPE_NO_LONGER_LIVE`** — el sobre no estaba vivo en el
momento del commit. Ya lo publicábamos en otras tres rutas (la apertura, el read-model y la prosa de
los bytes), así que es posible que ya tengáis rama para él.

⚑ **`SESSION_ALREADY_COMPLETED` y no `ALREADY_SIGNED`, aunque `ALREADY_SIGNED` fuese la que vuestro
`mapError` ya nombra.** `commitSignature` es el acto de **todos** los roles interactivos, no solo del
firmante: un `APPROVER` con pierna bloqueante registra su consentimiento por el mismo sitio. Un
término que afirma que alguien *firmó* es falso para quien aprueba. Ese ahorro era real y se gasta a
propósito; el orden de salida de abajo es lo que lo paga. ⚠ **`ALREADY_SIGNED` se retira**: lo
publicaba la ruta delegada, no lo emitía nada y no estaba en el catálogo, así que quien ramificara
sobre él nunca casaba ([`BL-249`](../BACKLOG.md)).

### Por qué son DOS códigos para un sobre muerto y no uno

`SESSION_CLOSED` y `ENVELOPE_NO_LONGER_LIVE` significan lo mismo para el firmante: no se firmó nada y
no se va a firmar. **Para un caso de soporte no**: cuál de los dos contesta depende de si la reacción
interna que cierra las sesiones de un sobre anulado ha llegado ya. `SESSION_CLOSED` dice *la
revocación corrió*; `ENVELOPE_NO_LONGER_LIVE` dice *todavía no*. Ese salto es invisible desde fuera y
un solo código lo escondería.

▶ **Para vosotros eso significa que los dos van al mismo sitio.** No hay ninguna decisión de producto
que dependa de cuál de los dos llegó.

⚑ **Un hecho verificado que os interesa, y que es de hoy, no para siempre.** Una sesión `REVOKED`
viene **solo** de una anulación del remitente: `SigningSession::revoke()` tiene un único llamante de
producción (`RevokeEnvelopeSessionsUseCase`, reaccionando a `EnvelopeVoided`), ese hecho lo escribe
solo `Envelope::void()`, y a ese método solo se llega desde el caso de uso de anulación del emisor. El
vencimiento y el rechazo **no** pasan por ahí (hoy no existen en el lado de escritura). ⚠ El nombre es
deliberadamente inespecífico precisamente para que siga siendo verdad el día que sí existan — no
deduzcáis «anulado por el remitente» del código; deducid «cerrada sin que tú actuaras».

### El `CONFLICT` pelado: qué queda debajo

Después de este cambio, un `409` **sin** `code` reconocible en el commit significa **una sola cosa**:
*la puerta de acceso no se ha pasado* (`notAuthenticated`). En la ruta del firmante eso es
inalcanzable — esa ruta exige credencial de sesión, y la credencial solo se acuña pasando la puerta —
así que en la práctica no lo vais a ver. En la ruta **delegada** de máquina sí se alcanza: un
destinatario `SIGNING_PLATFORM` cuya ceremonia el integrador solo *releva*, si confirma sin haber
relevado el código.

### Las seis 409 publicadas que cambian

| Ruta | Qué cambia en su `#[OA\*]` |
|---|---|
| `POST /api/v1/signing/commit` | deja de argumentar la omisión y publica la partición, con un remedio por código |
| `POST /api/v1/envelopes/{id}/recipients/{rid}/signature` | `ALREADY_SIGNED` → `SESSION_ALREADY_COMPLETED`, y gana los otros tres |
| `POST /api/v1/signing/session/auth` | decía *«Otherwise, with no `code`: the envelope is no longer live, or the session is already completed»*. Esa frase deja de ser cierta: ahora nombra los tres |
| `POST /api/v1/signing/session/auth/otp/send` | decía *«Also the usual conflict cases: …»*. Igual |
| `POST /api/v1/envelopes/{id}/recipients/{rid}/auth` | remite a la primera y ahora nombra los tres términos, para no obligar a un integrador a leer la prosa de otra ruta |
| `POST /api/v1/envelopes/{id}/recipients/{rid}/auth/otp/send` | igual, remitiendo a la de envío |

⚠ **En las cuatro rutas de puerta no hemos medido si esos brazos son alcanzables** o si los rechazos
de capa de aplicación contestan antes. La corrección no depende de eso: una frase publicada que
afirma la **ausencia** de un `code` es falsa en cualquiera de los dos casos.

## Lo que el frontal tiene que hacer

### Signer — obligatorio

Recogido de lo que vuestra sesión dice haber enrutado ya, para que este documento y lo que
construisteis digan lo mismo. Si algo de esto no coincide con vuestra rama, **gana vuestra rama** y
avisadnos. ⚑ **Contrastado el 2026-09-16 con vuestro `develop`** (`639a788` y `2f4e721`): coincide.
⛑ Decía *«sin push»*; están pusheados desde el 2026-09-16.

| `code` (409) | Destino |
|---|---|
| `SESSION_ALREADY_COMPLETED` | vuestra pantalla de **hecho**, con evidencia positiva de que hay firma |
| `SESSION_CLOSED` | vuestra pantalla de **rechazado / cancelado** |
| `ENVELOPE_NO_LONGER_LIVE` | la misma pantalla de **rechazado / cancelado** |
| `SIGNING_CHALLENGE_MISBOUND` | **reabre la puerta de firma en el sitio**, sin navegar: pedid un código nuevo **con `resend: true`** (ver abajo) |
| `CONFLICT` pelado | ya no va a `/done`: la rama está quitada (`01ffece`) — ver abajo. ⛑ Decía *«lo que hacéis hoy — ver abajo»* hasta el 2026-09-16 |

⛔ **`SIGNING_CHALLENGE_MISBOUND` es el único de los cuatro que no es terminal**, y es el que más fácil
se enruta mal. Reintentar el mismo commit no sirve y **volver a pedir el mismo código tampoco**: hace
falta uno **nuevo**. Por eso no lleva prefijo `AUTH_`: los `AUTH_` que un cliente encuentra en la
puerta son 401 y significan *vuelve a responder la puerta*, y este es un 409 precisamente porque
responder otra vez no puede funcionar. Un cliente que lo leyera como miembro de esa familia entraría
en el bucle que el código existe para romper.

⚑ **Cómo se pide ese código nuevo, y por qué con uno caducado no hace falta — fijado con vosotros el
2026-09-16.** Son dos hechos, y los dos los publica la 409 de `POST /api/v1/signing/commit` desde
`117f7d3`. **Citad esa respuesta del `doc.json`, no este párrafo**: el mecanismo que hay detrás es
nuestro y puede cambiar; la respuesta publicada es lo que os debemos.

- **Un reto `SIGNING_CHALLENGE_MISBOUND` sigue vivo después del rechazo.** Pedir código con
  `resend: false` os devuelve ese mismo, que no sirve; hace falta `resend: true`.
- **Un reto caducado deja de estar vivo solo.** Con `AUTH_CHALLENGE_EXPIRED`, asegurar (`resend: false`)
  ya acuña uno nuevo, sin forzar.

Parecen el mismo caso y se comportan al revés. Vuestro `2f4e721` fuerza solo en el primero, `eb5ac02`
deja el segundo como hecho leído y `1638c6b` cita la 409 publicada en vez de la conversación.
⛑ **Añadido el 2026-09-16**: hasta entonces este documento decía *«pedid un código nuevo»* sin decir cómo,
y la forma por defecto de pedirlo devolvía justo el que no sirve.

⛑ **La rama de `CONFLICT` está quitada (`01ffece`), y lo que os protege pasa a ser el despliegue conjunto.**
**Cambiado el 2026-09-16, confirmado por el mantenedor.** Este párrafo decía *«Mantened la rama de
`CONFLICT` hasta que esto esté DESPLEGADO, y el despliegue es la señal, no el merge»*, y mandaba mirar el
`doc.json` servido para saber cuándo quitarla. Era la regla correcta mientras esa compatibilidad existía:
un backend anterior a este cambio sigue mandando `CONFLICT` para las cuatro condiciones. Al quitarla
antes de desplegar, vuestro signer nuevo deja de funcionar contra ese backend, y por eso los dos lados
salen en el mismo despliegue (*El orden de salida*). ⚑ Lo que no cambia es la regla 4 del README de este
directorio, que también es vuestra: no adoptéis (ni retiréis) nada por lo que diga un `Origen`; cuenta lo
servido.

⚠ **Al quitarla, quitadla entera.** Después del despliegue, un `CONFLICT` pelado en el commit ya **no**
significa *ya firmado*; significa *no autenticado*, que en esa ruta no debería ocurrir. Mandarlo a
`/done` sería reintroducir exactamente el defecto que esto arregla, con una sola condición en vez de
tres.

### Integradores con clave de máquina

`POST /api/v1/envelopes/{id}/recipients/{rid}/signature` gana los mismos cuatro códigos y pierde
`ALREADY_SIGNED`. Los tres terminales significan *parad*; `SIGNING_CHALLENGE_MISBOUND` significa
*conseguid y relevad un código nuevo*, nunca reenviar el mismo — y conseguirlo pide `resend: true` en
`POST /api/v1/envelopes/{id}/recipients/{rid}/auth/otp/send`, por lo mismo que en el signer (lo publica la
409 de esta ruta desde `117f7d3`). Un `CONFLICT` pelado ahí significa que
la puerta de acceso de ese destinatario no se ha pasado: relevad el código por
`POST /api/v1/envelopes/{id}/recipients/{rid}/auth` y después confirmad.

## El orden de salida

⛔ **Enmendado el 2026-09-16, confirmado por el mantenedor: ya no sale primero el signer. Salen los dos en
el MISMO despliegue.** La regla anterior, que se conserva debajo, era correcta mientras vuestra rama
conservaba `CONFLICT` junto a los cuatro códigos, porque entonces un signer nuevo seguía funcionando contra
el backend viejo. Al quitar esa rama antes de desplegar (`01ffece`), la dependencia va en los dos
sentidos, y ninguno de los dos lados puede salir sin el otro:

- **Signer viejo contra backend nuevo.** `SESSION_ALREADY_COMPLETED` es una **regresión**, no un hueco: el
  signer viejo solo manda a `/done` un 409 con `ALREADY_SIGNED` o `CONFLICT`. Quien ya firmó ve la pantalla
  de fallo genérica, con un botón de reintentar que no puede funcionar, y cada reintento es un evento de
  Sentry. `SESSION_CLOSED` y `SIGNING_CHALLENGE_MISBOUND` caen en ese mismo fallo con el mismo reintento
  inútil; en esos dos sí es la dirección buena, porque antes eran un «firmado» falso.
- **Signer nuevo contra backend viejo.** El backend viejo manda `CONFLICT` pelado para *ya estaba
  firmado*, y sin vuestra rama de compatibilidad eso cae en vuestro fallo genérico.
- **`STEP_NOT_ACTIVE`** ([TASK-042](TASK-042-no-recipient-acts-before-their-step.md)) va en el mismo
  `develop` y pesa poco: el signer viejo ya manda la apertura, el descriptor y el read-model a
  `/unavailable`, y solo el commit y las dos llamadas de código caen al fallo genérico.

▶ **Hecho es lo servido, no las ramas.** Antes de darlo por cerrado hacen falta las dos cosas:

1. **El backend servido incluye `acb20d0`.** Este backend no sirve ningún id de commit, así que desde
   fuera la prueba es que el `doc.json` de ese despliegue lleve `SESSION_ALREADY_COMPLETED` en
   `components.schemas.ProblemCode`.
2. **El bundle servido del signer incluye `01ffece`**, el commit que quita la rama de `CONFLICT`. Se prueba
   por **contenido** del bundle servido, no por la rama ni por la fecha:
   - **PROBADO** si algún chunk contiene `SESSION_ALREADY_COMPLETED` **y** ningún chunk contiene el literal
     `"CONFLICT"`. Lo primero existe desde `639a788`; lo segundo desaparece justo en `01ffece`, porque era la
     condición vieja de `mapError`.
   - **Prueba comportamiento, no el sha**: que el bundle enruta la partición y ya no lee un `CONFLICT`
     pelado, que es lo que el cierre necesita. **Falla cerrado**: si una dependencia futura trae el literal
     `"CONFLICT"`, o alguien lo reintroduce, dirá NO PROBADO, nunca un probado falso.
   - Uso: `python3 probe.py https://<host-del-signer>` (solo librería estándar). Recorre el cierre
     transitivo de chunks desde el HTML servido, así que la mitad de «ausencia» no puede saltarse el chunk
     de `mapError`:

     ```python
     import re, sys, urllib.request
     base = sys.argv[1].rstrip('/')
     def get(p):
         with urllib.request.urlopen(base + p, timeout=20) as r:
             return r.read().decode('utf-8', errors='ignore')
     todo = set(re.findall(r'/_nuxt/([A-Za-z0-9_-]+\.js)', get('/')))
     seen, bodies = set(), {}
     while todo:
         c = todo.pop()
         if c in seen: continue
         seen.add(c)
         try: bodies[c] = get('/_nuxt/' + c)
         except Exception: continue
         todo |= set(re.findall(r'([A-Za-z0-9_-]{6,}\.js)', bodies[c])) - seen
     if not bodies: sys.exit('NOT PROVEN — no chunk could be fetched')
     sac = [c for c, b in bodies.items() if 'SESSION_ALREADY_COMPLETED' in b]
     conflict = [c for c, b in bodies.items() if re.search(r'["\']CONFLICT["\']', b)]
     print(f'build: {get("/_nuxt/builds/latest.json").strip()}')
     print(f'chunks: {len(bodies)} | SESSION_ALREADY_COMPLETED: {sac or "none"} | "CONFLICT": {conflict or "none"}')
     if sac and not conflict: print('PROVEN — served bundle >= 01ffece')
     else: sys.exit('NOT PROVEN — bundle predates 01ffece (or something unexpected)')
     ```
   <!-- OFFREPO: la sonda y sus mediciones son del lado `f5sign-signer`, 2026-09-16, y se restatan aquí: un
   negativo real contra el bundle auténtico del 2026-09-02 (`SESSION_ALREADY_COMPLETED` en 0 chunks,
   `"CONFLICT"` en exactamente 1 — la condición vieja de `mapError`, literal que ninguna librería contiene);
   un positivo contra `pnpm generate` en `7ce2958` servido por HTTP (81 de 81 chunks, PROBADO, exit 0); y un
   negativo por HTTP con la condición vieja reinyectada (NO PROBADO, exit 1). Nada de esto se puede volver a
   medir desde este repo. -->
   ⛑ **Corregido 2026-09-16**: esta comprobación decía *«se mira en `/_nuxt/builds/latest.json` de ese
   despliegue»*. Ese fichero solo trae `{"id", "timestamp"}`: dice **qué** bundle se sirve, no **qué
   contiene**, y comparar su fecha con la del commit es un indicio, no una prueba — un build posterior desde
   otra rama también saldría «más nuevo». La sonda imprime ese `id` igualmente, como dato. ⚠ Es una
   comprobación de **un** despliegue, con los marcadores de este commit fijados; no es una herramienta
   permanente. Que el bundle exponga su commit sería la solución general, y es decisión de `f5sign-signer`.
   ⚠ Y `01ffece` cambió de sha antes del push (enmendasteis su mensaje): cualquier otro sha para ese commit
   está obsoleto.

El `develop` de ninguno de los dos lados responde a esto, y hoy no hay nada desplegado en ninguno de los
dos.

⚠ **Lo que sigue es la regla hasta el 2026-09-16**, y se conserva porque explica por qué un orden
secuencial era el correcto mientras la compatibilidad existía:

⛔ **El signer sale primero, y esto no es una preferencia: es la única dirección segura.** Vuestra rama
actual manda `CONFLICT` a `/done`. En cuanto el backend deje de mandar `CONFLICT` para *ya estaba
firmado*, ese caso cae a la pantalla de fallo genérica mientras no conozcáis
`SESSION_ALREADY_COMPLETED`. Es la dirección **buena** del mismo defecto — un fallo genérico en vez de
un «firmado» falso — pero es una regresión visible, y por eso este traspaso se escribe **antes** del
merge y no con él. Es la segunda vez que nos pasa la misma forma: la primera fue `STEP_NOT_ACTIVE`
([TASK-042](TASK-042-no-recipient-acts-before-their-step.md)). ⚑ **2026-09-16: vuestro `develop` ya
conoce los cuatro** (`639a788`, sin push), así que el orden ya no espera a que lo escribáis, sino a que
lo despleguéis antes que nosotros.

⚠ **Nada en nuestro repo puede vigilar esto** ([`BL-235`](../BACKLOG.md)): vuestro gate no ve nuestro
spec y el nuestro no ve vuestro código. Lo sostienen este documento y la revisión.

## Lo que NO está listo todavía

- **El despliegue, de los dos lados, y es uno solo.** La rama backend está mergeada en `develop` en
  `acb20d0` y pusheada, y **no está desplegada**; la del signer está pusheada en vuestro `develop` hasta
  `7ce2958`, con la retirada de la rama de `CONFLICT` dentro (`01ffece`), y tampoco está desplegada (fila
  *Status*). Los dos salen en el mismo despliegue (*El orden de salida*). ⛑ **Corregido el 2026-09-16, al
  mergear, al cambiar el orden y al pushear el signer**: esta viñeta decía *«La rama backend no está
  mergeada, ni pusheada, ni desplegada; la del signer está commiteada en vuestro `develop` y sin push … Hasta
  que el `doc.json` que os sirve publique `SESSION_ALREADY_COMPLETED`, la rama de `CONFLICT` se queda»*; y
  antes aún, *«El cambio del signer, que es este traspaso. Y la rama backend, que no está mergeada ni
  desplegada»*.
- **Nada comprueba que una 409 publicada enumere todos los códigos que esa ruta emite**
  ([`BL-209`](../BACKLOG.md)). Los seis bloques de arriba se editaron a mano y los sostiene la
  revisión. Si encontráis un `code` que llega y no está en el `doc.json`, es un fallo nuestro y
  queremos saberlo.
- **`ADR-0067` ya está en `Accepted (exercised)`, y eso tampoco lo despliega.** Lo aceptó el mantenedor el
  2026-09-16. En este repo *Accepted* significa *ejercitado*, no *mergeado* ni *desplegado*. ⛑ Esta viñeta
  decía *“`ADR-0067` sigue en `Proposed` … No cambia nada de lo que se describe aquí”*, y lo segundo sigue
  siendo cierto: vuestra señal es el `doc.json` servido, no la etiqueta del ADR.
- **Los dos sobre-anuncios que quedan en la 409 delegada** (`ENVELOPE_NOT_SENT` y
  `RECIPIENT_SLOT_NOT_CLAIMED`) siguen publicados y ese caso de uso no los emite. No son de esta
  tarea; no ramifiquéis sobre ellos.

## Lo que NO existirá, y por qué

⛔ **No habrá un `code` para *no autenticado* en el commit.** Se queda en el `CONFLICT` derivado del
status, a propósito: después de este cambio esa condición está **sola** ahí, así que un `CONFLICT`
pelado ya no colapsa nada — que es exactamente para lo que existe un valor por defecto. Si algún día
una segunda condición se le une, se le pondrá nombre; hay un censo en nuestros tests que se pone rojo
el día que eso pase en silencio.

⛔ **No habrá un código distinto para *anulado por el remitente* y *cerrada por otra causa*.**
`SESSION_CLOSED` es deliberadamente inespecífico para sobrevivir a la segunda causa (un rechazo, un
vencimiento) sin volverse falso. El día que esa segunda causa exista y tenga un **remedio distinto**,
ése es el momento de partirlo, no antes.

⛔ **No se moverá `notAuthenticated` a 401.** Su remedio es *demuestra algo*, que es lo que instruye un
401, pero está en 409 porque es un conflicto de ciclo de vida. Moverlo es una decisión sobre la
frontera de `ConflictException`, no una edición de paso.

## Cómo verificarlo desde el frontal

1. `GET /api/doc.json` → `components.schemas.ProblemCode` contiene `SESSION_ALREADY_COMPLETED`,
   `SESSION_CLOSED` y `SIGNING_CHALLENGE_MISBOUND`, y **ya no contiene** `ALREADY_SIGNED` (nunca lo
   contuvo). Si no están, ese despliegue es anterior a este cambio y sigue mandando `CONFLICT`.
2. La 409 de `POST /api/v1/signing/commit` en ese mismo `doc.json` enumera los cuatro con su remedio.
   Es la versión que vale; por la regla 1 del README de este directorio, este documento no la copia.
3. **Firmad dos veces con la misma credencial**: la primera → `200`; la segunda → `409` con
   `code: "SESSION_ALREADY_COMPLETED"`. Es la comprobación más barata de las cuatro y no necesita
   ningún estado especial.
4. **Anulad el sobre desde el panel del remitente y confirmad después**: `409` con
   `code: "ENVELOPE_NO_LONGER_LIVE"` o `code: "SESSION_CLOSED"` — cuál de los dos depende de si la
   reacción interna ha corrido ya, y para vosotros los dos van al mismo sitio.
5. `SIGNING_CHALLENGE_MISBOUND` es difícil de provocar contra el backend a mano: hace falta que el
   conjunto firmable se mueva por debajo de un código de firma ya verificado. **Probad esa rama en
   vuestros tests unitarios** contra un 409 simulado, como hicisteis con `STEP_NOT_ACTIVE`.
6. **Control positivo**: un firmante limpio firma y recibe `200`. Sin él, los pasos anteriores pasan
   también en un sistema que rechaza a todo el mundo.
