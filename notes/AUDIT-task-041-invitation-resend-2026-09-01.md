# AUDIT — TASK-041, resending a signing invitation

**Rama** `feat/recipient-invitation-reminder` (f5sign-backend) · **base** `70af999` (merge-base con
`origin/develop`) · **alcance** 47 ficheros, 4.573 inserciones, incluyendo los cambios sin commitear ·
**fecha** 2026-09-01.

Seis auditorías paralelas en lectura estática: seguridad, lógica de negocio, ADR + reglas del repo,
persistencia, rot de prosa + contratos publicados, y fuerza de los tests. Las afirmaciones de cada una
se re-verificaron a mano antes de escribirlas aquí; donde una comprobación contradijo al informe, manda
la comprobación (ver *Correcciones a los propios informes*).

---

## 1. Lo que sigue abierto y es una decisión, no un arreglo

Los tres están registrados en `docs/tasks/TASK-041-…md` §7 y no se han tocado.

### 1.1 Un reenvío a un destinatario sin dirección tiene éxito en silencio

`NotifyResentInvitationRecipientUseCase` retorna temprano con `$recipient->email === null`, y su
comentario justifica la colocación diciendo que *"no es algo que el borde de la API pueda producir"*.
**Es falso**, comprobado en el árbol:

- `AddRecipientRequest::$email` es `?string $email = null`; `#[Assert\Email]` no valida null.
- `DeclaredMethodDestinations::guard()` hace `return` cuando el destinatario no declara requisito de
  autenticación — el caso de la puerta neutra.
- `Envelope::ensurePreSendInvariants()` cubre documentos, artefactos, pasos, destinatarios por paso,
  asignación de firma y visibilidad. Ningún invariante de contacto.
- `grep -rn "email === null" src/F5Sign/Envelope/` → vacío.

Consecuencia: 204 al remitente con la descripción publicada *"a fresh invitation is on its way to the
address on file"*, ordinal gastado, `RecipientInvitationResent` escrito en un log **append-only**
afirmando un reenvío que no ocurrió, y al segundo intento un 409 *"enviado hace muy poco"* sobre un
correo que nunca existió. El arreglo natural es un rechazo en `Envelope::resendInvitation()` con su
propio `ProblemCode`, que deja contador y hecho sin gastar — pero es un rechazo nuevo en una ruta ya
publicada.

### 1.2 Un reenvío con éxito nunca limpia `DELIVERY_FAILED`; uno fallido sí puede ponerlo

El único escritor que devuelve un destinatario a `PENDING` es `correctContact()`. A la vez,
`RECIPIENT_INVITATION_RESENT` responde `carriesMeansToAct() === true`, así que
`PropagateDeliveryFailureUseCase` puede marcar el fallo desde un reenvío. La bandera que este gesto
puede subir es una que no puede bajar, y limpiarla sigue costando una corrección: el coste que §1 de la
tarea existe para eliminar. Devolver a `PENDING` pierde el registro de que una entrega falló, así que es
su propia decisión.

### 1.3 La colisión de versión de migración se trasladó, y en la dirección silenciosa

`doctrine_migration_versions` guarda la **cadena**. `7485b16` renombró `Version20260831000001` →
`...0002` para resolver una colisión con `feat/delegated-signature`, pero cualquier volumen que corriera
esta rama antes del renombrado tiene la cadena vieja grabada — y esa cadena es ahora la de la otra rama.
Cuando aterrice, `migrate` encuentra la fila, **reporta éxito y no crea ninguna de sus seis columnas
`asserted_*`**. Es el mismo no-op que documenta BL-211, apuntando al revés y sin ruido: no falla nada y
ninguna columna se reporta duplicada. `BL-211` ya lleva la cláusula que lo dice; falta que alguien corra
`make -C ../f5sign-infra test-db-reset` **antes** de esa rama.

---

## 2. Riesgos de diseño levantados y no resueltos

- **Acumulación ilimitada de credenciales vivas.** Cada reenvío acuña una credencial de 7 días y no
  retira la anterior — deliberado (ADR-0045 §2.6), pero argumentado cuando la única vía de reemisión
  estaba acotada a 3 por `MAX_CORRECTIONS`. Con el suelo en 60 s el techo es ~10.000 credenciales
  portadoras simultáneamente válidas para un destinatario. La premisa del ADR no se revisitó.
