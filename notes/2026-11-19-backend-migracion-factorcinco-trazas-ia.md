# f5sign-backend → Factorcinco: inventario de trazas de IA (borrador para afinar)

Fecha: 2026-11-19. Solo lectura: no se ha tocado nada del repo.
Alcance: **todo el historial** (`--all`, desde `0a8cd5c8`, 2026-04-14) + el árbol del **último commit**,
`origin/develop` = `b0a6cabb` (2026-11-18), que contiene a `master` (`f756b060`, release v1.0.1).
⚠ El `develop` local va **39 commits por detrás** de `origin/develop` (todos de Miguel, 13–18 nov): el rewrite
tiene que partir de `origin/develop`, no del local.

Leyenda: **Q** = quitar · **R** = reescribir/reformular · **D** = decides tú · **M** = mantener (falso positivo).

---

## A. Ficheros y rutas en el historial

| # | Qué | Cifras | Prop. |
|---|-----|--------|-------|
| A1 | `.claude/` (13 skills, 2 agents, `skills-config.yaml`) y `CLAUDE.md`: trackeados hoy (con skip-worktree) | 42 commits los tocan | **Q** de todo el historial (`--invert-paths`, como en infra/signer) |
| A2 | `docs/tooling-handoff/` (README + `2026-08-18-task-runner-lessons.md`): enteramente sobre skills/symlinks/`ai/` | 2 ficheros | **Q** del historial |
| A3 | `.dockerignore` líneas 46-47 (`CLAUDE.md`, `.claude`) y `.gitignore` | 2 líneas | **Q** (y que nunca hayan existido) |
| A4 | `var/task-runner/` | nunca trackeado | M (ya fuera) |
| A5 | Commits que **solo** existen para la IA: `chore(skills)` ×3, `chore(agents): the two flagger subagents run on sonnet`, `8709306b Activate skills via sync-skills.sh`, `478bffac track v1-touched-file-hygiene…`, `b8381a42 test(architecture): the docblock link check skips the root CLAUDE.md` + su merge `7a3ae1f5`, `ae94bbc9` | ~10 | **Q** (filter-repo los vacía y poda; el de `b8381a42` además cambia código, ver B4) |
| A6 | `d6490bf5 chore(backend): Harden dev/test environment for AI-agent workflows`: el contenido es legítimo (compose, DAMA, .env.test) | 1 | **R** solo el mensaje (y traducir las 2 frases en español del cuerpo) |

## B. Contenido del árbol (lo que se entrega)

| # | Qué | Cifras (en `origin/develop`) | Prop. |
|---|-----|------|-------|
| B1 | **`CLAUDE.md` citado como reglamento** ("`CLAUDE.md` authoring rule 5", "repo rule 4"…) | **~355 refs en ~185 ficheros**: docs 182/50, tests 93/72, **src 42/35**, **migrations 21/17**, phpstan 10/4, config 2, README, infection, php-cs-fixer | **D — la decisión gorda**, ver §E1 |
| B2 | Mensaje de error **en runtime** de la regla PHPStan `SeeReferenceFqcnRule` nombra `CLAUDE.md` (y su test lo asserta) | 1 regla + 3 asserts | **R** junto con B1 |
| B3 | `tests/README.md:262`, `phpstan/README.md`, `phpstan/AUTHORING.md` (enlazan `../CLAUDE.md`, "for an agent holding only this repo") | 4 ficheros | **R** con B1 |
| B4 | `DocumentationLinkTest::OUTSIDE_THE_MOUNT = 'CLAUDE.md'` (excepción porque es symlink) | 1 test | **R**: si el fichero de reglas pasa a ser real y trackeado, la excepción sobra |
| B5 | Docs de tasks/ADRs con **métricas de agentes**: "slices ran on opus/sonnet", "the replicator was used once", "`var/task-runner/TASK-042/`", "critical/opus, 3 rounds", "five-agent audit" | ~83 refs a opus/sonnet/haiku; ~30 a task-runner/slice-implementer/…; ~45 `docs/tasks/*` y ~10 ADRs afectados | **R**: quitar las secciones/frases de ejecución por modelo; dejar "Deviations" en lenguaje humano |
| B6 | `docs/BACKLOG.md`: filas sobre la propia herramienta (BL-109 *CLAUDE.md is a version behind*, BL-134 *task-runner runs phase-3 in parallel…*, BL-135, filas de "skills", "agent"…) | 46 hits en 1 fichero | **R/Q** fila a fila (lista en el anexo cuando lo pidas) |
| B7 | Frase recurrente "**so an agent can work in it**", "not agent-reachable" (`OFFREPO` en tests), "the contracts an agent must not drift from", "an agent following these instructions" | ~150 usos reales de *agent* (de 206; 33 son *user agent*) | **R** → "a reader / a developer / a contributor" |
| B8 | `docs/infra-handoff/2026-08-18-worktree-test-isolation.md` y `TASK-013` enlazan `.claude/skills/...` | 3 enlaces | **R** |
| B9 | Referencias a la raíz `ai/`, a symlinks, a "the store", a "peer session", "this session", "a fresh session" | por clasificar a mano (la palabra *session* tiene 1.468 usos y casi todos son la **signing session** del dominio) | **R** solo las de sesión-de-agente |
| B10 | **Glifos ⚑ ⛔ ⚠** en prosa | **7.761 en 1.056 ficheros**; **src: 2.514 en 400**; ~100 dentro de literales de string en `src/` | **D**: es una "firma de estilo" muy reconocible (signer 801, infra 220 en su árbol). Quitar en comentarios es mecánico; en strings/`#[OA\*]` hay que mirar tests y snapshots |
| B11 | Estilo de docblocks: muy largos, "X because Y", em-dashes masivos | todo el repo | **D**: no recomendado tocarlo en masa (coste/riesgo enorme); como mucho los glifos |
| B12 | **SHAs citados** en docs/src/tests (`117f7d3`…): tras el rewrite apuntan a nada, y eso delata reescritura | **1.490 en 150 ficheros**; + 249 en mensajes de commit | **D**: mapear viejo→nuevo con el `commit-map` de filter-repo y reemplazar (2ª pasada), o reformular por nombre de commit |
| B13 | `ghcr.io/dpeite-innatial/f5sign-backend` en `.github/workflows/build-image.yml` y `Dockerfile` | 2 | **R** a la org Factorcinco (no es IA, pero es la cuenta personal) |
| B14 | Texto en **español** en ~20 `docs/frontend-handoff/*`, BACKLOG, ADR-0055, y `assets/evidence-audit/*.typ` | ~25 ficheros | **M** los `.typ` (es el producto, salida en español). **D** los handoffs: en infra se tradujo todo |
| B15 | Nombre antiguo **Innasign** / `innatial` (`src/Innasign` en abril, `.env` `innasign:innasign`) | 9 ficheros hoy, 13 mensajes | **D**: no es IA; solo si tampoco queréis rastro de la marca previa |

