---
name: task-validate-frontend
description: 'Hard functional-quality gate on frontend (Nuxt 3 + Vue 3 + TypeScript): runs npm run lint, type-check (vue-tsc), unit/component tests (Vitest), build (vite), validates minimum 80% coverage, and verifies that the story ACs are covered by tests. Frontend repositories only. Use with /task-validate-frontend T{id}. Trigger with "validate frontend task", "run vitest", "check Vue/TS tests".'
---

# Task Validate Frontend

Hard functional-quality gate on frontend. Always invoked in a frontend repo.

## Invocation

```
/task-validate-frontend T{id}
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- Task `.md`
- Parent story README (for AC)

## Outputs

- `var/task-runner/T{id}/validate.report.md`
- `var/task-runner/T{id}/test-results.json` (structured Vitest output)
- JSON: `{"status":"pass|fail","summary":"...","issues":[...],"acCovered":[...],"acFailed":[],"coverage":0.87}`

## Precondition

Nothing beyond the repo's own test harness: this gate does not run E2E (Step 5).

## Execution

### Step 1 — Lint

```bash
npm run lint -- --format=json
```

- [ ] Exit code 0
- [ ] No errors (warnings allowed under a low threshold, e.g. ≤3)

If lint is configured with automatic `--fix`: do NOT run it here (validate only, do not modify). Lint should have been done by `implement-frontend`.

### Step 2 — Type check

```bash
npm run type-check
```

Equivalent to `vue-tsc --noEmit` or similar depending on the project.

- [ ] Exit code 0
- [ ] No new errors in diff files

### Step 3 — Unit + component tests

```bash
npm run test:unit -- --reporter=json --coverage --coverage-reporter=clover
```

- [ ] Exit code 0
- [ ] Number of tests run = tests declared in the `.md`'s `## Tests` table
  - Negative diff → FAIL
  - Positive diff → WARN

Parse the JSON output, extract:
- Total tests, passed, failed, skipped
- Tests covering each `AC-xx` (grep in names/DocBlocks)

### Step 4 — Coverage

- Coverage of new/modified lines (from the diff)
  - Parse clover.xml + cross-reference with diff lines
- Threshold: **80%** (no exceptions)
  - < 78% → FAIL
  - 78-80% → WARN
  - ≥ 80% → pass

### Step 5 — E2E tests: NOT run by this gate

⛔ **E2E is manual only** (owner, 2026-09-23): never launched while developing or validating a task — a full run is ~15 min and every browser on the machine. It runs only when the user explicitly asks for it.

- Do not run Playwright, not even for `critical-path` or when the `.md` declares E2E tests.
- If the task wrote or changed E2E specs, list them in the report as **"written, not run"** so the user
  can decide to run them by hand (`make test-signer-e2e` / `make wt-signer-e2e src=<path>`).
- An AC covered only by an E2E spec is reported as covered-by-spec-not-run, never as a failure.

### Step 6 — Build

```bash
npm run build
```

- [ ] Exit 0 (code compiles cleanly in production mode)
- [ ] No critical build warnings

### Step 7 — AC coverage

For each `AC-\d+` applicable to the task:
- [ ] There is at least one test whose name or DocBlock includes `AC-{xx}`
- [ ] The test has run and passes

List `acCovered` / `acFailed` / `acUncovered`.

### Step 8 — Declared vs actual files

- Parse the `## Archivos a crear/modificar` table
- `git diff --name-only {base}..HEAD`
- Declared files missing → FAIL
- Extra files → WARN

## Report

```markdown
# task-validate-frontend — T{id}

**Status:** {PASS|FAIL}
**Lint:** PASS (0 errors, 2 warnings)
**Type check:** PASS
**Unit/component tests:** {total} total, {passed} passed, {failed} failed
**E2E tests:** not run (manual only) — specs written/changed: {list or none}
**Coverage:** {%} (threshold 80%)
**Build:** PASS
**ACs covered:** {N}/{total}

## Failed tests
- {file}::{method}
  - Expected: {x}
  - Actual: {y}

## Uncovered ACs
- AC-{xx}: no test verifies it

## Files out of scope
- {list or "none"}
```

## Return JSON

```json
{"status":"fail","summary":"2 tests fail + coverage 76% < 80%","issues":[{"severity":"fail","category":"test-failure","test":"SignerForm.spec.ts::testValidation","message":"..."}],"acCovered":["AC-01","AC-02"],"acFailed":[],"acUncovered":["AC-03"],"coverage":0.76}
```

## What it does NOT do

- Does not audit security (`security-audit-core` + `security-audit-frontend`)
- Does not validate a11y (`a11y-check`)
- Does not validate the design system (`design-system-check`)
- Does not measure performance (`perf-smoke-frontend`)
- Does not fix code or tests
- Does not run lint `--fix` or formatting

## References

- Full design: `Implementación/Skills de Ejecución de Tareas/frontend/05 - Task Validate Frontend.md`