- **Sin techo de plataforma.** El endpoint no consume ninguna política de `rate_limiter.yaml`; el único
  freno es el intervalo por destinatario, que es una regla de dominio y así lo declara. N destinatarios
  × M sobres enviados dan 60·N correos/hora saliendo del dominio de envío, y la reputación de envío no
  es un recurso por-destinatario.
- **`next_resend_at` puede desaparecer del cable con la suite verde.** Basta borrar `, ProblemExtensions`
  de la declaración de `RecipientNotResendableException`: la única aserción llama al método
  directamente, el 409 de aceptación solo lee `code`, y no existe censo sobre esa interfaz (`ProblemCoded`
  sí lo tiene, bidireccional, en `OpenApiSpecTest`).
- **La guarda del intervalo es invisible a Infection.** Ningún test que la ejerza atribuye
  `#[CoversClass(Recipient::class)]` — el único que la tiene, `RecipientTest`, no contiene ningún caso de
  resend — y `#[UsesClass]` no da crédito de cobertura. Cae en *Not Covered*: mueve `minMsi` y nunca
  `minCoveredMsi`, así que su debilitamiento futuro puntúa verde por ausencia.
- **`next_resend_at` no está en el esquema publicado.** Corregido (§3), pero conviene saber por qué pasó:
  el controlador se modeló sobre `CorrectRecipientController`, que no lleva extensiones, y el hermano que
  sí las lleva (`SendAuthOtpController`, con `allOf`) no se abrió. Es la regla 3 de autoría al pie de la
  letra.

---

## 3. Arreglado en esta pasada

Todo lo de abajo es prosa, cuentas y punteros: cero cambios de comportamiento.

**El barrido del `900 → 60` que el cambio sin commitear no hizo.** El intervalo bajó de 15 min a 60 s y
tres cifras derivadas quedaron atrás, incluida la que sostiene la disposición de `BL-213` (*"341 días de
un integrador en bucle … por eso se archiva como nota y no como defecto"* — a 60 s son ~23 días, quince
veces más débil). Corregidos `BL-213` (×2), TASK-041 §7 y la fila de Status, más una frase de test a
medio convertir (`< 60` y `<= 900`) y el mensaje de un `self::fail` que describía una entrada que ya no
era. En los tres sitios la cifra se ató al constante en vez de reescribirse a pelo.

**Enumeraciones cerradas que ya mentían.** El docblock de `SigningTokenIssuer` concedía la licencia a
*"two triggers"* habiendo tres inyectores — y esta rama razonaba **desde** esa frase en dos ficheros
nuevos. `SigningTokenIssuance` decía *"its two minting sites"* y predecía literalmente que un tercero
*"hereda la pregunta, no la respuesta"*: el tercero llegó, así que ahora se registra que la heredó y la
contestó por su cuenta. También: *"its two siblings"* en `NotifyCorrectedRecipientUseCase` (son cuatro),
*"the strictest trigger of the four"* sobre un mapa de cinco, la afirmación de `CorrectRecipientController`
de que los 409 del lado Envelope son todos sin cuerpo (esta rama añadió el contraejemplo mientras editaba
ese mismo fichero), y las filas *"Two purposes"* de ADR-0037 y de su fila de índice en `docs/adr/README.md`
— fichero que no se abrió en toda la rama, y que además seguía listando como diferido el camino de
retorno `NotificationFailed` → Envelope, construido el 2026-08-18.

**Dos autocontradicciones dentro del mismo fichero**, ambas de la misma forma: la rama **midió** que una
afirmación vieja era falsa y la dejó en pie. El docblock de `RETIRES` decía que los casos conductuales
conducen *"every `true` and every `false`"*, y el caso nuevo, diecinueve líneas más abajo, registra la
medición de que no (voltear `resendInvitation` a `true` dejó el fichero verde). Ahora dice qué cuatro
filas están respaldadas y cuáles siete no, y por qué el censo no cierra el hueco: deriva el universo del
agregado y falla ante un gesto **sin clasificar**, lo que caza una fila que falta y no dice nada sobre una
equivocada.

**`docs/LIVE_SCHEMA.md`.** Tres columnas de `envelope.recipient` estaban documentadas **dos veces** con
redacciones que discrepaban (una decía que el vocabulario se comprueba con `from()` en la lectura, su
gemela decía *"No `CHECK`"*). Duplicados borrados. Y la nota que las justificó afirmaba que faltaban
**siete** columnas cuando faltaban tres: `corrections_made` y las tres de la traza de acceso ya estaban.
Esa frase era la que iba a impedir que el siguiente lector volviera a comprobar. También se acotó el rango
de la nota de cobertura, que afirmaba que ninguna migración del tramo añade *constraint* cuando la propia
marca añade `recipient_resends_made_chk`.