### Falsos positivos (M)
- *user agent* / `UserAgentHeader` (dato de evidencia HTTP) — 33+ usos.
- *session* del dominio (`SigningSession`, `session.copy_link`…).
- *prompt* en sentido UI ("a re-prompt for an envelope…", "the second prompt still appears").
- *generated* (códigos OTP, migraciones `doctrine:migrations:generate`, OpenAPI generado).
- *worktree* (258): es una función de git y el carril `wt-backend` es infra real. Se puede quedar; solo quitar
  el marco "parallel sessions/agents" donde aparezca.
- "AI" en las fuentes `.ttf` (binario).

## C. Mensajes de commit (2.157 commits en `--all`)

| # | Qué | Cifras | Prop. |
|---|-----|--------|-------|
| C1 | `Claude-Session:` | **109** (`--all`) | **Q** |
| C2 | `Co-Authored-By: Claude …` (`noreply@anthropic.com`) | **69** | **Q** |
| C3 | "Generated with…" / 🤖 | 1 / 0 | **Q** |
| C4 | Trailers por autor: Daniel 108, **Miguel 63** | — | Q en ambos |
| C5 | Asuntos con términos de IA (`claude`, `agent`, `skill`, `slice`, `task-runner`, `sonnet`…) | 17 asuntos (+ los de A5) | **R/Q** |
| C6 | Cuerpos que citan `CLAUDE.md`, "authoring rule N", "slice N", `var/task-runner`, "review agents found", "the orchestrator", "the TASK-028 session" | ~250 líneas con *claude*, 41 con slice/var/task-runner, 17 con agentes revisores | **R** |
| C7 | Glifos ⚑⛔⚠ en mensajes | 275 líneas | **Q** |
| C8 | **Longitud**: cuerpos de 16-40 líneas: 610; >40 líneas: 112. Solo-asunto: 127 | — | **R** como en infra: recortar a 0-6 líneas de "por qué + cómo se verificó" |
| C9 | SHAs citados en mensajes | 249 | R con el commit-map (o quitarlos al recortar) |
| C10 | Merges `Merge feat/x: TASK-NNN — …` | 205 | **M** formato (es el convenio humano), recortar si son kilométricos |
| C11 | `stash@{0}` "Pull autostash" | 1 | no se pushea; M |

## D. Patrón temporal y autoría

| # | Qué | Cifras | Prop. |
|---|-----|--------|-------|
| D1 | **Volumen**: 2.157 commits en 109 días con actividad; Daniel **1.011 en octubre** | 16 días con >50 commits; pico **156 el 2026-10-23**, 139 el 09-29, 138 el 10-21 | **D**: con reparto solo no basta (ver §E3) |
| D2 | **Ráfagas**: intervalo entre commits consecutivos <1 min: **611**; 1-3 min: 415 | 98 marcas de tiempo repetidas al segundo | **R** fechas |
| D3 | Horas: Daniel 00-02h: 23 commits (días 08-18 y 10-21); 19-23h: ~120 | Miguel: todo 8-18h | **R** a horario laboral |
| D4 | Fin de semana: 1 (sáb 11-07 19:39, `0de20862`) | — | R |
| D5 | Author date ≠ committer date | 272 (rebases) | **R**: igualar committer=author tras repartir |
| D6 | Zonas `+0200`/`+0100` coherentes con CEST/CET | — | M (mantener la zona correcta tras mover fechas, cambio de hora 25-oct) |
| D7 | Autores: Daniel 1.850 · Miguel 303 · Miguel vía web de GitHub 4 (`noreply@github.com` committer) | emails `@innatial.com` | **D**: ¿se mantienen los emails innatial o pasan a los de F5? ¿algún commit cambia de autor? |
| D8 | Desequilibrio: octubre 1.011 Daniel / 36 Miguel | — | D (si se fusiona, se corrige solo en parte) |

## E. Decisiones que necesito de ti

**E1 — ¿Qué hacemos con `CLAUDE.md` como reglamento (B1-B4)?** Recomiendo: en **todo el historial**,
`CLAUDE.md` → `CONTRIBUTING.md` (o `docs/AUTHORING-RULES.md`) con `--replace-text` sobre las ~355 refs, y que el
fichero renombrado contenga solo las secciones humanas (Stack, Conventions, *Authoring rules*, Repo-specific
rules), sin las de operación de agente (`make shell` "an agent cannot use it", test-runner, sesiones). Variante
barata: borrar `CLAUDE.md` del historial y crear `CONTRIBUTING.md` limpio solo en el último commit (las refs de
commits viejos quedarían a un fichero que aún no existe; poco visible). El `CLAUDE.md` del store `ai/` sigue
existiendo como symlink local.

