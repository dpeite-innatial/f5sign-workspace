---
name: task-runner
description: 'Orquestador único del stack de skills de ejecución de tareas del backend. Ejecuta una task de docs/tasks/ end-to-end invocando skills especializadas (spec-lint, implement-backend, task-validate-backend, security-audit-core, etc.), gestionando gates, workspace en var/task-runner/TASK-NNN/, rama git y PR final. Úsalo con /task-runner TASK-NNN o /task-runner {ruta al .md}. Activar con frases como "ejecuta TASK-024", "corre la tarea X", "task runner sobre...".'
---

# Task Runner

Orquestador del stack de ejecución de tareas del backend.

> **Convención de tasks: [`docs/tasks/README.md`](../../../docs/tasks/README.md).** Es la fuente de verdad
> del formato, de cómo se acuña un id y de qué significa cada campo de la tabla de cabecera. Esta skill
> valida contra ese README; si discrepan, gana el README.

## Invocación

```
/task-runner TASK-NNN                 # ej: /task-runner TASK-024
/task-runner {ruta al .md}
/task-runner TASK-NNN --auto          # no supervisado (default: supervised)
/task-runner TASK-NNN --resume         # reanudar workspace existente
```

Si no se pasa argumento, pedir al usuario el id o la ruta.

## Precondiciones

Verificar y **parar con mensaje claro** si falla:

1. El `.md` de la task existe en `docs/tasks/TASK-NNN-*.md` y es legible.
2. `git status` limpio en la rama actual.
3. La rama base es **`develop`**, no `master`. El trabajo de producto se integra en `develop`; `master`
   es la rama de publicación. ⚑ **Ramificar desde la *ref*, no desde el checkout**:
   `git checkout -b <rama> develop`. Es equivalente en cualquier entorno y es la única forma que funciona
   en un **worktree enlazado** —el entorno del que habla la precondición 5—: allí `git checkout develop`
   es *imposible*, porque el checkout principal ya tiene esa rama tomada y git se niega a tener la misma
   rama dos veces. Redactada como *"hacer checkout de `develop` primero"*, esta precondición se bloqueaba
   a sí misma justo donde más falta hace (medido 2026-08-18, corrida de TASK-029 en
   `f5sign-backend-develop`).
4. **El stack está arriba, y se comprueba desde `../f5sign-infra`, nunca con `docker compose` desde este
   repo** (regla 5 del repo: Symfony Flex genera `compose.yaml` que está deshabilitado y gitignorado).
   Comprobación: `make -C ../f5sign-infra worker-status` responde, o `docker ps` muestra `f5sign-php-fpm`.
   Si no → parar con *"entorno no disponible: `make -C ../f5sign-infra up`"*.
