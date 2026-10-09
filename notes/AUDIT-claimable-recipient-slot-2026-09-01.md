# AUDIT — `feat/claimable-recipient-slot` (TASK-036 / ADR-0057)

| Campo | Valor |
|---|---|
| **Fecha** | 2026-09-01 |
| **Repo** | `f5sign-backend`, worktree `f5sign-backend-claimable` |
| **Rango auditado** | `a259389..feat/claimable-recipient-slot` (`829574c`) — 18 commits, 57 ficheros, +6257 / -147 |
| **Estado** | **No fusionada.** `develop` = `origin/develop` = `7cf063a`, que se movió después del último merge de la rama. |
| **Método** | 4 auditores paralelos e independientes (tests+contrato · ADR+normas del repo · arquitectura+puertas de seguridad · barrido de prosa), más una pasada propia sobre dominio, persistencia y contrato publicado. Todo hallazgo de severidad alta verificado a mano contra el árbol. |
| **Convergencia** | 3 de 4 auditores llegaron al defecto de docblocks huérfanos por caminos distintos. |
| **Lo más grave** | **B3** — las dos condiciones de `Recipient::guardClaimable()` no las ejecuta ningún test, y el registro afirma lo contrario. |

---

## Resumen ejecutivo

**La rama es de calidad alta y ya pasó un ciclo de revisión duro** — se nota, y buena parte de lo que
queda es residuo *de ese ciclo*, no del trabajo original. El diseño de dominio es sólido: la conjunción
`declaredClaimable AND claimedAt IS NULL` publicada como único accesor, la migración razonada estado por
estado, los tres guards en tres caminos distintos, y fixtures que de verdad discriminan.

Lo que la bloquea son dos cosas, y ninguna es de diseño:

1. **La evidencia de verde es anterior a tres commits de producción**, dos de ellos correcciones de
   comportamiento. Nada ha corrido sobre la punta.
2. **Dos superficies publicadas de la propia rama se contradicen** sobre si `locale` es editable.

Después hay un bloque grande de rot documental — casi todo generado *por el propio ciclo de revisión*,
que corrigió ficheros uno a uno y dejó los gemelos. Es el patrón que la regla 1 nombra literalmente:
*"un cambio hecho después de un barrido invalida el barrido"*.

**Nada de lo encontrado reabre la fuga de credencial que `b0c5eb5` cerró.** Las tres puertas están bien
cerradas y la enumeración de caminos salió completa (ver §Comprobado y limpio).

---

## BLOQUEANTES

### B1 — El verde declarado no cubre la punta de la rama

TASK-036 §Status y ADR-0057 §5 citan la lane verde en **`cd8947a`** (`OK (2500 tests)`) como la evidencia.
Después de `cd8947a` hay **tres commits que tocan `src/`**:

```
0802326  fix(task-036): a claim erased the contact it was not asked to change
39014a4  docs(task-036): la rot que esta rama creó tras el barrido que la limpió   [+27 en src/]
c1c0516  fix(task-036): the state question is asked before the body question
```

```
$ git diff --stat cd8947a..feat/claimable-recipient-slot -- src/
 6 ficheros, +173 / -17
 ClaimRecipientUseCase.php · Envelope.php · Recipient.php
 RecipientNotClaimableException.php · ClaimRecipientController.php · SigningTokenIssuance.php
```

Dos de los tres son **correcciones de comportamiento**, no de prosa. Ni lint, ni PHPStan, ni deptrac, ni
la suite han visto `c1c0516` — que es además el commit que introdujo B2/I1. Un revisor lee `OK (2500
tests)` y asume que cubre la rama.

▶ **Correr la lane sobre la punta y re-fechar las dos filas.** Es la única acción bloqueante mecánica.
Ningún documento menciona `0802326` ni `c1c0516` (grep de los hashes en `docs/`: cero), pese a que §8 es
la sección de desviaciones.

### B2 — Dos superficies publicadas de esta rama se contradicen sobre `locale`

`config/packages/nelmio_api_doc.yaml:340` (schema `Recipient`, emitido literal al OpenAPI que ratifica el
frontal):

> Language this recipient is written to in, as a BCP-47 tag. **Set when the recipient is added and not
> editable afterwards.**

