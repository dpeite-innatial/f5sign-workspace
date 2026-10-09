# Traspaso al frontal (BORRADOR PROVISIONAL) — cómo termina un sobre: acuerdo, expiración y política de paso

| | |
|---|---|
| **Origen** | [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md), **Status: Proposed** (redactado 2026-09-24, re-cortado por última vez 2026-09-28 tras nueve rondas de auditoría con decisiones explícitas del mantenedor — no es un borrador sin dueño, pero tampoco está "Accepted"). Lo realizan [TASK-048](../tasks/TASK-048-what-an-unagreed-envelope-keeps.md), [TASK-049](../tasks/TASK-049-an-envelope-expires.md) y [TASK-050](../tasks/TASK-050-a-step-says-how-much-agreement-it-needs.md), **las tres en la misma rama** `feat/task-048-how-an-envelope-ends`, construidas en ese orden y **desplegadas juntas**. TASK-048 está en implementación desde el 2026-09-28 (primer commit `ec05e42`); TASK-049 y TASK-050 van después. Sin PR todavía. |
| **Fecha** | 2026-09-28 |
| **Repos afectados** | signer (`f5sign-signer`) |
| **Naturaleza** | Retira dos miembros de `status`, retira un `ProblemCode`, añade un `outcome` de sobre y uno de destinatario, renombra varios campos, y **estrecha una lectura que hoy funciona** (quién puede leer el documento sellado tras el fin). |
| **Acción requerida** | **Ninguna todavía.** Este documento es un AVANCE para que el equipo del signer pueda planificar y, donde el código ya lo permite, dejar hueco — no para empezar a programar contra un contrato que aún no existe. El traspaso oficial, con el sha de aterrizaje y el `doc.json` real, llegará más tarde en `f5sign-backend/docs/frontend-handoff/`. |
| **Desplegado** | No. En implementación, sin mergear en `develop`. |
| **Status** | **PROVISIONAL — accionable contra mocks** |

---

## ⚑ Esto es un avance, no un traspaso

- **El backend está EMPEZANDO a construirlo ahora**, no lo ha construido. Lo único que existe hoy en el árbol es la regla de negocio como código puro, sin conectar: `EnvelopeEndingEvaluator`, `StepCompletionEvaluator` y `ReleaseReasons` en `src/F5Sign/Envelope/Domain/Service/`, ejercitados contra un catálogo de casos (`tests/F5Sign/Envelope/Testing/Scenario/EndingScenarioCatalog.php`). **Nada de esto persiste, bloquea ni publica todavía** — eso es exactamente lo que hacen TASK-048, 049 y 050.
- **El contrato viene del diseño ya aceptado en ADR-0073**, pero un ADR en `Proposed` puede recortarse de nuevo hasta que aterrice. El propio documento lleva nueve rondas de auditoría registradas (§9 del ADR) en las que nombres, causas y hasta el orden de las columnas cambiaron. **Los nombres y detalles de aquí pueden cambiar.** Lo que es estable es la forma de las decisiones (un `outcome` separado del `status`, un `end_cause` con causas específicas, un `RELEASED` con dos columnas) porque ya sobrevivió a esas nueve rondas.
- **El traspaso oficial llega más tarde**, en `f5sign-backend/docs/frontend-handoff/`, cuando TASK-048 (la primera de las tres) tenga código real, tests y un commit de aterrizaje. Ese documento sustituye a este, con el sha exacto y el `doc.json` real para contrastar.
- **Por qué merece la pena leerlo ya de todos modos:** el cambio es grande (recorta dos miembros de `status`, retira un `ProblemCode`, renombra media docena de campos, añade dos enums nuevos) y toca exactamente los ficheros donde este repo ya tiene comentarios avisando de que el catálogo puede crecer. Saber qué viene deja tiempo para decidir si algo se puede dejar ya preparado sin construir nada que no exista.

---

## 1. Qué cambia, por task

### TASK-048 — el sobre termina en un `outcome`, no en un `status` nuevo