5. ⚑ **Comprobar qué checkout monta el stack antes de prometer que las validaciones valen.**
   `f5sign-infra/docker-compose.override.yml` monta `../f5sign-backend`. Si estás trabajando en un
   **worktree enlazado** (p. ej. `f5sign-backend-develop`), `make test` y `make phpstan` validan el otro
   árbol y su verde no dice nada de tu código. Rutas válidas en ese caso, en orden de preferencia:
   - **① `make -C ../f5sign-infra wt-backend src=$(pwd)`** — lane efímero por worktree, y **la única ruta
     que aísla de verdad**. ⚠ **Reconstruido 2026-08-18 por la sesión de `f5sign-infra`; esta entrada decía
     *"hoy levanta solo postgres"* y las tres consecuencias que sacaba de ahí ya no valen.** El lane levanta
     **su propio juego de todo servicio con estado que los tests mutan** — hoy `postgres-test`, `minio` +
     `minio-init` (los 5 buckets, con Object Lock), `rabbitmq` y `mailpit`, más su `php-fpm-wt`. El criterio
     es *por lane si un test puede escribir en él*, así que enumera `docker-compose.wt.backend.yml` en vez de
     fiarte de esta lista. **Los tests de storage y los de broker pasan ahí.**
     - `eu-dss` es el **único compartido**, y por lo que es, no por lo que cuesta: petición/respuesta pura, y
       su único estado es la caché de Trusted Lists, de solo lectura. Se alcanza por un proxy `socat` que es
       el **único** contenedor en las dos redes — si el contenedor de php estuviera en ambas, los nombres
       `minio`/`rabbitmq`/`mailpit` resolverían **ambiguamente** (el DNS de Docker une las entradas de todas
       las redes a las que estás conectado) y un lane podría acabar escribiendo en el MinIO del stack
       compartido.
     - `scripts/wt-validate.sh` hace **preflight** de que ese `eu-dss` compartido está vivo y **aborta con el
       motivo escrito** si no (escape hatch `WT_REQUIRE_DSS=0`, que corre igual y deja esos tests en rojo a
       sabiendas). Lo que obliga al preflight es la corrección anterior de esta entrada, que **sigue intacta**:
       ⚠ **Corregido 2026-08-18 por la sesión de `f5sign-infra`, y esta línea decía "se saltan"**: grep sobre
       `tests/` da **cero** llamadas a `markTestSkipped` — las dos apariciones que quedan son prosa
       afirmando justamente esta regla. No hay mecanismo en la suite que salte nada. La distinción importa
       porque "se salta" y "falla" llevan a diagnósticos distintos, y además la lista de hosts era corta:
       `.env.test` resuelve **cinco** (`postgres-test`, `minio`, `rabbitmq`, `mailpit`, `eu-dss`), no tres.
       De esos cinco, el lane sirve cuatro **por lane** y proxya el quinto.
       ⚠ **Corregido 2026-08-20: esta línea decía además que `phpunit.dist.xml` "no filtra ningún grupo" y
       que su único `<exclude>` era de *cobertura*.** TASK-030 añadió
       `<groups><exclude><group>sandbox</group>`, el único grupo excluido — y lo añadió **por esta misma
       regla**: esa tier llama a `api.twilio.com` de verdad y, como el repo no salta, un host que no
       resuelve la pondría roja en cualquier `composer test` offline. Los demás grupos (`eIDAS-*`, `bl38`)
       son **selectores** para un humano, no exclusiones: corren todos por defecto.
       ⛔ Añadir un nombre a ese `<exclude>` hace que el gate reporte sobre menos código **sin decirlo**;
       es la edición de este repo que más se parece a fabricar un verde.
     - **Memoria: el lane monta `./docker/php/php.ini`, o sea 512M**, y encima `zz-wt-infection.ini`, que lo
       sube a 1536M — existe porque el gate `infection` relanza `phpunit` como proceso hijo y un `php -d` no
       se hereda. ⚠ Ese 1536M es **un punto de partida, no una medición**: nadie ha medido el pico real de
       Infection en esta suite, y el propio fichero lo dice. Si muere por memoria, súbelo ahí **y** en
       `WT_PHP_MEM`. La trampa de los 128M ([BL-135](../../../docs/BACKLOG.md)) es del contenedor **a mano**
       de ② , no del lane.
     - **`COMPOSER_PROCESS_TIMEOUT=1800`**: la observación anterior de *"muere en el process timeout de 300 s
       de Composer"* está **arreglada**, y su diagnóstico era correcto — no era la duración de la suite. Y ya
       no empaqueta los pasos en un proceso: son **`docker compose run` separados** —`composer install`,
       migraciones como superuser, y después **uno por gate** como el rol de app—, así que un fallo dice
       **qué paso** murió en vez de tumbar la corrida sin nombre.
     - **Gates: el lane corre cuatro por defecto, no solo la suite.** `WT_GATES` los elige y su default es
       `lint arch phpstan test`; `infection` es **opt-in** (`WT_GATES="lint arch phpstan test infection"`)
       porque tarda órdenes de magnitud más y haría el lane inservible para iterar, y `WT_GATES="test"`
       reproduce el comportamiento antiguo.
       ⚑ El gate `phpstan` del lane hace `cache:warmup --env=dev` y **comprueba que el dump del contenedor
       existe antes de analizar**: en un lane `var/` es un volumen propio y nace vacío, y un PHPStan sin ese
       dump reporta servicios **sin registrar que sí lo están** — que se lee exactamente como un defecto de
       tu rama. Ojo al modo de fallo, que es el contrario al del árbol principal: allí el dump está
       *rancio*, aquí *no está*.
       ⚠ **Corregido 2026-08-18, y esta entrada decía que el lane corría "`composer test` y nada más" y que
       las estáticas no tenían ruta worktree-aware.** Era cierto a las 16:11, cuando se escribió;
       `f5sign-infra` metió los cuatro gates a las 18:18 del mismo día. La moraleja no es el dato sino el
       desfase: esta skill va por detrás del lane, así que enumera `scripts/wt-validate.sh` antes de fiarte
       de esta lista.
     - **Dos costes reales:** el teardown es `down -v`, que se lleva el volumen de vendor del lane, así que
       **cada corrida rehace `composer install`**; y `flock` limita el backend a **un lane a la vez**. Medido
       2026-08-18: la corrida entera (install + migraciones + suite) tarda unos minutos, de los cuales la
       suite son **1:46**. ⚠ Esa cifra es de **la suite sola**: con el default de `WT_GATES` corren además
       `lint`, `arch` y `phpstan`, así que no la cites como el coste del lane completo.
   - ⛔ **Una *base de datos* aparte dentro del clúster compartido NO es aislamiento — y es justo el apaño
     que uno se monta al llegar aquí.** `EventRelay` filtra por
     `sys_transaction_id < pg_snapshot_xmin(pg_current_snapshot())`, y **`pg_snapshot_xmin` es de CLÚSTER**:
     una transacción abierta en *cualquier* base del clúster —incluida `postgres`, que no contiene ninguna
     tabla nuestra— para el relay, **y el relay reporta éxito sin drenar nada**
     ([BL-138](../../../docs/BACKLOG.md), que probó el mecanismo con un A/B/C controlado). **La regla es un
     clúster por sesión, no una base por sesión**: lo que comparte clúster está expuesto por muchas bases en
     que lo partas. El lane aísla porque levanta **su propio** contenedor `postgres-test`.
     ⚑ **Confirmado 2026-08-18** sobre el mismo árbol, el mismo commit y sin una sola edición, **n=1 por
     brazo** — confirmación consistente con BL-138, **no** prueba independiente del mecanismo:

     | Brazo | Clúster | Resultado |
     |---|---|---|
     | contenedor puntual, base aislada `f5sign_test_wt` | **compartido** | 1681 tests, 7177 asserts, **5 fallos** |
     | `make -C ../f5sign-infra wt-backend src=$(pwd)` | **propio** | 1681 tests, 7210 asserts, **OK** |

     Mismo número de tests en los dos brazos, así que no se saltó ni se filtró nada: el delta es puro
     pass/fail. Los cinco rojos caían todos en relay / event-log (`EventLogBrokerRoundTripTest`,
     `EventRelayTest`, `ReplayEventLogEventCommandTest`) y dos llevaban las firmas documentadas de BL-138 al
     pie de la letra (`0 is identical to 2`, `-1 is identical to 1`).
   - **② Contenedor puntual sobre la red del stack — degradado 2026-08-18 a segunda opción.** Esta entrada lo
     presentaba como *"la vía que sí completa la suite"* (medido entonces: 1489 tests en ~74 s); es la ruta
     que produjo los cinco rojos falsos de arriba, porque comparte el clúster de `postgres-test` con las
     demás sesiones. **No se borra, se degrada** — sigue siendo la ruta correcta para: (a) corridas acotadas
     mientras iteras (`--filter`, un solo fichero de PHPStan), porque el lane corre siempre el gate entero y
     rehace `composer install` en cada arranque; y (b) fallback si el lane no está disponible — sin stack
     compartido no hay `eu-dss` que proxyar, y `flock` sólo da **un** lane de backend a la vez.
     ⚠ **Corregido 2026-08-18: aquí decía que las estáticas *"no tienen ninguna otra ruta desde un
     worktree"*, y el lane ya las corre** (`WT_GATES`, arriba).
     ⛔ Lo que ya no vale es correr la **suite entera** por aquí y declarar el resultado como validación de
     tu rama.
     ⚠ **Migra primero contra `postgres-test`**, que es tmpfs y arranca vacío — sin ese paso los
     tests de DB fallan con `could not translate host name` o tabla inexistente, y parece un fallo de código:
     ⛔ **Esta imagen arranca con `memory_limit=128M`; el contenedor `php-fpm` que usan los targets del
     Makefile arranca con 512M** (medido 2026-08-18: `docker exec f5sign-php-fpm php -r 'echo
     ini_get("memory_limit");'` → 512M, contra 128M aquí). O sea que esta ruta te da **un cuarto de la
     memoria** que la documentada, y nada te lo advierte. **Pon `php -d memory_limit=-1` en TODO comando
     PHP que metas por aquí**, no solo en los dos de abajo — `composer infection` murió por esto y el
     diagnóstico apuntaba a la herramienta, no al contenedor ([BL-135](../../../docs/BACKLOG.md)).
     ⚑ `mkdir` y demás comandos de shell no lo necesitan: no son procesos PHP. La regla es *PHP sí, shell no*.
     ⚠ Y ojo, `-d` **no se hereda por los hijos**: `infection` lanza su propio `phpunit`, que vuelve a 128M.
     Para esos casos hace falta un `php.ini` montado, no la bandera. ⚑ Esto es de **esta** ruta: en el lane
     de ① no pasa, porque monta el `php.ini` de 512M.
     ```
     docker run --rm --network f5sign-net -v $(pwd):/var/www/html -w /var/www/html \
       -e DATABASE_URL='postgresql://f5sign:f5sign_test_pw@postgres-test:5432/f5sign_test?serverVersion=16&charset=utf8' \
       f5sign/backend:dev sh -c 'php -d memory_limit=-1 bin/console doctrine:migrations:migrate --env=test --no-interaction --allow-no-migration'
     docker run --rm --network f5sign-net -v $(pwd):/var/www/html -w /var/www/html \
       f5sign/backend:dev sh -c 'php -d memory_limit=-1 bin/phpunit --no-progress'
     ```
     Las estáticas no necesitan ni `--network` ni migraciones:
     ```
     docker run --rm -v $(pwd):/var/www/html -w /var/www/html \
       f5sign/backend:dev sh -c 'php -d memory_limit=-1 "$(command -v composer)" arch'
     ```
   Elegir una y **declararla en el report**; una validación cuya diana no era tu árbol es peor que
   ninguna, porque se lee como verde.

