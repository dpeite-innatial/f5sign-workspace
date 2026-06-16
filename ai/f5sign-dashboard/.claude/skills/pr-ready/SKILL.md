---
name: pr-ready
description: Cierra la tarea creando el Pull Request final en GitHub. Consolida el commit (amend con .md actualizado), hace push de la rama, genera título (conventional commits) y body del PR (tarea + AC cubiertos + tabla de validaciones + test plan), aplica labels derivados del .md (fase, epic, tipo, tags), y marca el PR como draft si hubo warnings activos. Úsalo con /pr-ready T{id}. Activar con "crear PR", "abrir pull request", "cerrar tarea y publicar", "pr ready".
---

# PR Ready

Cierre final. Solo se invoca si los gates previos pasaron (o el usuario forzó continuar en supervised).

## Invocación

```
/pr-ready T{id}
/pr-ready T{id} --draft         # forzar draft (override)
/pr-ready T{id} --ready         # forzar ready (override — cuidado)
```

## Inputs

- `var/task-runner/T{id}/` (todos los artefactos y reports)
- `.md` de la tarea (ya editado por task-close)
- `plan.md`, `context-digest.md`
- Reports: spec-lint, doctrine-guard, contract-check, task-validate, security-audit, eidas (si aplica), perf-smoke, docs-sync

## Outputs

- Commit final amendado en la rama
- Rama pusheada a `origin`
- PR creado en GitHub
- `.md` editado una vez más con URL del PR (2º amend)
- `var/task-runner/T{id}/pr-ready.report.md`
- JSON:
  ```json
  {"status":"pass|fail","summary":"...","prUrl":"...","prNumber":N,"branchName":"..."}
  ```

## Ejecución

### Paso 1 — Pre-check

- [ ] `git status --short` → no hay ficheros sin stagear inesperados. Ficheros esperables: el `.md` de la tarea, ficheros de `docs/`, `.env.example`.
- [ ] `git rev-parse --abbrev-ref HEAD` devuelve `feat/T{id}-*`
- [ ] `git log --oneline {base}..HEAD | wc -l` devuelve exactamente 1 (un solo commit sobre base)
  - Si más de 1: squash defensivo antes de continuar: `git reset --soft {base} && git commit` con el mensaje original de implement.
- [ ] `gh auth status` no falla (si falla → `status: fail, summary: "gh not authenticated, run gh auth login"`)

### Paso 2 — Amend con `.md` actualizado

Ficheros a incluir en el amend:
- `.md` de la tarea (si task-close lo dejó en staging, ya está; si no, `git add`)
- Cualquier fichero de `docs/` tocado por docs-sync que no haya sido amendado ya
- `.env.example` si fue modificado

```bash
git add {rutaMd} {otros ficheros de docs/, .env.example si aplica}
git commit --amend --no-edit
```

### Paso 3 — Determinar modo (draft vs ready)

Leer todos los reports del workspace. Contar WARNs activos (no resueltos):
- Sí, hay WARNs → `--draft`
- No hay WARNs → ready (no pasar `--draft`)
- Override explícito: respetar `--draft` o `--ready` del argumento

Ejemplos que implican WARN activo:
- perf-smoke con `status: warn` alto
- security-audit con WARN
- docs-sync con tag mismatches (estos realmente ya se limpiaron en task-close; si quedaron → es un bug)
- Cualquier gate con `status: warn`

### Paso 4 — Push

```bash
git push -u origin feat/T{id}-{slug}
```

Si la rama ya existía en remote → `git push --force-with-lease` (NUNCA `--force` sin lease).

Si el push falla con conflicto/protection rule:
- `status: fail, summary: "push rechazado: {razón}"`
- Detallar en el report
- NO hacer `--force` real ni rebase automático

### Paso 5 — Generar título del PR

Formato: `{tipo}(T{id}): {título de la tarea}`

Mapeo `Tipo` → conventional commit:
- `Backend` → `feat` (o `fix` si el título o descripción indica "fix"/"bug")
- `Frontend` → `feat` (o `fix`)
- `Integracion` → `feat`
- `Infraestructura` → `chore`
- `Diseno` → `design` (o `docs` si el repo no acepta `design`)

Extraer título de la primera línea del `.md` (tras `# `). Máximo 70 chars; truncar título si hace falta.

### Paso 6 — Generar body del PR

Plantilla:

