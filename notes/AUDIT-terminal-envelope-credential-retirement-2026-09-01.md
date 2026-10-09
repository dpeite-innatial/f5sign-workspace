# AUDIT — `feat/terminal-envelope-and-credential-retirement` (TASK-038 + TASK-039)

| Campo | Valor |
|---|---|
| **Fecha** | 2026-09-01 |
| **Repo** | `f5sign-backend` |
| **Rango auditado** | `889d102..HEAD` (`825f8aa`) — 79 ficheros, +3793 / -120 |
| **Commits propios** | `bb6c43c` · `a7b350f` · `44b0551` (código) · `a9e2b66` · `825f8aa` (docs) |
| **Estado** | ⛔ **Ya fusionada y empujada.** `develop` = `origin/develop` = `70af999`, vía los merges `0428971` y `a259389`. La migración está **publicada**: regla 2 del repo → suceder, no editar. |
| **Método** | 5 auditores paralelos e independientes (seguridad · lógica de negocio · ADR+normas · persistencia · tests+contrato), sus hallazgos verificados a mano contra el árbol. |
| **Convergencia** | **4 de 5** llegaron al mismo BLOCKER por caminos distintos; **3 de 5** al segundo. |

---

## Resumen ejecutivo

La rama entrega **1 de los 3 commits que TASK-039 §3 especifica**, y aun así marca la task
`✅ Done`, promociona ADR-0060 a `Accepted — exercised` y cierra BL-152 y BL-158.
El medio mecanismo que falta es justamente el que cubre el caso con el daño nombrado.

Añadido a eso, el guard de TASK-038 usa `isTerminal()`, que incluye `COMPLETED`, y con ello
cierra al firmante el acceso a su propia copia firmada — contradiciendo cuatro superficies que
la propia rama escribe, una de ellas en la spec publicada.

**Lo bueno, y es mucho:** deptrac / phpstan / baseline / composer con **delta cero** (ninguna
allowlist ensanchada); la migración es intachable (aditiva, reversible, sin default, sin backfill,
con la regla 6 razonada y descartada correctamente); `SessionStatus` es un ejemplo de manual de
enumeración cerrada en las dos direcciones; `ReactorConvergenceTest` se **extendió**, no se debilitó;
el contrato del evento `SessionRevoked` está fijado con payload cerrado y fixture; el round-trip
de escritura/lectura de `credentials_retired_at` está cerrado; y las tres ediciones del índice de
ADR se hicieron completas. La higiene de rastro IA es limpia (0 trailers, 0 marcas).

---

## BLOQUEANTES

### B1 — La retirada de credencial se esquiva reabriendo el enlace (BL-152 sigue abierto)

**Convergen 4 de 5 auditores.** Verificado a mano.

TASK-039 §3 especifica tres commits. Solo existe el primero:

| Commit | Qué es | Estado |
|---|---|---|
| 1 — el ancla | `envelope.recipient.credentials_retired_at` + 3 comparaciones | ✅ construido |
| 2 — revocación del token | `session.signing_token.revoked_at` + 2ª función `SECURITY DEFINER` + filtro en `resolve_signing_token()` | ❌ **no existe** |
| 3 — el reactor de renovación | consumo de `RecipientCorrected` / `RecipientAuthUnlocked` | ❌ **no existe** |

Verificación (falsador original de la propia task, que sigue dando vacío):

    grep -rn "revoked_at" migrations/ src/ | grep -v IdentityAccess | grep -v Version20260803000012
    → (nada)
    ls src/F5Sign/Session/Application/Subscriber/  → solo OnEnvelopeVoided.php

**El mecanismo del bypass.** La retirada compara el ancla contra `agp`, el instante en que se pasó
la puerta de acceso, que viaja dentro del JWT. Pero `StartSessionController:252` estampa
`agp = now` en **cada** apertura — su propio comentario en la línea 243 lo dice: *"Under the neutral
gate pair the open IS the gate passage, so `accessGatePassedAt` is now."* Y el open **no** consulta
el ancla: `grep -rn credentialsRetiredAt src/` da exactamente 3 cruces
(`SigningSessionReader`, `SigningDocumentReader`, `CommitSignatureUseCase`), todos rutas
`SESSION_CREDENTIAL`. El open es ruta `SIGNING_TOKEN`, y es el cruce que **emite** la credencial
que los otros tres comparan.