| Concepto | Hoy | Con ADR-0073 |
|---|---|---|
| `status` (enum del sobre) | incluye `VOIDED` y `EXPIRED` | **ambos se retiran**. `COMPLETED` pasa a significar "el sobre terminó", con acuerdo o sin él |
| `outcome` (sobre) | no existe | **nuevo**: `AGREED` \| `NOT_AGREED` — enum abierto (un valor desconocido se lee como "no completamente acordado") |
| `end_cause` | se llama `void_cause`, dos valores: `SENDER_VOIDED`, `RECIPIENT_DECLINED` | **se renombra** a `end_cause`; gana `RECIPIENT_VETOED`, `MINIMUM_UNREACHABLE`, `STEP_DEADLINE_MISSED`, `MEMBER_NOT_REACHED` (los cuatro, de TASK-050) y `EXPIRED` (de TASK-049). Null en un sobre `AGREED` |
| `voided_at` / `voided_by` / `voided_by_recipient_id` / `void_reason` | así se llaman hoy | **se renombran**: `closed_at` / `ended_by` / `ended_by_recipient_id` / `end_reason` |
| `agreed_at`, `completed_at` | no existen | **nuevos**, publicados en el sobre |
| `expires_at` | no se publica | **nuevo**, publicado (TASK-049) |
| Destinatario `outcome` | `PENDING, COMPLETED, DECLINED, DELEGATED, SKIPPED` | **gana `RELEASED`**: cerrado sin haber actuado — deadline de su paso, cierre anticipado del emisor, o expiración |
| Destinatario `release_reason` (nuevo) | no existe | `NOT_REQUIRED`, `INTEGRATOR_NO_ACT`, `OPENED_NO_ACT`, `DELIVERY_FAILED`, `UNCLAIMED`, `NOT_REACHED`, `LINK_EXPIRED`, `SENT_NO_RESPONSE` — el hecho que el backend puede probar sobre ese destinatario |
| Destinatario `released_by` (nuevo) | no existe | `STEP_DEADLINE`, `EXPIRY`, `SENDER_CLOSED`, `ENVELOPE_CLOSED` — qué lo liberó |

**El cambio de comportamiento real, no solo de vocabulario — ADR-0073 §2.15, "esto estrecha ADR-0070 §2.6":**

> Hoy (desde TASK-046), un sobre `VOIDED` sirve su documento sellado a quien **firmó o rechazó**. Con ADR-0073, tras `COMPLETED`, solo leen el documento sellado quienes **firmaron** (incluida una aprobación admitida) y los **destinatarios informativos** (`VIEWER`/`REVIEWER`/`EDITOR`). **Quien rechazó, y cualquier otro liberado (`RELEASED`), deja de poder leerlo.** La razón que da el ADR: "un rechazo lo prueba el documento de evidencias, no un PDF que lleva las firmas de otros".

Esto es un cambio real de comportamiento, no una etiqueta nueva sobre lo mismo: hoy `GET /signing/session` para un rechazador tras `VOIDED` contesta 200 con el PDF sellado; con ADR-0073 contestará 409 `ENVELOPE_NO_LONGER_LIVE` en el mismo caso.

**Gate y lecturas — ADR-0073 §2.1, §2.3, §2.9, §2.14:**

- `SEAL_PENDING` (409 en `GET /signing/session`) hoy está documentado **solo para un sobre `VOIDED`**. Con ADR-0073 aplica a **cualquier** sobre cerrado (`closed_at` puesto) y aún no `COMPLETED`, sea cual sea el desenlace — el backend generaliza `readsWaitForTheSeal()`.
- `ENVELOPE_NO_LONGER_LIVE` sigue siendo el mismo código, pero el conjunto de estados que lo produce crece: hoy solo lo produce una anulación; con ADR-0073 también lo produce una expiración, un deadline de paso o un cierre anticipado (`close-now`, TASK-050) que libera a ese destinatario. **El backend ya avisa explícitamente en la doc de `GetSigningSessionController` de no ramificar por lista de estados** — el `code` es el contrato, no la lista — así que si el signer ya sigue esa regla (y la sigue, ver apartado 2), esto no exige tocar nada.
- `RecipientAuthContext` gana el `outcome` del destinatario (interno, no cruza la API) para que las rutas previas a la credencial respondan "pata cerrada" de forma consistente.

### TASK-049 — el sobre expira

