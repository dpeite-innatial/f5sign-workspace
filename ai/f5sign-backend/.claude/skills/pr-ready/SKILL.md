---
name: pr-ready
description: 'Cierra la task abriendo el Pull Request contra develop. Hace push de la rama, genera título (conventional commits) y body del PR (task + propiedades verificadas + tabla de validaciones con el harness declarado + test plan derivado del diff), y lo marca draft si quedan warnings activos. Úsalo con /pr-ready TASK-NNN. Activar con "crear PR", "abrir pull request", "cerrar task y publicar", "pr ready".'
---

# PR Ready

Cierre final. Solo se invoca si los gates previos pasaron (o el usuario forzó continuar en supervised).

## Invocación

```
/pr-ready TASK-NNN
/pr-ready TASK-NNN --draft      # forzar draft
/pr-ready TASK-NNN --ready      # forzar ready (cuidado)
```

## Inputs

- `var/task-runner/TASK-NNN/` — artefactos y reports de las fases previas
- El `.md` de la task, ya editado por `task-close`

## Outputs

- Rama pusheada a `origin`, PR abierto contra **`develop`**
- Commit de seguimiento con la URL del PR en el `.md`
- `var/task-runner/TASK-NNN/pr-ready.report.md` — ⚠ `var/` puede ser de root y no dejarte escribir; en ese
  caso, scratchpad de la sesión y **decir dónde quedó** (`task-runner` Fase 0 lo documenta)
- JSON: `{"status":"pass|fail","summary":"...","prUrl":"...","prNumber":N,"branchName":"...","draft":bool}`

## Ejecución

### Paso 1 — Pre-check

- [ ] `git status --short` limpio, salvo lo que se espera (el `.md`, `docs/`, `.env*`).
- [ ] La rama sigue la convención real del repo, `<tipo>/<slug>` (`feat/notification-email-html`,
      `docs/task-conventions`). ⚠ **Ninguna rama de este repo ha llevado nunca el id de la task en el nombre**,
      así que no exijas `feat/TASK-NNN-*`: ese patrón falla en el 100 % de las ramas reales. El id va en el
      cuerpo del PR.
- [ ] `gh` existe. ⛔ **Hoy no está instalado** — ni en el host ni en la imagen `f5sign/backend:dev`, y el
      Makefile de infra no tiene target — así que esta skill **no puede completar su trabajo en esta máquina**
      y el PR se abre a mano. `status: fail`, `summary: "gh CLI ausente: abrir el PR manualmente"`, y **no**
      lo diagnostiques como problema de autenticación: no hay binario que autenticar.
- [ ] **La base es `develop`.** `master` es la rama de publicación; el trabajo de producto no se integra ahí
      directamente.

⛔ **Sin squash defensivo.** Este repo integra PRs de varios commits y merges de `develop`; contar commits
y hacer `git reset --soft` para dejar uno solo destruye historia útil y fuerza `--force-with-lease` sin
ganar nada. Si los commits son coherentes y explican su *por qué*, están bien como están.

### Paso 2 — Push

```bash
git push -u origin <rama>
```

Si la rama ya existe en remoto y el push no es fast-forward → **parar**: `status: fail` con la razón. Nunca
`--force`; `--force-with-lease` solo si el usuario lo pide explícitamente y sabe qué descarta.

### Paso 3 — Draft o ready

Leer los reports del workspace y contar WARNs no resueltos. Con WARNs → `--draft`. Sin WARNs → ready.
`--draft` / `--ready` del argumento manda.

⚑ **Un `skipped` declarado no es un WARN, pero tampoco un PASS.** `perf-smoke-backend` hoy se salta por
falta de `composer perf:seed`; va al body como *skipped, con su razón*, no como verde.

### Paso 4 — Título

`{tipo}({ámbito}): {qué hace, en imperativo}`, ≤70 chars. El `tipo` sale de lo que el diff hace
(`feat`, `fix`, `docs`, `chore`, `refactor`, `test`), no de un campo `Tipo` — este formato de task no lo
tiene. El `ámbito` es el BC o subsistema tocado (`envelope`, `notification`, `session`, `foundation`…).
Si el cambio rompe contrato publicado, `!` antes de los dos puntos.