**E2 — Glifos ⚑⛔⚠ (B10/C7)**: ¿fuera de todo (historial incluido), solo de comentarios, o se quedan?

**E3 — Fusión de commits (D1/D2)**. 2.157 commits entre el 14-abr y el 18-nov ≈ 155 días laborables;
agosto-octubre concentra ~1.800 en ~66 días laborables (~27/día). Propuesta:
- Fusionar dentro de cada rama de task los commits de "slice + fix de review + sweep de docs + close" en
  3-8 commits por task (objetivo total ~700-900).
- Repartir después en L-V, 9:00-14:30 y 15:30-19:00, separación mínima 6-10 min, máx. ~15-20/día por persona,
  conservando orden, topología de merges y fechas de los tags de release (v1.0.0 = despliegue prod 2026-11-06).
- ¿Umbral de commits/día y ventana horaria que quieres?

**E4 — Ramas y tags que se publican en Factorcinco**: propongo `master`, `develop`, tags `v0.0.0…v1.0.1`
re-apuntados. **No** publicar: `backup/compatibility-doc-2b81c3dc`, tag `pre-squash-backup`, las 20 ramas
feat/fix ya mergeadas (sus merges siguen en el grafo). Ramas vivas con worktree (`feat/document-certificate`,
`feat/explicit-access-gate`, `fix/form-engine-binary-framing`, `fix/unclaimed-slot-on-machine-routes`,
`fix/evidence-unprintable-characters`): ¿se rebasean sobre el historial nuevo o se cierran antes?
¿"Fakear ramas" = crear merges `--no-ff` donde hoy hay commits directos a develop?

**E5 — SHAs citados (B12/C9)**: ¿remapear con el commit-map (2ª pasada de `--replace-text`) o eliminar las citas?

**E6 — Autoría (D7)**: ¿emails innatial o F5? ¿Hay commits que deban pasar de uno a otro?

**E7 — Español en `docs/frontend-handoff/` (B14) y marca Innasign (B15)**: ¿traducir/limpiar como en infra?

## F. Riesgos/operativa (para cuando se aplique)

- Rewrite **sobre un clon espejo nuevo** de `origin` (backups en `backups/`, como infra), nunca en el checkout vivo.
- Miguel tiene trabajo encima (39 commits del 13-18 nov): congelar pushes al repo personal durante el corte y
  que re-clone después.
- Prod: el host despliega el backend desde un SHA/imagen concreta → anotar su equivalente en el historial nuevo
  (como se hizo con infra, `81cdd59` = `ed2d5d2`).
- Migraciones: los nombres `VersionYmdHis` no cambian (están en el contenido, no en el SHA) → la BD de prod no se
  entera. Solo cambian docblocks (permitido por la regla 2).
- Tras reescribir: `make qa` completo en el historial nuevo (tests que leen docs/enlaces: `DocumentationLinkTest`,
  `OpenApiSpecTest`, `SeeReferenceFqcnRuleTest`).
- Auditoría final que tiene que dar 0:
  `git log --all --format=%B | grep -ciE 'claude|anthropic|co-authored-by|sonnet|opus|haiku|subagent|task-runner'`
  y lo mismo con `git grep` sobre cada tag publicado.

---

# Ronda 2 (2026-11-19): decisiones tomadas y revisiones previas

## Decisiones del owner
| # | Decisión |
|---|----------|
| E2 | Glifos ⚑ ⛔ ⚠ **fuera**, de todo el historial (árbol + mensajes) |
| E3 | Umbrales: **a acordar** (propuesta abajo, §U) |
| E4 | Aspecto de **git flow no estricto** (propuesta abajo, §G) |
| E5 | **Reescribir los SHAs citados** al historial nuevo (commit-map de filter-repo) |
| E6 | Autores: **solo Daniel o Miguel** |
| E7 | **Traducir al inglés** lo que toque |
| — | Paso 0 obligatorio antes de cualquier acción: comparar `CLAUDE.md`/`.claude` trackeados con el store (§1) y cerrar lo pendiente (§4) |

## §1. `CLAUDE.md` y `.claude/` trackeados frente al store (`ai/f5sign-backend/`, vía symlink)

Comparado `origin/develop` con el destino del symlink, fichero a fichero:

| Ruta | Estado | Qué implica |
|------|--------|-------------|
| `.claude/agents/v1-docblock-flagger.md`, `v1-hygiene-flagger.md`, `.claude/skills-config.yaml`, `.claude/skills/v1-touched-file-hygiene/SKILL.md` | **IGUAL** | nada que rescatar |
| Las otras 12 skills trackeadas (`contract-check-backend`, `docs-sync`, `doctrine-guard`, `eidas-compliance`, `implement-backend`, `perf-smoke-backend`, `pr-ready`, `security-audit-*`, `spec-lint`, `task-close`, `task-runner`, `task-validate-backend`) | **DIFIEREN**: el repo tiene la versión del **2026-04-15**, el store es la evolución posterior (p. ej. `task-runner` tiene 183 líneas en el repo y 520 en el store) | nada que rescatar: el store es la versión buena |
| Solo en el store: 13 agents (`test-runner`, `slice-*`, `plan-runner`, `replicator`, `*-runner`…), skills `plan-backend`, `task-author`, `skills/README.md`, `settings.json` (shared), `settings.local.json` | nunca han estado en el historial | nada que purgar; no se pierde nada |
| **`CLAUDE.md`** | **HA DIVERGIDO.** Lo editan **38 commits, todos de Miguel**, mezclados con código (el último, `ce15dc63`, es del 17-nov). Su copia es una base **antigua** (de agosto aprox.: "4 populated BC trees", sin Twig, Sentry, KeyManagement, ADR-0088…) más **4 cambios recientes que el store NO tiene** | ⚠ **portar al store antes de purgar**, o se pierden |

