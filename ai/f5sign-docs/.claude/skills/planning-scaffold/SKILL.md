---
name: planning-scaffold
description: Generates the complete Planning/ directory structure for InnaSign MVP with all phases, epics, stories, and tasks as skeleton markdown files. Use this skill when the user wants to create or regenerate the project planning scaffolding, set up the task breakdown structure, or initialize the Planning/ folder. Trigger on mentions of "scaffolding", "planning structure", "task breakdown", "create planning", "generate epics", "generate stories", or anything about creating the planning folder.
---

# Planning Scaffold

Generate the complete `Planning/` directory structure for the InnaSign MVP. This creates skeleton markdown files at every level — phases, epics, stories, and tasks — following strict templates and a deterministic breakdown.

The detailed content (functional context, acceptance criteria, technical specs) is filled in later by the `/planning-detail` skill. This skill ONLY creates the skeleton structure.

## Reference files

This skill has two reference files that you MUST read before executing:

1. **`references/templates.md`** — The EXACT format templates for each file type (phase README, epic README, story README, task .md). Also contains naming conventions, task decomposition patterns, and story point calibration. **Read this FIRST.**

2. **`references/stories-breakdown.md`** — The COMPLETE and DETERMINISTIC list of all stories and tasks to create. Do NOT invent additional stories or tasks. Do NOT omit any. This is the single source of truth for what to scaffold. **Read this SECOND.**

## Execution steps

### Step 0: Pre-flight check
Before creating anything, check if `Planning/` already exists in the project root.
- If it exists AND contains files: warn the user and ask whether to overwrite, merge, or abort. Do NOT proceed without confirmation.
- If it does not exist: proceed normally.

### Step 1: Read reference files
Read `references/templates.md` and `references/stories-breakdown.md` completely. These define WHAT to create and HOW to format it.

### Step 2: Read project docs for context
Read these files to understand the project — you need them for writing accurate user stories, dependency mapping, and bounded context assignment:

1. `Checklist Funcionalidades.md` — verify all 83 MVP features are covered
2. `Arquitectura/Mapa de Módulos - Bounded Contexts.md` — map epics to bounded contexts
3. `Arquitectura/Patrones de Código y Convenciones.md` — verify file path conventions
4. `Implementación/Contexto de Desarrollo MVP.md` — team and constraints context

### Step 3: Create directory structure
Create ALL directories and files listed in `references/stories-breakdown.md`, using the templates from `references/templates.md`.

**Order of creation:**
1. `Planning/README.md` (master index)
2. For each phase F0 through F5:
   a. Phase `README.md`
   b. For each epic in the phase:
      - Epic `README.md`
      - For each story in the epic:
        - Story folder + `README.md`
        - All task `.md` files inside the story folder

### Step 4: Fill in skeleton content
For each file created, fill in:
- **All metadata** (IDs, story points, dependencies, tipo, **repo**)
- **Repo assignment** (`Repo:` field in task headers and `Repo` column in story task tables) — apply the mapping rules in `references/templates.md` § "Asignacion de Repo a cada task". One task = one repo. Never leave this field empty.
- **User stories** (Como/Quiero/Para) — these should be meaningful, not generic
- **Bounded context mapping** for each epic
- **MVP feature checklist** for each epic (copied from Checklist Funcionalidades.md)
- **References section** with correct relative links to spec documents
- **Task tables** in each story README with summary info
- **Smoke tests section** in each phase README (copy from planning-detail's references/dev-conventions.md section 6)
- **Definition of Done** in the master Planning/README.md (copy from planning-detail's references/dev-conventions.md section 2)

Leave these sections as `{PENDIENTE — sera rellenado por /planning-detail}`:
- "Contexto funcional" in story READMEs
- "Criterios de aceptacion" in story READMEs
- "Archivos a crear/modificar" in task .md files
- "Detalle tecnico" in task .md files
- "Tests" in task .md files

### Step 5: Verify completeness
After creating all files:
- Count stories and tasks — they must match `references/stories-breakdown.md` exactly
- Verify all dependency references (Depende de / Bloquea) point to valid IDs
- Verify story point totals roll up correctly (tasks → stories → epics → phases)
- Verify every MVP feature from the checklist is mapped to at least one epic
- Verify all relative links in References sections are valid paths

## Handling uncertainties

When something in `references/stories-breakdown.md` is ambiguous or a dependency ID doesn't resolve clearly, do NOT stop execution. Instead:

1. Mark the issue inline with `[NEEDS CLARIFICATION: description of the issue]`
2. Continue creating the rest of the files
3. At the end, list ALL flagged items in the master `Planning/README.md` under a section `## Items pendientes de clarificacion`

This keeps the scaffold complete while surfacing issues for the user to resolve.

## Design tasks

For every story that contains frontend tasks with significant UI (pages, complex components, multi-step flows), the scaffold MUST add a design task as the FIRST frontend task of the story. This is the ONE exception to the "do not add tasks beyond the breakdown" rule.

Read `planning-detail/references/wireframe-conventions.md` to understand:
- Which stories need designs (and which don't) — section 5
- The complete inventory of ~48 screens — section 10
- Which screens need state variants (empty, error) — section 6
- The naming convention and template format — sections 7-9

Design task naming: `T{xx}.{y}.0 — Diseno: {descripcion}` (use .0 to keep it before other tasks).
Type: `Diseno`. Story points: typically 2-3 pts. These are final designs (not wireframes) created with Pencil MCP, using Tailwind defaults as design system.

## Important rules

- Do NOT add stories or tasks beyond what is listed in `references/stories-breakdown.md` — EXCEPT wireframe tasks as described above
- Do NOT omit any story or task from the breakdown
- Every task MUST carry a `Repo:` value (`f5sign-backend`, `f5sign-dashboard`, `f5sign-signer`, `f5sign-infra`, `f5sign-docs`) and the story README table MUST include the matching `Repo` column. See `references/templates.md` § "Asignacion de Repo a cada task"
- A task that would touch more than one repo MUST be split into separate tasks at scaffold time
- Do NOT fill in PENDIENTE sections — that is the job of `/planning-detail`
- Folder names use kebab-case without accents: `Autenticacion` not `Autenticación`
- Story points come from the breakdown file — do not re-estimate
- Dependencies must reference valid IDs that exist in the breakdown
- Each epic README must list which MVP features from the checklist it covers
- The master README must have working relative links to all epics
- Acceptance criteria placeholders in story READMEs should use prefix `AC-xx` (e.g., `AC-01`, `AC-02`) so `/planning-detail` fills them with numbered identifiers
