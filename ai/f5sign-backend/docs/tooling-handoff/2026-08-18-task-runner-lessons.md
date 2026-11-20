# Traspaso a tooling — seis lecciones de correr `/task-runner` de punta a punta, cuatro ya aplicadas en la skill

| | |
|---|---|
| **Origen** | rama `feat/session-credential-and-refresh` · commit `f318c9e` · corrida de `/task-runner TASK-029` con **cinco subagentes en paralelo**, 2026-08-18, desde el worktree `f5sign-backend-develop` |
| **Fecha** | 2026-08-18 |
| **Store afectado** | `ai/f5sign-backend/.claude/skills/task-runner/SKILL.md`, en el **repo raíz del workspace**. Desde este repo se ve como `.claude/skills/task-runner/SKILL.md`, que es el symlink al mismo fichero. **Ninguna otra skill se ha tocado** |
| **Naturaleza** | **cuatro cambios ya aplicados** en `task-runner` · **dos propuestas no aplicadas** que cambian política de puertas y son decisión del usuario · dos confirmaciones |
| **Acción requerida** | **revisar y commitear el store en el repo raíz** (aquí no aparece y no puede aparecer) · **decidir las dos propuestas de §2** |
| **Status** | Pending |

> ⚠ **Los cambios de §1 están en el árbol del repo raíz, sin commitear.** Commitearlos cruza repos y es
> decisión del usuario (reglas 1 y 4 del workspace). El `git status` de **este** repo no los muestra:
> el fichero vive en otro sitio y llega por symlink ignorado.

La corrida fue una task grande —credencial de sesión, refresco con rotación, partición de rutas— ejecutada
con el orquestador y cinco agentes de validación en paralelo. Todo lo de aquí sale de esa corrida; nada es
teórico. Las dos lecciones que **cambiaron un resultado** son §1.2 y §2.1.

## 1. Lo que se cambió en `task-runner` (aplicado)

### 1.1 Precondición 3 — pedía un checkout que un worktree no puede hacer

**Lo que decía**, literal: *"Si no estás en `develop`, hacer checkout antes de crear la rama de la task."*

**Lo que pasó.** En un **worktree enlazado** ese checkout es imposible: el checkout principal ya tiene
`develop` tomada y git se niega a tener la misma rama dos veces. O sea que la precondición se bloqueaba a
sí misma justo en el entorno del que habla su propia precondición 5 —la que avisa de que las validaciones
por Makefile miran el otro árbol—, y no hay forma de cumplirla ahí.

**Lo que dice ahora.** Ramificar desde la **ref**, no desde el checkout: `git checkout -b <rama> develop`.
Es equivalente en cualquier entorno y funciona en todos. Una línea. El paso 5 de la Fase 0 (el de la
convención de nombres de rama) apunta ahora a esa precondición en vez de decir sólo *"desde `develop`"*.

### 1.2 Fase 3 — cada agente en paralelo necesita una lista explícita de rutas

**Lo que decía**, literal y completo sobre el reparto de trabajo:
*"En paralelo (varias llamadas Agent en un solo mensaje)."* Nada sobre **qué ficheros puede tocar cada uno**.

**Lo que pasó**, y es daño real, no hipotético:

- Un `git add -A` del orquestador se llevó por delante las ediciones **en vuelo** de un agente de
  validación. El agente reportó después que sus entregables *"estaban en HEAD aunque él nunca commiteó"*, y
  que **HEAD no estaba verde** sin el delta que todavía tenía en el árbol de trabajo. Ninguna de las dos
  cosas se ve desde el diff, y las dos son exactamente lo que uno no quiere descubrir tarde.
- Dos agentes necesitaron **sabotear ficheros del orquestador** para comprobar que una guarda falla por su
  propio motivo. Salió bien, y salió bien **sólo** porque el brief les exigía restaurar de inmediato y
  demostrarlo con un `git diff` vacío. Esa exigencia estaba en el brief de esa corrida, no en la skill.

**Lo que dice ahora.** Cada Agent lanzado en paralelo recibe una **lista explícita de rutas que puede
tocar**, y la orden de **reportar —no editar—** cualquier cosa que encuentre fuera de ella; `git add -A` con
agentes vivos queda declarado incorrecto (rutas explícitas, o commitear cuando no quede ninguno corriendo);
y el sabotaje de ficheros ajenos se declara legítimo **con** su obligación de restaurar y demostrarlo.