## Flujo de ejecución

### Fase 0 — Preparación

1. **Resolver el `.md`**: si vino un id, `docs/tasks/TASK-NNN-*.md` con Glob. Si vino ruta, usarla.
2. **Leer la tabla de cabecera** (formato en el README §2): `Status`, `Type`, `Why`, `Builds on`,
   `Scope`, `Decision record`, `Delivery bar`, `Sibling`. **No hay `Complejidad`, `Tags`, `Story Points`
   ni `Depende de`** — ese era el formato del `Planning/` del repo de docs, que es legado (README §1).
   - Si falta `Status` o `Type` → parar. **`Why` solo es obligatorio en tasks aún no implementadas**
     (ver `spec-lint` Paso 2): medido 2026-08-17, 15 de los 21 registros existentes no lo llevan, y exigirlo
     en bloque haría que este orquestador se negara a arrancar en la mayoría del corpus.
   - Los encabezados de sección **no** están en posiciones fijas: localiza alcance y verificación por
     intención, no por `§N` (§3 es *Scope* en 13 de 21; §5 es *Verification* en 7).
   - Si hay `Sibling` marcado con ⚑ → **leerlo antes de empezar**: dice explícitamente que la task no se
     puede planificar de forma independiente.
3. **Verificar `Builds on`**: para cada task citada, leer su `Status`. Si alguna sigue `Not started` y la
   nuestra la reusa *unchanged* → parar con *"`Builds on` TASK-X en estado Y"*. Una task en
   `docs/two-gate-signer-auth` u otra rama no está disponible: si `Builds on` la cita, parar y decirlo.