**Escenario (puerta de acceso neutra — el default, per BL-184):**
1. Invitación a `wrong@x`; ese tenedor abre → `agp = T0`, lee, descarga.
2. El emisor corrige el contacto en `T1` → `credentials_retired_at = T1`. La credencial `T0`
   queda rechazada en los tres cruces. **Correcto.**
3. El mismo tenedor vuelve a hacer `POST /api/v1/signing/session` con **el mismo token de firma**,
   que sigue vivo 7 días: `session.resolve_signing_token()` no tiene concepto de revocación.
4. El sobre está vivo (una corrección exige no-terminal), la puerta es neutra → se mintea con
   `agp = now > T1` → `retires()` devuelve `false`.
5. **Read-model, bytes del documento y `POST /signing/commit` restaurados.** Una firma de la
   parte equivocada, sellada en la cadena PAdES.

Efecto colateral del paso 4: `mintCredentialFor()` escribe sobre la fila de sesión **compartida**
`(tenant, envelope, recipient)`, reemplazando el refresh digest que el destinatario correcto tiene.

`correctContact()` **no toca el código de acceso** (verificado, `Recipient.php:470-478`: solo email,
phone y outcome), así que ni una puerta `ACCESS_CODE` declarada frena este escenario.

**Caso reset (BL-158) sí queda cerrado** cuando la puerta de **acceso** declara `ACCESS_CODE`,
porque reabrir exige el código nuevo. Con puerta de acceso neutra, no: el intruso recupera
read-model y bytes; solo el commit queda bloqueado.

**La prueba está en la propia rama.** `Recipient.php:481`:
> *"…retiring here is what ends that, **and the token's own row is revoked separately because the
> two kinds are stored differently**."*

Esa segunda mitad afirma un mecanismo que nunca se construyó — regla de autoría 2 en su forma más
cara, escrita en el único docblock que un lector abriría para comprobar si el caso de corrección
está completo.

### B2 — Completar un sobre le quita al firmante su propia copia firmada

**Convergen 3 de 5.** Verificado a mano.

`EnvelopeStatus::isTerminal()` = `COMPLETED, DECLINED, VOIDED, EXPIRED` (`EnvelopeStatus.php:24`).
Los cuatro guards nuevos usan ese predicado. Antes solo miraban `sentAt === null`.

Sobre de un solo firmante: firma → sella → sobre `COMPLETED`. Al día siguiente vuelve a su enlace:
- `POST /signing/session` → **409 `ENVELOPE_NO_LONGER_LIVE`**, *"The sender has closed this envelope"* (nadie lo cerró)
- `GET /signing/session` → 409
- `GET /signing/session/documents/{id}` → 404

**No hay otra ruta.** `DownloadSealedDocumentController` es ruta de emisor (`MACHINE_KEY`), y
`NotifyCompletedEnvelopeRecipientsUseCase.php:37` dice literalmente: *"It carries no link and mints
no token — **recipient self-serve download is NOT IMPLEMENTED**."*

Contradice **cuatro** superficies, tres de ellas escritas por esta misma rama:
1. `SigningSession.php:1101-1103` — *"ADR-0056 lets a `COMPLETED` session keep renewing so the
   signer can still fetch the copy they signed"*. La renovación ahora tiene éxito y trae un 404.
2. ADR-0059 §7.4 — ofrece *"a signer who already signed legitimately wants their copy"* como la
   razón por la que la alternativa fue **rechazada**.
3. `SigningSessionRevocationTest::a_completed_session_still_renews()` — su propósito declarado.
4. ⛔ **La spec publicada**, `StartSessionController.php:91`, emitida verbatim al OpenAPI:
   *"COMPLETED does NOT imply this body withholds a credential: a terminal session whose access
   gate is neutral still mints one, **and that recipient can read the read-model and download their
   sealed copy**."* Ahora es falso y no se barrió.

