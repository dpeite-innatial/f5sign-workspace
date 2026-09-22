# Skill stack adaptation status (backend)

This stack was written for an earlier version of the project: tasks in the docs repo's `Planning/`,
test tiers `composer test:unit|test:integration|test:e2e`, ORM with `*.orm.xml` mappings, base branch
`master`, and `docker compose` from the repo itself. **None of that is true today** — see
[`docs/tasks/README.md`](../../../docs/tasks/README.md) §1 for where `Planning/` stands.

The adaptation goes in phases. This table is the actual status, measured on **2026-08-17**.

| Skill | Status | What's left to fix |
|---|---|---|
| `spec-lint` | ✅ adapted | — |
| `implement-backend` | ✅ adapted | — |
| `task-validate-backend` | ✅ adapted | — |
| `pr-ready` | ✅ adapted | — |
| `task-runner` | ✅ adapted | — |
| `task-close` | ✅ adapted | — |
| `doctrine-guard` | ✅ adapted | — |
| `contract-check-backend` | ✅ adapted | — |
| `perf-smoke-backend` | ◑ half, static adapted | The dynamic part (p95, throughput, memory) still has no target: `composer perf:seed` doesn't exist. Creating the seed is a decision, not a skill fix |
| `docs-sync` | ✅ adapted | — |
| `security-audit-core` / `security-audit-backend` | ✅ adapted | — |
| `eidas-compliance` | ✅ adapted | — |
| `v1-touched-file-hygiene` | ✅ native | Written for this repo. Used before committing |

## Audited on 2026-08-17

The twelve went through an audit by five agents with fresh context: four checking every factual claim
against the tree (one command per claim) and one asking the opposite — what the stack should be watching
given the architecture that nobody watches. About 100 findings came out, and all the ones in these four
classes are fixed: **claiming a protection or rule that doesn't exist** (encrypted PII, identity derived
against ADR-0042, `final readonly` VOs across the board, B-LT by default), **checks that couldn't fail**
(event log, `NO FORCE`, `CHECK (... IN ...)`, four entire eIDAS steps), **unrunnable instructions**
(`feat/TASK-NNN-*` branches that never existed, `--testsuite <tier>`, unconfigured JUnit, `make sf` for the
dry-run) and **duplicating a test that already exists** (`OpenApiSpecTest`, `SchemaConformanceTest`).

What the audit left **open and isn't a skill fix** is logged in `docs/BACKLOG.md`: the two product holes it
found, the row-lock census that leaves out four use cases, `BC_SCHEMAS ⊄ OWNED_SCHEMA`, the 26 unpinned
`EVENT_TYPE`s, and that there's no CI.

⚑ **The big gap that's still there:** none of the twelve names a kernel category, and `Repository`'s
behavioral contract —seven invariants of `save`— doesn't have a single test file. The form is enforced
almost completely; the behavior, not at all. That's new work, not adaptation.

## Two rules for whoever continues the adaptation

1. **Test each adapted skill against a real task before trusting it.** A skill whose checks find nothing
   returns green, and that green reads as all-clear: it's the pattern that authorship rule 5 of
   [`CLAUDE.md`](../../../CLAUDE.md) describes (*"an exempt set that's empty today can't turn red, so
   green is the expected signal, not evidence"*).
2. **Edit in the store, never in the subrepo.** These files reach the repo as symlinks to
   `ai/f5sign-backend/.claude/` with `skip-worktree`; an edit made in the checkout is lost on the next
   `bin/sync-ai.sh` — or worse, it gets committed inside the subrepo and breaks the "zero AI trace" rule.
   The `f5sign-backend-develop` worktree was serving July copies precisely because of that.
