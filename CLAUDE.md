# F5Sign — Workspace raíz (repo interno)

Esta carpeta **es un repo git privado e interno** que ensambla el workspace de F5Sign y
**centraliza toda la configuración de IA** (Claude). **Nunca se entrega al cliente.** Cada
subcarpeta `f5sign-*` es un proyecto independiente con su propio git, dependencias y ciclo
de vida, y **no debe contener rastro de IA** (lo recibe por symlink, ignorado localmente).

## Estructura

- `ai/` — **Fuente de verdad** de la config IA. `ai/shared/` = skills idénticas en todos los
  repos que las usan; `ai/f5sign-*/` = `CLAUDE.md` + `.claude/` propios de cada subrepo.
- `bin/` — scripts: `bootstrap.sh` (clonar + sync), `sync-ai.sh` (symlinks de IA),
  `unlink-ai.sh` (revertir), `purge-ai-history.sh` (fase 4, destructiva).
- `notes/` — handoffs y notas internas de trabajo.
- `repos.manifest` — subrepos (nombre/url/rama) para `bootstrap.sh`.
- `f5sign-docs/` — **Fuente de verdad** de specs, decisiones de producto y arquitectura. Solo lectura.
- `f5sign-backend/` — API y lógica de servidor.
- `f5sign-dashboard/` — Frontend de administración.
- `f5sign-signer/` — App de firma para el firmante final.
- `f5sign-infra/` — Infraestructura y entorno local (stack de desarrollo).

## Reglas de trabajo

1. **Una tarea = un repo.** Sitúate (`cd`) en el subrepo que toca. Código, commits y PRs se
   hacen siempre dentro de ese subrepo, nunca en la raíz.
2. **La raíz es solo tooling/IA interno.** En la raíz NO va código de producto. Sus commits
   son config IA, scripts y notas. (Por eso este repo sí lleva git, a diferencia de antes.)
3. **`f5sign-docs/` es referencia.** Consúltalo para specs; no lo modifiques salvo tarea documental.
4. **Cruzar repos está prohibido en un mismo commit.** Dos proyectos = dos PRs coordinados.
5. **Config IA centralizada.** El `CLAUDE.md` y `.claude/` de cada subrepo son **symlinks**
   al store `ai/`. Edítalos ahí (o a través del symlink). Tras clonar/actualizar un subrepo,
   re-ejecuta `bin/sync-ai.sh`. Skills de usuario en `~/.claude/`.

## Worktrees

Varios `git worktree` del mismo subrepo conviven en el workspace (hoy tres del backend). Tres reglas,
las tres aprendidas a golpes:

1. **Van como hermanos de su repo, no dentro de él**: `f5sign-backend-<slug>/`, al lado de
   `f5sign-backend/`. ⛔ Un worktree **dentro** del checkout principal (`f5sign-backend/worktrees/…`)
   queda dentro del bind-mount `../f5sign-backend` del stack y aparece como `?? worktrees/` en el
   `git status` del principal. Añade el nombre nuevo a `.gitignore` de la raíz.
2. **`bin/sync-ai.sh` después de crear uno.** El script ya cubre worktrees enlazados, pero hay que
   correrlo: un worktree sin sincronizar **sirve los ficheros de IA trackeados en el historial** —viejos,
   y commiteables—, que es justo lo que prohíbe la regla de cero rastro. `skip-worktree` es por índice y
   cada worktree tiene el suyo, así que ponerlo en el clon principal no hace nada por ellos.
3. **Los targets normales de test validan el checkout PRINCIPAL, no el tuyo.**
   `f5sign-infra/docker-compose.override.yml` monta `../f5sign-backend`, `../f5sign-signer` y
   `../f5sign-dashboard` a mano. Desde un worktree hay que usar el lane efímero
   (`make -C ../f5sign-infra wt-backend|wt-signer src=$(pwd)`), que monta *tu* árbol y se destruye al
   terminar. ⛔ **`wt-dashboard` no existe** (sin suite hasta EP26): desde un worktree del dashboard hoy
   no hay ruta aislada, y eso se declara en vez de tomar prestado el verde del principal.
   Detalle en `f5sign-infra/CLAUDE.md` § *Validación efímera por worktree*.

⚠ **Un directorio con pinta de worktree no es un worktree.** `git worktree list` en el subrepo es la
única respuesta; el listado de la raíz miente. A 2026-08-25, `f5sign-signer-develop/` es un huérfano sin
`.git` que `sync-ai.sh` salta —correctamente— y que sigue ahí pareciendo lo que no es.

## Flujo típico para una tarea

1. Localizar la spec en `f5sign-docs/` (la tarea debería indicar la ruta).
2. `cd` al subrepo de implementación.
3. El subrepo ya lee su `CLAUDE.md` (symlink) + las reglas de esta raíz (heredadas por jerarquía).
4. Implementar, testear y commitear dentro de ese subrepo.
5. Referenciar la spec de docs en el mensaje de PR (ruta relativa desde el workspace).

## Secreto: cero rastro de IA en los subrepos

- Los ficheros IA llegan como **symlinks** ignorados vía `.git/info/exclude` de cada subrepo
  (local, no commiteado → la propia regla de ignore no se autodelata).
- `includeCoAuthoredBy: false` evita firmar commits con rastro de Claude.
- **Pendiente (FASE 4):** los `.claude/`/`CLAUDE.md` siguen *trackeados* en el historial de
  los subrepos (silenciados con `skip-worktree`). Purga con `bin/purge-ai-history.sh`
  (destructivo, reescribe historial + limpia mensajes; push forzado manual).

## Qué NO hacer

- No poner código de producto ni hacer commits de producto en la raíz.
- No commitear ficheros de IA dentro de los subrepos (rompe el secreto).
- No mezclar cambios de varios subrepos en una misma sesión sin delimitarlos.
- No duplicar specs dentro de los repos de código: enlazar a `f5sign-docs/`.
- **No correr `f5sign-docs/scripts/sync-skills.sh`.** Fue el mecanismo de distribución antes de `ai/` y
  está **retirado y bloqueado** desde 2026-08-25: hacía `rm -rf` del destino y `cp -r`, o sea borrar los
  symlinks, dejar ficheros de IA **reales** dentro del subrepo y revertir las skills a junio, con
  `exit 0`. `skills-library/` se conserva como lectura histórica; la fuente es `ai/`.