Está **fijado como intencionado** por `SigningDocumentReaderTest::terminalStatuses()`, que itera
todos los miembros terminales — así que es una decisión, no un descuido. Pero contradice ADR-0056
§2.2 sin cambio de ADR, que es la regla 7 del repo. Y el bar de ADR-0056
`GatedSigningCeremonyHttpTest::a_signed_session_behind_a_neutral_door_is_completed_and_still_mints()`
sigue **verde** solo porque `async_events` es `in-memory://` en test: el bucle de sellado no corre,
su sobre sigue `SENT` mientras la *sesión* está `COMPLETED`. El harness no alcanza la propiedad.

### B3 — Ningún test toca `credentials_retired_at` por SQL: todo el guard de ADR-0060 se puede inertizar en verde

Verificado: `grep -rn "credentials_retired_at" tests/` → **0 resultados**.
`grep -rln "CREDENTIAL_RETIRED" tests/` → **1 fichero** (`CommitSignatureUseCaseTest`).

Todos los tests de retirada doblan en el puerto (`FakeEnvelopeQuery`) o construyen `RecipientView`
a mano. Sabotajes que dejan la suite verde:

| Sabotaje | Efecto en producción |
|---|---|
| `DoctrineEnvelopeReadRepository:450` → `credentialsRetiredAt: null` | Todo destinatario lee como no-retirado; los 3 guards quedan código muerto |
| `DbalEnvelopeRepository:817` — quitar la columna del upsert | El ancla nunca se persiste |
| `DbalEnvelopeRepository:427` — quitar la hidratación | El siguiente comando de autoría escribe `NULL` sobre el ancla |
| `Recipient::rehydrate()` — dejar de reenviar el parámetro | **Es el defecto exacto que TASK-039 §8 dice haber encontrado a mano** — y no se añadió nada que cace el siguiente |

TASK-039 §6 exige *"One acceptance case per driving row, end to end over HTTP, because §1's two
survival windows are traced from source and have never been executed"*. No se escribió ninguno.

---

## ALTOS

**A1 — La spec publicada ahora afirma que un reset contiene una filtración.**
`ResetRecipientAccessCodeController.php:78-84` **invirtió** un aviso correcto. Antes: *"⛔ Un reset
NO expulsa a quien ya pasó la puerta … NO es suficiente por sí solo; para ese caso, anula el sobre."*
Ahora: *"⛑ Un reset SÍ expulsa … este endpoint es suficiente por sí solo."* El endpoint **no tiene
precondición** de que la puerta de acceso declare `ACCESS_CODE` (el único guard es `isTerminal()`),
así que con puerta neutra es falso — y la rama **borró el único remedio que sí funciona ahí**
(*"For that case, void the envelope"*). Regla 5: el conjunto exento es todo destinatario cuya puerta
de acceso no sea `ACCESS_CODE`.

**A2 — La cadena de reactores Envelope→Session no tiene test de cruce.**
Sabotaje: `OnEnvelopeVoidedHandler.php:18`, cambiar `bus: 'event.bus'` por `bus: 'command.bus'`.
Suite verde; ninguna sesión llega nunca a `REVOKED` en un sistema real. `SESSION_REVOKED` no llega
a `platform.event_log` en ningún test. El patrón hermano existe y no se siguió
(`AuthHardLockCrossingTest`, `RecipientAccessTraceCrossingTest`).

**A3 — El `FOR UPDATE` de `findByEnvelope()` no está testeado; el harness no lo alcanza.**
Su único test extiende `RlsIntegrationTestCase` — una conexión bajo rollback DAMA, donde lecturas
con y sin lock son indistinguibles. Borrar el `FOR UPDATE` deja los 4 casos verdes.
`tests/F5Sign/Support/ProbesRowLocks.php` ya está en el repo y no se usó.

**A4 — Los dos ficheros de task siguen diciendo que su ADR es `Proposed`, cinco líneas debajo de decir que es `Accepted`.**
`TASK-038:10` y `TASK-039:10` — *"**`Proposed`**. ⛔ Promoting it … belongs in this changeset"*,
mientras la fila `Status` (línea 5) cita *"ADR-0059 reads `Accepted`"* como su propio falsador.
Un fichero que se contradice consigo mismo — regla 1, *"check the file against itself"*.
Regla 7 del repo: un ADR leído como `Proposed` deja de vincular.