Los 4 cambios de Miguel que faltan en el store (`609bc4c8`, `c58d6d2b`, `ce15dc63`):
1. `PHPUnit 13.4` (el store aún dice 11.5; `composer.json` de `origin/develop` ya pide `^13.4`).
2. Fila `make test-without-acceptance`.
3. `make qa` = lint + arch + phpstan + tests con coverage + **Infection solo en las líneas cambiadas** frente a `origin/develop` (`bin/infection-changed`).
4. Fila `make infection` (el suelo global de covered-MSI).

Todo lo demás en lo que difieren es más nuevo en el store.

⚠ **Consecuencia para Miguel**: él trabaja con los ficheros **trackeados** (sin symlink). Sus sesiones usan `CLAUDE.md` de agosto + parches y las **skills de abril**. Tras la purga se queda sin nada, así que necesita el montaje con el store (`bin/sync-ai.sh` o una copia local ignorada) **antes** de re-clonar.

## §4. Lo que está sin commitear, sin pushear o sin mergear (a 2026-11-19)

| Dónde | Qué | Acción propuesta |
|-------|-----|------------------|
| `develop` (checkout principal) | **39 commits por detrás** de `origin/develop` (Miguel, 13-18 nov) | base del rewrite = `origin/develop`; el pull local no hace falta |
| `fix/unclaimed-slot-on-machine-routes` (worktree `f5sign-backend-unclaimed-slot-machine`) | **TASK-078**: 23 commits **sin mergear**, 21 **sin pushear** (fixes reales: 409 en las rutas máquina para un slot sin reclamar, tests, handoff). `git cherry`: ninguno está en develop | **cerrar antes del rewrite**: gates + merge a develop |
| `fix/evidence-unprintable-characters` (worktree) | 1 commit sin mergear (`54358f63`, fila de BACKLOG, que ya está también en TASK-078) + **sin commitear**: `docs/tasks/TASK-079-…unprintable…md` (nuevo) y 1 línea de `docs/BACKLOG.md` | decidir: ¿TASK-079 validada → commit, o se queda fuera? |
| `feat/document-certificate` (worktree) | rama ya mergeada; **sin commitear**: `docs/adr/ADR-0094-…certificate…md` (borrador) + 5 líneas de `docs/adr/README.md` | borrador no validado; decidir si entra antes del corte |
| `backup/compatibility-doc-2b81c3dc` (local, sin upstream) | 2 commits sin mergear: `2b81c3dc docs(compatibility): the services and what was measured…` (+ `54358f63`) | decidir: mergear `docs/COMPATIBILITY.md` o descartarlo |
| `feat/explicit-access-gate`, `fix/form-engine-binary-framing` (worktrees) | limpios y mergeados | retirar los worktrees |
| Otras 20 ramas locales | todas mergeadas en `origin/develop` | no se publican |
| `stash@{0}` (develop, 03-nov) | solo cambia el modo de 25 fakes de `tests/Fixtures/typst-fakes/` (755→644) | descartar (el 755 trackeado es el correcto) |
| Remoto `origin/fix/unclaimed-slot-on-machine-routes` | el único remoto sin mergear (2 commits) | se resuelve con TASK-078 |
| Repo raíz | `.gitignore` modificado + notas sin trackear (incluida esta) | no afecta al backend; commit aparte en la raíz |

## §U. Propuesta de umbrales (a negociar)

Volumen real (sin merges, `origin/develop` + ramas pendientes): Daniel **~1.610 commits en las semanas W34-W44** (11 semanas),
con picos de **397 en W43** y 216 en W34. Miguel nunca pasa de 67 por semana (W45). Repartir fechas no basta: con
el tope de abajo, Daniel tiene que **fusionar ~2,5× de media y ~6× en W43**.

| Parámetro | Propuesta |
|-----------|-----------|
| Commits por persona y día | lo normal 4-12; **tope duro 16**; algún día suelto con 0-2 |
| Commits por persona y semana | **tope 55** (Daniel queda en unos 600-700 sin merges en total; Miguel casi intacto, ~300) |
| Separación entre commits de una persona | **mínimo 6 min**; lo normal 12-45 min, con distribución sesgada y no uniforme (que no se note un patrón) |
| Horario | L-V 09:00-14:15 y 15:15-18:45; hasta un **5 %** entre 18:45 y 20:30; **nada entre 21:00 y 08:30** ni en fin de semana. Festivo: 12-oct (lunes) sin commits |
| Merge de una rama | 2-15 min después de su último commit; el merge de release el mismo día que el tag |
| Anclas que no se mueven (±1 día laborable) | tags `v0.0.0`…`v1.0.1`, despliegue prod v1.0.0 (06-nov), entregas a signer/dashboard que constan en handoffs |
| Movilidad | cada commit se queda en su **semana real** (como mucho se adelanta o atrasa 1 día laborable), respetando el orden padre→hijo y que las fechas de Daniel y Miguel no se crucen en el mismo fichero |
| Zona horaria | +0200 hasta el 25-oct, +0100 después (como ahora) |
| Committer | = author (nombre, email y fecha) en todos; los 4 merges web de GitHub de Miguel pasan a committer Miguel |
| Commits idénticos al segundo | 0, salvo el par merge + tag |

