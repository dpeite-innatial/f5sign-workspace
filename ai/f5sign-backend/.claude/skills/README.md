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
| `task-close` | ✅ adaptada | — |
| `doctrine-guard` | ✅ adaptada | — |
| `contract-check-backend` | ✅ adaptada | — |
| `perf-smoke-backend` | ◑ mitad estática adaptada | La dinámica (p95, throughput, memoria) sigue sin diana: no existe `composer perf:seed`. Crear el seed es una decisión, no un arreglo de la skill |
| `docs-sync` | ✅ adaptada | — |
| `security-audit-core` / `security-audit-backend` | ✅ adaptadas | — |
| `eidas-compliance` | ✅ adaptada | — |
| `v1-touched-file-hygiene` | ✅ nativa | Escrita para este repo. Se usa antes de commitear |

## Auditadas el 2026-08-17

Las doce pasaron por una auditoría de cinco agentes con contexto fresco: cuatro comprobando cada afirmación
factual contra el árbol (un comando por claim) y uno preguntando lo contrario — qué debería vigilar el stack
dada la arquitectura y no vigila nadie. Salieron ~100 hallazgos y todos los de estas cuatro clases están
corregidos: **afirmar protección o regla inexistente** (PII cifrada, identidad derivada contra ADR-0042, VOs
`final readonly` en bloque, B-LT por defecto), **checks que no podían fallar** (registro de eventos, `NO FORCE`,
`CHECK (... IN ...)`, cuatro pasos enteros de eIDAS), **instrucciones inejecutables** (ramas `feat/TASK-NNN-*`
que nunca existieron, `--testsuite <tier>`, JUnit sin configurar, `make sf` para el dry-run) y **duplicar un
test que ya existe** (`OpenApiSpecTest`, `SchemaConformanceTest`).

Lo que la auditoría dejó **abierto y no es arreglo de skill** está fichado en `docs/BACKLOG.md`: los dos
agujeros de producto que encontró, el censo de row-lock que se deja cuatro use cases, `BC_SCHEMAS ⊄
OWNED_SCHEMA`, los 26 `EVENT_TYPE` sin pin, y que no hay CI.

⚑ **El hueco grande que sigue ahí:** ninguna de las doce nombra una categoría del kernel, y el contrato
conductual de `Repository` —siete invariantes de `save`— no tiene ni un fichero de test. La forma está
enforzada casi por completo; el comportamiento, por nada. Eso es trabajo nuevo, no adaptación.

## Dos reglas para quien siga la adaptación

1. **Probar cada skill adaptada contra una task real antes de fiarse.** Una skill cuyos checks no
   encuentran nada devuelve verde, y ese verde se lee como all-clear: es el patrón que la regla de autoría
   5 de [`CLAUDE.md`](../../../CLAUDE.md) describe (*"un conjunto exento que hoy está vacío no puede
   ponerse rojo, así que verde es la señal esperada, no evidencia"*).
2. **Editar en el store, nunca en el subrepo.** Estos ficheros llegan al repo como symlinks a
   `ai/f5sign-backend/.claude/` con `skip-worktree`; una edición hecha en el checkout se pierde en el
   siguiente `bin/sync-ai.sh` — o peor, se commitea dentro del subrepo y rompe la regla de "cero rastro de
   IA". El worktree `f5sign-backend-develop` estuvo sirviendo copias de julio precisamente por eso.