**A5 — ADR-0060 §2.6, §2.4 y §3.2 describen en presente mecanismos que no existen**, y §6
*"Realized in"* simplemente **omite** la fila en lugar de marcarla pendiente. AUTHORING.md ofrece el
calificador `*(persistence partial)*` para exactamente esto y no se usó. Un agente que lea
ADR-0060 como `Accepted` construirá sobre *"una corrección mata el enlace viejo"*. No lo hace.

**A6 — `BL-152` marcado Closed mientras el código que nombra sigue documentando el hueco.**
`NotifyCorrectedRecipientUseCase.php:145` sigue diciendo *"the earlier credential is NOT revoked and
stays live until its own expiry, which is the gap BL-152 records"*. Es el puntero vivo
*"deferred to BL-N"* que la regla 1 nombra explícitamente, y está en la ruta de la que va la fila.

---

## MEDIOS

- **M1 — `submitAuthResponse()` no se revisó para `REVOKED`.** `SigningSession.php:528` guarda
  `=== SessionStatus::COMPLETED` y **no recibe `envelopeIsAlive`** (sí lo reciben `issueAuthChallenge`
  ×2 y `commitSignature`). Puede devolver una sesión terminal a `AUTH_PASSED`, contradiciendo el
  hecho `SessionRevoked` ya escrito en el log y reabriendo `renewWith()`. Lo sostiene hoy solo
  `OpenGateResolver` una capa afuera. El propio docblock de `revoke()` (línea 759) escribe la regla
  — *"`isTerminal()`, not `!== COMPLETED`. El conjunto exento de una comparación es «todo lo que aún
  no está en la lista»"* — y no se aplicó a los cuatro hermanos (líneas 379, 453, 528, 886).
- **M2 — Segundo sitio de minteo sin guard para métodos entregados.**
  `DbalSigningSessionRepository:455` pasa `envelopeIsAlive` solo a la rama `!deliversCode()`. Con
  puerta `OTP_EMAIL`, un código emitido antes del void y enviado después **pasa**, y
  `SubmitAuthResponseUseCase` mintea credencial sobre un sobre anulado. `ACCESS_CODE` sí se rechaza
  por la misma ruta — los dos métodos discrepan. Falsifica el bar *"the session open mints nothing"*.
- **M3 — Enumeración cerrada a medio convertir en la spec.** `StartSessionController:91` publica
  `enum: ['AUTH_PASSED','AUTH_PENDING','COMPLETED']` y su fuente (`terminalOutcome()`) ya puede
  devolver `'REVOKED'`. El gemelo `GetAuthDescriptorController` **sí** se actualizó a
  `['COMPLETED','REVOKED']`. Un par convertido a medias se lee como distinción deliberada.
- **M4 — `CommitSignatureUseCase:21`** — *"⛔ **Two things are now asked that were not before**"*
  seguido de una lista de dos, en el mismo commit que añadió la **tercera** comprobación.
- **M5 — La frase corregida en un fichero sobrevive verbatim en otro.**
  `SigningSession.php:907` conserva *"what changes is that it buys nothing, because both gates refuse"*,
  que `SigningSessionStateException.php:68-73` — editado por esta rama — cita explícitamente como la
  cláusula falsificada.
- **M6 — Cuatro citas nuevas apuntan a `docs/LOAD-BEARING.md` §2 por una entrada que no está ahí.**
  `OnEnvelopeVoided:30`, `RevokeEnvelopeSessionsUseCase:24`, `SessionStatus:94`, `SigningSession:750`.
  `grep -c "OnEnvelopeVoided\|ADR-0059" docs/LOAD-BEARING.md` → **0**; el fichero no lo tocó la rama.
  El par de guards que construye es el caso de manual de *"parece duplicación y no lo es"* que la
  regla 8 enruta a ese fichero, y está sin registrar.
- **M7 — Los modelos de dominio vivos no se reconciliaron.**
  `docs/ddd/signing-session-domain-model.md:196` *"the **only** terminal state in code"* (falso),
  `:353` *"**five cases**"* (son seis), `:361` idem, sin fila `REVOKED` en la tabla de ciclo de vida,
  sin `SessionRevoked` en eventos publicados, y sin la suscripción a `EnvelopeVoided` — que es la
  **primera arista cross-BC en dirección inversa** del sistema.
  `docs/ddd/envelope-domain-model.md:376` omite a Session como consumidor.