**Fusión** (orden de preferencia, siempre dentro de una misma rama/task):
1. Los commits "close/record/sweep" de docs de una task (`docs(task-NNN): the record says…`, `docs(backlog): BL-…`) → 1-2 commits por task.
2. Los fixes de review encima del commit que corrigen (`fix(...)` / `test(...)` del mismo día y alcance).
3. Las slices de una task → 2-6 commits por task (por capa o por comportamiento), nunca uno solo por task.
4. Los commits que se quedan vacíos tras quitar `.claude`/`CLAUDE.md` → se podan.

## §G. Propuesta de git flow "no estricto"

Estado real: hasta el 18-sep `master` fue el tronco (302 commits en primer padre); desde entonces `develop` lleva
**241 commits directos** (128 de Daniel, 113 de Miguel) y ~200 merges de rama.

| Elemento | Propuesta |
|----------|-----------|
| `master` | solo releases desde septiembre; antes, trabajo directo **pero** con una rama `develop` que nace pronto (p. ej. en julio, cuando entra Miguel con regularidad) |
| `develop` | integración. Directos solo los commits sueltos de docs/chore (~15-25 %); el resto entra por merges |
| Ramas | se mantienen `feat/`, `fix/`, `docs/`, `chore/`, `refactor/`, `test/` (git flow puro usa `feature/`; no hace falta) |
| Ramas "fingidas" | agrupar en ramas `--no-ff` las tandas de commits directos a develop que son una misma task (sobre todo de Miguel, W37-W46), con nombres como los existentes |
| `release/vX.Y.Z` | crear 3 ramas cortas (`release/v0.0.1`, `release/v1.0.0`, `release/v1.0.1`) con 0-2 commits (versión/changelog), mergeadas a master **y de vuelta a develop**. `v0.0.0`, `v0.0.2` y `v0.0.3` siguen siendo tags sobre master |
| `hotfix/` | 1-2 donde hubo arreglo directo tras un despliegue (candidatos: `7f6a419e ci(build-image): a tag has to be on master`, los fixes del 13-nov previos a v1.0.1) |
| Merges de develop en una rama | los hay (`Merge develop into feat/recipient-notices…`) y se quedan: dan realismo |
| Mensajes de merge | `Merge branch '<rama>' into develop` en algunos (estilo por defecto de git, sobre todo de Miguel) y `Merge <rama>: …` en otros; no todos iguales |
| Publicar | `master`, `develop` y los tags. Las ramas de feature, no (sus merges quedan en el grafo) |

## §4 bis. Revisión de lo pendiente (2026-11-19, tras actualizar develop a `b0a6cabb`)

- **develop**: fast-forward a `origin/develop` hecho (receta skip-worktree → pull → sync-ai). Los 4 cambios de Miguel a
  `CLAUDE.md` están portados al store (commit raíz `66f527e`). Rango: Dockerfile, composer.lock y services.yaml
  cambian, **sin migraciones**. Al levantar el stack: reconstruir `f5sign/backend:dev`, `composer install`,
  `make up` y `worker-down`/`worker-up`.
- **TASK-078** (`fix/unclaimed-slot-on-machine-routes`, 23 commits del 04-nov, 21 sin pushear): implementada y
  verde en el lane (10.693 tests, Infection 19/19 en las líneas cambiadas). Bloqueos para mergear:
  1. **AC-15**: la consulta de solo lectura en prod (§7 del record: slots reclamables sin reclamar con
     `first_opened_at`) la tiene que correr el owner.
  2. **Conflictos** con develop en `docs/BACKLOG.md` y en `IssueAuthChallengeUseCaseTest.php`.
  3. **Ids BL repetidos**: la rama usa BL-507 (su cierre) y BL-508 (credenciales emitidas antes del deploy), y en
     develop Miguel ya dio BL-507 y BL-508 a otras filas (y BL-501 a otra cosa). Hay que renumerar a ≥ BL-520.
  4. El record trae `### Delegated work` y `### Cost of the run` (traza de IA), que caen en el rewrite.
- **TASK-079** (record sin commitear, 04-nov 12:56, "Not started"): **superada**. Ese mismo día Miguel arregló el
  problema en develop (`ae5427b5 fix(evidence-audit): print what a page cannot draw as its code`: BL-500 cerrado; el
  BL-501 de develop es justo la BL-502 que proponía la 079) y `fefb3abb` (fuente de la marca). Propuesta:
  descartarla, junto con su línea de BACKLOG y la rama `fix/evidence-unprintable-characters`.
- **ADR-0094** (borrador sin commitear del 28/29-oct, en el worktree `document-certificate`): **un certificado
  sellado por documento final** (prueba de entrega del albarán: quién actuó sobre ese documento y cómo terminó,
  visible para todos los que pueden verlo, sin evidencia técnica y sin informativos). El fondo lo decidió el owner
  el 28-oct; está *Proposed*, sin task. El número está reservado: ADR-0095 se lo saltó a propósito y TASK-077 lo
  cita dos veces. ⚠ **Solo existe en disco**: si se borra el worktree, se pierde.
- **`backup/compatibility-doc-2b81c3dc`**: `docs/COMPATIBILITY.md` (201 líneas + 1 enlace en ARCHITECTURE.md), escrito el
  04-nov 13:40 en el develop local y **nunca pusheado**. Es un registro de lo **medido** sobre cada dependencia (EU DSS,
  pyHanko, Typst y lo que mide el signer), con estados WORKS/FAILS/DEGRADES/PENDING/READ, fecha y versión. El 07-nov
  19:49 develop se reseteó a origin y el commit se guardó en esa rama de backup. Parte de lo que mide ya cambió
  (DejaVu y la fuente de la marca los arregló Miguel). Opciones: actualizarlo y mergearlo, o descartarlo.

