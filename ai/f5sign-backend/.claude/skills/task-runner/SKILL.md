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

### Fase 0 — Preparación

1. **Parsear argumento** → resolver ruta al `.md` de la tarea (si vino un ID, buscar `Planning/F*-*/EP*-*/S*-*/T{id}-*.md` con Glob)
2. **Leer frontmatter** del `.md`:
   - `Story Points`, `Tipo`, `Complejidad`, `Tags`, `Depende de`
   - Si falta alguno → informar al usuario y abortar (lo normal es que `spec-lint` lo detecte después, pero hay campos mínimos para decidir el flujo)
3. **Verificar dependencias**: para cada task listada en `Depende de`, leer su `.md` y comprobar Estado = `completed`. Si alguna no lo está → **abortar** con mensaje "dependencia T{X} en estado {Y}; completar primero"
4. **Crear workspace**: `var/task-runner/T{id}/`
   - Si ya existe y no se pasó `--resume` → preguntar: reanudar desde última fase `pass` o reiniciar desde cero
   - Si se reinicia → borrar el workspace y crear de nuevo
5. **Verificar rama git**:
   - Nombre: `feat/T{id}-{slug-del-título}` (slug kebab-case del título de la tarea, máx 40 chars, ASCII)
   - Si no existe → crear desde base y checkout
   - Si existe → checkout
6. **Si tag `critical-path`**: ejecutar `composer perf:seed` — si falla, informar al usuario y preguntar si continuar (perf-smoke warnirá)
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
"Execute the implement skill defined at .claude/skills/implement/SKILL.md on task {rutaMd}.
Workspace: var/task-runner/T{id}/.
Model assigned: {haiku|sonnet|opus según Complejidad}.
Commit changes as a single commit at the end. Produce context-digest.md, plan.md, and ensure changes.diff is generable.
Return the JSON summary."
```

Si falla con diagnóstico tipo `"spec contradictorio"` o `"contexto insuficiente"` → NO escalar, parar y pedir al usuario ampliar el `.md`.

Si falla por otro motivo (3 intentos del modelo asignado) y el diagnóstico justifica escalada → reinvocar Agent con `model: "opus"` y **contexto ampliado** (README story padre + README epic padre + `.md` de dependencias + catálogo de eventos + cross-cutting-concerns + diagnóstico nivel 1).

Si nivel 2 también falla → abortar con recomendación de enriquecer `Contexto requerido`.

Generar `changes.diff`: `git diff {base}..HEAD > var/task-runner/T{id}/changes.diff` donde `{base}` es el commit común con `master`.

### Fase 3 — Validaciones condicionales

Determinar qué skills invocar según tags del frontmatter.

Invocar en **paralelo** (múltiples Agent calls en un solo mensaje) las que no se bloquean mutuamente:

- `doctrine-guard` [Haiku] si tags incluye `db`, `migration`, `rls`, `tenancy`
- `contract-check` [Haiku] si tags incluye `api` o `event`
  - Pre-requisito: ejecutar `bin/console nelmio:apidoc:dump --format=json > var/task-runner/T{id}/openapi-snapshot.json` (si tag `api`)
- `task-validate` [Haiku] — **siempre**

Esperar a que terminen todas. Consolidar JSONs de retorno.

Después (secuencial, puede consumir reports anteriores):
- `security-audit` [Sonnet] — **siempre**, GATE
  - Si tags incluye `signing`, `crypto` o `eidas`: dentro de security-audit se invocará `eidas-compliance` [Opus]

Si algún gate duro falla:
- Modo supervised: mostrar report, preguntar "reintentar implementación con el report como contexto" o "abortar"
- Si reintentar: volver a Fase 2 pasando el report como input adicional (máx 2 iteraciones de corrección)
- Modo auto: al 1er fallo de gate duro que no se puede auto-corregir, abortar

### Fase 4 — Validaciones no-gate

- `perf-smoke` [Sonnet] si tag `critical-path` — no bloquea
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

1. Amend final con `.md` actualizado
2. Push de la rama
3. `gh pr create` con título y body generados
4. Actualizar campo `PR/Branch` del `.md` con URL
5. Amend final + push `--force-with-lease`
6. Devolver URL al usuario

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

## Referencias

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/common/01 - Task Runner.md`
- Índice del stack: `Implementación/Skills de Ejecución de Tareas/README.md`
