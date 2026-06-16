---
name: task-runner
description: Orquestador único del stack de skills de ejecución de tareas. Ejecuta una tarea del Planning/ end-to-end invocando skills especializadas (spec-lint, implement, task-validate, security-audit, etc.), gestionando gates, workspace en var/task-runner/T{id}/, rama git, commit único y PR final. Úsalo con /task-runner T{id} o /task-runner {ruta al .md}. Activar con frases como "ejecuta T02.1.1", "corre la tarea X", "task runner sobre...", "ejecuta la siguiente tarea del planning".
---

# Task Runner

Orquestador del stack. Ver diseño completo en `Implementación/Skills de Ejecución de Tareas/common/01 - Task Runner.md`.

## Invocación

```
/task-runner T{id}                    # ej: /task-runner T02.1.1
/task-runner {ruta absoluta al .md}
/task-runner T{id} --auto             # modo no supervisado (default: supervised)
/task-runner T{id} --resume           # reanudar workspace existente
```

Si no se pasa argumento, pedir al usuario el ID o ruta.

## Precondiciones

Antes de empezar, verificar (y parar con mensaje claro si falla):

1. El `.md` de la tarea existe y es legible
2. `git status` está limpio (no hay cambios sin commitear en la rama actual)
3. Estás en rama `master` (o la rama base del proyecto) — si no, checkout a base antes de crear rama nueva
4. Docker Compose está up: `docker compose ps` muestra los servicios esenciales (postgres, rabbitmq, redis) en estado `running`
   - Si no lo están → parar con "entorno no disponible: levantar con `docker compose up -d` antes de continuar"

## Flujo de ejecución

> **Rendimiento — principios (un run no debería tardar ~1h):**
>
> 1. **Validación pesada compartida, no repetida.** El orquestador corre la suite de validación del repo (lint + análisis estático/typecheck + unit + build, con los comandos del CLAUDE.md del repo) **una sola vez** tras `implement` (ver Fase 3.0) y vuelca los resultados al workspace; `task-validate` y `perf-smoke` **consumen esos artefactos** en lugar de recompilar/retestear. Ejecutar el mismo build/test 3-4 veces (implement + task-validate + perf-smoke) es el mayor desperdicio.
> 2. **Serializa lo pesado, paraleliza lo estático.** En repos con un único contenedor de app, dos builds simultáneos compiten por CPU/caché y dan flakiness → no paralelizar comandos de build/test. En cambio `security-audit` es análisis estático del diff y SÍ corre en paralelo con `task-validate`.
> 3. **`implement` da feedback rápido.** Durante su TDD corre solo unit + lint + typecheck (rápido); no el e2e + build completo al final — esa corrida autoritativa la hace `task-validate` una sola vez.
> 4. **Prompts de gate ajustados.** Cada skill hija recibe la ruta a `changes.diff` y la lista exacta de ficheros tocados; se le indica no re-explorar el repo entero ni re-ejecutar build/test si ya existen los artefactos compartidos del workspace.

### Fase 0 — Preparación

1. **Parsear argumento** → resolver ruta al `.md` de la tarea (si vino un ID, buscar `Planning/F*-*/EP*-*/S*-*/T{id}-*.md` con Glob)
2. **Leer frontmatter** del `.md`:
   - `Story Points`, `Tipo`, `Complejidad`, `Tags`, `Depende de`
   - Si falta alguno → informar al usuario y abortar (lo normal es que `spec-lint` lo detecte después, pero hay campos mínimos para decidir el flujo)
3. **Verificar dependencias**: para cada task listada en `Depende de`, leer su `.md` y comprobar Estado:
   - `completed` → OK.
   - `review` (implementada y commiteada, pero su PR sin mergear → su código vive en su rama, no en la base): en **supervised**, preguntar si **apilar (stacked branch)** — crear la rama de esta tarea DESDE la rama de la dependencia y calcular `changes.diff` contra el HEAD de esa rama (no contra `master`). En **auto**, abortar.
   - Cualquier otro estado → **abortar** con mensaje "dependencia T{X} en estado {Y}; completar primero".