## §4 ter. Estado al cierre del 2026-11-19 (sustituye a la tabla de §4 / §4 bis)

- **TASK-078**: mergeada en develop (`06ce2726`) y pusheada. Validada en el lane del worktree con una imagen
  construida desde la rama: lint, deptrac y PHPStan limpios, `OK (11482 tests)`. BL-528 (cerrada) y BL-529
  (abierta). AC-15 queda como no ejecutada, por decisión del owner, con su motivo en el §7 del record.
- **TASK-079**: descartada (Miguel lo arregló en develop el 04-nov, `ae5427b5`).
- **ADR-0094**: revisada frente a ADR-0096/0097 y mergeada en develop como *Proposed* (`beb58847`). Le quedan tres
  preguntas abiertas para el owner (§2.9).
- **Ramas**: en origin solo quedan `master` y `develop` (borradas 18 remotas y 22 locales, todas ya en develop).
  Los worktrees están retirados. Queda en local `backup/compatibility-doc-2b81c3dc` (**sin decidir**) y el stash
  (solo cambios de modo; se puede descartar).
- **Raíz**: 3 commits locales sin pushear (`66f527e` store `CLAUDE.md`, `2305d2c` y `b2e9a18` `.gitignore`).
- **Stack de dev**: levantado con la imagen `f5sign/backend:dev` de hace 4 semanas. Antes de usarlo: reconstruir la
  imagen, `composer install` y recrear los contenedores.

**Lo que falta antes de reescribir el historial**: decidir `COMPATIBILITY.md`, acordar los umbrales (§U) y la forma de
git flow (§G), y decidir E1 (qué hacer con `CLAUDE.md` como reglamento: renombrarlo a `CONTRIBUTING.md` en todo el
historial o la variante barata). Después: congelar los pushes (avisar a Miguel), clonar un espejo de backup y aplicar.

---

# Ronda 3 (2026-11-20): plan acordado

## Decisiones cerradas
| Tema | Decisión |
|------|----------|
| `COMPATIBILITY.md` | tirado (rama `backup/compatibility-doc` borrada) |
| Refs a `CLAUDE.md` en el código (~355) | **opción a**: cada comentario se reescribe para explicarse solo, sin apuntar a ningún fichero |
| Volumen de Daniel | **combinar**: repartir ±1-2 semanas **y** reasignar tasks enteras a Miguel (Miguel está de acuerdo) |
| Umbrales | los de §U + tope de ~1.500 líneas a mano por commit, mediana de 2-3k líneas/día y ninguna semana > ~30k. **La doc sacada no cuenta** |
| Emails | no se tocan |
| Innasign | fuera de todo el historial |
| Corte | libre: el equipo no trabaja hasta que esté hecho, y Miguel está avisado |
| Docs de proceso | **fuera del repo**: `docs/tasks/`, `docs/frontend-handoff/`, `docs/infra-handoff/`, `docs/tooling-handoff/`, `docs/BACKLOG.md` |
| Docs que se quedan (limpios) | `docs/adr/`, `docs/ddd/`, `ARCHITECTURE.md`, `LOAD-BEARING.md`, `LIVE_SCHEMA.md` |

## Destino de los docs de proceso
- Van al repo raíz: `ai/f5sign-backend/docs/{tasks,frontend-handoff,infra-handoff,tooling-handoff,BACKLOG.md}`
  (copia del estado actual; su historial no se conserva).
- `bin/sync-ai.sh` los enlaza en el subrepo como symlinks ignorados por `.git/info/exclude`, igual que `CLAUDE.md`.
  Las skills (`task-runner`, `spec-lint`, `task-close`…) y las sesiones del signer y del dashboard siguen viendo las
  mismas rutas.
- En el código y en las ADRs/ddd que se quedan: un enlace markdown a un doc sacado pasa a texto plano, como un id de
  ticket (`TASK-078`, `BL-528`). Los ids en sí se quedan. `DocumentationLinkTest` debe seguir en verde.

## Efecto medido
Al sacar tasks, handoffs y BACKLOG, Daniel pierde 315 de 1.640 commits (19 %) y ~41k de 420k líneas (10 %), y Miguel
20 commits.

## Fases
0. **Preparación (local, reversible)**: backup espejo de origin + bundle; copiar los docs de proceso al store
   y extender `sync-ai.sh`.
1. **Purga y reescritura de contenido** con git-filter-repo sobre un clon de trabajo:
   - quitar paths (`.claude/`, `CLAUDE.md`, los docs sacados);
   - reemplazar texto en todo el historial: refs a `CLAUDE.md` (opción a), enlaces a docs sacados, glifos ⚑⛔⚠⛑,
     Innasign, rutas `ghcr.io/dpeite-innatial`;
   - traducir al inglés lo que queda en español en lo que se conserva;
   - limpiar los mensajes de commit (trailers, glifos, refs a IA, recorte de cuerpos).
2. **Reestructuración del grafo**: fusiones dentro de rama, ramas de feature que muestren la evolución, reasignación a
   Miguel y reparto de fechas según los umbrales.
3. **Remapeo de SHAs citados** (commit-map), en el árbol y en los mensajes.
4. **Verificación**: auditorías a 0, `make qa` completo en el tip, y comparación del árbol final con
   `origin/develop` (solo pueden diferir docs, comentarios y los ficheros sacados).
5. **Revisión con el owner** → crear el repo en Factorcinco → push de `master`, `develop` y los tags → reapuntar prod
   y los clones.

## Progreso 2026-11-20