4. **Crear workspace**: `var/task-runner/TASK-NNN/` (`/var/` está gitignorado; nada de esto se commitea).
   Si existe y no se pasó `--resume` → preguntar reanudar o reiniciar.
   ⚠ **`var/` puede ser de root y no dejarte escribir.** Las herramientas corren en contenedores como
   root, así que `var/` y `var/cache/` suelen quedar con ese dueño (comprobado 2026-08-17: `mkdir` desde
   el host da *Permission denied*). Si pasa: crear el directorio dentro del contenedor
   (`docker run --rm -v $(pwd):/var/www/html -w /var/www/html f5sign/backend:dev mkdir -p var/task-runner/TASK-NNN`)
   o escribir los reports en el scratchpad de la sesión y **decir en el summary dónde quedaron**. Lo que
   no vale es perderlos en silencio.
5. **Rama**: la convención real de este repo es `<tipo>/<slug>` — `feat/notification-email-html`,
   `docs/task-conventions`, `chore/dockerfile-dev-target`. ⚠ **Ninguna rama en la historia del repo ha
   llevado el id de la task en el nombre**, así que no inventes `feat/TASK-NNN-…`: el id va en el cuerpo del
   PR y en el `Status` del `.md`. Kebab-case, ASCII, desde `develop` — con `git checkout -b <rama> develop`
   (precondición 3), no haciendo checkout de `develop` primero.
