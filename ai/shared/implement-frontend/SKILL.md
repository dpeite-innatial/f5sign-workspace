---
name: implement-frontend
description: Implements a frontend task (Nuxt 3 + Vue 3 + TypeScript + Tailwind + Pinia) from Planning/ following TDD (Vitest for unit/component, Playwright for E2E), respecting the pages/composables/components separation and i18n and design system conventions. Reads the task's .md and its Contexto requerido, writes code + tests, and produces context-digest.md, plan.md artifacts and a single final commit. Frontend repositories only. Use with /implement-frontend T{id}. Trigger with "implement frontend T{id}", "code Vue task...", "implement component...".
---

# Implement Frontend

TDD implementation of a frontend task. The model is chosen based on `Complejidad` (Sonnet for low/medium, Opus for high).

## Invocation

```
/implement-frontend T{id}
/implement-frontend T{id} --model=opus
/implement-frontend T{id} --amplified-context
```

## Inputs

- Task `.md`
- Files listed in `## Contexto requerido`
- ⚑ **Pending backend handoffs: `../f5sign-backend/docs/frontend-handoff/*.md`.** A contract change in the
  backend and its adoption here are **two PRs** (workspace rule 4: two projects, two coordinated PRs),
  so that directory is the only place where *what changed and what needs to be done in this repo* is
  written. Each file names its source commit — compare it against what's already applied to know
  if you're behind — and read its *"What is NOT ready yet"* section **before** building against an
  endpoint: half the value of that document is stopping work against an incomplete seam.
  If the directory is not reachable (access to this repo only), **ask the user for the handoff file**
  instead of inferring the contract; and types are regenerated from OpenAPI, which is the machine-readable
  source of truth, never by hand from the handoff prose.
- If `--amplified-context`: parent story README + parent epic README + dependencies' `.md` + event catalog if applicable
- Fixed references: `Arquitectura/Arquitectura Frontend.md`, `.claude/skills/planning-detail/references/wireframe-conventions.md`
- `tailwind.config.ts` (canonical tokens)

## Outputs

- Code + tests committed (1 single commit) on branch `feat/T{id}-*`
- `var/task-runner/T{id}/plan.md`
- `var/task-runner/T{id}/context-digest.md`
- JSON: `{"status":"pass|fail","summary":"...","filesChanged":N,"testsAdded":N,"attempts":N,"diagnosis":"..."}`

## Execution

### Step 1 — Load context

1. Read the task's `.md` in full
2. Read files from `## Contexto requerido`
3. Read fixed references (frontend architecture + wireframe conventions)
4. Read `tailwind.config.ts` to learn tokens
5. If the project has types generated from OpenAPI (e.g. `types/api.ts` or similar): read them if the task consumes endpoints

### Step 2 — Plan

Draft `var/task-runner/T{id}/plan.md` with TDD order. If you detect unresolvable ambiguity:
- diagnosis = "contradictory spec" or "insufficient context" → `status: fail` without implementing

### Step 3 — TDD loop

For each entry in the `## Tests` table:

1. Write the test (Vitest unit/component or Playwright E2E as appropriate)
   - Include `AC-xx` in the test name
   - Components: use `@vue/test-utils` with `mount`/`shallowMount`
   - Composables: isolated tests passing store mocks
   - Pinia stores: tests with `createTestingPinia()`
2. Run the test → it must fail for the right reason
   - `npm run test:unit -- {path}`. ⛔ E2E specs may be WRITTEN, but never run here: E2E is manual only,
     at the user's explicit request (owner, 2026-09-23). Say which E2E specs were written/changed.
3. Write minimal production code
4. Run the test → green
5. Run module/feature tests to avoid introducing regressions

**Retry and escalation policy:** same as implement-backend (3 attempts with the assigned model + diagnosis + 3 Opus attempts with amplified context if the diagnosis justifies escalating).

### Step 4 — Non-negotiable rules

#### Layer architecture
- **Pages (`pages/`)**: orchestrate. Call composables, render components. NO business logic.
- **Composables (`composables/`)**: usage layer. Encapsulate state + API + side effects. Return reactive `{ state, actions, getters }`.
- **Components (`components/`)**: presentational. Receive props, emit events. Do NOT import stores or fetch directly (except specific clearly documented "container" components).
- **Stores (`stores/`)**: typed Pinia stores with state/actions/getters.