| Concepto | Hoy | Con ADR-0073 |
|---|---|---|
| Duración de vida | fija, 30 días desde la **creación**, no se publica, nada la usa | el remitente la elige (1–180 días, 30 por defecto) al crear; se resuelve a `expires_at` al enviar; **se puede extender**, siempre hacia delante, hasta 180 días desde el envío |
| `EnvelopeStatus::EXPIRED` | existe en el enum pero sin escritor real | **se retira** por completo — expira como `COMPLETED`/`NOT_AGREED`/`end_cause: EXPIRED`, nunca como un `status` propio |
| `envelope.expired` (evento/webhook) | reservado, nunca se emite | **sigue sin emitirse, para siempre**: la expiración se publica como `envelope.voided` con causa `EXPIRED` |

El enlace de firma sigue teniendo sus siete días de vida (`StoreBackedSigningTokenIssuer::LIFETIME`), sin cambios — pero si un paso tiene un deadline más largo que eso, el backend recomendará un reenvío; no hay reenvío automático (`BL-306`, sigue abierto).

### TASK-050 — un paso declara cuánta conformidad necesita

| Concepto | Hoy | Con ADR-0073 |
|---|---|---|
| Rechazar en un paso de quórum | **refusado**: `ProblemCode` `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` | **se retira**. Rechazar en un paso `AT_LEAST n` deja de estar bloqueado — el paso se re-evalúa como cualquier admisión |
| Rol informativo (`VIEWER`/`REVIEWER`/`EDITOR`) que firma/comete | hoy se admite (es el único modo en que su pata se cierra) | **se rechaza por nombre** — nuevo `ProblemCode`, aún sin nombre fijado en las tasks |
| `status` de sesión `REVOKED` | hoy solo lo produce una anulación del emisor | también lo produce un `RELEASED` de un miembro bloqueante con sesión viva: deadline de su paso, cierre anticipado (`close-now`) o expiración (TASK-050 §3.4: *"RecipientReleased ahora también dispara la revocación de las sesiones de ese destinatario"*) |
| Cierre anticipado (`close-now`) | no existe | **nueva acción del emisor**: cierra un sobre cuyo acuerdo ya está asegurado, liberando a quien quede pendiente. Ruta nueva, aún sin URL fijada en las tasks |

---

## 2. Dónde toca al signer (repo `f5sign-signer`, medido en `develop` `e353e98`)

Nada de esto se puede tocar todavía — el contrato no existe — pero aquí están los puntos exactos que habrá que revisar cuando llegue el traspaso oficial:

### `app/composables/useSignerNavigation.ts`

- **El `case` de `DECLINE_NOT_OFFERED_TO_ROLE` / `DECLINE_NOT_OFFERED_IN_QUORUM_STEP`** (los dos van juntos, ambos a `/s/${token}/view`): pierde el segundo miembro, que se retira. El primero se queda igual.
- **La constante `CODES_DECLINE_NOT_OFFERED`** (al final del fichero): `['DECLINE_NOT_OFFERED_TO_ROLE', 'DECLINE_NOT_OFFERED_IN_QUORUM_STEP']` — pierde el mismo miembro.
- **El comentario del `case 'SEAL_PENDING'`** dice hoy *"the envelope ended VOIDED and this recipient signed or declined in it"* — se queda desfasado: con ADR-0073 este código también cubre un sobre que terminó `AGREED` y aún espera el sello. El destino (`/s/${token}/unavailable`) no cambia.
- **Buena noticia, y merece decirse:** `errorCodeToPath` y `CEREMONY_CLOSED_CODES` ya están escritos para ramificar por `code`, nunca por una lista de estados de sobre — es literalmente el patrón que el propio comentario del fichero defiende citando al backend ("a code the backend never declared is NOT evidence of a bad link"). Eso significa que el ensanchamiento de `ENVELOPE_NO_LONGER_LIVE` y `SESSION_CLOSED` a nuevas causas (expiración, deadline de paso, cierre anticipado) **no exige tocar ninguna de las dos listas**.
- **Ningún `case` para `RELEASED` todavía** (no puede haberlo: el backend no lo publica en esta superficie hoy). Cuando `GET /signing/session/auth` → `outcome` lo publique (ver más abajo), este fichero no tiene un destino propio para él — cae en el `default` de la tabla de auth, que ya trata cualquier valor no reconocido como "cerrado pero no nombrable" (ver `app/composables/api/types.ts` más abajo). Funcionalmente correcto por diseño, pero sin mensaje específico.

