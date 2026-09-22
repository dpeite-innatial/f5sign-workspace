---
name: task-close
description: 'Documentally closes a task after implementation and validations: updates the .md (Estado=review, Fin, Commit SHA), consolidates tagMismatches from all previous skills, adds a "Desviaciones de lo planificado" section to the .md, and extracts non-obvious learnings to notes.md if there are any. Use it with /task-close T{id}. Trigger with "close task", "update .md", "consolidate learnings", "mark task as review".'
---

# Task Close

Documentation closeout for the task. Not a hard gate.

## Invocation

```
/task-close T{id}
```

## Inputs

- `var/task-runner/T{id}/` (all the `*.report.md` reports generated)
- `var/task-runner/T{id}/context-digest.md`
- `var/task-runner/T{id}/plan.md`
- The task's `.md` (to edit it)

## Outputs

- The task's `.md` EDITED:
  - Frontmatter: Estado, Fin, Commit, PR/Branch (branch, no URL yet), Tags (cleaned up)
  - New `## Desviaciones de lo planificado` section added after `## Tests`
  - `## Tests` section updated if `task-validate` ran different/additional tests than declared
- `var/task-runner/T{id}/task-close.report.md`
- `var/task-runner/T{id}/notes.md` (ONLY if there are real learnings; if empty, do NOT create it)
- JSON:
  ```json
  {"status":"pass|warn","summary":"...","mdSectionsUpdated":[...],"lessonsCount":N}
  ```

## Execution

### Step 1 — Read reports

Parse all the workspace's `*.report.md` files. Extract:
- Status of each skill
- `tagMismatches` from each one (consolidate into a single array)
- Active WARNs (for technical debt)
- Relevant unresolved issues

### Step 2 — Determine the commit SHA

- `git log -1 --format=%H` (the current branch should have the implement commit + amends)
- Save the SHA to update the frontmatter

### Step 3 — Edit the `.md`'s frontmatter

Use the Edit tool. Find the "Seguimiento" table in the `.md`:

- `Estado` → `review`
- `Fin` → current date (format `YYYY-MM-DD`)
- `Commit` → full SHA (40 chars)
- `PR/Branch` → name of the current branch (e.g. `feat/T02.1.1-slug`); `pr-ready` will add the full URL
  later

Also, in the header block (above, with `> **Tags:** ...`):
- Remove tags present in the consolidated `tagMismatches`. If only 1-2 tags remain, leave them (don't
  empty it out).

### Step 4 — Add the "Desviaciones" section

Find the `## Tests` section and add after it (if it doesn't already exist):

```markdown
## Desviaciones de lo planificado

### Archivos
- {si hay diferencia entre declarados y reales: listar. Si no: "Ninguna"}

### Tags corregidos
- Eliminado `{tag}`: {razón extraída del report que lo detectó}

### Decisiones tomadas en implementación
- {extraídas de context-digest.md § "Decisiones tomadas durante implementación"}

### Escaladas
- {si implement reportó escalada Sonnet→Opus en su JSON, documentar razón. Si no: "Ninguna"}

### Deuda técnica dejada
- {WARNs activos que el usuario decidió no corregir; extraer de perf-smoke, security-audit, etc.}
```

If any subsection has no content → write "Ninguna" (don't omit it).

### Step 5 — Update the "Tests" table (if applicable)

Read the workspace's `test-results.json`. If the number/names of tests run differ from the `.md`'s
`## Tests` table:
- Update the table to reflect the tests actually added
- Keep the original format (`| Test name | Type | File path | What it verifies |`)

### Step 6 — Extract learnings → notes.md

Look at the reports and detect patterns applicable to future tasks:

- **Insufficient context**: did `implement` escalate to Opus due to a missing rule/spec? Document what
  was missing in `Contexto requerido`.
- **Poorly assigned tags**: tag mismatches ≥ 1 → suggest reviewing the planning-detail criteria.
- **Implicit decisions**: decisions made during implementation without an ADR → suggest creating an ADR
  if the pattern repeats.
- **Retried failed gates**: if there was an automatic correction (implement re-invoked with the
  validation/security report), document what changed.
- **Unclosed technical debt**: unresolved perf-smoke/security-audit WARNs.

If there's at least one learning → create `var/task-runner/T{id}/notes.md`:

```markdown
# Notes — T{id}

## Potential learnings
- [Insufficient context] Escalated to Opus due to missing rule X; future similar tasks should list [rule/file]
- [Misused tag] Tag `db` applied but didn't touch persistence; review the planning-detail criteria

## Metrics
- Total time: {min}
- Estimated tokens: {breakdown per skill}
- Escalated to Opus: {yes/no, reason}
- Failed and retried gates: {N}

## Implicit decisions (ADR candidates if they repeat)
- {list extracted from context-digest.md}
```

If there are no learnings (everything went ideally) → **do NOT create** the file.

### Step 7 — Do NOT commit yet

`task-close` modifies the `.md` but does NOT commit. `pr-ready` will do the final `--amend` that includes
these modifications + the PR URL once created.

Leaving the changes staged is optional; if done, `git add {mdPath}` and that's it. If not, `pr-ready`
will add it.

## Report

`var/task-runner/T{id}/task-close.report.md`:

```markdown
# task-close — T{id}

**Status:** PASS  |  **Sections updated:** {N}  |  **Learnings:** {N}

## Changes applied to the .md
- Frontmatter: Estado → review, Fin → 2026-04-13, Commit → abc123f
- Tags: removed `db` (mismatch detected by doctrine-guard)
- "Desviaciones" section created with 3 entries
- "Tests" section updated (2 additional tests added vs. the original plan)

## Learnings written to notes.md (2)
- Insufficient context about state rule X
- Implicit decision about strategy Y (ADR candidate if it repeats)
```

## Return JSON

```json
{"status":"pass","summary":".md updated, 2 learnings extracted","mdSectionsUpdated":["frontmatter","tags","deviations","tests"],"lessonsCount":2}
```

## Failure handling

- If it can't parse a previous report → WARN "skipped section X", not FAIL
- If the `.md` is corrupt or not parseable → FAIL (unlikely case)
- If the commit SHA is missing (git returns nothing) → FAIL "no commit found, implement did not run?"

## What it does NOT do

- Does not open a PR (pr-ready)
- Does not commit (pr-ready does the final amend)
- Does not decide whether to publish (user confirmation)
- Does not write ADRs (docs-sync, as a draft)
- Does not fix tests or code

## References

- Full design: `Implementación/Skills de Ejecución de Tareas/common/03 - Task Close.md`