Y `docs/frontend-handoff/TASK-036-claimable-recipient-slot.md` §2 le pide al dashboard que mande `locale`
en el claim — que es lo correcto: `Recipient::claim()` lo escribe (`if ($locale !== null)`), y el docblock
de `Recipient::locale()` **ya está barrido** y lo declara (*"add time is no longer the only moment the
value may be written"*).

**Daño concreto:** el spec es la superficie ratificada. Un cliente generado desde él —o un integrador que
lo lea— no manda `locale` en el claim, y el consignatario del eCMR se queda con `NULL` = *"no indicado"*
de forma permanente, porque **no hay otra ruta que lo escriba**. Cae al default de tenant/plataforma para
siempre.

⚑ La misma inmutabilidad falsificada sobrevive en tres sitios más, todos con el mismo origen (I11).

### B3 — Las dos condiciones de `guardClaimable()` no las ejecuta ningún test, y el registro afirma lo contrario

`src/F5Sign/Envelope/Domain/Entity/Recipient.php:585-593` es el guard que decide si un destinatario
**puede ser reclamado siquiera**. Sus dos condiciones están sin cubrir:

```
$ rg -n 'RECIPIENT_NOT_CLAIMABLE|notDeclaredClaimable' tests/
(nada)
```

Y la rama hermana `legAlreadyClosed()` tampoco se alcanza: el único test que afirma
`RECIPIENT_CAN_NO_LONGER_ACT` (`EnvelopeClaimRecipientTest:152`) cierra el paso **completando el propio
slot**, así que `Envelope::requireRecipientWhoCouldStillAct()` lanza `stepAlreadyComplete` **antes** de que
`guardClaimable()` mire el outcome. El propio docblock del test lo dice — con honestidad — en su línea 143:
*"the entity's leg-closed guard **would** fire on this fixture with the step guard deleted"*. Es decir: la
rama sabe que ese fixture no discrimina la mitad de la entidad, y no hay otro.

Ningún fixture construye un `Recipient` con `declaredClaimable: false` y le llama `claim()`. Los tres
sitios que despachan `ClaimRecipient` (`ConcurrentRecipientClaimTest`, `UnclaimedSlotRefusedIssuanceTest`,
`ClaimRecipientUseCaseTest`) siembran siempre `declaredClaimable: true`. Los usos de `false` que sí existen
están todos en **otros** caminos (el brazo negativo del mint, la corrección, la tabla de verdad de
`isUnclaimedSlot()`, el alta).

**Sabotaje:** borra las dos condiciones del cuerpo de `guardClaimable()`. **La suite entera sigue verde.**
Con el guard fuera, `POST /api/v1/envelopes/{id}/recipients/{recipientId}/claim` sobre **cualquier**
destinatario ya nombrado de un sobre no terminal sobrescribe `full_name`, `email`, `phone` y `locale` y
estampa `claimed_at` — el editor genérico de destinatarios que ADR-0057 §7.1 rechaza y la re-asignación que
§2.4 difiere, alcanzados en silencio.

⛔ **Y hace alcanzable la cuarta combinación** `(declared_claimable = false, claimed_at NOT NULL)` que
`Version20260828000001` decidió **no** prohibir con un `CHECK` — con esta razón textual: *"The invariant is
the aggregate's, and it is asserted there."* No está aserta en ninguna parte.

⚑ **El registro afirma lo contrario.** TASK-036 §5, línea 1036, dice que `RECIPIENT_NOT_CLAIMABLE`,
`RECIPIENT_CAN_NO_LONGER_ACT` y `RECIPIENT_CANNOT_RECEIVE_METHOD` *"are proved at the domain and
application tiers and **never through the controller's translation**. Each is proved where the *decision*
lives"*. El primero no está probado en **ningún** tier, y el segundo solo en su mitad del agregado.

Esto es CLAUDE.md regla 4 al pie de la letra: *"Before citing a green run, name where the property lives
and check the harness goes there"* — y el covered-MSI del 85% es whole-tree, así que un mutante escapado
aquí es perfectamente compatible con él.

▶ **Dos tests, ambos triviales:** un `claim()` sobre un recipient con `declaredClaimable: false` → 409
`RECIPIENT_NOT_CLAIMABLE`; y una pata terminal en un paso **abierto** → 409 por la vía de la entidad. El
segundo necesita un sobre multi-recipient donde el slot sea `DECLINED` y el paso siga vivo — construible
hoy sin BL-192.

---

## IMPORTANTES

### I1 — Dos docblocks huérfanos: `claim()` se queda sin contrato *(convergen 3 de 4 auditores)*

`c1c0516` insertó los guards nuevos **encima** del docblock existente en vez de debajo. PHP asocia solo el
último bloque, así que:

| Fichero | Docblock huérfano | Método que se queda sin ninguno |
|---|---|---|
| `Recipient.php` | 520-556 (el de `claim()`) → cuelga sobre `guardClaimable()` (585) | **`claim()`** (595) |
| `Envelope.php` | 1317-1349 (el de `requireRecipientWhoCouldStillAct()`) → cuelga sobre `guardRecipientCouldBeClaimed()` (1392) | **`requireRecipientWhoCouldStillAct()`** (1397) |

En este repo el docblock **es** la definición canónica. Lo que se pierde no es decorativo:

- De `claim()`: la regla *"un campo que la réplica no suministra no se compara"* (§4 D4), el ⛔ *"This is
  a FILL, not a correction"*, el porqué de que `$fullName` sea obligatorio, y el contrato `@return bool`.
- De `requireRecipientWhoCouldStillAct()`: el ⛔ *"A property, not an enumeration of today's statuses"* —
  justo el argumento contra reescribir el guard como lista de estados.

Y en la otra dirección: `guardClaimable(): void` "lleva" ahora un `@return bool whether anything changed`
y un `@throws` que describen la comparación de replay que ese método explícitamente **no** hace. El
`@throws` huérfano conserva además la redacción *"diverges from the claim already recorded"* que `0802326`
había corregido dos commits antes, a propósito.

Ningún gate ve dos docblocks seguidos. Lint verde, PHPStan verde.

### I2 — Un `#[OA\*]` publicado queda falsificado por lo que acabas de mergear

`MintSigningTokenController.php:136-139` publica:

> ⚠ NEITHER covers a terminal envelope: a voided, **completed** or expired one still mints, and the link
> the sender is handed then opens nothing at all — `POST /signing/session` refuses it with
> `ENVELOPE_NO_LONGER_LIVE` ... so the token is inert rather than merely gate-blocked.

En `origin/develop`, `EnvelopeStatus::withholdsDocumentFromRecipient()` da `COMPLETED => false` (tu
`11a2106`). Tras el merge esa frase es falsa para `COMPLETED`: el enlace **sí** abre — es la garantía que
ADR-0059 restauró (*"a signer keeps the copy they signed"*). Era cierta en `a259389` y dejó de serlo con
tu fix. Le dice al integrador que algo está muerto cuando está vivo, sobre la superficie ratificada.

### I3 — La misma frase es una enumeración cerrada ya incompleta

`EnvelopeStatus::isTerminal()` tiene **cuatro** miembros:

```php
self::COMPLETED, self::DECLINED, self::VOIDED, self::EXPIRED => true,
```

`MintSigningTokenController:136` publica tres y se deja **`DECLINED`**. Igual en
`SigningTokenIssuance.php:85` (*"A **VOIDED, COMPLETED or EXPIRED** envelope still mints"*).

⚑ La rama **reescribió los dos bloques** — no son líneas heredadas sin tocar — y arrastró la lista. Es el
generador exacto contra el que escribiste `c532cb8` hace unas horas, y sobre la misma superficie: el spec
que el signer copia. Merece la pena aplicarles ahí el mismo tratamiento (nombrar la propiedad y el
`code`, no la lista).

### I4 — Un handoff publicado niega la ruta nueva, y en futuro

`docs/frontend-handoff/2026-08-21-no-sender-side-otp-resend.md:25`:

> Las cinco rutas de remitente sobre un destinatario son, **y seguirán siendo**: `recipients` ·
> `access-code` · `auth-unlock` · `corrections` · `signing-assignments`

La rama añade la sexta, del mismo tipo exacto (`.../claim`, `Authn::MACHINE_KEY`). Ningún barrido por
símbolo la alcanza: la frase no nombra nada que la rama tocara.

**Daño:** es el documento al que el dashboard acude para *"¿qué puede hacer un emisor sobre un
destinatario?"*, y no solo omite el claim — afirma que la lista **no crecerá**. Un desarrollador que
recibe `409 RECIPIENT_SLOT_NOT_CLAIMED`, cuyo remedio publicado *es* esa ruta, tiene un registro firmado
por nosotros diciendo que esa ruta no existe ni existirá.

### I5 — El censo de llamantes del issuer no tiene eje *claimable*

`tests/F5Sign/Session/Application/Query/SigningReadersRefuseUnsentEnvelopeTest.php` es el mecanismo que
ADR-0058 §2.3 ofrece **en lugar de** un guard en el puerto. Tiene dos ejes —
`GUARD = 'sentAt === null'` y `TERMINAL_GUARD` — y **la rama no lo toca** (diff vacío), pese a haber
añadido una tercera negativa a `SigningTokenIssuance::issueFor()`.

**Escenario:** TASK-037 aterriza `NotifyClaimedRecipientUseCase` — ya nombrado como tercer sitio de
minteo de Notification en TASK-037:480. Su autor añade la fila a `ISSUER_CALLERS` con su argumento de
trigger. Los cuatro tests del censo pasan. **Nada pregunta si el sitio nuevo consulta `isUnclaimedSlot()`.**
Lo mismo con el slice de firma delegada de ADR-0055, que ADR-0057 §2.5 ya cita como el que retira el
accidente que hoy protege.

El propio docblock de `SigningTokenIssuance:184` declara que *"none of the three may be weakened on the
strength of the other two"* — esa es justo la propiedad que el censo sostiene **mecánicamente** en los
otros dos ejes y que aquí solo sostiene la prosa.

### I6 — TASK-037 se contradice dentro de la misma celda

`docs/tasks/TASK-037-claimable-invitation-and-visibility.md:5`, misma celda `Status`, por ese orden:

> `NotifyActivatedStepRecipientsUseCase` now carries **a fourth `continue`** … ⛔ **Do not rebuild the
> exclusion**

…y treinta palabras después:

> **Nothing else here is built, and the check is one command:** `grep …` **returns nothing** (run
> 2026-08-25) … `NotifyActivatedStepRecipientsUseCase` **carries three `continue` guards and no fourth**

Medido ahora: ese fichero tiene **4** `continue;`, y el grep devuelve decenas de hits. El implementador de
TASK-037 tiene, en una sola celda, una prohibición de reconstruir el guard y una afirmación de que el
guard no existe. Y el cuerpo (líneas 82-97) repite la premisa que dejó viva la fuga: *"an unclaimed slot
has no e-mail, so it is already skipped"*.

### I7 — `docs/adr/README.md:96` dice que la exclusión del fan-out está sin construir

La fila lista como **Unbuilt** *"§2.7's notification occasion **and fan-out exclusion** … y con ellos §5
bars **1**, 7 y 12"*. La escribió `b0c5eb5` — **el commit que construyó la exclusión y colocó la bar 1**.
El índice es la superficie que se consulta *antes* de abrir el ADR: quien la lea planificará construir lo
que ya existe (que es exactamente I6), y fijará la barra de promoción en tres bars en vez de dos.

### I8 — La fila `Decision record` de TASK-036 contradice a su propio §5

Dice *"§5 bars **1**, 7 y 12 cannot be reached from here … Promotion needs those two clauses built and
**those three bars** placed."* Su §5 *Bars this task cannot place* (línea 719) dice **"(1) PLACED after
all, on 2026-08-28"**. La fila recibió una corrección fechada ese mismo día sobre §4 D2, **sin** tocar
esta cláusula.

### I9 — La premisa falsa que ya causó dos defectos vuelve a estar escrita como justificación

*"A claimable slot has no contact **by construction**"* aparece en negrita en `ClaimRecipientUseCase:93`,
`Recipient.php:568` y TASK-036:527 — todas escritas en `c1c0516`, el último commit de código.

Esa premisa es **falsa y la rama lo demostró dos veces**: `b0c5eb5` (fuga de credencial de 7 días) y
`0802326` (`claim()` borraba el email almacenado). El contrato publicado del propio repo la contradice:
`AddRecipientRequest::$claimable` dice *"nothing stops you sending a `phone` with `claimable: true`"*.

**Daño:** el siguiente lector concluye que el merge `$command->email ?? $recipient->email()` es
decorativo y lo borra — reintroduciendo el destinatario reclamado tras una puerta sin destino, que es
justo lo que `0802326` arregló.

### I10 — El nombre retirado *"the authoring guard"* sobrevive en cuatro sitios

`DeclaredMethodDestinations.php:19` sí está corregido y explica por qué importa: *"A reader who takes
'authoring' literally … will **decide the claim path may skip it**"*. Los que quedaron son justo los que
producen ese daño:

| Fichero:línea | |
|---|---|
| `Contract/Type/RequiredDestination.php:13` | *"so **the authoring guard** is a predicate over the catalog"* |
| `Contract/Type/AuthMethod.php:216` | *"the per-method half of TASK-023 §2's **authoring guard**"* |
| `tests/…/DeclaredMethodDestinationsTest.php:26` | docblock de clase: *"**the per-method authoring guard**"* |
| `Application/Port/PhoneNumberParser.php:27,38` | *"in the same **authoring guard**"* |

Los dos primeros son los ficheros que abre quien añade un método entregado nuevo. El del test es peor:
quien mire si el claim está cubierto ve un test titulado "authoring guard" y concluye que no le aplica.
(`AuthMethodAvailability.php:11` **sí** es correcto — ese guard sigue siendo solo de authoring.)

### I11 — La inmutabilidad de `locale` falsificada sobrevive en tres sitios más (además de B2)

| Fichero:línea | Dice hoy |
|---|---|
| `docs/LIVE_SCHEMA.md:172` | *"Set once at add time; **no edit path exists**"* — en la misma tabla a la que la rama añade sus dos filas, tres líneas más abajo. Su §8 llega a comentar ese fichero y no lo ve. |
| `migrations/Version20260817000001.php:26` | *"permanently, since the value is set once at add time and **there is no edit path** (§3). **Do not add one.**"* — la superficie que la regla 1 marca como la de mayor daño. El `Do not add one` queda colgando de una premisa muerta. |
| `EnvelopeJsonPresenter.php:224` | *"Read back rather than write-only … **the field is settable only at add time**"* — un *X porque Y* con la Y falsa; el `read back` queda candidato de "limpieza" (LOAD-BEARING §2). |

⚑ En los tres, la regla 2 aplica literal: **sustituir el mecanismo nombrado, no borrar la razón**. El
fundamento real (`NULL` = *"no indicado"*, el tier se salta) sigue intacto.

### I13 — El arreglo de orden (409 de estado antes que 422 de cuerpo) no lo prueba nada

`c1c0516` existe entero para mover `guardRecipientCouldBeClaimed()` **delante** de `destinations->guard()`,
y lo documenta en tres docblocks largos. **Ningún fixture tiene a la vez un rechazo de estado y uno de
destino aplicables**, así que el orden no lo observa nada.

**Sabotaje:** intercambia las dos sentencias en `ClaimRecipientUseCase:105-111`. Un slot claimable con
`OTP_EMAIL` y sin contacto —la forma canónica, porque §2.13 difiere el guard justamente por eso— sobre un
sobre que el emisor ha hecho `void()` pasa de `409 CONFLICT` a `422 RECIPIENT_CANNOT_RECEIVE_METHOD`
(*"aporta el contacto que falta"*, sobre un sobre anulado) — el defecto exacto que la rama arregló — y
**nada se pone rojo**.

`a_claim_that_cannot_satisfy_a_later_declared_method_is_refused_naming_it` usa un sobre SENT con la pata
PENDING (sin rechazo de estado), y los tests de estado de `EnvelopeClaimRecipientTest` llaman al agregado
directamente, saltándose el use case.

Corolario: `Envelope::guardRecipientCouldBeClaimed()` — el método público que existe **solo** por este
arreglo — no tiene test directo; su única mención en `tests/` es como **clave de un mapa** en
`EnvelopeCredentialRetirementTest:85`.

### I14 — La nota de traspaso no nombra ninguno de los códigos 409 de la ruta que introduce

El `#[OA\*]` de `ClaimRecipientController` publica un 409 que dice *"`code` distinguishes the reasons, and
they route to **different screens**"* y enumera `RECIPIENT_NOT_CLAIMABLE` / `RECIPIENT_ALREADY_CLAIMED` /
`RECIPIENT_CAN_NO_LONGER_ACT` / `CONFLICT`. La nota de traspaso dice solo *"Una repetición que sí manda un
campo y difiere → **409**"*, y su instrucción *"Ramificad sobre `code`"* está acotada a *"las dos rutas
rotas"*.

**Daño:** un dashboard construido desde la nota trata los tres como uno y ofrece *"reintentar / cambiar el
nombre"* ante `RECIPIENT_CAN_NO_LONGER_ACT`, cuyo remedio es el contrario; o parsea `detail` — que el 400
de esa misma ruta le dice explícitamente que no parsee.

⚑ La misma nota se contradice al contar: la cabecera dice *"tres códigos nuevos en rutas que ya usáis"*,
§3 se titula *"segundo código nuevo"* y §4 *"tercer código"* — y §4 cierra con *"es el **mismo** código que
en el mint, a propósito"*. Sobre las dos rutas ya usadas hay exactamente **uno**:
`RECIPIENT_SLOT_NOT_CLAIMED`.

### I12 — El `Origen` del handoff apunta a un commit con el bug que el propio documento promete que no existe

`docs/frontend-handoff/TASK-036-claimable-recipient-slot.md:5` declara `commit 2b98b5c`. El fichero se
**añadió** en `ac20f13` y se tocó por última vez en `013a758`; `2b98b5c` no es ninguno de los dos. Y
después de `2b98b5c` entró `0802326`, *"a claim erased the contact it was not asked to change"*.

El `Origen` es literalmente el campo contra el que el frontal integra. En `2b98b5c`, un claim que **omite**
`email` **borra** la dirección — lo contrario de lo que este documento promete en su §2 (*"ausente
significa 'no lo afirmo', no 'bórralo'"*).

---

## MENORES

- **`docs/adr/ADR-0057…md:8`** — la cabecera afirma que `ADR-0055-delegated-signature.md` *"no está en
  este árbol"*, que un enlace *"dangles"*, e instruye **"Linkify when it lands on develop, not before"**.
  El fichero **está** en el árbol y en el merge-base, y `README.md:94` ya lo enlaza. Peor: `cd8947a` **sí**
  añadió un enlace funcional en la línea 384 — el documento a la vez enlaza ADR-0055 y ordena no
  enlazarlo. Cuatro marcadores `(unlinked)` quedan permanentes si alguien obedece la cabecera.
- **`docs/adr/ADR-0057…md:242`** — *"BL-61 **is** the general defect … **Fixing** BL-61 does not discharge
  this"*, en presente. BL-61 está **CLOSED**. El párrafo gemelo en TASK-036 §1 **sí** fue corregido a
  pasado en esta rama: se convirtió un fichero y se dejó el gemelo.
- **`migrations/Version20260828000001.php:143`** — *"TASK-036 §2.8 **attributes** the RLS half to
  `Version20260721000001`"*, en presente; §2.8 fue corregido en `b0c5eb5`. Debería ir en pasado.
- **`NotifyCompletedEnvelopeRecipientsUseCase.php:79`** — el **cuarto** fan-out sobre el roster, sin guard
  de slot; su único filtro es `email === null`. ⚑ **No mintea nada** (verificado: cero `issueFor`), así
  que no viola el invariante de credencial. Hoy es inalcanzable porque un slot sin reclamar nunca es
  terminal y el paso no cierra — pero **BL-192 es exactamente la capacidad que lo hace alcanzable**, y la
  fila de ADR-0057 en `README.md:96` lo dice con esas palabras. Cuando llegue, el aviso de finalización
  (título del sobre, `recipient_name: ''`) sale a la dirección del slot. Es el hermano que la regla 3
  manda leer y no se leyó.
- **`docs/BACKLOG.md`, fila BL-69** — la rama editó esa fila (añadió `claim()` como *"un séptimo"*) y dejó
  intacta su enumeración cerrada: *"a replayed `RecipientId` resets that recipient's outcome, email and
  role"*, sin el par nuevo — que es el de mayor radio, porque un slot ya reclamado revertiría a
  reclamable y re-reclamable por otra parte. Latente (los ids los genera el servidor en
  `AddRecipientController:185`), pero es el registro de esa latencia.
- **`RecipientClaimed` no es `AuditableEvent`** y ni ADR-0057 ni TASK-036 lo discuten. `EnvelopeRosterDeclared`
  es PII-free por construcción, así que la fila de un slot es byte-idéntica a la de una parte nombrada, y
  el hecho que la completa queda fuera del subconjunto legalmente material que leerá el proyector de
  TASK-014. Precedente en contra: `RecipientCorrected` tampoco lo es. Recuperable desde
  `platform.event_log`; lo que falta es la clasificación.
- **`locale` no se trimea en la ruta de claim** (`ClaimRecipientController`). La rama razona largo sobre
  por qué `full_name` necesita el `trim()` explícito (`normalizer: 'trim'` no reescribe el DTO) y por qué
  `email` está protegido por `Assert\Email`, y **no dice nada de `locale`**, que `guardReplayMatches()`
  compara byte a byte. Espeja el camino de alta (`AddRecipientController:204` hace lo mismo), así que no
  lo introduce esta rama — pero es un tratamiento incompleto del problema que ella misma identificó.
- **`docs/adr/ADR-0055…md:550`** — enumera los sub-recursos de destinatario sin `claim`, y ADR-0055 está
  diseñando rutas nuevas sobre el destinatario; el precedente más cercano a lo que necesita (sub-recurso
  verbo, escritura una sola vez, sin id de retorno) le queda invisible.
- **El paso 1 de «Cómo verificarlo desde el frontal»** (nota de traspaso, sección final) manda un cuerpo
  `{"role":"SIGNER","claimable":true,"auth":{...}}` que **omite `step_ordinal`**, obligatorio
  (`AddRecipientRequest:67`, `#[OA\Schema(required: ['step_ordinal','role'])]`). Las dos mitades del par
  dan `422 VALIDATION_ERROR`, no `201` / `422 RECIPIENT_CANNOT_RECEIVE_METHOD`. La nota llama a ese paso
  *"el par que demuestra que el diferimiento va atado a la declaración"* y, ejecutado tal cual, demuestra
  lo contrario: fallan igual, así que el lector concluye que `claimable` no hace nada.
- **`ClaimableSlotPersistenceTest`**, docblock de `a_claim_instant_round_trips_and_closes_the_conjunction`
  — dice *"Until `ClaimRecipientUseCase` is reachable from this tier… ▶ **Re-point this arm at the real
  command once the claim lands**"*. Ya aterrizó, **en esta misma rama**: `UnclaimedSlotRefusedIssuanceTest`
  y `ConcurrentRecipientClaimTest` despachan `ClaimRecipient` por el bus desde ese mismo tier. El arm
  sigue estampando `claimed_at` con un `UPDATE` crudo, así que hidrata una fila que ningún camino de
  escritura produce. (`an_unrelated_later_write_does_not_erase_the_slot` sí lo observa, así que es
  debilidad, no agujero.)
- **El fixture llamado *phone-only slot* no lleva teléfono.** En
  `NotifyActivatedStepRecipientsUseCaseTest`, `$unclaimedPhoneOnly` se construye con `email: null` y el
  helper `recipient()` **nunca pasa `RecipientView::$phone`** (que existe). El docblock promete que *"the
  third fixture below is what turns red then"* el día que TASK-031 borre el skip `email === null` — pero
  seguirá siendo un destinatario sin contacto ninguno, no el tripwire de una fuga *phone-only*. La
  aserción se sostiene; la propiedad que dice proteger no está construida.
- **`docs/ddd/envelope-domain-model.md:402`** — nombra `RECIPIENT_CLAIM_REVOKED` en telemetría, una
  revocación que `Version20260828000001`, ADR-0057 §2.4 y BL-205 usan como premisa de que **no existe**.
  Atenuado: toda la subsección es diseño no construido.

---

## Merge con `origin/develop`

`git merge-tree` da **5 ficheros en conflicto**:

```
docs/BACKLOG.md
src/F5Sign/Envelope/Contract/View/RecipientView.php
src/F5Sign/Envelope/Domain/Entity/Recipient.php
src/F5Sign/Envelope/Infrastructure/Persistence/Doctrine/DbalEnvelopeRepository.php
src/F5Sign/Envelope/Infrastructure/Persistence/Doctrine/Read/DoctrineEnvelopeReadRepository.php
```

`docs/ddd/signing-session-domain-model.md` automerge limpio.

⚑ **Un detalle para quien resuelva:** `invitationsRevokedAt` (develop) y `declaredClaimable`/`claimedAt`
(rama) se añaden **los dos** justo detrás de `credentialsRetiredAt`, y **ambos ficheros llevan escrita la
frase** *"Added **last** … so no fixture constructing this positionally has to move"*. Después del merge
una de las dos es falsa.

Además: la migración de la rama es `Version20260828000001` y la de develop `Version20260901000001`, así
que se aplicará fuera de orden en entornos que ya corrieron la segunda. Doctrine lo hace, avisando; solo
hay que saberlo al desplegar.

---

## Comprobado y limpio

Lo hago explícito porque la mitad del valor está aquí:

**Las tres puertas están cerradas, y la enumeración de caminos es completa.** `rg 'issueFor' src/` da
exactamente cuatro llamantes de producción, revisados por línea de **constructor**:

| Llamante | Estado |
|---|---|
| `SigningTokenIssuance:194` | tras las dos negativas (`sentAt === null`, `isUnclaimedSlot()`) |
| `MintSigningTokenController:161` | llama al servicio guardado, nunca al puerto |
| `NotifyActivatedStepRecipientsUseCase:143` | `continue` sobre `isUnclaimedSlot()` en :112, **antes** del issuer |
| `NotifyCorrectedRecipientUseCase:136` | sin guard propio, cerrado **en origen** por `correctContact()` — transitividad no registrada en ningún censo (I5) |

Abrir sesión / firmar: toda ruta de destinatario declara `SIGNING_TOKEN` o `SESSION_CREDENTIAL`, y sin
token no hay entrada — cerradas aguas arriba. `MockSignUseCase` tiene handler pero **cero despachadores en
`src/`**. `ResetRecipientAccessCode` devuelve el código solo al llamante `MACHINE_KEY` y no entrega nada al
destinatario.

**El sentido inverso (silenciar a una parte ya reclamada) es imposible de escribir por accidente.** Todos
los predicados usan la conjunción; las cuatro lecturas de un solo término son legítimas y verificadas
(persistencia ×2, `guardClaimable()` que necesita distinguir los dos códigos, y `AddRecipientUseCase:61`
donde `claimedAt` es `null` por construcción).

- **Sin colisión de ids**: la rama usa BL-204…209; develop añade 229-230; los hermanos ocupan 210-213 y
  216-228. Censado con `git worktree list --porcelain`, incluido el anidado.
- **Regla 7 completa**: las cinco ediciones de aterrizaje están (fila de índice, grafo 341-345, crosswalk
  434, campo `Crosswalk` de cabecera, secciones `## 1..7`+`## 9`). ADR-0057 **no** se promueve.
- **Los 18 tests que §5 cita por nombre existen todos**, con ese nombre exacto. Ningún
  `RecipientClaimableSlotTest` fantasma sobrevive.
- **Regla 2 de repo limpia**: `Version20260820000002.php` solo cambia docblock (carve-out explícito);
  cero SQL publicado tocado.
- **Delta cero en `deptrac.yaml`, `phpstan.dist.neon` y `phpstan-baseline.neon`**: ninguna allowlist
  ensanchada, ninguna entrada nueva en el baseline.
- **La migración es ejemplar**: aditiva, `DEFAULT`+`DROP DEFAULT` con las dos razones separadas, regla 6
  respondida estado por estado incluyendo el lado de escritura, sin predicado de estado (correcto:
  *"nadie declaró esto"* es cierto en todos), sin envoltorio `NO FORCE`, sin trabajo de RLS ni grants
  (columnas heredan de `tenantStamp('recipient')` en `Version20260713000002`; grants son de tabla).
- **Round-trip de persistencia cerrado**: un solo constructor de producción de `RecipientView`, un solo
  `SELECT` por lado, `'declared_claimable' => 'boolean'` en el mapa de tipos DBAL, y
  `GetEnvelopeContextForRecipientHandler:47` reutiliza la **misma instancia** — no hay ruta que produzca
  una vista con los defaults.
- **Categorías del kernel conformes**: `RecipientClaimed` cumple `DomainEvent` (payload cerrado, sin PII,
  fixture); `ClaimRecipient` cumple `Command`; `ClaimRecipientUseCase` cumple `UseCase` (lock de raíz,
  guard antes de la mutación). `ClaimRecipientController` no importa `Envelope\Domain`.
- **`MACHINE_KEY::requiresDeclaredSubject()` es `true`**, así que la premisa del controlador (re-parsear
  la cabecera sin poder fallar por gramática) se sostiene.
- **El fixture de `it_does_not_invite_a_slot_nobody_has_claimed` discrimina de verdad** — tres brazos
  (declarado+sin reclamar+alcanzable / declarado+reclamado+alcanzable / declarado+sin reclamar+inalcanzable)
  — y asierta sobre **emisión de credencial**, no sobre el mensaje.
- **`docs/ARCHITECTURE.md` no debía tocarse**: 45 líneas de tabla de enrutado, sin una sola afirmación
  que la rama falsifique.
- **Catálogo `ProblemCode`**: los cuatro miembros nuevos son exactamente el conjunto que llevan las
  factories nuevas, y `OpenApiSpecTest` lo fuerza mecánicamente **en las dos direcciones**. Toda respuesta
  que pide ramificar por `code` declara `content: ProblemDetails`, así que ninguna se tipa `void` en un
  cliente generado.
- **Promesa de idempotencia vs. código**: lo que el `#[OA\*]` promete (réplica idéntica → 204; campo
  **omitido** no se compara; campo suministrado que contradice → 409 nombrándolo) coincide exactamente con
  `claim()` + `guardReplayMatches()` — `fullName` sin condición, los otros tres solo si no son `null`, y el
  teléfono por valor canónico E.164 y no por identidad de objeto.
- **`RecipientClaimed`**: `EVENT_TYPE` fijado por aserción literal, key-set cerrado por igualdad sobre
  `array_keys()` (no `assertArrayNotHasKey`), y el fixture satisface los dos brazos de
  `GoldenPayloadBytesTest`.
- **La conjunción vs. una sola bandera está genuinamente discriminada en los tres tiers del mint**
  (hermético, integración, HTTP): cada uno tiene el arm *claimed* que enrojece si el guard se teclea sobre
  `declaredClaimable` solo. El 409 del claim enumera los outcomes terminales como **ejemplos** de la
  propiedad, no como lista cerrada, así que no se pudre en silencio.
- **Metadatos de cobertura**: los ocho ficheros de test nuevos llevan `#[CoversClass]` o `#[CoversNothing]`
  con la razón escrita. `php -l` limpio en los 42 ficheros PHP del rango.

---

## Recomendación

**No fusionar hasta B3 y B1.**

- **B3** es el único hallazgo que deja código de seguridad sin red: dos tests triviales lo cierran, y hasta
  que existan, la frase de §5 que dice que ese código está probado hay que borrarla o hacerla cierta.
- **B1** es mecánico y barato: correr la lane sobre la punta y re-fechar las dos filas. Hoy no hay ninguna
  ejecución que cubra `c1c0516`, que es justo el commit que introdujo I1 y cuyo arreglo I13 no prueba nada.
- **B2** y **I2/I3/I4/I14** están en **superficies publicadas que otro repo consume**: se arreglan antes del
  merge o no se arreglan.

**I5** (el eje ausente del censo de `ISSUER_CALLERS`) es el único hallazgo estructural: no rompe nada hoy y
es lo que impide que se vuelva a abrir una cuarta puerta mañana. Cabe en TASK-037 si se registra ahora.

⚑ **Un patrón vale más que la lista.** B3, I13 y el fixture *phone-only* son el mismo defecto: la rama
escribió el razonamiento de por qué un guard importa **antes** que el test que lo ejerce, y el razonamiento
es tan bueno que se lee como cobertura. Los tres docblocks son correctos; lo que falta es el fixture. Es
literalmente lo que CLAUDE.md avisa al final de las Authoring rules — *"knowing a rule is not the same as
applying it under momentum"* — y lo que caza es lo mecánico: sabotear el guard y ver si enrojece.

⚠ **I2 e I3 tocan `MintSigningTokenController` y `SigningTokenIssuance`, que es territorio de la rama
hermana ya fusionada.** Coordinar antes de editar.

---

## Resolución — 2026-09-01, mismo día

Arreglado en `feat/claimable-recipient-slot`, catorce commits sobre `829574c`, cerrando con un merge de
`origin/develop` en `5db1d28`. **Lane verde en `22328ad`**: `lint 0 of 1058` · `Violations 0` ·
PHPStan `[OK] No errors` · **`OK (2547 tests)`**, como `f5sign_app` contra RLS real, exit 0. Cero líneas
de fallo en la salida completa.

**Los tres bloqueantes, cerrados.** B3 tiene ahora dos bars, cada una verificada por sabotaje
independiente. B1 está re-fechado con la cifra real y la lectura vieja conservada como lo que era
cierto el 08-28. B2 resultó estar además en **una segunda superficie publicada** que la auditoría no
vio (`AddRecipientRequest::$locale`).

**Un hallazgo que la auditoría no tenía, encontrado al planificar** (§0 del plan): la convergencia del
replay estaba **acotada por el tiempo** — si el firmante completaba entre la llamada y su reintento, el
cliente recibía el `409` que el `#[OA\*]` le decía que no podía recibir. Y el arreglo obvio en la
entidad **no bastaba**: la ruta HTTP seguía dando 409 con el test del agregado en verde, porque el use
case pregunta antes por su propio guard temprano. Dos bars, una por tier, porque fallan por razones
distintas y un arreglo que satisfacía solo una es exactamente lo que pasó.

**Lo que hicieron los agentes en paralelo y yo no habría visto**: la segunda superficie de `locale`, el
espejo del defecto de enlaces en ADR-0055 y ADR-0058 (tres ADRs negándose a enlazarse entre sí, ninguno
re-comprobado contra el árbol), dos filas de `docs/adr/README.md` con un `|` sin escapar, y que
`problem-code-catalog.md` publicaba 19 códigos cuando son 26.

**Diferido con fila propia**, no olvidado: `BL-231` (el cuarto fan-out, alcanzable el día que llegue
BL-192), `BL-232` (`RecipientClaimed` fuera del subconjunto auditable, sin decisión registrada) y
`BL-233` (`locale` sin trimear, con el arreglo correcto nombrado en el value object).

**I2/I3 no los arreglé yo**: la sesión hermana los corrigió en `develop` tras el aviso, y encontró un
tercer sitio (`EnvelopeNoLongerLiveException`). Aquí solo se resolvió el merge tomando su redacción.

⚑ **Dos cosas que aprendí ejecutando y que no estaban en el plan.** Un sabotaje mío no saboteaba
—reinsertaba el mismo orden— y pasó verde; si no llego a mirar el fichero, habría reportado un test
como verificado sin serlo. Y resolviendo el merge concatené dos veces un docblock separándolo de su
campo, porque el `/**` de apertura vive en el **contexto compartido encima** del marcador y pertenece
al lado que vaya primero: un hunk de conflicto dentro de una lista de propiedades promovidas no es
autocontenido. Las dos las cazó algo mecánico (`php -l`), no la lectura.