6. **Inicializar `run.log`** (JSON lines) con `{phase: "prepare", status: "pass", at: ISO8601}`.
7. ⚑ **Baseline verde, antes de tocar una sola línea.** Correr la suite completa **por el harness que
   declaraste en la precondición 5** y anotar el **número exacto de tests y de asserts**, en `run.log` y
   en el resumen final. Sin ese número no se pueden separar los rojos propios de los preexistentes, y una
   corrida se pone roja por motivos de entorno más a menudo de lo que parece (medido 2026-08-18, corrida
   de TASK-029: `1619 tests / 6704 assertions` verdes antes de la primera edición — y esa corrida sí se
   puso roja después por entorno; ese número fue lo único que permitió decirlo sin dudar).
   ⚠ **Un baseline rojo no aborta la task: se declara.** Lo que no vale es descubrirlo a mitad de la
   Fase 3 y atribuirlo al diff.
   Registrar en `run.log` como `{"phase":"baseline","status":"pass","tests":N,"assertions":M,"harness":"…"}`.

### Fase 1 — `spec-lint` [GATE]

```
Agent({
  subagent_type: "general-purpose",
  description: "spec-lint on TASK-NNN",
  prompt: "Execute the spec-lint skill defined at .claude/skills/spec-lint/SKILL.md on task {rutaMd}. Write the report to var/task-runner/TASK-NNN/spec-lint.report.md. Return the JSON summary as the last line of your response."
})
```

Si `status: "fail"` → supervised: mostrar report y preguntar (editar el `.md` y reintentar, o abortar);
auto: abortar.

### Fase 2 — `implement-backend` [GATE]

```
"Execute the implement-backend skill defined at .claude/skills/implement-backend/SKILL.md on task {rutaMd}.
Workspace: var/task-runner/TASK-NNN/.
Produce context-digest.md and plan.md. Return the JSON summary."
```

**Sin selección de modelo por `Complejidad`** — ese campo no existe en este formato. Hereda el modelo de
la sesión. Escalar a un modelo mayor solo tras fallo repetido *con diagnóstico que lo justifique*, nunca
de entrada.

Si falla con `"spec contradictorio"` o `"contexto insuficiente"` → **no escalar**: parar y pedir al usuario
ampliar el `.md` (normalmente su sección de *lo que ya existe* o la de *alcance*).

⛔ **Si devuelve `"awaiting-adr-acceptance"`, el turno es del usuario y de nadie más.** La skill ha
encontrado una decisión transversal (contradice un ADR aceptado, abre una dependencia cross-BC, toca
Kernel/Foundation, o edita `deptrac.yaml` / `phpstan.dist.neon` / el baseline) y ha dejado el ADR redactado
como `Proposed`. Presentar el ADR al usuario —qué decide, qué descarta, qué prohíbe— y **parar ahí**, en los
dos modos, `--auto` incluido. Prohibido: aceptarlo en su nombre, marcarlo `Accepted`, reintentar la Fase 2
"a ver si pasa", o recortar el cambio para que la decisión deje de hacer falta. Un `--auto` que acepta
decisiones de arquitectura solo no es no supervisado: es sin supervisión.