### `app/composables/api/types.ts`

- **`export type SigningLegOutcome = 'COMPLETED' | 'REVOKED' | 'DECLINED'`** (línea ~741) — el tipo de `outcome` en `GET /signing/session/auth`. Con ADR-0073 el backend publica ahí también `RELEASED` (ADR-0073 §2.9: *"the pre-credential routes publish RELEASED in their status/outcome unions"*). El cliente ya cae de forma segura en la rama "cerrado pero no nombrable" (línea ~708) si no se añade — pero un mensaje propio para "tu turno pasó / el remitente cerró el sobre antes" sería más correcto que el genérico.
- **El comentario sobre `REVOKED`** (líneas ~66–72 y ~724) afirma *"lo unico que lo produce es una anulacion"* / *"the SENDER voided the envelope"*. Deja de ser verdad con TASK-050: `REVOKED` también lo produce un `RELEASED` con sesión viva por deadline de paso, cierre anticipado o expiración. El comentario habrá que corregirlo cuando llegue el traspaso oficial (regla de este repo: la prosa que explica un mecanismo debe seguir siendo cierta).
- **`export type SessionStatus = ... | 'VOIDED' | 'EXPIRED'`** (líneas ~54–78): ⚠ **esto NO es el `EnvelopeStatus` que retira ADR-0073.** El propio comentario del fichero ya lo dice: son dos miembros *docs-future*, guardados para una escritura de rechazo/anulación por el LADO del firmante que el backend no ha construido (*"ramas muertas que se conservan mientras exista la escritura que las traerá"*) — nada que ver con el `status` del sobre. No hay que tocar nada aquí por causa de ADR-0073; se deja constancia para que nadie confunda el hallazgo si hace `grep VOIDED` en este repo.

### `app/pages/s/[token]/auth.vue` (línea ~721-727) — copy que nombra al remitente por nombre

La pantalla que se muestra cuando `GET /signing/session/auth` responde `outcome: REVOKED` (`legRevoked`, `data-testid="gate-leg-revoked"`) usa los textos de `i18n/locales/es.json` líneas 235-237:

```json
"legRevoked": {
  "title": "El remitente canceló este documento",
  "subtitle": "Quien te lo envió lo ha anulado, así que ya no hay nada que firmar ni que verificar. ..."
}
```

El propio comentario del componente (línea ~721) explica la elección: *"Se dice QUIEN lo cerro, que es lo unico que el firmante no puede deducir"*. Con TASK-050, `REVOKED` deja de significar siempre "el remitente lo anuló": también lo produce un deadline de paso vencido o una expiración del sobre — ninguno de los dos es un gesto del remitente. **Este es el hallazgo con más impacto de usuario final de todo el documento**: el mismo texto ("el remitente canceló", "quien te lo envió lo ha anulado") pasaría a mostrarse a un firmante cuyo turno simplemente venció, sin que nadie lo cancelara. Como el `outcome` en esta ruta no trae más que el valor `REVOKED` (no hay `released_by` publicado aquí — eso vive en `RecipientAuthContext`, interno), **hoy no hay forma de distinguir los dos casos desde este endpoint**; puede que haga falta pedirlo en el traspaso oficial si el signer quiere un texto que no invente un culpable.

### `app/middleware/session.global.ts` (líneas ~225, 234, 261)

El middleware global lee `opened.status === 'REVOKED' | 'DECLINED' | 'COMPLETED'` directamente sobre la respuesta de `POST /signing/session` (antes de que exista credencial). Los tres valores en sí no cambian — solo lo que puede producir `REVOKED` crece (mismo caso que arriba). No hace falta tocar la lógica de enrutado, solo el texto que se muestra después (`legRevoked`, arriba).

### `app/pages/s/[token]/click-sign.vue` (líneas ~102, 113, 146, 182)