- **M8 — ADR-0060 §5 dice *"The bars are unchanged from the `Proposed` text"*** — pasaron de 5 a 7,
  con dos añadidos y dos degradados a *held-by-construction*. Honesto sobre la degradación, falso
  sobre *"unchanged"*.
- **M9 — Puntero a un test que no existe.** `Recipient.php:797` cita `EnvelopeRecipientRetirementTest`;
  el fichero es `EnvelopeCredentialRetirementTest`. Es el único tenedor no-mecánico de la decisión
  de no-expulsión de `unlockAuth()`, que ADR-0060 §3.3 llama *"one keystroke from being wrong"*.
- **M10 — Transacción de revocación sin cota.** `findByEnvelope()` hace `SELECT … FOR UPDATE` sin
  `LIMIT`, y el bucle corre ~4 sentencias por sesión dentro de una sola transacción. Con muchos
  destinatarios eso fija `pg_snapshot_xmin` y **el relay deja de drenar para todos los tenants del
  clúster mientras reporta éxito** — el mecanismo que BL-138 midió.

---

## BAJOS

- **Handoff a frontal.** No se escribió ninguno para TASK-038/039, pese a que
  `docs/frontend-handoff/README.md` lo exige *"whenever a change touches any `#[OA\*]` attribute,
  a `Contract/` type the API emits, an enum whose values cross the wire"* — y la rama añade 2
  `ProblemCode`, amplía `outcome` y recompone 401/404/409 en tres rutas de destinatario.
- **`docs/frontend-handoff/2026-08-21-problem-code-catalog.md`** dice *"los **19 códigos**"* y su
  paso de verificación es *"`ProblemCode.enum` … trae 19 miembros"*. Verificado: ahora hay **22**.
  Un lector de frontal que corra ese check concluye que el despliegue está viejo.
- **`docs/frontend-handoff/TASK-035-…md:62`** mantiene bajo *"Lo que NO está listo todavía"* la frase
  *"La dirección terminal sigue abierta … Se rastrea en BL-87"*. BL-87 está Closed. La rama arregló
  esa misma frase en `SigningTokenIssuance.php:78` y no barrió el handoff — la superficie escrita
  precisamente para quien trabaja en otro repo sin este a mano.
- **Texto de rechazo falso para 3 de los 4 estados que cubre.** `EnvelopeNoLongerLiveException:69`
  *"The sender has closed this envelope"*. El docblock de la clase argumenta que el **código** no
  debe llamarse `ENVELOPE_VOIDED` porque hay cuatro terminales — y luego el `detail` nombra el acto
  del emisor igualmente.
- **`ResetRecipientAccessCodeController:136`** enumera *"COMPLETED or VOIDED"* mientras el guard es
  `isTerminal()` (cuatro miembros).
- **`GetAuthDescriptorController`** (ruta `SIGNING_TOKEN`, sin check de retirada ni terminal)
  publica `masked_destination` del contacto **actual**: el buzón equivocado aprende que la dirección
  fue corregida, y una forma parcial de ella.
- **Orden de migraciones.** `Version20260826000001` ordena **antes** de `Version20260827000001`, que
  llegó de `develop` en el merge `4c0cccd` y cuyo docblock registra haberse ejecutado en preprod el
  2026-08-27. Tocan tablas distintas, así que no interaccionan — anotado para que no se redescubra.
- **Ventana de retirada de 1 segundo** (`RecipientAuthContext:172`, comparación por `getTimestamp()`).
  Deliberada, documentada y fijada por test. Se anota por ser un hueco real en un predicado de seguridad.

---

## Verificado y limpio

- **Deltas de gates: cero.** `deptrac.yaml`, `phpstan.dist.neon`, `phpstan-baseline.neon`,
  `composer.json`/`.lock` sin tocar. Ninguna allowlist ensanchada; la arista cross-BC nueva ya estaba
  concedida.
- **Migración `Version20260826000001`:** `ADD COLUMN` aditivo, reversible, cero filas escritas, sin
  default (ADR-0019 §4), sin índice, y rechaza correctamente una ventana `NO FORCE` con el
  razonamiento de LOAD-BEARING §1.7. Regla 6 razonada y correctamente descartada: `NULL` es el valor
  verdadero en draft, in-flight, terminal y superseded por igual — un backfill habría expulsado en
  masa a firmantes vivos en el despliegue.