4. **Crear workspace**: `var/task-runner/T{id}/`
   - Si ya existe y no se pasó `--resume` → preguntar: reanudar desde última fase `pass` o reiniciar desde cero
   - Si se reinicia → borrar el workspace y crear de nuevo
5. **Verificar rama git**:
   - Nombre: `feat/T{id}-{slug-del-título}` (slug kebab-case del título de la tarea, máx 40 chars, ASCII)
   - Si no existe → crear desde base y checkout
   - Si existe → checkout
6. **Si tag `critical-path`** (solo backend): ejecutar `composer perf:seed` — si falla, informar al usuario y preguntar si continuar (perf-smoke warnirá). En repos **frontend NO aplica** (no hay seed de DB; `perf-smoke` mide bundle/Lighthouse directamente) → saltar este paso.
7. **Inicializar `run.log`** (JSON lines, una línea por fase) con entrada `{phase: "prepare", status: "pass", at: ISO8601}`

### Fase 1 — `spec-lint` [Haiku, GATE]

Invocar skill via Agent tool:
```
Agent({
  subagent_type: "general-purpose",
  model: "haiku",
  description: "spec-lint on T{id}",
  prompt: "Execute the spec-lint skill defined at .claude/skills/spec-lint/SKILL.md on task {rutaMd}. Write the report to var/task-runner/T{id}/spec-lint.report.md. Return the JSON summary as the last line of your response."
})
```

Leer el último mensaje → extraer JSON. Si `status: "fail"`:
- Modo supervised: mostrar report al usuario, preguntar qué hacer (editar `.md` y reintentar, o abortar)
- Modo auto: abortar con exit code 1

### Fase 2 — `implement` [Opus si Complejidad=alta, Sonnet si media/baja, GATE]

Decidir modelo según `Complejidad` del frontmatter.

Invocar Agent con el modelo correspondiente y prompt:
```
"Execute the implement skill defined at .claude/skills/implement-{stack}/SKILL.md on task {rutaMd}   (implement-backend o implement-frontend según el repo).
Workspace: var/task-runner/T{id}/.
Model assigned: {haiku|sonnet|opus según Complejidad}.
Durante el TDD ejecuta en el contenedor solo unit + lint + typecheck (feedback rápido); NO corras el e2e + build completo al final — esa corrida autoritativa la hace task-validate una sola vez (ver Fase 3.0).
Commit changes as a single commit at the end. Produce context-digest.md, plan.md, and ensure changes.diff is generable.
Return the JSON summary."
```

Si falla con diagnóstico tipo `"spec contradictorio"` o `"contexto insuficiente"` → NO escalar, parar y pedir al usuario ampliar el `.md`.

Si falla por otro motivo (3 intentos del modelo asignado) y el diagnóstico justifica escalada → reinvocar Agent con `model: "opus"` y **contexto ampliado** (README story padre + README epic padre + `.md` de dependencias + catálogo de eventos + cross-cutting-concerns + diagnóstico nivel 1).

Si nivel 2 también falla → abortar con recomendación de enriquecer `Contexto requerido`.

Generar `changes.diff`: `git diff {base}..HEAD > var/task-runner/T{id}/changes.diff` donde `{base}` es el commit común con `master`.

### Fase 3 — Validaciones condicionales

#### Fase 3.0 — Validación pesada compartida (una sola vez)

Antes de invocar los gates, el orquestador corre la suite pesada del repo **una vez** y guarda los artefactos en el workspace para que las skills hijas los reutilicen (principio de rendimiento 1). Comandos según el CLAUDE.md del repo, **siempre en el contenedor, nunca en el host**:

- **Frontend** (f5sign-signer/dashboard): `make -C ../f5sign-infra test-signer` (lint + typecheck + unit con cobertura) → volcar a `var/task-runner/T{id}/docker-validate.log`; y el `build` en el contenedor de la app → deja `.output/` para `perf-smoke`.
- **Backend**: el equivalente `composer test` / `bin/console` dentro del contenedor PHP.

