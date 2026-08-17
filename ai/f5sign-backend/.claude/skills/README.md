# Estado de adaptación del stack de skills (backend)

Este stack se escribió para una versión anterior del proyecto: tasks en el `Planning/` del repo de docs,
tiers de test `composer test:unit|test:integration|test:e2e`, ORM con mapeos `*.orm.xml`, rama base
`master`, y `docker compose` desde el propio repo. **Nada de eso es cierto hoy** — ver
[`docs/tasks/README.md`](../../../docs/tasks/README.md) §1 para dónde queda `Planning/`.

La adaptación va por fases. Esta tabla es el estado real, medido el **2026-08-17**.

| Skill | Estado | Qué queda por arreglar |
|---|---|---|
| `spec-lint` | ✅ adaptada | — |
| `implement-backend` | ✅ adaptada | — |
| `task-validate-backend` | ✅ adaptada | — |
| `pr-ready` | ✅ adaptada | — |
| `task-runner` | ✅ adaptada | — |
| `task-close` | ⚠ pendiente | Escribe `Estado`, `Fin` y `Commit SHA` en una tabla *Seguimiento* que este formato no tiene. El equivalente es el campo `Status` de la tabla de cabecera, y debe **nombrar rama o commit** ([README](../../../docs/tasks/README.md) §3) |
| `doctrine-guard` | ⚠ pendiente | Valida mapeos `*.orm.xml` y "entidades Doctrine": **0 ficheros `*.orm.xml`** en el árbol y el ORM se retiró (ADR-0018). Lo que sí aplica y hay que conservar: reversibilidad de migraciones, índices, RLS (ADR-0017), convenciones de esquema (ADR-0019), coherencia ENUM SQL↔PHP, y la regla de autoría 6 |
| `contract-check-backend` | ⚠ pendiente | La mitad Nelmio `#[OA\*]` vale tal cual; la mitad AsyncAPI **no tiene diana**: `docs/asyncapi/` no existe. O se ficha crearlo, o se recorta la skill a la mitad que existe |
| `perf-smoke-backend` | ⛔ no ejecutable | Depende de `composer perf:seed`, que no existe (`composer run-script --list`: `test`, `coverage*`, `phpstan`, `arch`, `lint`, `format`, `infection`, `qa`). `task-runner` la salta **declarándolo** en `run.log`, no la da por verde |
| `docs-sync` | ⚠ pendiente | Condiciona por tags del frontmatter, que no existen. La condición correcta es lo que toca el diff, como ya hace `task-runner` Fase 3 |
| `security-audit-core` / `security-audit-backend` | ⚠ pendiente | Revisar referencias a rutas y namespaces del prototipo (`Innasign\`) |
| `eidas-compliance` | ⚠ pendiente | Cita `project_cloud_signing_decisions.md`, que vive en el repo de docs. Cada hecho que tome de ahí debe quedar **restatado** aquí |
| `v1-touched-file-hygiene` | ✅ nativa | Escrita para este repo. Se usa antes de commitear |

## Dos reglas para quien siga la adaptación

1. **Probar cada skill adaptada contra una task real antes de fiarse.** Una skill cuyos checks no
   encuentran nada devuelve verde, y ese verde se lee como all-clear: es el patrón que la regla de autoría
   5 de [`CLAUDE.md`](../../../CLAUDE.md) describe (*"un conjunto exento que hoy está vacío no puede
   ponerse rojo, así que verde es la señal esperada, no evidencia"*).
2. **Editar en el store, nunca en el subrepo.** Estos ficheros llegan al repo como symlinks a
   `ai/f5sign-backend/.claude/` con `skip-worktree`; una edición hecha en el checkout se pierde en el
   siguiente `bin/sync-ai.sh` — o peor, se commitea dentro del subrepo y rompe la regla de "cero rastro de
   IA". El worktree `f5sign-backend-develop` estuvo sirviendo copias de julio precisamente por eso.