⚑ **Y la parte que no es defensiva:** *"reporta lo que veas fuera de tu lista"* fue lo que produjo el
hallazgo más valioso de toda la corrida — el de §2.1. La instrucción se paga sola.

### 1.3 Fase 0 — no había ningún paso que estableciera un baseline verde

**Lo que decía.** La Fase 0 tenía seis pasos —resolver el `.md`, leer la cabecera, verificar `Builds on`,
crear workspace, rama, `run.log`— y **ninguno ejecutaba nada**.

**Lo que pasó.** Antes de tocar una línea corrí la suite completa y anoté **1619 tests / 6704 assertions**
en verde. Esa corrida **sí** se puso roja más tarde, por motivos de entorno, y ese número fue lo único que
permitió separar mis rojos de los preexistentes sin dudar. Sin él, la alternativa es discutir a ciegas o
volver a bisecar a mano.

**Lo que dice ahora.** Un paso 7 de Fase 0: correr la suite **por el harness declarado en la precondición 5**
y anotar tests y asserts en `run.log` y en el resumen final, con su línea
`{"phase":"baseline","status":"pass","tests":N,"assertions":M,"harness":"…"}`. Un baseline rojo **no aborta**
la task, se declara: lo que no vale es descubrirlo a mitad de la Fase 3 y atribuirlo al diff.

### 1.4 Fase 3 — nada comprobaba que un listener o servicio nuevo esté registrado

**Lo que decía.** Nada. La tabla de validaciones condicionales deriva skills del diff, y ninguna de ellas
mira el contenedor.

**Lo que pasó.** Corrí `debug:event-dispatcher kernel.controller` por instinto y confirmé que los dos
listeners nuevos ([`SessionCredentialListener`](../../src/F5Sign/Foundation/Http/SessionCredentialListener.php)
y [`SessionRenewalListener`](../../src/F5Sign/Foundation/Http/SessionRenewalListener.php)) estaban
registrados y disparando. Que salieran bien no quita que **nada lo comprobaba**: un listener sin cablear es
un **no-op silencioso** —sin error, sin excepción— y la suite puede seguir verde porque los tests unitarios
de controlador fijan los atributos de la request a mano y **se saltan el listener**. Eso no es una sospecha:
la barra de aceptación 11 de [TASK-029](../tasks/TASK-029-session-credential-and-refresh.md) lo dice de sus
propios tests, *"do not read their green as coverage of this change"*.

**Lo que dice ahora.** Si el diff añade un event listener, un middleware o un servicio etiquetado, comprobar
que está **registrado**: `debug:event-dispatcher <evento>`, `debug:container --tag=<tag>`, `debug:messenger`.
Un comando, y ningún gate del stack lo cubre.

## 2. Lo que NO se cambió, y por qué: es decisión del usuario

Las dos cambian **política de puertas** —qué bloquea una corrida y qué exige una validación—, y eso no lo
decide el agente que ejecuta la task. Van con su evidencia y se quedan esperando.

### 2.1 `docs-sync` está declarada como no-gate, y encontró un defecto de código real

**Lo que la skill dice hoy** (Fase 5, sin tocar): *"No es gate duro: si falla, warn y seguir."*

**Lo que encontró.** [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) §2.3 promete sesenta
minutos de vida para la credencial de refresco, y su §2.5 dice que esa caducidad **es** el reloj de
inactividad de la sesión. **No había código que lo implementara.** Sólo existían el tope absoluto de doce
horas y la ventana de gracia de treinta segundos, así que **no había timeout de inactividad en absoluto**:
un firmante podía abandonar la sesión once horas y reanudarla.

⚑ **Por qué ningún test lo cazó.** Las **doce** barras de aceptación de la task nombran rotación, ventana de
gracia o tope. **Ninguna nombra la inactividad.** La lista de barras era ella misma el predicado incompleto
contra el que avisa la regla de autoría 5 de [`CLAUDE.md`](../../CLAUDE.md) —*"an enumeration is a predicate,
and the set it exempts is everything not yet listed"*—, aplicada a un **checklist** en vez de a código. Un
gate no puede cazar lo que la lista no nombra, por construcción.

Se arregló dentro de la propia corrida: `f318c9e`, *"the twelve acceptance bars, and the idle clock nobody
had built"*; el reloj vive ahora en
[`SigningSession`](../../src/F5Sign/Session/Domain/Aggregate/SigningSession.php).