- **Regla 2 del repo:** el cambio a `Version20260824000001` es solo docblock, y la corrección es
  correcta (`Version20260713000002` es quien crea el stamp, no `Version20260721000001`).
- **RLS y grants:** no hay tabla nueva; `envelope.recipient` ya lleva ENABLE+FORCE+policy+trigger, y
  una columna nueva lo hereda. `GRANT … ON ALL TABLES` es a nivel de tabla y cubre columnas nuevas.
- **Índices:** `findByEnvelope` la sirve exactamente `signing_session_envelope_idx (tenant_id, envelope_id)`.
- **SQL nuevo:** binding por parámetros nombrados, cero interpolación, sin `IN (…)`.
- **Aislamiento de tenant:** `findByEnvelope` filtra `tenant_id` explícitamente **encima** de RLS,
  correcto porque el reactor corre en un worker sin tenant ambiental.
- **`SessionStatus`:** conjunto cerrado en las dos direcciones, cuatro tablas de clasificación, más
  la invariante de acuerdo `isTerminal()`/`terminalOutcome()`. Ejemplo de manual.
- **`ReactorConvergenceTest`:** extendido, no debilitado. No existe lista de exenciones.
- **`SchemaConformanceTest`:** `BC_SCHEMAS` ya no es la lista de 2; censa el universo vivo y falla
  ante lo no clasificado.
- **Contrato del evento `SessionRevoked`:** `EVENT_TYPE` fijado, payload aserido **cerrado**,
  `streamKey()` fijado, round-trip aserido, fixture forzado por censo bidireccional.
  `EnvelopeVoided` solo cambió docblock — la historia escrita sigue legible.
- **PII:** el payload lleva solo ids y `occurred_at`. Cero llamadas `logger->` nuevas.
- **Round-trip de `credentials_retired_at`** cerrado en escritura, lectura y `rehydrate()`.
- **`agp`:** integridad protegida por firma, conjunto de claims cerrado intacto → ningún firmante
  en vuelo expulsado por el despliegue. La renovación lo arrastra sin resetear.
- **Idempotencia:** `revoke()` devuelve `false` en terminal y el use case salta `save()` — una
  redelivery no escribe nada ni duplica eventos. `ORDER BY created_at, id` evita deadlocks.
- **Categorías de kernel** conformes; convención `@see` totalmente cualificada en los ficheros nuevos.
- **BACKLOG:** 203 filas, sin ids duplicados, sin renumerar. BL-203 es genuinamente el siguiente libre.
- **Índice de ADR:** las tres ediciones (fila, grafo, crosswalk) presentes para ambos ADRs.
- **Higiene de rastro IA:** 0 trailers `Claude-Session:`/`Co-Authored-By:`, 0 marcas de autoría.

---

## Orden de arreglo sugerido

1. **B1** — decidir: construir el commit 2 (revocación del token), o consultar el ancla en el open.
   Lo segundo es más barato y cierra el bypass; lo primero es lo que ADR-0060 §2.6 decidió y lo que
   da la respuesta de soporte *"por qué mi enlace dice que no vale"*. Mientras tanto: revertir A1
   (restaurar el puntero al void), reabrir BL-152, y bajar ADR-0060 a `Accepted *(persistence partial)*`.
2. **B2** — decidir si `COMPLETED` debe cerrar la lectura. Si no, el predicado no es `isTerminal()`;
   si sí, hace falta ruta de descarga para el firmante y un cambio de ADR sobre ADR-0056 §2.2.
3. **B3 / A2 / A3** — los tres tests que faltan: uno de integración que lea el ancla por SQL, uno de
   cruce Envelope→Session, y `ProbesRowLocks` sobre `findByEnvelope`.
4. **A4 / A5 / A6 / M1–M9** — barrido de prosa y el guard de `submitAuthResponse`.
5. **M10** — cota en `findByEnvelope`, o fan-out por lotes.

⛔ La migración está publicada: cualquier cambio de esquema va en migración nueva (regla 2).
