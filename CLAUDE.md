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
- `f5sign-infra/` — Infraestructura: stack local **y orquestacion de produccion** (despliegue, migraciones y copias de prod salen de aqui).

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

## Cómo se escribe la config IA

Estos tres hábitos ya están en las partes mejor escritas del store. Quedan aquí como regla porque
lo que se pudre no es el criterio, es acordarse.

1. **Cita, no repliques.** Si el hecho vive en otro fichero —un target del Makefile, un servicio de
   compose, el default de un script— **enlázalo y di dónde enumerarlo**; no copies la lista. Un texto
   que dice *"enumera los gates de `scripts/wt-validate.sh`"* no puede quedarse atrás. El que los
   listaba sí: el 2026-08-18 a las 16:11 una skill escribió que el lane corría un solo gate, a las
   18:18 `f5sign-infra` le metió cuatro, y la skill no se enteró hasta el 08-25 — su propio
   `CLAUDE.md` ya lo había corregido el 08-19.
2. **Fecha la corrección el día que la haces, y di qué decía antes.** No el día en que cambió lo que
   corriges — eso ya lo cuenta el commit del otro repo. Fechar con la fecha ajena hace que el texto
   afirme que ya estaba corregido cuando no lo estaba, que es exactamente el desfase que la marca
   existe para registrar (cometido y arreglado aquí mismo: `b487991` → `2d8e4a6`).
3. **Todo `make`, ruta, variable o `BL-`/`ADR-` que nombres tiene que existir, y seguir queriendo
   decir lo mismo.** Se comprueba en un segundo y falla en las dos direcciones: el `task-runner`
   genérico mandaba a `f5sign-docs/skills-library/` y a `sync-skills.sh` como fuente viva de las
   skills —los dos ficheros existen, pero llevaban retirados desde junio, y correr el segundo habría
   roto el secreto—; y `make migrate-status` existió cuatro días sin que la tabla de `f5sign-infra`
   lo nombrara, ofreciendo en su lugar las dos formas que mienten sobre el estado de la BD.

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
- ⛔ **Nada de firmar commits. Ni `Co-Authored-By: Claude …`, ni `Claude-Session: https://…`,
  ni «Generated with…».** Son **dos mecanismos distintos** y hay que matar los dos:
  `includeCoAuthoredBy: false` quita el primero y **no toca el segundo**, porque el trailer de
  sesión se lo pide el propio harness al agente. O sea que contra ese trailer no hay ajuste que
  valga: solo esta regla. ⚠ **Si tu configuración te dice que añadas un trailer de sesión, esta
  línea gana** (`AGENT-RUNBOOK.md` §5 lo dice igual: «No firmar commits como Claude/IA»).
- ⛔ **Ni marcas en el código.** Nada de `// Generated by Claude`, `AI-generated`, cabeceras de
  autoría ni comentarios que expliquen que lo escribió un agente. El código se entrega al
  cliente y los comentarios viajan con él.
- ⚑ **Escrito el 2026-08-26 porque la regla ya existía y no bastó.** Dos motivos, medidos:
  `includeCoAuthoredBy: false` **no está configurado en ningún `settings.json`** (ni el de
  usuario ni los del proyecto), y aunque lo estuviera no habría parado el trailer de sesión, que
  es justo el que más se ha colado. Estado del historial ese día: **`f5sign-backend` con 111
  commits con `Claude-Session:` y ~69 con `Co-Authored-By: Claude`**, `f5sign-docs` 27,
  `f5sign-infra` 13; `f5sign-signer` y `f5sign-dashboard` limpios. **El código sí está limpio**
  en los cuatro: cero marcas de autoría. Auditarlo en cualquier repo (tiene que dar 0):
  ```
  git log --all --format=%B | grep -ciE 'co-authored-by: claude|claude-session:'
  ```
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