### Paso 5 — Body

```markdown
## Task
[TASK-NNN](docs/tasks/TASK-NNN-{slug}.md) — {título}

## Resumen
{2-3 líneas de context-digest.md § Task summary}

## Cambios
- **Domain / Application / Infrastructure / Contract / UI:** {ficheros por capa}
- **Tests:** {ficheros}
- **Docs:** {ADRs, docs/, .env*}

## Propiedades verificadas
- [x] {afirmación de la sección de verificación} → {test que la prueba}
- [ ] {la que no se pudo probar} → {por qué el harness no la alcanza}

## Validaciones ejecutadas
| Skill | Status | Notas |
|---|---|---|
| spec-lint | PASS | — |
| task-validate-backend | PASS | N tests · covered-MSI X% · **harness: {la vía usada}** |
| doctrine-guard | PASS/n-a | — |
| contract-check-backend | PASS/n-a | — |
| security-audit-core | PASS | — |
| eidas-compliance | PASS/n-a | — |
| perf-smoke-backend | skipped | no existe `composer perf:seed` |
| docs-sync | PASS/n-a | — |

## Notas para el reviewer
{WARNs, deuda declarada, ADRs cuyo Status se movió en este changeset, y los Open follow-ups nuevos}

## Test plan
{derivado de lo que toca el diff, no de tags}
- [ ] {si toca UI/Http o config/routes:} llamar al endpoint en cada caso declarado, y comprobar que el
      OpenAPI generado dice lo mismo que el código
- [ ] {si toca migrations/:} `migrate`, verificar esquema, `migrate --dry-run` a la baja y comprobar
      reversibilidad. Si escribe filas que el dominio lee: enumerar los estados del agregado sobre los que
      cae la fila
- [ ] {si toca un Contract/Event/ o un payload:} comprobar que no se añadió un campo obligatorio
      (`Row::optionalString()`) y que ningún `event_type` se renombró en sitio
- [ ] {si toca un worker o un reactor:} drenar (`worker-down` → profundidad 0) → desplegar → `worker-up`
```

**El campo `harness` de la tabla es obligatorio.** Un PR que afirma verde sin decir qué árbol y qué
servicios corrieron es exactamente el fallo que `task-validate-backend` documenta en su precondición: el
stack monta `../f5sign-backend`, así que un verde sacado del checkout equivocado no dice nada del código
del PR.

### Paso 6 — Crear el PR

```bash
gh pr create --base develop --head <rama> \
  --title "{título}" --body-file {tmp} [--draft]
```

Si ya hay un PR abierto para la rama (`gh pr list --head ...`), hacer push y **actualizar el existente**;
no crear otro. Reportarlo en el summary.

### Paso 7 — Labels (solo las que existan)

`gh label list` primero; aplicar solo intersección. **No inventar labels** de fase/epic/tag: esos campos no
existen en este formato de task, y crear labels fantasma ensucia el repo.

### Paso 8 — URL del PR en el `.md`

Actualizar el `Status` del `.md` para que nombre la rama y el PR (README §3: un `Status` que afirma código
debe nombrar rama o commit) y commitear **encima**, sin amend:

```bash
git add {rutaMd} && git commit -m "docs(tasks): point TASK-NNN at its PR" && git push
```

## Manejo de fallos

- **Push rechazado (branch protection):** `status: fail`, decir qué regla se violó.
- **`gh pr create` falla:** `status: fail`. ⚠ Antes de sugerir `gh auth login`, comprueba que el binario
  existe: hoy **no está instalado**, y confundir ausencia con falta de credenciales manda al usuario a
  autenticar algo que no está ahí.
- **Alguien integró en `develop` entretanto:** `status: fail`, `summary: "merge de develop requerido"`. No
  rebasar automáticamente. ⚑ Si el merge toca `.claude/` o `CLAUDE.md`, puede abortar por `skip-worktree`:
  `bin/unlink-ai.sh` → merge → `bin/sync-ai.sh` desde la raíz del workspace.

## Qué NO hace

- No mergea el PR.
- No asigna reviewers ni milestones.
- No ejecuta CI a mano.
- No hace squash ni reescribe historia.
