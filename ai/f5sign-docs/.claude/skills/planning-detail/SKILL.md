---
name: planning-detail
description: Fills in the detailed content of InnaSign MVP planning documents (epics, stories, tasks) that were created by /planning-scaffold. Reads project specifications and populates each document with complete functional context, acceptance criteria (Given/When/Then), technical details (DB schemas, API contracts, file paths), and test specifications. Use when the user wants to fill in planning details, flesh out stories or tasks, or complete PENDIENTE sections. Trigger on "fill detail", "planning detail", "flesh out", "complete story", "complete task", "complete epic", "detail EP", "detail S", "detail T", "detail F", or any reference to filling in PENDIENTE sections in Planning/ documents.
---

# Planning Detail

Fill in the detailed content of planning documents created by `/planning-scaffold`. This skill reads the project specs and populates each planning file with ALL the information a developer or AI needs to implement it — without consulting any other document.

## Reference files

This skill has six reference files. Read them in order BEFORE starting work:

1. **`references/example-story-completed.md`** — A COMPLETE, real example of a fully detailed story (S09.1) and task (T09.1.1). This is the gold standard for format, depth, and tone. Every story and task you produce must match this level of detail. **Read this FIRST.**

2. **`references/architecture-patterns.md`** — Strict rules for Hexagonal Architecture, DDD, TDD, and CQRS. Every task you write must comply with these rules. Includes aggregate roots, layer dependencies, testing order, command bus middleware, and sync vs async rules. **Read this SECOND.**

3. **`references/epic-spec-mapping.md`** — For each epic, lists EXACTLY which spec documents to read. Do not read documents not listed here for the target epic — it wastes context. **Read the section for your target epic.**

4. **`references/cross-cutting-concerns.md`** — Patterns for PlanEnforcement, RLS, SaaS vs Dedicated, i18n, testing, and error handling. These appear in many stories. Include the relevant ones using the short templates provided.

5. **`references/domain-events-catalog.md`** — Complete catalog of MVP domain events with producers and consumers. When a task emits or subscribes to an event, consult this catalog to know all downstream effects. Essential for EventSubscriber tasks.

6. **`references/dev-conventions.md`** — Test factories (names, methods, locations), Definition of Done (task + story level), migration strategy, environment variables by module, TypeScript type contracts for frontend, and smoke tests per phase. Include relevant conventions in each task.

7. **`references/wireframe-conventions.md`** — Conventions for design tasks: complete design system (Tailwind defaults — colors, typography, spacing, components), layout patterns (Dashboard sidebar, Signer mobile-first), inventory of ~48 screens with variants, Pencil file structure, and the special task template for design tasks (type: Diseno). Consult when filling design tasks (T{xx}.{y}.0).

## Invocation

The skill accepts a target argument:

- `/planning-detail F{n}` — Fill ALL epics, stories, and tasks in phase F{n}
- `/planning-detail EP{xx}` — Fill the epic README + ALL its stories + ALL their tasks
- `/planning-detail S{xx}.{y}` — Fill the story README + ALL its tasks
- `/planning-detail T{xx}.{y}.{z}` — Fill only that specific task

When no argument is provided, ask the user what they want to detail.

## Execution steps

### Step 1: Locate target files

Parse the argument and find the corresponding files in `Planning/`.

- Phase: `Planning/F{n}-*/` → all epics, stories, tasks inside
- Epic: `Planning/F*-*/EP{xx}-*/` → epic README + all stories + all tasks
- Story: `Planning/F*-*/EP{xx}-*/S{xx}.{y}-*/` → story README + all tasks
- Task: `Planning/F*-*/EP{xx}-*/S{xx}.{y}-*/T{xx}.{y}.{z}-*.md`

### Step 2: Read the skeleton files

Read the existing skeleton(s) to understand:
- The title, user story, and dependencies
- Which references are listed
- Which tasks exist in the story

### Step 3: Read specification documents

Consult `references/epic-spec-mapping.md` for the target epic. Read ONLY the listed documents and ONLY the sections relevant to the specific story/task you're filling in.