**Fase 0 hecha**:
- `backups/f5sign-backend-pre-purge.git` (espejo de origin, develop `beb58847`) y `backups/f5sign-backend-local-2026-11-20.bundle`;
- los docs de proceso están en `ai/f5sign-backend/docs/` y se enlazan con `sync-ai.sh` (commit raíz `049782e`).

**Fase 1a (contenido), ensayada y verificada en `rewrite/try3`** (clon desechable, sin remoto):
- Herramientas en `rewrite/tools/`: `inventory.py`, `units.py`, `spanish_units.py`, `blob_filter.py`,
  `cmp_tokens.php`. Todo con búsqueda literal; el filtro corre con el python del venv pipx de git-filter-repo.
- Entradas: `inv/units2.rewritten.jsonl` (395 frases, reescritas por Sonnet sin inventar nombres de regla),
  `inv/overrides.jsonl` (13 correcciones a mano) y `inv/spanish.rewritten.jsonl` (21 traducciones).
- Resultado:
  - 2.148 → 1.784 commits (se podan los que solo tocaban docs de proceso o IA);
  - Claude, modelos, flujo de agentes y glifos a **0** en todo el historial;
  - en el último commit, 847 PHP con el código idéntico token a token (solo comentarios), 31 que solo cambian en
    strings (glifos y el mensaje de la regla PHPStan, igual en su test) y 1 cambio de código buscado
    (`DocumentationLinkTest` pierde la excepción de `CLAUDE.md`).
- Fallo encontrado y corregido: `file_info_callback` no ve los borrados, así que un fichero renombrado desde
  `src/Innasign/` sobrevivía como fantasma. El renombrado y el borrado de rutas van ahora por las opciones de
  filter-repo.
- Pendiente de decisión: la titularidad ("Proprietary — Innatial", `.cspell.json`), "workspace scratchpad" y las
  menciones a "the workspace" (27 ficheros), y los comentarios `<!-- OFFREPO -->` (69).
- Consecuencia: los glifos salen de descripciones del OpenAPI, así que hay que regenerar el snapshot del signer
  al hacer el corte.

## Progreso 2026-11-20 (tarde): historial nuevo construido

- Herramientas de la fase 2: `rewrite/tools/graph_extract.py`, `plan_graph.py` (v2: fusión, reparto a Miguel,
  partición de gigantes por capa y contexto, ramas fingidas, fechas), `msg_inputs.py`, `sha_scan.py`, `build.py`.
- Mensajes: `rewrite/msgs/batch_*.out.jsonl` (954, escritos por Sonnet con `msgs/GUIDE.md` y validados en global:
  0 términos prohibidos, ningún asunto de más de 90 caracteres, ningún "wip", ningún cuerpo de más de 6 líneas).
- Resultado en `rewrite/final2.git` (bare): 954 commits (759 + 195 merges), `develop`, `master` y los 6 tags.
  - Autores: solo Daniel y Miguel, con sus emails `@innatial.com`; committer = autor.
  - Fechas: L-V, de 9 a 18 h, segundos repartidos, ningún par en el mismo segundo.
  - Rastros: 0 en contenido y en mensajes.
  - Árbol final y tags idénticos al historial limpio salvo los SHAs citados traducidos (157 líneas en 36 ficheros
    del último commit). 8 citas de versiones intermedias no se pudieron traducir porque citan un commit posterior;
    ninguna está en el último commit.
- Cifras semanales en `rewrite/plan/final-weeks.txt`. Picos aceptados: Miguel en W45 (55k líneas; release y el
  commit de key-management partido) y 17-18 commits/día en W45/W47 (semana de release).
- Pendiente: el resultado de la suite completa sobre el último commit (lane con imagen propia), la revisión del owner,
  y después crear el repo en Factorcinco, pushear, reapuntar prod y los clones, y regenerar el snapshot OpenAPI del
  signer.

## Estado final 2026-11-20: listo para revisión

