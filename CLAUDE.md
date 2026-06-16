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