**El docblock de la migración**, que el `CLAUDE.md` señala como la superficie de mayor valor cuando se
pudre. Cuatro cosas: enunciaba el conjunto terminal como *"COMPLETED / VOIDED / EXPIRED"* omitiendo
`DECLINED`; reformulaba la regla 2 con *"unmerged"* donde la regla dice **unpushed** (una cláusula después
de decir que la rama estaba pusheada); ofrecía un round-trip `down()`/`up()` como segundo remedio que **no
funciona** —el volumen afectado tiene `last_reminded_at`, que `down()` no dropea, y ninguna propiedad de
conformidad busca columnas desconocidas—; y llamaba a los recordatorios *"the automatic half of this
feature"*, encuadre que `BL-210` retiró el 2026-08-31 en el renombrado de esta misma rama.

**Punteros y varios.** `notification-domain-model.md` llamaba *nudge* al reenvío — la palabra de la
feature de la que esta rama se separó a propósito — y afirmaba un binding `SendReminder.#` *"reservado y
sin usar"* que **no existe** (`grep -rn SendReminder config/ src/` → 0). El docblock de
`RecipientNotResendableException` decía que la familia de cooldown usa un miembro relativo, cuando publica
`retry_at` absoluto **y** `retry_after_seconds` al lado. `NotifyResentInvitationRecipientUseCase` decía
*"todo lo que difiere está en las dos líneas de abajo"* sobre cinco párrafos de los que cuatro describen
cosas que comparte con la corrección. Y el ejemplo del handoff mostraba una ventana de 15 minutos, con una
advertencia añadida de no deducir el intervalo del ejemplo.

### La cita `BL-214` no estaba colgando: aterrizaba sobre otro

Un test citaba `[BL-214]`, que no existe en `docs/BACKLOG.md` (máximo local: BL-213). El audit de ids
**a través de todas las refs y worktrees** —que es la parte que casi se salta— da un máximo real de
**221**: `BL-214`/`BL-215` son de `feat/delegated-signature` y `BL-216`–`221` de `docs/outbound-webhooks`.
Escribir la fila como BL-214 habría colisionado, y la cita viva habría acabado apuntando al asunto de otro.
La fila se creó como **BL-222**.

---

## 4. Lo que está bien, dicho en voz alta

- **ADR-0037 no se afloja.** Los cuatro hunks de la edición sustituyen cuentas por propiedades, ningún
  texto de decisión cambia, y la dirección real está verificada en código: cero imports de
  `F5Sign\Notification` en Envelope (los 10 hits son punteros `{@see}`), y los 26 de Notification hacia
  Envelope pasan **todos** por `Contract/`.
- `deptrac.yaml`, `phpstan.dist.neon`, el baseline, `composer.json/lock`, `Kernel/`, `Foundation/` y todos
  los `.env*`: diff vacío. Trailers de IA en los commits: **0**.
- **El barrido `reminder → resend` es impecable** en código, tests y config: `RECIPIENT_REMINDER`,
  `Recipient::remind()`, `last_reminded_at`, la ruta `/reminders` — todo ausente; lo que sobrevive es o el
  distinto `RemindersSchedule` o un registro fechado del cambio.
- **La regla 6 de autoría sale bien.** `resends_made` se rellena con `DEFAULT 0` y luego `DROP DEFAULT`,
  sin predicado de estado y correctamente sin él porque el valor es universalmente cierto (el comando no
  existía). `last_resent_at` **no** se rellena, con la asimetría argumentada: `NULL` significa "nunca
  reinvitado", que es lo que admite el primer reenvío; rellenarla habría dejado a cada destinatario
  preexistente bloqueado el intervalo sin API para limpiarlo.
- **No hay defecto tipo `Role::signs()`.** No existe predicado de rol en el camino, y la invitación tampoco
  lo tiene, así que no hay conjunto exento infra-justificado. (Sí queda sin escribir que reenviar a un
  `IN_PERSON_HOST` o `CERTIFIED_DELIVERY` manda un correo cuya sesión responde `ROLE_NOT_INTERACTIVE` —
  heredado de la invitación, no una regresión.)