Camino paralelo del MVP `click-to-sign` (activo bajo `NUXT_PUBLIC_SIGNING_MVP`, documentado en el propio `useSignerNavigation.ts` como "las DOS puertas del mismo endpoint"): lee `res.status === 'COMPLETED' | 'DECLINED'` directamente de la respuesta del commit/decline, sin pasar por `errorCodeToPath`. No depende de `VOIDED`/`EXPIRED` ni de `RELEASED`, así que no hay nada que cambiar aquí — se cita para dejar constancia de que se miró, ya que es la otra vía por la que un veredicto llega a pantalla.

### `app/stores/useSessionStore.ts`

- **`isDeclined` (línea ~216)** compara `s.session?.status === 'VOIDED'` — comparación **ya muerta hoy** (el `status` real de sesión del backend nunca vale `VOIDED`; es el mismo resto docs-future de arriba). ADR-0073 no la reactiva ni la mata: sigue igual, sin impacto.

### `app/stores/useSessionStore.ts` (además de la línea ~216 ya citada)

- **`declineNotOffered: boolean`** (declarado línea ~77, puesto a `true` en la línea ~469, resetado en la ~352) es el flag que oculta el control de Rechazar en la UI cuando el backend contesta `DECLINE_NOT_OFFERED_TO_ROLE` o `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` (comentario línea ~72-77). Cuando el segundo código se retire, este flag lo sigue poniendo igual por el primero — no hay que tocar el flag en sí, solo confirmar que el `catch` que lo activa no depende de una lista propia de códigos (no la tiene: recibe lo que `useSignerNavigation` ya clasificó).

### `app/composables/api/types.ts` (segunda mención, línea ~1192)

- El docblock del método `decline()` de la interfaz del cliente API enumera a mano los 409 de `POST /api/v1/signing/decline`, incluido `DECLINE_NOT_OFFERED_IN_QUORUM_STEP`. Es prosa descriptiva, no un tipo que compile distinto — pero es exactamente el tipo de comentario que la regla 1 de autoría del backend (y la misma disciplina que ya seguís en este fichero con otros catálogos) pide mantener cierto: cuando el código se retire, esta línea también.

### `tests/fixtures/openapi-snapshot.json`

- Es la instantánea congelada del `doc.json` real del backend que `pnpm contract:check` usa para detectar deriva de contrato (citada explícitamente por TASK-049 §3.7 como superficie a actualizar cuando `EnvelopeStatus::EXPIRED` se retire). Hoy lleva, **verbatim**, la prosa inglesa de `GetSigningSessionController` y `GetAuthDescriptorController` tal como está hoy — incluida la frase que quedará falsa, *"REVOKED... the only thing that produces it is a void"* (línea ~247) y las menciones a un sobre `VOIDED` en varias descripciones (líneas ~207, ~353, ~787). **No hay que editarlo a mano**: se regenera contra el `doc.json` real del despliegue que traiga TASK-048, y `pnpm contract:check` es quien detecta si hace falta. Se cita aquí solo para que quede localizado.

### Tests que mencionan el código retirado

- `tests/unit/composables/useSignerNavigation.spec.ts`
- `tests/unit/composables/useSignerNavigation.authgates.spec.ts`
- `tests/unit/composables/useDecline.spec.ts`

Los tres referencian `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` (confirmado también en `tests/unit/composables/useSignerNavigation.spec.ts:168` y `useDecline.spec.ts:90`, ambos con `it.each(['DECLINE_NOT_OFFERED_TO_ROLE', 'DECLINE_NOT_OFFERED_IN_QUORUM_STEP'])`) y tendrán que perder los casos que dependen de él cuando el código real se retire.

### Confirmado por barrido directo, sin hallazgos (para que quede constancia de que se miró)

- **`RELEASED`**: cero apariciones en todo el repo (`grep -rn RELEASED` sobre `.ts`/`.vue`/`.json`, fuera de `node_modules`/`coverage`) — nada que romper hoy, es contrato nuevo puro.
- **`min_signatures` / `quorum` como dato**: cero apariciones como campo leído; la palabra "quorum" solo aparece en prosa explicando por qué se oculta Rechazar, nunca como un valor que el cliente lea.
- **`ENVELOPE_REACHED_AGREEMENT`**: cero apariciones — es un código del lado emisor (`VoidEnvelopeController`) que el signer nunca ve, al no llamar nunca a `void`.

