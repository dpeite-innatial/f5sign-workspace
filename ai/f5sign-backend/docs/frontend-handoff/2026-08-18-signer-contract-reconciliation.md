# Traspaso al frontal — `f5sign-signer` llama a siete rutas que no existen, y su botón de descarga sí puede funcionar hoy

| | |
|---|---|
| **Origen** | **en `develop`, commit `7e9f610`** · sin PR. ⚠ Ese commit dice *"fix(event-log): reject an undecodable message instead of dying on it"* y **no menciona este fichero**, así que no es localizable por su mensaje: entraron juntos por un `git add -A` en un checkout que dos sesiones compartían sin saberlo. Quien firma ese commit **no** escribió este documento. La cabecera anterior se autoatribuía a `feat/event-decoding-failure-dead-letter` @ `0d8c383`, que era de dónde salió el árbol, no de quién lo escribió |
| **Fecha** | 2026-08-18 |
| **Repos afectados** | **signer** únicamente. El dashboard queda fuera de este traspaso |
| **Naturaleza** | **no hay cambio de contrato, y ese es el punto.** Es una reconciliación: la divergencia entre lo que el signer llama y lo que el backend expone ya existía, y nadie la había puesto por escrito |
| **Acción requerida** | **arreglar la descarga** (1 abajo) · **aparcar código muerto** (2, 3 — con una excepción: `/expired` **se queda**, ver 3) · **no construir** sobre los cinco bloques stub (§NO está listo) |
| **Status** | Pending |

> ⚑ **Antes de tocar nada: hay trabajo sin commitear en `f5sign-signer@develop`** — 51 ficheros
> modificados y 7 sin trackear (la aplicación del traspaso de `occurrences`; `FieldOccurrence` ya está
> tipado y las fixtures regeneradas). **Commitea eso primero.** Todo lo de aquí toca
> `app/composables/api/types.ts`, que está en ese conjunto: empezar antes garantiza el conflicto.

## Lo que cambió en el contrato — nada, y eso es el punto

Ninguna ruta, campo ni enum ha cambiado en este commit. Lo que este documento hace es **medir** el
contrato publicado contra lo que el signer consume, porque el desfase se había acumulado en silencio: el
adapter real llama a siete rutas que no existen, y hay seis ramas de error que no pueden ejecutarse nunca.

Todo lo que sigue es medible contra `develop` tal cual. (Una primera versión de esta sección avisaba de que
el arma `DELIVERY_FAILED` → `AUTH_PASSED` del `match` de `SigningSessionReader::status()` todavía no estaba
en `develop`; TASK-025 aterrizó y esa salvedad ya no aplica.)

El inventario autoritativo de rutas es `php bin/console debug:router`, no los ficheros de rutas. Hoy la
superficie de firma es **cinco** rutas: acuñar token, abrir sesión, leer sesión, bytes de un documento,
y commit. Las formas exactas están en `GET /api/doc.json`; aquí sólo va qué hacer.

## Lo que el frontal tiene que hacer

### 1. El botón de descarga puede funcionar hoy, sin nada del backend

`useDocumentDownload` condiciona `canDownload` a un `signed_copy_url` que **este backend no emite en
ningún sitio**, así que el botón de la pantalla de completado lleva permanentemente oculto. El campo que
funciona ya está tipado en vuestro propio `types.ts`: **`documents[].download_url`**, por documento, no por
sesión. Es exactamente el defecto con el que [`README.md`](README.md) de este directorio justifica su
existencia, y sigue sin arreglar.

Debajo hay un segundo error que hay que arreglar en el mismo movimiento: el composable pasa la **URL** a
`getDocument({ docId })`, y ese método construye la ruta a partir del **id** del documento. Con la URL
dentro produce una ruta inválida aunque el campo existiera.

Tres hechos del backend que necesitáis para etiquetar el botón sin mentir:

- **`GET /api/v1/signing/session` sigue sirviendo después del commit.** No hay ninguna guarda por
  `COMPLETED` ni en el controlador ni en el reader, así que la sesión se lee igual con `status: COMPLETED`.
- **Los bytes son la punta de la cadena de artefactos**, no el original: la firma del propio destinatario
  ya está dentro.
- ⚠ **Pero no son la copia sellada final del sobre.** Los destinatarios posteriores aún no han firmado.
  Un botón que prometa "tu copia firmada" es correcto; uno que prometa "el documento final" no.

La autorización la resuelve el backend por destinatario (ADR-0039), así que no filtréis vosotros: si un
documento está en `documents[]`, es alcanzable.

### 2. Siete rutas que el adapter llama y que no existen

Están todas en `SigningApi.real.ts`. Ninguna devuelve 404 "todavía": no hay ruta, y no la habrá con esa
forma.