- **Dos ejemplos de disciplina que merecen copiarse**: el censo de retirada de credenciales se acompañó de
  un caso conductual *después de medir* que la fila del mapa sola no se autoverificaba; y el test de la
  frontera del intervalo asevera el mensaje con el número dentro, así que cambiar el constante enrojece el
  par en vez de mover la línea bajo él.

---

## 5. Correcciones a los propios informes

Registradas porque el patrón —un agente seguro sobre un árbol equivocado— es el que más caro sale aquí.

- Una comprobación mía dio `BL-214` inexistente y "341 days" ausente del repo. **Las dos eran falsas**: un
  `cd` a un worktree anidado había persistido entre llamadas y estaba mirando otro árbol. Repetidas en el
  checkout principal, las dos afirmaciones del informe se sostuvieron.
- El agente de ADR dio la cita `BL-214` como "no existe". Existe — en otra rama. El diagnóstico correcto
  no es *dangling* sino *colisión futura*, y cambia el arreglo.
- El `CLAUDE.md` del backend dice que `make test` "auto-ensures stack + test-db". No lo hace: con el stack
  abajo, `ensure-stack` falla y manda ejecutar `make up`. No se corrige aquí porque ese fichero es un
  symlink al repo raíz y no puede aterrizar con esta rama.

---

## 6. Higiene del workspace, fuera del diff

`f5sign-backend/worktrees/f5sign-backend/Senry` es un worktree **real dentro del checkout principal**, en
`feat/terminal-envelope-and-credential-retirement`. Lo prohíbe la regla 1 de worktrees del `CLAUDE.md`
raíz: queda dentro del bind-mount `../f5sign-backend` del stack, es el `?? worktrees/` del `git status`, y
sus ficheros son visibles a toda ejecución de puertas. Debería ser hermano (`f5sign-backend-senry/`) y
entrar en el `.gitignore` de la raíz, cuya lista —dice el propio fichero— se mantiene a mano.

---

## 7. Puertas, tras los arreglos de prosa

Corridas desde el checkout **principal** con el harness verificado (`git rev-parse --git-dir` = `.git`,
`git -C ../f5sign-infra status --porcelain` vacío, el `docker-compose.override.yml` **commiteado**
bindeando `../f5sign-backend`), es decir validando *este* árbol:

| Puerta | Resultado |
|---|---|
| `make lint` | `0 of 1054` |
| `make composer cmd=arch` (deptrac) | `Violations 0` |
| `make phpstan` (L9) | `[OK] No errors` |
| `make test` | `OK (2515 tests, …)` |

Dos cosas que salieron de correrlas y que no estaban en ningún informe:

**`make test` no levanta el stack.** El `CLAUDE.md` del backend dice *"Tests (auto-ensures stack +
test-db)"*. Con los servicios abajo, los cuatro targets mueren con *"servicios requeridos no estan
arriba: postgresql redis rabbitmq php-fpm — Ejecuta 'make up'"*. Confirmado por `f5sign-infra-33`: el
target vive en `f5sign-infra/Makefile:306`, y *ensure* ahí significa **comprobar**, no levantar. La
elección texto-vs-target es de infra, no del backend; queda trasladada.

**El conteo de aserciones de la suite es no determinista.** Tres corridas consecutivas del mismo árbol,
sin edición entre medias, dieron **12173 · 12175 · 12174**, con el número de tests fijo en 2515. No lo
causa esta rama —se reproduce en ella, no nace de ella— pero sí invalida la práctica de citar una cifra
exacta de aserciones como línea base: la fila de Status de TASK-041 comparaba *"assertion-identical"*
contra un número que se mueve ±2. El número estable es el de tests. Registrado en esa fila.

Un falso positivo propio, dejado aquí porque el razonamiento es reutilizable: al ver el +2 la hipótesis
obvia era que mi docblock había contaminado el censo de
`SigningReadersRefuseUnsentEnvelopeTest`, que deriva sus miembros escaneando fuente y asigna una
aserción por miembro. Es imposible: su helper `code()` filtra `T_COMMENT` y `T_DOC_COMMENT` antes de
contar, así que ningún comentario puede entrar en ese censo. La comprobación costó menos que la
suposición.

## 8. Estado de la rama al cerrar

Arreglado y verde: 19 ficheros de prosa, cuentas y punteros; cero cambios de comportamiento. Sin tocar:
los tres hallazgos de §1, registrados en TASK-041 §7 y en `BL-211`/`BL-222`. Pendiente de decisión del
usuario antes de commitear.