`changes.diff`: `git diff $(git merge-base HEAD develop)..HEAD > var/task-runner/TASK-NNN/changes.diff`.

### Fase 3 — Validaciones condicionales

⚑ **La condición es lo que la task TOCA, no una lista de tags.** El formato de este repo no tiene `Tags`,
y una enumeración de tags sería además el patrón que la regla 5 de autoría prohíbe: el conjunto que exime
es "todo lo que aún no está en la lista". Derivar del `changes.diff`:

| Skill | Se invoca si el diff toca |
|---|---|
| `doctrine-guard` | `migrations/`, `src/**/Infrastructure/Persistence/`, o SQL/RLS en cualquier fichero |
| `contract-check-backend` | `src/**/UI/Http/`, `config/routes/`, cualquier `#[OA\`, o un `Contract/Event/` |
| `task-validate-backend` | **siempre** |

⚑ **Si el diff añade un event listener, un middleware o un servicio etiquetado, comprobar que está
registrado de verdad** — no que la clase existe. Un comando por superficie:
`make -C ../f5sign-infra sf cmd="debug:event-dispatcher kernel.controller"` (o el evento que toque),
`debug:container --tag=<tag>`, `debug:messenger`. Un listener sin cablear es un **no-op silencioso**: no
hay error, no hay excepción, y la suite puede seguir verde porque los tests unitarios de controlador
suelen fijar los atributos de la request a mano y **saltarse el listener** — así que su verde no dice
nada de que el listener corra. Ningún gate de este stack lo cubre. Cuesta un comando (comprobado
2026-08-18 en TASK-029: los dos listeners nuevos salían registrados y disparando).

En paralelo (varias llamadas Agent en un solo mensaje). Prerequisito de `contract-check-backend` si hay
endpoints: `make -C ../f5sign-infra sf cmd="nelmio:apidoc:dump --format=json"` → guardar en el workspace.

⛔ **Cada Agent en paralelo recibe una lista explícita de rutas que puede tocar, y la orden de reportar
—no editar— cualquier cosa que encuentre fuera de ella.** Varios agentes escriben a la vez sobre **el
mismo árbol de trabajo**; sin esa lista no hay forma de saber de quién es cada delta.

- **Lo que pasó** (2026-08-18, TASK-029): un `git add -A` del orquestador se llevó por delante las
  ediciones **en vuelo** de un agente de validación. El agente reportó después que sus entregables
  "estaban en HEAD aunque él nunca commiteó", y que HEAD **no** estaba verde sin el delta que todavía
  tenía en el árbol. Ninguna de las dos cosas se ve desde el diff.
- **Con agentes vivos, `git add -A` es siempre incorrecto**: commitea trabajo ajeno a medias. Añadir
  rutas explícitas, o commitear cuando no quede ningún agente corriendo.
- **Sabotear un fichero ajeno es legítimo, y hay que pedirlo bien.** Dos agentes necesitaron sabotear
  ficheros del orquestador para ver una guarda fallar por su propio motivo; salió bien **solo** porque
  el brief les exigía restaurar de inmediato y demostrarlo con un `git diff` vacío. Esa exigencia va en
  el brief, no en la buena voluntad del agente.
- ⚑ **La lista no es solo defensiva.** *"Reporta lo que veas fuera de tu lista"* fue lo que produjo el
  hallazgo más valioso de esa corrida: un mecanismo decidido en un ADR y **nunca construido**, que
  ningún test podía cazar porque ninguna barra de aceptación lo nombraba.

Después, secuencial: `security-audit-core` [GATE] — **siempre**. Delega en `security-audit-backend`, y en
`eidas-compliance` si el diff toca firma/crypto (`src/F5Sign/SignatureExecution/`, `Foundation/Crypto/`,
DSS, PAdES).

Si un gate duro falla → supervised: mostrar report y preguntar (reintentar Fase 2 con el report como
contexto, máx 2 iteraciones, o abortar); auto: abortar.

### Fase 4 — Validaciones no-gate

`perf-smoke-backend`: ⚠ **hoy no es ejecutable y se salta declarándolo.** Depende de `composer perf:seed`,
que no existe en `composer.json` (los scripts son `test`, `coverage*`, `phpstan`, `arch`, `lint`, `format`,
`infection`, `qa`). Registrar en `run.log` como `{"phase":"perf-smoke","status":"skipped","reason":"no
perf:seed script"}` — un skip declarado, no un verde.

### Fase 5 — `docs-sync`

Se invoca si el diff toca ADRs, `config/`, `.env*`, un `Contract/Event/`, o añade un módulo. Los cambios
se añaden como **commit propio**, no amendeados (ver Fase 8).

No es gate duro: si falla, warn y seguir.

### Fase 6 — `task-close`

Siempre. Edita el `.md`: `Status` → lo que sea cierto **nombrando rama o commit** (README §3), y añade la
sección de desviaciones **al final**, sin renumerar (las secciones son anclas `§N` citadas desde otros
documentos).

⚑ **Su trabajo real es que nada de lo aprendido se quede en `var/`.** Cada deferral va a
`§Open follow-ups` de la task **más** su fila en `docs/BACKLOG.md`; cada decisión transversal, a su ADR. Un
aprendizaje escrito solo en el workspace es un aprendizaje perdido — este repo ya tuvo que reconstruir a
mano *"eight deferrals that lived only in an untracked memo"*.

⚑ **Si la task descargó un deferral de un ADR, el `Status`/`Enforced by`/`Realized in` de ese ADR van en
este changeset**, no en una limpieza posterior (`CLAUDE.md` regla de autoría 7).

### Fase 7 — Confirmación (solo supervised)

Resumen de fases, ficheros cambiados, tests añadidos, criterios de §5 cubiertos, warnings activos, y **qué
harness ejecutó la validación** (precondición 5). Preguntar: ¿abrir PR?

### Fase 8 — `pr-ready`

⛔ **Hoy no se puede completar en esta máquina: `gh` no está instalado**, ni en el host ni en la imagen
`f5sign/backend:dev`, y el Makefile de infra no tiene target para él. `pr-ready` falla cerrado en su
precondición en vez de romper, pero el PR hay que abrirlo a mano. Decirlo en el resumen en vez de reportar
un fallo de la skill.

Solo si el usuario confirma (o `--auto`). **Sin política de commit único:** este repo integra PRs de varios
commits y merges de `develop`; un `--amend` sobre un commit ya pusheado obliga a `--force-with-lease` sin
ganar nada. `pr-ready` hace push, `gh pr create` contra **`develop`**, y actualiza el `.md` con la URL en un
commit de seguimiento.

## Contrato con skills hijas

Cada skill hija recibe `taskDir` (`var/task-runner/TASK-NNN/`) y `taskMdPath`, escribe su `*.report.md` en
ruta predecible, y devuelve como último mensaje `{ status, summary, issues?, metrics? }`.

## run.log

Una línea JSON por fase: `{"phase":"implement","status":"pass","attempts":1,"at":"2026-08-17T10:15:00Z"}`.

## Manejo de fallos

- **status=fail**: según gate (duro → parar/reintentar; no gate → warn y seguir).
- **Agent falla** (red, timeout): reintentar una vez; si vuelve a fallar, reportar.
- **Git falla**: nunca `--force` ni `reset --hard`; parar y pedir intervención.
- ⚑ **Un merge que toque `.claude/` o `CLAUDE.md` puede abortar**: esos paths son symlinks al store con
  `skip-worktree`. Salida: `bin/unlink-ai.sh` → merge → `bin/sync-ai.sh` en la raíz del workspace.
- **Ctrl+C**: el workspace queda como está; `--resume`.

## Qué NO hace

- No edita código.
- No interpreta reports de otras skills (solo su JSON).
- No crea tasks. Para eso, escribir el `.md` a mano siguiendo `docs/tasks/README.md` — incluido acuñar el
  id con el sweep de su §4, que hay que correr **en el momento**, sobre todas las ramas.
- No mergea PRs.