| Método del adapter | Estado real |
|---|---|
| `auth` → `/signing/session/auth` | No existe. Llega en TASK-029 y luego TASK-021 — **con otra forma** (ver §NO está listo) |
| el envío de OTP → `/signing/session/auth/otp/send` | No existe. TASK-022 (email) / TASK-023 (SMS) |
| el PATCH de campos → `/signing/session/fields` | **Deliberadamente no construido** (ADR-0040 decisión 6, BL-57) |
| `/signing/session/evidence` | El BC Evidence & Audit no está poblado (TASK-014 sin empezar) |
| `/signing/session/complete` | **Es `POST /api/v1/signing/commit`, que ya existe y ya usáis.** Vuestro propio docblock de `CompleteResponse` lo dice ("docs-future"); el método muerto sigue en el adapter |
| `/signing/session/decline` | No hay ruta de rechazo. `RecipientOutcome::DECLINED` existe en lectura, pero **el lado de escritura no está construido** |
| `/signing/session/review-ack` | La ceremonia de revisor/aprobador no está construida |

Lo accionable: **borrar `complete`** (es un alias muerto de `commit`) y **marcar las otras seis como no
implementadas en el backend**, con el puntero a la task que las traerá, en vez de dejarlas como si fueran
llamadas vivas. Un método que parece existir es peor que uno ausente.

### 3. Ramas de error que no pueden ejecutarse

La taxonomía de `code` del backend es corta y cerrada: **tres** códigos propios de la ceremonia de firma
—`RECIPIENT_DELEGATED`, `STEP_NOT_ACTIVE`, `ROLE_NOT_INTERACTIVE`, los tres 409— y el resto derivado del
status HTTP (`UNAUTHORIZED`, `NOT_FOUND`, `CONFLICT`, `BAD_REQUEST`, `VALIDATION_ERROR`…). El mecanismo es
`ProblemCoded`: un código propio existe sólo si una excepción lo declara.

**Los tres los manejáis bien** (`useSignerNavigation` los enruta a `/unavailable`, con tests). El problema
es el otro lado: `useSessionStore` y `done.vue` bifurcan sobre **seis códigos que nadie emite** —
`ENVELOPE_VOIDED`, `ENVELOPE_DECLINED`, `ALREADY_DECLINED`, `ENVELOPE_COMPLETED_NOT_FOR_RECIPIENT`,
`ENVELOPE_EXPIRED`, `TOKEN_EXPIRED`.

Dos consecuencias que sí se ven en pantalla:

- **El estado "ya habías firmado"** de `done.vue` cuelga de `ENVELOPE_COMPLETED_NOT_FOR_RECIPIENT`, que
  nunca llega. Ese aviso no se muestra jamás.
- **Un enlace caducado da 401 con `code: 'UNAUTHORIZED'`**, no `TOKEN_EXPIRED`: `SigningTokenCodec::verify()`
  colapsa ocho motivos distintos en un `null` y el listener los sella todos igual. Vuestra rama de caducidad
  está muerta hoy y el usuario cae en la ruta genérica de 401.

#### ✅ Lo pedisteis, y está decidido: `TOKEN_EXPIRED` se va a emitir

**Decisión tomada el 2026-08-18.** El backend emitirá `code: 'TOKEN_EXPIRED'` cuando la credencial de firma
sea **auténtica pero caducada**. `UNAUTHORIZED` se queda para inválida, malformada, ausente y **desconocida**.

⏳ **Pero NO aterriza todavía, y esto es lo que decide qué hacéis ahora mismo.** Llega dentro de
[TASK-028](../tasks/TASK-028-opaque-signing-token.md), que convierte el token en credencial opaca respaldada
por BD. Ahí la caducidad deja de ser una *claim* del token y pasa a ser una *fila*, con lo que "digest
desconocido" y "fila encontrada pero caducada" son ramas distintas por construcción en vez de tener que
fabricarlas. Hacerlo antes y aparte era colisionar con esa task en los mismos dos ficheros.

Así que: **no cerréis `/expired`, y no la encendáis tampoco.** Dejadla donde está y esperad el aviso — hasta
que TASK-028 aterrice, el `code` no se emite y la ruta sigue siendo inalcanzable. Cuando llegue tendréis su
propio registro de traspaso.

⚠ **Dos cosas para el copy, y la primera es la que se equivoca sola.** `UNAUTHORIZED` no significa
"manipulado": significa **inválida, malformada, ausente o desconocida**. Post-TASK-028 no hay secreto que
rotar — invalidar una credencial es borrar o caducar su fila, y un digest que no está en la tabla es
*desconocido*, que cae en `UNAUTHORIZED`. Un copy de `/invalid` que afirme manipulación será falso en el
caso más común. Y segunda: la cadena `TOKEN_EXPIRED` **es** el contrato; si cambiara, se os avisa antes de
escribirla, no después.