For each spec document you read, extract:
- Data model (table columns, types, constraints, ENUMs)
- API contracts (endpoints, request/response schemas, error codes)
- Business rules (state machines, validation rules, limits)
- UI behavior (interaction flows, component structure)
- Notification triggers (which domain events trigger which notifications)

### Step 4: Fill in content

Replace ALL `{PENDIENTE — sera rellenado por /planning-detail}` sections. Never leave any section as PENDIENTE.

Follow the format rules below. For the exact level of detail expected, refer to `references/example-story-completed.md`.

## Format rules for stories

### "Contexto funcional" section

This must be COMPLETELY SELF-CONTAINED. A developer reading only this story file must understand everything needed. Include:

1. **What the thing is** — 2-3 sentences explaining the concept
2. **Business rules** — every rule, explicit, not summarized
3. **State machines** — if applicable, ALL transitions with triggers
4. **Data model** — tables and columns relevant to this story (name, PHP type, DB type, nullable, default, constraint)
5. **API contract** — if the story has an endpoint:
   - Method + path
   - Complete request JSON schema with types and descriptions
   - Complete response JSON schema
   - Error table (HTTP status, error code, when it happens)
   - Required and optional headers
6. **UI behavior** — if frontend is involved, step-by-step interaction flow
7. **SaaS vs Dedicated** — only if there are actual differences (use template from cross-cutting-concerns.md)
8. **PlanEnforcement** — only if the story creates limited resources (use template from cross-cutting-concerns.md)
9. **Edge cases** — document how they should be handled
10. **Security** — auth requirements, input validation, OWASP concerns

### "Criterios de aceptacion" section

Use numbered prefixes `AC-01`, `AC-02`, etc. for each criterion. This makes them cross-referenceable from tasks and tests.

Write Given/When/Then covering AT MINIMUM:
- Happy path with concrete example values and JSON bodies
- Each validation error (missing field, wrong type, out of range)
- Auth failure (no token, expired token)
- Authorization failure (wrong role)
- Business rule violation (quota, invalid state)
- At least one edge case
- Tenant isolation (if applicable)
- Idempotency (if the endpoint supports it)

Each criterion must be specific, testable, and use concrete values. See the example in `references/example-story-completed.md`.

Format:
```
### AC-01 — {Nombre descriptivo del criterio}
- **Given** ...
  **When** ...
  **Then** ...
```

## Format rules for tasks

### Task header fields (Complejidad, Tags, Repo)

Every task header must set these fields explicitly (no PENDIENTE):

- **Repo:** one of `f5sign-backend | f5sign-dashboard | f5sign-signer | f5sign-infra | f5sign-docs`. This is set by `/planning-scaffold` at skeleton time following the mapping rules in `planning-scaffold/references/templates.md` § "Asignacion de Repo a cada task". `/planning-detail` MUST preserve this value and use it as context to: (a) pick correct file path conventions (Symfony vs Nuxt vs Docker), (b) include the right test framework in the Tests section (PHPUnit vs Vitest/Playwright), (c) reference only file paths that live inside the task's target repo. If the value is missing or set to a placeholder, infer it from the `Tipo:` and story path using the mapping rules, fill it in, and continue.

- **Complejidad:** one of `baja | media | alta`. Used by the execution orchestrator (`task-runner`) to route implementation between Sonnet (baja/media) and Opus (alta). Use `alta` for: crypto, digital signature logic (PAdES/XAdES/CAdES/LTV), eIDAS compliance, RLS policy design, state machines with >3 states, complex concurrency/idempotency, multi-aggregate coordination. Use `baja` for: simple CRUD, DTOs, fixtures, config files, plain migrations without RLS. Everything else is `media`.
- **Tags:** CSV of semantic tags. Used by `task-runner` to decide which validation skills to invoke. Canonical tags (use these when applicable):
  - `db` (any schema/migration work), `migration` (dedicated migration file), `rls` (touches RLS policies)
  - `api` (HTTP endpoint), `event` (emits/subscribes domain events), `worker` (async message handler)
  - `signing`, `crypto`, `eidas` (any signature/crypto/compliance concern — triggers eidas-compliance skill)
  - `ui`, `i18n` (frontend strings)
  - `state-machine`, `idempotent`, `critical-path` (perf-sensitive)
  - `tenancy` (multi-tenant isolation concern)