Si esta corrida ya falla en lint/typecheck/unit/build → es un fallo de gate duro: tratarlo como tal (parar/reintentar) sin gastar agentes en gates que dependen de un build sano.

#### Fase 3.1 — Gates en paralelo

Determinar qué skills invocar según tags del frontmatter e invocarlas **en paralelo** (múltiples Agent calls en un solo mensaje). A cada una se le pasa la ruta a `changes.diff`, los artefactos de la Fase 3.0 y la lista de ficheros tocados, con la instrucción de **no** recompilar/retestear lo ya cubierto ni re-explorar el repo entero:

- `task-validate` [Haiku] — **siempre**, GATE (skill stack-específica: `task-validate-backend` / `task-validate-frontend`). Consume `docker-validate.log` + `.output/` de la Fase 3.0 y solo añade lo que falte (p. ej. `e2e` mobile + lectura de cobertura/AC). No repite lint/typecheck/unit/build.
- `security-audit` [Sonnet] — **siempre**, GATE. Análisis estático del diff → corre en paralelo con `task-validate` (apenas toca Docker; ya no es secuencial).
  - Si tags incluye `signing`, `crypto` o `eidas`: dentro de security-audit se invocará `eidas-compliance` [Opus]
- `doctrine-guard` [Haiku] si tags incluye `db`, `migration`, `rls`, `tenancy` (backend)
- `contract-check` [Haiku] si tags incluye `api` o `event` (skill stack-específica: `contract-check-backend` / `contract-check-frontend`)
  - Pre-requisito backend: ejecutar `bin/console nelmio:apidoc:dump --format=json > var/task-runner/T{id}/openapi-snapshot.json` (si tag `api`)

Esperar a que terminen todas. Consolidar JSONs de retorno.

Si algún gate duro falla:
- Modo supervised: mostrar report, preguntar "reintentar implementación con el report como contexto" o "abortar"
- Si reintentar: volver a Fase 2 pasando el report como input adicional (máx 2 iteraciones de corrección)
- Modo auto: al 1er fallo de gate duro que no se puede auto-corregir, abortar

### Fase 4 — Validaciones no-gate

- `perf-smoke` [Sonnet] si tag `critical-path` — no bloquea (skill stack-específica: `perf-smoke-backend` / `perf-smoke-frontend`)
  - **Reutiliza el `.output/` (o artefacto de build) de la Fase 3.0** (analiza el bundle ya construido); NO vuelve a compilar. Por eso puede lanzarse dentro del mismo bloque paralelo de la Fase 3.1.
  - Si WARN alta: en supervised, preguntar si iterar

### Fase 5 — `docs-sync` [Haiku/Sonnet según actividad]

Invocar si tags incluye `adr`, `config`, `breaking`, `event`, `worker`, `new-module`.

Modelo: Sonnet si la actividad incluye redactar ADR; Haiku en cualquier otro caso.

Los cambios se amend-ean al commit existente: `git add <ficheros-tocados-por-docs-sync> && git commit --amend --no-edit`.

No es gate duro: si falla, warn y seguir.

### Fase 6 — `task-close` [Haiku]

Invocar siempre. Edita el `.md` de la tarea (Estado → review, Fin, Commit SHA, limpia tagMismatches consolidados, añade sección Desviaciones). Escribe `notes.md` solo si hay aprendizajes.

### Fase 7 — Confirmación (solo modo supervised)

Mostrar al usuario:
- Resumen de fases con status
- Ficheros cambiados
- Tests añadidos
- AC cubiertos
- Warnings activos

Preguntar: ¿abrir PR ahora?

### Fase 8 — `pr-ready` [Haiku]

Invocar solo si el usuario confirma (o modo auto).