### 4. Dos uniones de tipos, una de ellas mal

- **`SessionStatus`**: el backend puede emitir `AUTH_PASSED`, `COMPLETED` y `DECLINED` (este último como
  literal del reader, no como caso del enum — está así a propósito hasta que exista la escritura).
  `VOIDED` y `EXPIRED` **no aparecen en ningún punto del BC Session**: son ramas muertas.
- **`RecipientRole`**: aquí el desajuste es real pero pequeño, y **no en la dirección que parece**. El
  backend tiene siete roles y los **mapea a propósito** a vuestro vocabulario en
  `SigningSessionReader::role()`: `VIEWER` se pliega en `REVIEWER`, e `IN_PERSON_HOST` y
  `CERTIFIED_DELIVERY` se **rechazan** con `ROLE_NOT_INTERACTIVE` porque no tienen ceremonia. Así que no
  os faltan roles. Lo que os sobra es **`FORM_FILLER`**, que el backend no emite nunca.

## Lo que NO está listo todavía

**Cinco bloques del payload de sesión están hardcodeados en el presenter.** Se leen como datos y no lo
son. Construir UI que se los crea es construir sobre arena:

| Bloque | Qué devuelve de verdad |
|---|---|
| `auth_requirements` | **`[]` siempre.** Y sin embargo `auth.vue`, `useReauth`, `useAccessCodeAuth` y `sign.vue` derivan de ahí |
| `auth_status` | Entero sintético: `authenticated: true`, `method_used: 'DIRECT_LINK'`, `auth_completed_at` = **ahora, recalculado en cada lectura**, `auth_expires_at: null`, `auth_ttl_minutes: 0`. Cualquier "tu sesión caduca en X" es una invención |
| `config` | Literales: `allowed_signature_modes: ['DRAW','TYPE']` y los tres flags a `false`. Nada de la autoría los mueve |
| `branding` | `logo_url: null`, `primary_color` fijo, y ⚠ **`company_name` es el nombre del sobre**, no de una empresa. `view.vue` ya lee `logo_url`, siempre nulo |
| `fields_draft` | `null` siempre (BL-57), igual que `fields[].current_value` |

**⛔ Y el aviso que más dinero ahorra: no toquéis el borde de auth/sesión.** Está a punto de moverse, y
el orden está decidido: **TASK-029** (credencial de sesión + refresh) va **primero**, y es
explícitamente *donde ocurre la cascada de `f5sign-signer`*, con partición de rutas. **TASK-021** (las dos
puertas) va después. Dos cosas que ya se saben de esa forma y que contradicen lo que el signer tiene hoy:

1. **Pasar la puerta acuña una credencial, no marca un flag.** La sesión se identifica de forma
   determinista por `(tenant, sobre, destinatario)`, así que todo el que tenga el enlace converge en la
   misma sesión: un booleano `authenticated` en esa fila lo aprovecharía quien no ha probado nada. Vuestro
   `useAccessCodeAuth` hoy hace exactamente eso — parchea `auth_status` en el store.
2. **El catálogo de `AuthMethod` aterriza entero.** Vuestra unión tiene cuatro miembros; TASK-021 lo trae
   completo y con bastantes más. No lo tipéis a mano ahora: se re-tipa entero en esa task.

Los dos traspasos en `Pending` de este directorio (`TASK-025`, `TASK-027`) dicen ambos **signer: ninguna
acción**. Ahí no hay nada que hacer.

## Cómo verificarlo desde el frontal

- **La lista de rutas, autoritativa:** `docker compose exec -T php-fpm php bin/console debug:router` desde
  `f5sign-infra`. Si una ruta no sale ahí, no existe, diga lo que diga el adapter.
- **Las formas:** `GET http://localhost:8000/api/doc.json` — la única ruta sin autenticar de la API.
- **La descarga, de punta a punta:** abre una sesión, haz commit, y vuelve a leer
  `GET /api/v1/signing/session`. Con `status: COMPLETED`, cada `documents[].download_url` debe devolver
  PDF. Ese es el caso que hoy nadie ejercita.
- ⚠ **`smoke-signing-session.sh` está muerto — no lo uséis como referencia.** Acuña con `X-Tenant-Id` +
  `X-Acting-User-Id`, y **ese resolver está borrado**: el tenant sale ahora de la propia API key. La ruta
  de acuñar es `MACHINE_KEY`: bearer `f5s_ak_…` de `app:identity:provision-api-client`, más la cabecera
  `F5Sign-Declared-Subject` obligatoria. El comentario de `MintTokenRequest` en vuestro `types.ts` que
  dice "gated por X-Tenant-Id, no por bearer" es de la época anterior y engaña. (Las copias del script en
  los dos repos además ya difieren entre sí.)