Add additional free-form tags only if they help downstream skills. Do NOT invent synonyms of the canonical ones.

### "Contexto requerido" section

This section is consumed by the `task-runner` orchestrator (and specifically the `task-kickoff` skill) to load the minimum sufficient context into the implementation agent. It must be explicit, exhaustive for THIS task, and contain no prose — only pointers.

Structure it with these subsections (omit subsection if empty, never leave PENDIENTE):

```markdown
## Contexto requerido

### Specs del proyecto
- `Especificaciones/<file>.md` § <anchor or heading> — <why it's needed>

### ADRs y decisiones
- **Backend (`f5sign-backend`): los ADR in-repo de `docs/adr/` son la autoridad.** Antes de escribir rutas/patrones de una task de backend, leer el índice `f5sign-backend/docs/adr/README.md` y los ADR aplicables. **Si un ADR contradice esta spec o las plantillas de rutas de abajo, manda el ADR** (ver "Architecture compliance"). Citar el ADR por su ruta in-repo (p. ej. `f5sign-backend/docs/adr/ADR-0009-observability-at-the-boundary.md`).
- `memory/project_cloud_signing_decisions.md` — <which decisions apply>
- (otros ADRs/decisiones si existen)

### Tareas previas (ya implementadas de las que depende)
- `Planning/F{n}-*/EP{xx}-*/S{xx}.{y}-*/T{xx}.{y}.{z}-*.md` — <what this task reuses/extends>

### Código existente a consultar
- `src/<path>/<File>.php` — <what pattern or class to follow>
- `tests/<path>/<File>Test.php` — <test pattern to mirror>

### Eventos de dominio involucrados
- `<EventName>` (producer / consumer) — see `domain-events-catalog.md`

### Contratos externos
- OpenAPI: `docs/openapi/<file>.yaml` § <path>
- AsyncAPI: `docs/asyncapi/<file>.yaml` § <channel>
```

Rules for filling this section:

1. **Be surgical.** Only list what is actually needed to implement THIS task. Do not dump the whole epic's specs.
2. **Every entry must include a reason** after the `—`. A bare path is not acceptable.
3. **Use section anchors or headings** when referring to a spec (e.g., `§ "Estados del envelope"`), not just the filename.
4. **If the task has no prior-task dependencies**, write `- Ninguna` under that subsection, don't omit it silently.
5. **Do NOT list** generic references (architecture-patterns, dev-conventions) — those are loaded by every skill by default.
6. **Keep it under ~15 bullets total.** If you need more, the task is too big and should be split.

### "Archivos a crear/modificar" section

Table with EVERY file, its action (Crear/Modificar), and a brief description. File paths must follow the conventions in `Arquitectura/Patrones de Código y Convenciones.md`:

```
src/{Module}/Domain/Entity/{Name}.php
src/{Module}/Domain/ValueObject/{Name}.php
src/{Module}/Domain/Event/{Name}{PastVerb}.php
src/{Module}/Domain/Exception/{Name}Exception.php
src/{Module}/Domain/Repository/{Name}RepositoryInterface.php
src/{Module}/Application/Command/{UseCase}/{Verb}{Noun}Command.php
src/{Module}/Application/Command/{UseCase}/{Verb}{Noun}Handler.php
src/{Module}/Application/Query/{Module}QueryService.php
src/{Module}/Application/Query/DTO/{Noun}Response.php
src/{Module}/Application/EventSubscriber/{Action}On{Event}.php
src/{Module}/Infrastructure/Persistence/Doctrine{Name}Repository.php
src/{Module}/Infrastructure/Persistence/Mapping/{Name}.orm.xml
src/{Module}/Infrastructure/Http/Controller/{Name}Controller.php
tests/Unit/{Module}/Domain/Entity/{Name}Test.php
tests/Integration/{Module}/Application/Command/{UseCase}/{Handler}Test.php
tests/E2E/{Module}/Infrastructure/Http/Controller/{Name}ControllerTest.php
```

### "Detalle tecnico" section

Include ALL of the following that apply to this task:

**Domain entities/VOs:**
- Complete property table (name, PHP type, DB type, nullable, default, constraint)
- ALL enum values with descriptions
- State machine transitions (from, to, trigger, side effects)
- Domain events (name, every payload property with type)
- Invariants (business rules validated in the entity)

**Commands/Handlers:**
- Command properties (name, type, nullable, validation constraints)
- Handler steps (numbered: 1. check plan, 2. load aggregate, 3. execute, 4. persist, 5. dispatch events)
- Which domain events are dispatched
- Transaction boundary notes

**Controllers:**
- HTTP method, route pattern, route name
- Request validation constraints (Symfony #[Assert\*])
- Response DTO fields
- Middleware: auth required? rate limited? idempotent?

**Frontend (Pinia stores, components, pages):**
- Store: state properties with types, actions, getters
- API calls: composable name, method, URL, request/response TS types
- Components: props, emits, slots
- Route: path, name, middleware

**Migrations:**
- Complete CREATE TABLE SQL
- All indexes (CREATE INDEX)
- RLS policy (CREATE POLICY)
- ENUM types if new

**Workers:**
- Queue name, message DTO properties, handler steps, retry config, error handling

**Wireframe tasks (type: Diseno):**
- List of screens to create with Pencil page names and variants (Desktop/Mobile)
- For each screen: detailed list of UI elements, components, states, and interactions
- Data examples (realistic, not lorem ipsum)
- Reference to wireframe-conventions.md for Pencil structure and naming
- Acceptance criteria specific to the wireframe (screens created, variants, components visible)

### "Tests" section

Table with EVERY test:

| Test name | Type (Unit/Integration/E2E) | File path | What it verifies |

Include:
- Unit tests for every domain entity, VO, and domain service method
- Integration tests for every command handler
- E2E tests for every controller endpoint (happy + error paths)
- Each test must be specific enough to write without further research

## Anti-fabrication: verify before you reference

When filling `Contexto requerido` (or any section that references other files, tasks, specs, section anchors, or code paths), **NEVER invent plausible-sounding names**. Fabricated references are a silent failure mode — they look correct but break the `task-runner`, linters and humans downstream.

### Hard rules

1. **Never invent a Planning path.** Before writing `Planning/F<n>-*/EP<xx>-*/S<xx>.<y>-*/T<xx>.<y>.<z>-*.md`:
   - For references inside the target epic, only cite tasks you have seen in the scaffold.
   - For cross-epic references, verify the real epic + story + task names with `ls Planning/F*-*/` / Glob, or consult the phase README which lists canonical epic IDs and names.
   - Wildcards like `.../S<xx>.<y>-*/T<xx>.<y>.<z>-*.md` are OK, but the task ID must be real.

2. **Never invent a spec filename.** The canonical specs live under `Arquitectura/` and `Arquitectura/Pilares/`. Before referencing:
   - Consult `references/epic-spec-mapping.md` — it lists authoritative specs per epic.
   - For anything outside that mapping, list the real `Arquitectura/` directory via Glob/Bash **before** writing the reference.
   - **Common fabrications to NEVER use** (these do not exist; use the real counterpart):

     | Do NOT write | Real spec |
     |---|---|
     | `Arquitectura/Patrones arquitectonicos.md` | `Arquitectura/Patrones de Código y Convenciones.md` |
     | `Arquitectura/Mapa de Modulos.md` | `Arquitectura/Mapa de Módulos - Bounded Contexts.md` |
     | `Arquitectura/Integracion con EU DSS.md` | `Arquitectura/EU DSS - Guía de Integración.md` |
     | `Arquitectura/Observabilidad y Monitorizacion.md` | `Arquitectura/Pilares/7. Infraestructura y Compliance.md` § E |
     | `Arquitectura/Multi-tenancy y RLS.md` | `Arquitectura/Pilares/7. Infraestructura y Compliance.md` § C.1 (or ERD § 1) |
     | `Arquitectura/Seguridad y Cumplimiento Normativo.md` | `Arquitectura/Pilares/7. Infraestructura y Compliance.md` § D |
     | `Arquitectura/Diseño visual y UX.md` | `Arquitectura/Arquitectura Frontend.md` |

3. **Never invent a section anchor.** If you write `<file>.md § <anchor>`, the anchor must match a real heading:
   - Open the file with Read and confirm the heading, OR
   - Use numeric notation (`§3`, `§4.1`, `§A.2`) matching the spec's own numbering, OR
   - Omit the anchor — a bare filename is acceptable.

4. **Never invent class names, interface names, or file paths in `src/`.** Every `src/<path>/<File>.php` you reference must either exist (from a prior task) or be about to be created by a known task. If neither is verifiable, do not write it.

5. **When you cannot verify, flag it.** Use `[NEEDS CLARIFICATION: <precise description of what cannot be verified and why>]` inline. Never substitute a plausible guess.

### Canonical epic IDs

Before referencing any epic, the IDs and slugs are listed in `Planning/README.md` (master index) and in each phase's `Planning/F<n>-*/README.md`. Do **not** paraphrase the slug from memory — copy it literally. Common fabrications include: `EP02-Symfony-y-Base-de-Datos` (real: `EP02-PostgreSQL-Schema-Base-y-Enums`), `EP03-Multi-tenancy-y-RLS` (real: `EP03-Mensajeria-y-Cache`), `EP04-MinIO-S3` (real: `EP04-EU-DSS-y-Almacenamiento`), `EP06-EU-DSS` (real: `EP04-EU-DSS-y-Almacenamiento`), `EP05-RabbitMQ-Messenger` (real: `EP03-Mensajeria-y-Cache`).

---

## Handling missing or ambiguous information

When a spec document is missing data for a field you need to fill (e.g., a column type not in the ERD, an endpoint not fully specified), do NOT stop or guess silently. Instead:

1. Mark the gap inline with `[NEEDS CLARIFICATION: description of what is missing]`
2. Continue filling the rest of the content
3. At the end of each completed epic, add a section `## Items pendientes de clarificacion` listing ALL flagged items

This keeps the work flowing while surfacing gaps for the user to resolve.

## Self-verification checklist

After completing each story (README + all tasks), verify against this checklist before moving to the next:

- [ ] No `PENDIENTE` text remains anywhere in the story or its tasks
- [ ] Every task has `Complejidad` set (baja/media/alta) and non-empty `Tags`
- [ ] Every task has a filled `Contexto requerido` section with a reason on each bullet
- [ ] All enum values are listed completely (not "etc." or "...")
- [ ] All table columns from the ERD relevant to this story are present
- [ ] All API error codes include both HTTP status AND application error code
- [ ] All JSON schemas (request/response) are complete — no abbreviated fields
- [ ] All tasks have a Tests section with at least one test per file created
- [ ] All file paths follow the conventions in `references/architecture-patterns.md`
- [ ] Acceptance criteria use `AC-xx` prefixes
- [ ] Domain entities never import Infrastructure or Application (hexagonal rule)
- [ ] Repositories exist only for Aggregate Roots, never for subordinate entities
- [ ] The handler step order follows CQRS pattern (check plan → load → execute → persist → dispatch)
- [ ] TDD is reflected: test files are listed alongside (or before) implementation files

If any check fails, fix it before moving on.

## Final verification: path linter

After completing an epic (all stories + all tasks filled in), run this linter to catch fabricated references. Paths to Planning epics and `Arquitectura/*.md` specs must all resolve to files that actually exist.

```bash
python3 <<'PY'
import re, os, glob, sys

REAL_EPICS = set()
for d in glob.glob("Planning/F*-*/EP*-*/"):
    REAL_EPICS.add(os.path.basename(os.path.dirname(d)))

REAL_ARQ = set()
for root, _, files in os.walk("Arquitectura"):
    for f in files:
        if f.endswith(".md"):
            REAL_ARQ.add(os.path.join(root, f).replace("\\", "/"))

ep_re  = re.compile(r'Planning/F\d+-[A-Za-z\-]+/(EP\d+-[A-Za-z0-9\-]+)')
arq_re = re.compile(r'Arquitectura/[A-Za-z0-9 \-áéíóúÁÉÍÓÚñÑ.]+\.md')

target = sys.argv[1] if len(sys.argv) > 1 else "Planning/"
issues = 0
for path in glob.glob(f"{target}/**/*.md", recursive=True):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    for m in ep_re.finditer(content):
        if m.group(1) not in REAL_EPICS:
            print(f"FABRICATED EPIC: {path} → {m.group(1)}"); issues += 1
    for m in arq_re.finditer(content):
        if m.group(0) not in REAL_ARQ:
            print(f"FABRICATED SPEC: {path} → {m.group(0)}"); issues += 1

print(f"\n{issues} fabricated reference(s) found." if issues else "\nOK: no fabricated references.")
sys.exit(1 if issues else 0)
PY
```

**Pass condition:** exit code 0 with `OK: no fabricated references.`
**If it finds issues:** fix each one (use a real epic slug or a real spec filename) before considering the epic done. The linter is **blocking** — do not stop until it passes.

## Architecture compliance

Every task you write must comply with `references/architecture-patterns.md`. Specifically:

- **Hexagonal**: Domain files never import Symfony, Doctrine, or any framework. Repository interfaces go in Domain, implementations in Infrastructure.
- **DDD**: Only Aggregate Roots have repositories. Subordinate entities are modified through their Aggregate Root. VOs are `final readonly` with private constructors. Domain Events use past tense names.
- **TDD**: In the "Orden de implementacion" note of each task, tests come FIRST. The task description should reflect: write test → run (fails) → write code → run (passes).
- **CQRS**: Commands go through the bus (sync or async). Queries are called directly. Controllers only inject CommandBusInterface and QueryService.

### Backend: los ADR in-repo mandan sobre estas plantillas y sobre los Pilares

`f5sign-backend` es el prototipo "Innasign", con arquitectura propia (capas `src/Innasign/{Kernel,Foundation,<BC>}/`, Deptrac estricto, **sin capa `Shared/Infrastructure`**) documentada en sus **ADR in-repo** (`f5sign-backend/docs/adr/`, índice `README.md`). Esos ADR son la **fuente de verdad del "qué/forma"** y **mandan sobre**: (a) las plantillas de rutas genéricas `src/{Module}/...` de este skill (ilustrativas), y (b) las specs derivadas de los Pilares cuando haya conflicto (regla "Arquitectura/DDD > Pilares").

Al **definir/detallar** una task de backend:
1. Leer `f5sign-backend/docs/adr/README.md` y abrir los ADR que toquen el área de la task.
2. Escribir `Archivos a crear/modificar` y `Detalle técnico` con las **rutas y patrones reales del repo** (`src/Innasign/Foundation/...`, etc.), no con las plantillas genéricas si difieren.
3. Si la spec original (heredada de los Pilares) contradice un ADR, **adaptar la spec al ADR** y dejar nota de la divergencia.

Precedente: **EP27 (Observabilidad)** se adaptó a **ADR-0009 / ADR-0021** (commit `eb569b1`) — rutas `Innasign/Foundation/Observability`, 3 health endpoints fuera de `/api`, redacción PII type-driven, Sentry edge-only.

## Important rules

- NEVER leave any section as PENDIENTE after your work
- Copy information from specs, don't summarize — precision matters
- Include ALL enum values, not just examples
- Include ALL table columns relevant to the story, not a subset
- Request/response JSON schemas must be complete, not abbreviated
- Error codes must include HTTP status AND application error code
- No placeholder values, no "e.g." as the only example, no "..." in schemas
- When filling an epic, work through stories in order (S{xx}.1, S{xx}.2, ...)
- When filling a story, work through tasks in order (T{xx}.{y}.1, T{xx}.{y}.2, ...)
- If you discover a missing story or task needed to cover a feature, add a section "## Stories faltantes" or "## Tasks faltantes" at the bottom — do NOT create new files
- Always verify your content against the ERD and spec docs — if a column name or type differs from the ERD, the ERD is the source of truth
- For **backend tasks**, the implementation repo's in-repo ADRs (`f5sign-backend/docs/adr/`) are authoritative for file paths and patterns and **override** both the generic `src/{Module}/...` templates here and any Pilares-derived spec they conflict with — read them before detailing (see "Architecture compliance" → "Backend: los ADR in-repo mandan")