```markdown
## Tarea
[T{id}]({ruta-relativa-al-.md}) — {título de la tarea}

Epic: EP{xx} | Story: S{xx}.{y} | Fase: F{n}

## Resumen
{2-3 líneas extraídas de context-digest.md § "Task summary"}

## Cambios
{lista generada parseando changes.diff, agrupada por capa}:
- **Domain:** {ficheros bajo Domain/}
- **Application:** {ficheros bajo Application/}
- **Infrastructure:** {ficheros bajo Infrastructure/}
- **Tests:** {ficheros bajo tests/}
- **Docs:** {ficheros bajo docs/, .env.example}

## Criterios de aceptación cubiertos
{extraído de task-validate.report acCovered[]}:
- [x] AC-01 — {nombre del criterio extraído de la story}
- [x] AC-02 — ...

## Validaciones ejecutadas
| Skill | Status | Notas |
|---|---|---|
| spec-lint | PASS | — |
| doctrine-guard | PASS | — |
| contract-check | PASS | — |
| task-validate | PASS | N tests, coverage X% |
| security-audit | PASS | — |
| eidas-compliance | PASS | Nivel PAdES B-LT |
| perf-smoke | WARN | p95 = 312ms (ver notas) |

## Notas para el reviewer
{si hay WARNs o deuda técnica de task-close, listarlos aquí}
- Performance: p95 en el límite del budget; se deja para iteración futura
- ADR en borrador: `docs/adr/0012-*.md` (marcar como accepted al aprobar)

## Test plan
- [ ] Revisar cobertura de AC
- [ ] {si tag api:} curl al endpoint con cada caso del AC
- [ ] {si tag worker:} encolar mensaje y verificar procesamiento
- [ ] {si tag ui:} abrir página X y ejecutar flujo Y
- [ ] {si tag migration:} ejecutar migrate, verificar schema, migrate:down y verificar reversibilidad
```

### Paso 7 — Crear PR con gh

```bash
gh pr create \
  --base master \
  --head feat/T{id}-{slug} \
  --title "{título}" \
  --body-file {fichero temporal con el body} \
  [--draft]
```

Alternativa (body inline con HEREDOC):
```bash
gh pr create --base master --head feat/T{id}-{slug} \
  --title "..." \
  --body "$(cat <<'EOF'
...
EOF
)" [--draft]
```

Capturar la URL del PR que devuelve `gh` y el número (`gh pr view --json number`).

### Paso 8 — Labels

Derivar labels del `.md`:
- `fase:F{n}`, `epic:EP{xx}`
- `tipo:{backend|frontend|integracion|infraestructura|diseno}` (lowercase)
- Por cada tag canónico del `.md`: `tag:{tag}` (ej. `tag:signing`, `tag:critical-path`)

```bash
gh pr edit {prNumber} --add-label "fase:F0,epic:EP02,tipo:backend,tag:db,tag:migration"
```

Si algún label no existe en el repo, `gh` lo reporta; ignorar silenciosamente (no crear labels fantasma).

### Paso 9 — Amend final con URL del PR

Editar el `.md` de la tarea: actualizar el campo `PR/Branch` en la tabla Seguimiento de solo la rama → `{rama} — {URL del PR}`.

```bash
git add {rutaMd}
git commit --amend --no-edit
git push --force-with-lease
```

Resultado: un único commit final, con el `.md` totalmente actualizado (incluida la URL del PR que GitHub acaba de asignar).

### Paso 10 — Devolver JSON

```json
{"status":"pass","summary":"PR abierto","prUrl":"https://github.com/owner/innasign/pull/42","prNumber":42,"branchName":"feat/T02.1.1-slug","draft":false}
```

## Manejo de fallos

- **Push rechazado por branch protection:** `status: fail`, detallar en report, sugerir al usuario qué regla violó
- **`gh pr create` falla:** `status: fail`; si es por autenticación → `summary` sugiere `gh auth login`
- **Conflicto con main durante push** (alguien mergeó entretanto): `status: fail, summary: "rebase requerido, intervención manual"`. NO intentar rebase automático.
- **Rama ya tiene un PR abierto:** detectarlo con `gh pr list --head feat/T{id}-*`; si existe, hacer push y actualizar el PR existente en vez de crear uno nuevo; reportarlo en el summary.

## Qué NO hace

- No mergea el PR (responsabilidad del reviewer humano)
- No asigna reviewers (se configuran con CODEOWNERS, fuera de scope)
- No añade a milestones ni projects
- No ejecuta CI manualmente (GitHub lo dispara al abrir PR)
- No edita `.md` post-merge (SHA de main, fecha de merge) — sería otra skill futura o hook

## Referencias

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/common/04 - PR Ready.md`