- **Repo definitivo: `rewrite/final3.git`** (bare). develop `f3e822ad`; 954 commits, 195 merges, 6 tags.
  - Sustituye a `final.git` y `final2.git`, que se pueden borrar. El origen de su contenido es `try6`.
  - Cambio respecto a final2: un glifo usado como referencia ("see the ⛔ below") pasa a ser una palabra ("see the
    warning below"), y ninguna línea gana espacio final (era el único fallo de lint).
- **Validado en el lane con una imagen construida desde su Dockerfile** (`f5sign/backend:dev-rewrite`):
  - suite completa `OK (11482 tests, 196694 assertions)`, 0 saltados, deptrac 0 y PHPStan limpio, sobre el árbol
    de `final-wt`;
  - lint `Found 0 of 2863` y PHPStan limpio sobre `final3-wt`;
  - entre los dos árboles, el código PHP es idéntico token a token (solo cambian comentarios).
- Auditorías sobre final3: rastros 0 en contenido y mensajes (los 4 "session:" son `app:session:` y
  `SigningSession::`), autores Daniel 627 y Miguel 327 con committer = autor, ningún par de commits en el mismo
  segundo.
- **Después del push, pendiente**:
  1. reemplazar el checkout local `f5sign-backend` por un clon nuevo y ejecutar `bin/sync-ai.sh`;
  2. avisar a Miguel para que re-clone (y montarle el store `ai/`);
  3. reapuntar el host de prod al historial nuevo, como con infra, y anotar la equivalencia del commit desplegado;
  4. en infra, las 5 referencias a `ghcr.io/dpeite-innatial/f5sign-backend` pasan a `ghcr.io/factorcinco/…`;
  5. regenerar el snapshot OpenAPI del signer (los glifos han salido de las descripciones);
  6. archivar el repo personal y, más tarde, borrarlo; actualizar `repos.manifest`.

---

# CÓMO RETOMAR (leer esto primero)

**Dónde está todo**, en disco y no en temporales, bajo `f5sign/rewrite/` (ignorado por git en la raíz):
- `final3.git`: **el historial nuevo terminado y validado**. Es lo que se pushea.
- `work/`: clon intacto del original, el origen de todo. `try6/`: el original con el contenido ya limpio (fase 1).
- `tools/`: los scripts. `inv/`: las reescrituras de frases. `plan/`: el plan del grafo. `msgs/`: los 954 mensajes
  (`batch_*.out.jsonl`) y su guía (`GUIDE.md`).
- Se pueden borrar: `try1`…`try5`, `build0`…`build2`, `final.git`, `final2.git`, `final-wt`, `cmp/`, `msgs-dummy/`.
- Backups del original: `f5sign/backups/f5sign-backend-pre-purge.git` (espejo de origin) y
  `f5sign/backups/f5sign-backend-local-2026-11-20.bundle` (todas las refs locales).

**Regenerarlo de cero** (todo literal, sin regex; desde `f5sign/rewrite/`):
```
PY=~/.local/share/pipx/venvs/git-filter-repo/bin/python
git clone -q --no-local work tryN && (cd tryN && git branch -q master origin/master; git remote remove origin)
$PY tools/blob_filter.py tryN inv/units2.rewritten.jsonl,inv/overrides.jsonl,inv/spanish.rewritten.jsonl,inv/units_ws.rewritten.jsonl repN
python3 -I tools/inventory.py tryN inv-tryN                      # must give 0 for claude/models/glyphs/innasign
python3 -I tools/graph_extract.py tryN plan/commits.json
# plan/refs.tsv: refs/heads/{develop,master} and refs/tags/* -> sha in tryN (see the earlier for-loop)
python3 -I tools/plan_graph.py plan/commits.json plan/refs.tsv plan   # 954 nodes, 0 violations
python3 -I tools/sha_scan.py work tryN plan/sha_cites.json
git clone -q --no-local tryN buildN && (cd buildN && git branch -q master origin/master; git remote remove origin)
python3 -I tools/build.py buildN plan/plan.json msgs plan/sha_cites.json plan/buildN.json
git init -q --bare finalN.git && git -C finalN.git fetch -q ../buildN 'refs/heads/develop:refs/heads/develop' 'refs/heads/master:refs/heads/master' 'refs/tags/*:refs/tags/*'
```
The messages are keyed by plan node id. The plan is deterministic (`SEED`); if the structure changes (different
knobs or a different content filter), check that the ids still match (`plan.v1.json` vs `plan.json`) before reusing
the messages, or regenerate them with `tools/msg_inputs.py` and Sonnet using `msgs/GUIDE.md`.

**Siguiente paso (necesita al owner):**
1. El owner revisa `final3.git`:
   `git -C rewrite/final3.git log --graph --oneline --date-order develop`.
2. El owner crea el repo vacío en Factorcinco (nombre por confirmar; propuesto `Factorcinco/f5sign-backend`).
3. Push (con el sandbox desactivado; git usa el ssh.exe de Windows):
   `git -C rewrite/final3.git -c core.sshCommand=/mnt/c/Windows/System32/OpenSSH/ssh.exe push <url-nueva> develop master --tags`.
4. Después, la lista "Después del push, pendiente" de arriba: checkout local nuevo + `sync-ai.sh`, Miguel,
   prod, infra ghcr, snapshot del signer, `repos.manifest`, archivar el repo personal.

**Estado del entorno al apagar (2026-11-20):**
- Stack de dev de f5sign **levantado** (`make up`), con la imagen `f5sign/backend:dev` vieja.
- La imagen `f5sign/backend:dev-rewrite` queda (es la de la validación).
- Checkout `f5sign-backend` en `develop` = origin `beb58847`, limpio.
- **Nadie debe pushear al repo personal**, o habrá que rehacer desde `work` con lo nuevo.

## 2026-11-23: checkout local pasado al historial nuevo (sin push)

- Repo destino: `git@github.com:Factorcinco/f5sign-backend.git` (vacío y accesible el 2026-11-23). Antes del corte, el
  personal seguía en develop `beb58847`, sin cambios desde el día 20.
- Copia de seguridad previa: `backups/f5sign-backend-local-2026-11-23.bundle` (`--all`, incluido el stash).
- `f5sign-backend/` en el sitio: develop `f3e822ad`, master `21027e23`, 6 tags; árbol idéntico a `final3.git`;
  `origin` apunta a Factorcinco; refs remotos y stash borrados; reflog expirado y gc hecho, así que el historial
  antiguo ya no está en el `.git` local (solo en `backups/`). `sync-ai.sh` ejecutado: 0 paths con skip-worktree.
- **No pusheado.**
- Pendiente: el push y la lista "Después del push". Las referencias ghcr del historial (`ghcr.io/factorcinco/…`)
  ya cuadran con la org.

### 2026-11-23: push hecho
- Pusheados develop `f3e822ad`, master `21027e23` y los 6 tags a `Factorcinco/f5sign-backend`; upstream configurado.
- Imágenes: el push de develop lanza `:develop`. Los tags NO lanzan el workflow (GitHub omite los eventos si se
  pushean más de 3 tags a la vez): `:v1.0.1`/`:latest` hay que lanzarlos a mano (Run workflow sobre el tag v1.0.1).
- Infra: rama local `chore/backend-image-factorcinco` (`3d2c74e`), sin pushear: compose prod, `BACKEND_REGISTRY`
  y deploy.md pasan a `ghcr.io/factorcinco`. Mergear y desplegar solo cuando el paquete nuevo tenga `:v1.0.1`.