**La lección, dicha con precisión — y no es "convertir `docs-sync` en gate duro":** una pasada de
documentación detecta una clase de defecto que **ningún test puede** detectar — *un mecanismo decidido y
documentado que nunca se construyó* — precisamente porque los tests sólo cubren lo que a alguien se le
ocurrió nombrar. Si eso justifica hacerla gate, o un warn con otra forma (por ejemplo: bloquear sólo cuando
el diff toca un ADR que la task cita), es decisión del usuario.

### 2.2 Exigir evidencia de sabotaje en `task-validate-backend`

**No se ha tocado esa skill**, ni ninguna otra. La disciplina de sabotaje está hoy en `CLAUDE.md` (regla de
autoría 4, *"sabotage before you trust it"*) y **no** en ninguna skill del stack.

**Lo que pasó.** Todos los defectos genuinos de esta task salieron de sabotear, no de leer:

- **El codec JWT**: los siete tests de rechazo pasaban mientras **el camino feliz fallaba**.
  [`SessionCredentialCodec`](../../src/F5Sign/Foundation/Http/SessionCredentialCodec.php) verifica con
  `StrictValidAt`, que **exige** un `nbf` que la emisión no acuñaba — así que nuestro propio verificador
  rechazaba toda credencial que emitíamos. Un codec que rechazara *absolutamente todo* habría pasado 7 de 8
  comprobaciones.
- **Quitar la sentencia GUC del listener de sesión** sirvió el nombre del sobre, el id del documento y el
  nombre y el email del firmante **de un tenant a la credencial de otro**: un **200**, sin 401, sin 403 y
  sin excepción de ningún tipo. Sólo filas que no debían salir.
- **Los rojos del reuse-kill** caían sobre la aserción de **estado** mientras la de **resultado**, una línea
  más arriba, seguía en verde: una guarda que decía dispararse sin limpiar nada.

**La propuesta.** Que `task-validate-backend` exija **evidencia de sabotaje para toda guarda nueva** y
—esto es la parte que importa— que **obligue a reportar honestamente cuando NO se ha conseguido hacer fallar
un test**, en vez de reportar el verde. Cambia lo que un gate duro exige, así que no se ha aplicado.

## 3. Confirmaciones — lo que ya funcionaba, y no hay que "arreglar"

- **El skip declarado de `perf-smoke-backend` (Fase 4) es el precedente bueno**, y conviene nombrarlo como
  tal: la skill lo registra como
  `{"phase":"perf-smoke","status":"skipped","reason":"no perf:seed script"}` y remata *"un skip declarado, no
  un verde"*. Esa forma —declarar lo que no se pudo ejecutar, con su razón— es exactamente lo que §2.2 pide
  en otro sitio. **No convertirlo en verde ni quitarlo** mientras `composer perf:seed` no exista.
- **`var/task-runner/TASK-NNN/` es de root y no deja escribir desde el host, y la skill lo anticipa.** El
  fallback que propone —escribir los reports en el scratchpad de la sesión y **decir en el resumen dónde
  quedaron**— funcionó tal cual en esta corrida. Se confirma para que a nadie le parezca residuo: quitar el
  fallback, o "arreglarlo" con un `chown` de `var/`, elimina una salida que sí funciona.

## 4. Cómo verificarlo

- **El estado real de la skill** es el fichero, no este registro: `cat .claude/skills/task-runner/SKILL.md`
  desde este repo (sigue el symlink), o `ai/f5sign-backend/.claude/skills/task-runner/SKILL.md` desde la
  raíz del workspace. Si discrepan, gana el fichero.
- **Que los cambios de §1 siguen ahí**: buscar en esa `SKILL.md` *"Ramificar desde la ref"*, *"Baseline
  verde"*, *"lista explícita de rutas"* y *"registrado de verdad"*. Cuatro cadenas, cuatro cambios.
- **El defecto de §2.1, en código**: buscar `idle` en
  [`SigningSession`](../../src/F5Sign/Session/Domain/Aggregate/SigningSession.php) — si el reloj de
  inactividad no está ahí, la corrección se ha perdido en un rebase.
- ⚠ **Nada de §1 está commiteado, y no saldrá en el `git status` de este repo.** Vive en el repo raíz del
  workspace, donde ya puede haber otros cambios del store sin commitear de otras sesiones: mirar antes de
  commitear en bloque.