> **El `.md` de la tarea vive en `f5sign-docs` (repo separado), NO en el repo de código.** El cierre de Seguimiento (Estado/Fin/Commit/PR) es un **commit aparte en `f5sign-docs`**, nunca un `amend` al branch de código (regla cross-repo: prohibido mezclar repos en un commit). Stagear solo el `.md` de esa tarea.

1. Push de la rama de código.
2. Crear el PR:
   - Si `gh` está disponible: `gh pr create` con título (conventional) y body (tarea + AC + tabla de validaciones + test plan); marcar **draft** si hay warnings activos.
   - Si `gh` **NO está instalado** (caso de este entorno): tras el push, devolver el enlace `…/pull/new/<rama>` para que el usuario abra el PR a mano (draft si hay warnings).
   - Si la rama está **apilada** (dependencia en `review`): avisar de poner la **base del PR** en la rama de la dependencia (no `master`) hasta que esta se mergee.
3. Actualizar el campo `PR/Branch` del `.md` (URL o enlace de creación + nota de stacking) y **commitear ese cambio en `f5sign-docs`** (junto con el cierre de Seguimiento, en su propio commit).
4. Devolver URL/enlace al usuario.

## Contrato con skills hijas

Cada skill hija:
- Recibe `taskDir` (var/task-runner/T{id}/) y `taskMdPath` como parte del prompt
- Lee lo que declara necesitar; no re-lee si ya existe en workspace
- Escribe su `*.report.md` en ruta predecible del workspace
- Devuelve JSON estructurado como último mensaje (parseable): `{ status, summary, issues?, tagMismatches?, metrics? }`

## run.log

Tras cada fase, append entrada JSON al `run.log`:
```json
{"phase": "implement", "status": "pass", "model": "sonnet", "attempts": 1, "tokens_estimated": 12500, "duration_s": 145, "at": "2026-04-13T10:15:00Z"}
```

## Manejo de fallos

- **Skill devuelve status=fail**: actuar según gate (duro → parar/reintentar; no gate → warn y seguir)
- **Agent tool falla** (error de red, timeout): reintentar una vez con el mismo modelo; si falla otra vez, reportar al usuario
- **Git falla** (conflicto, push rechazado): nunca usar `--force` ni `reset --hard`; parar y pedir intervención manual
- **Ctrl+C del usuario**: el workspace queda en el estado actual; se puede reanudar con `--resume`

## Qué NO hace

- No edita código
- No interpreta reports de otras skills (solo lee su JSON de retorno)
- No inventa tags, complejidad ni dependencias
- No crea tareas (eso es `/planning-scaffold`)
- No mergea PRs
- No edita las copias por-repo de las skills (`<repo>/.claude/skills/`): son **generadas**. La fuente es `f5sign-docs/skills-library/` y se propaga con `scripts/sync-skills.sh <stack> <repo>`. Editar la copia se pierde en el siguiente sync.

## Entorno (monorepo F5Sign)

- **Tests/lint/typecheck/build SIEMPRE en el contenedor, nunca en el host** (ver CLAUDE.md del repo). Frontend: `make -C ../f5sign-infra test-signer*`; los E2E corren en una imagen Playwright dedicada (el contenedor de la app es Alpine).
- **El `.md` de la tarea vive en `f5sign-docs`** (repo de specs), no en el repo de código → cerrar Seguimiento y actualizar `PR/Branch` son commits en `f5sign-docs`, separados del commit de código (regla cross-repo).
- **`gh` puede no estar instalado** en el host: `pr-ready` hace `push` y devuelve el enlace `…/pull/new/<rama>` para abrir el PR a mano; no asumir `gh pr create`.
- **Skills sincronizadas**: para cambiar una skill, editar `f5sign-docs/skills-library/{common,backend,frontend}/<skill>/SKILL.md` y re-sincronizar con `sync-skills.sh`. `task-runner` es **common** (presente en los 4 repos).

## Referencias

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/common/01 - Task Runner.md`
- Índice del stack: `Implementación/Skills de Ejecución de Tareas/README.md`
