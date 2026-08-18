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
   es la rama de publicación. Si no estás en `develop`, hacer checkout antes de crear la rama de la task.
4. **El stack está arriba, y se comprueba desde `../f5sign-infra`, nunca con `docker compose` desde este
   repo** (regla 5 del repo: Symfony Flex genera `compose.yaml` que está deshabilitado y gitignorado).
   Comprobación: `make -C ../f5sign-infra worker-status` responde, o `docker ps` muestra `f5sign-php-fpm`.
   Si no → parar con *"entorno no disponible: `make -C ../f5sign-infra up`"*.
5. ⚑ **Comprobar qué checkout monta el stack antes de prometer que las validaciones valen.**
   `f5sign-infra/docker-compose.override.yml` monta `../f5sign-backend`. Si estás trabajando en un
   **worktree enlazado** (p. ej. `f5sign-backend-develop`), `make test` y `make phpstan` validan el otro
   árbol y su verde no dice nada de tu código. Rutas válidas en ese caso, en orden de preferencia:
   - `make -C ../f5sign-infra wt-backend src=$(pwd)` — lane efímero por worktree. ⚠ Hoy levanta **solo
     postgres** (`docker-compose.wt.backend.yml` declara `postgres-test` + `php-fpm-wt` y nada más): los
     tests de storage **fallan** (`Could not resolve host: minio`) y los de broker se saltan. Observado
     además que la corrida muere en el *process timeout* de 300 s de Composer — pero **la causa no es la
     duración de la suite**: medida aparte tarda ~74 s y los fallos de storage caen en ~28 s. El lane mete
     `composer install` + migraciones + suite en el mismo proceso, que es la explicación probable. Si lo usas
     y muere, no lo leas como "los tests son lentos".
   - Contenedor puntual sobre la red del stack, que es la vía que sí completa la suite (medido: 1489 tests
     en ~74 s). ⚠ **Migra primero contra `postgres-test`**, que es tmpfs y arranca vacío — sin ese paso los
     tests de DB fallan con `could not translate host name` o tabla inexistente, y parece un fallo de código:
     ⛔ **Esta imagen arranca con `memory_limit=128M`; el contenedor `php-fpm` que usan los targets del
     Makefile arranca con 512M** (medido 2026-08-18: `docker exec f5sign-php-fpm php -r 'echo
     ini_get("memory_limit");'` → 512M, contra 128M aquí). O sea que esta ruta te da **un cuarto de la
     memoria** que la documentada, y nada te lo advierte. **Pon `php -d memory_limit=-1` en TODO comando
     PHP que metas por aquí**, no solo en los dos de abajo — `composer infection` murió por esto y el
     diagnóstico apuntaba a la herramienta, no al contenedor ([BL-135](../../../docs/BACKLOG.md)).
     ⚑ `mkdir` y demás comandos de shell no lo necesitan: no son procesos PHP. La regla es *PHP sí, shell no*.
     ⚠ Y ojo, `-d` **no se hereda por los hijos**: `infection` lanza su propio `phpunit`, que vuelve a 128M.
     Para esos casos hace falta un `php.ini` montado, no la bandera.
     ```
     docker run --rm --network f5sign-net -v $(pwd):/var/www/html -w /var/www/html \
       -e DATABASE_URL='postgresql://f5sign:f5sign_test_pw@postgres-test:5432/f5sign_test?serverVersion=16&charset=utf8' \
       f5sign/backend:dev sh -c 'php -d memory_limit=-1 bin/console doctrine:migrations:migrate --env=test --no-interaction --allow-no-migration'
     docker run --rm --network f5sign-net -v $(pwd):/var/www/html -w /var/www/html \
       f5sign/backend:dev sh -c 'php -d memory_limit=-1 bin/phpunit --no-progress'
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
   PR y en el `Status` del `.md`. Kebab-case, ASCII, desde `develop`.
6. **Inicializar `run.log`** (JSON lines) con `{phase: "prepare", status: "pass", at: ISO8601}`.

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

En paralelo (varias llamadas Agent en un solo mensaje). Prerequisito de `contract-check-backend` si hay
endpoints: `make -C ../f5sign-infra sf cmd="nelmio:apidoc:dump --format=json"` → guardar en el workspace.

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