### Lo que no toca nada del signer

- El signer **no lee** `min_signatures`, `quorum`, `void_cause` ni ningún campo del sobre a nivel de sender (su superficie es `/signing/*`, con credencial de sesión o de firma). Los renombrados de campo (`voided_at`→`closed_at`, etc.) viven en `GET /envelopes/{id}`, que el signer no llama.
- `app/pages/s/[token]/declined.vue` **no ofrece descarga** (`DownloadButtons` solo está en `done.vue`). Así que el estrechamiento de lectura (rechazador ya no lee el sellado tras `COMPLETED`) no tiene hoy ningún botón que dejar de mostrar — la pantalla ya no promete nada que el backend vaya a dejar de dar.

---

## 3. Qué se puede construir ya vs qué espera al backend

**Se puede construir ya (contra mocks, sin depender del backend real):**
- Quitar `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` de `useSignerNavigation.ts` y de los tests — es una retirada pura, sin contrapartida que aprender del backend. ⚠ Pero no lo hagáis todavía: hacerlo antes de que el backend lo retire de verdad dejaría un código vivo hoy sin destino en el cliente (caería al `default`, que en este fichero ya es seguro — pero hacerlo *antes* de tiempo no gana nada y sí desincroniza este repo del contrato real por un tiempo).
- Decidir el mensaje de "cerrado pero no nombrable" que ya cubre `RELEASED` por defecto, y si merece un mensaje propio cuando llegue.

**Tiene que esperar al backend real:**
- El nombre exacto del `ProblemCode` nuevo para el commit de un rol informativo (TASK-050 §3.2) — no está fijado en las tasks.
- La URL exacta de la ruta de cierre anticipado y de la de extensión de expiración — no afectan directamente al signer (son rutas del emisor), pero sus efectos (una liberación, `REVOKED`) sí.
- Cualquier prueba de verdad contra `SEAL_PENDING` generalizado, `outcome: RELEASED`, o el estrechamiento de lectura — nada de esto existe en ningún despliegue todavía.

---

## 4. Preguntas abiertas

0. **La copy de `legRevoked` (`auth.vue`, `i18n/locales/es.json:235-237`) nombra al remitente como causa única** ("El remitente canceló este documento"). Con `REVOKED` alcanzable también por deadline de paso o expiración, ¿el signer necesita que el backend publique algo más que `outcome: REVOKED` en `GET /signing/session/auth` para no inventar un culpable, o basta con un texto más neutro ("ya no hay nada que firmar aquí", sin decir quién ni por qué)? Es la pregunta con más impacto de cara al usuario final de todo este documento.
1. **¿El signer quiere un mensaje propio para `RELEASED`** ("tu turno pasó", "el remitente cerró el sobre antes de que llegara tu paso") o basta con la rama genérica de "cerrado pero no nombrable" que ya existe? No es una decisión del backend.
2. **El nombre del `ProblemCode` para el commit de un rol informativo** no está decidido en las tasks — vale la pena pedirlo pronto si el signer quiere una pantalla específica en vez de caer en el catch-all de errores.
3. **¿Vale la pena que `declined.vue` ofrezca alguna vez la descarga del documento de evidencias** (no el PDF sellado, que ya no verá un rechazador) cuando ese documento exista? Fuera del alcance de ADR-0073 (lo cita como pendiente, ADR-0073 §3.2: *"A decliner keeps no copy until the per-signer evidence document exists"*), pero relacionado.
4. **Extensión de expiración y cierre anticipado son acciones del emisor** (dashboard, no signer) — pero un destinatario a mitad de ceremonia puede verse afectado en cualquier momento por uno de los dos. ¿El signer necesita distinguir en el mensaje "tu paso venció" de "el remitente cerró el sobre antes"? Ambos casos llegan hoy al mismo `ENVELOPE_NO_LONGER_LIVE` / `REVOKED`; el backend no promete distinguirlos en esta superficie (ADR-0073 §2.9 solo dice que el pre-credential outcome publica `RELEASED`, sin más).

---

*Este documento vive solo en el scratchpad de esta sesión. No se ha escrito ni se va a escribir en ningún repo — cuando TASK-048 aterrice en `develop`, el traspaso real sustituye a este.*