Violation → redo before continuing.

#### TypeScript strict
- No `any` (if unavoidable, comment the reason and use `unknown` + narrowing)
- No `@ts-ignore` unless documented justification
- `defineProps<T>()` with an explicit interface
- `defineEmits<{(e: 'eventName', payload: T): void}>()`
- API responses use types generated from OpenAPI (if the project has that tooling)

#### i18n
- No hardcoded strings in templates. Everything goes through `$t('key')` / `useI18n().t()`
- Translation keys are added to the project's `locales/*.json` / `i18n/*.json` files
- Date/number formats with `$d()` / `$n()`, not direct `toLocaleString`

#### Tailwind / Design system
- Use design system classes (colors `primary-*`, spacing `xs/sm/md/...`, etc. defined in `tailwind.config.ts`)
- Avoid arbitrary values `[13px]`, `[#ff5733]`. If unavoidable, comment the reason
- Reuse the system's base components (Button, Input, Modal per wireframe-conventions) instead of reimplementing

#### Basic accessibility (the exhaustive check is done by `a11y-check`)
- `<label>` associated with each input
- `alt` on every `<img>` (empty if decorative)
- Real buttons (`<button>`) instead of `<div role="button">`
- Visible focus (no `outline: none` without a replacement)
- Coherent `tabindex`

#### Tests
- Vitest for unit (utils, composables) and component (@vue/test-utils)
- Playwright for E2E (critical flows)
- Every applicable AC covered by at least 1 test

### Step 5 — If it consumes an API

- If the task has tag `api`: verify that the composable/store calling the backend:
  - Uses types generated from OpenAPI (if the project has `openapi-typescript` configured)
  - Handles all error codes declared in the AC (does not silently ignore 4xx)
  - Cancels pending requests on component unmount (AbortController)

### Step 6 — Commit consolidation

1. Verify `git status`: files declared in `## Archivos a crear/modificar` are present
2. If there are extras: document in `plan.md § Desviaciones`
3. If declared files are missing: FAIL
4. `git add <touched-files>`
5. Single commit:
   ```
   feat(T{id}): {task title}
   
   {2-3 line summary}
   ```
6. `git diff {base}..HEAD > var/task-runner/T{id}/changes.diff`

### Step 7 — context-digest.md

Write `var/task-runner/T{id}/context-digest.md` (≤ 150 lines), adapted for frontend:

```markdown
# Context Digest — T{id}

## Task summary
{2-3 lines: what was implemented}

## Routes / pages affected
- /path/route — new / modified

## Components touched
- components/Button.vue — new props, emits
- components/SignerCard.vue — new component

## New / modified composables
- composables/useEnvelopes.ts

## Pinia stores
- stores/envelope.ts — `closeEnvelope` action added

## Endpoints consumed
- POST /api/v1/envelopes/{id}/close
  - Types: request CloseEnvelopeRequest, response EnvelopeResponse (generated)

## Events emitted / listened to
- `envelope:closed` (internal emit via event bus), `push:envelope.closed` (websocket)

## i18n keys added
- envelope.actions.close
- envelope.errors.alreadyClosed

## Decisions made during implementation
- {decision + why}

## Scope outside this task
- ...
```

### Step 8 — plan.md § Final status

Update the final section of `plan.md`:
```
## Final status
- New tests: N (all green)
- Module suite: PASS
- Build: PASS (vite build)
- Files modified: N
- Deviations documented: {yes|no}
```

### Step 9 — Return JSON

```json
{"status":"pass","summary":"T{id} implemented, N tests green, 1 commit","filesChanged":N,"testsAdded":N,"attempts":N}
```

## What it does NOT do

- Does not run exhaustive a11y validation (`a11y-check`)
- Does not validate design system coherence (`design-system-check`)
- Does not validate API contracts (`contract-check-frontend`)
- Does not audit security (`security-audit-core` + `security-audit-frontend`)
- Does not measure performance (`perf-smoke-frontend`)
- Does not update external docs (`docs-sync`)
- Does not open a PR or update the `.md`

## References

- Full design: `Implementación/Skills de Ejecución de Tareas/frontend/01 - Implement Frontend.md`
- Architecture: `Arquitectura/Arquitectura Frontend.md`
- Wireframes and design: `.claude/skills/planning-detail/references/wireframe-conventions.md`
