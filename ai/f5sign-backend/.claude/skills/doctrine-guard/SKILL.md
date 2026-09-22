---
name: doctrine-guard
description: 'Mechanical validation of the persistence layer after a task: migrations (reversibility, indexes, published SQL that isn''t edited), RLS (ENABLE + FORCE + policy on current_tenant_id(), with the documented exception for the event log), coherence between PHP enums and what the column accepts, and —the costliest thing to get wrong— the rows a migration writes and the domain later reads. No ORM: doctrine/orm was retired (ADR-0018) and there isn''t a single *.orm.xml. Use it with /doctrine-guard TASK-NNN. Trigger with "validate migration", "review task persistence", "audit RLS".'
---

# Doctrine Guard

Mechanical persistence validation. Invoked when the diff touches `migrations/`,
`src/**/Infrastructure/Persistence/`, or SQL/RLS in any file.

⛔ **This repo has no ORM.** `doctrine/orm` is not a dependency and **there isn't even a single
`*.orm.xml`** (ADR-0018, pure DBAL). Everything this skill used to check about mappings and
entity↔XML↔table triangulation has no target. If the diff **adds** `doctrine/orm` or a `.orm.xml`,
that reverts an accepted ADR → `fail`, category `retired-mechanism`, and it's the decision gate of
`implement-backend` Step 2b.

## Invocation

```
/doctrine-guard TASK-NNN
```

## Inputs

- `var/task-runner/TASK-NNN/changes.diff` (without it: `fail`, `missing changes.diff`)
- `migrations/Version*.php` and `src/**/Infrastructure/Persistence/*` from the diff
- [`docs/LOAD-BEARING.md`](../../../docs/LOAD-BEARING.md) §1.7 and its **Never** list

## Outputs

- `var/task-runner/TASK-NNN/doctrine-guard.report.md`
- JSON: `{"status":"pass|fail|warn","summary":"...","issues":[...]}`

## Execution

### Step 1 — What can be edited in a migration

- [ ] **SQL of an already-published (pushed) migration: don't touch it.** It gets superseded by
      another one. Editing it is `fail`, category `published-migration`.
- [ ] **Comments and docblocks: always in scope**, published or not. Authoring rule 1 calls them
      the surface that does the most damage when it rots, because nobody re-reads an applied
      migration except to reconstruct *why* the schema is the way it is — and there a false reason
      costs the most. Fixing them doesn't re-run anything.
- [ ] **On a local branch that hasn't been pushed, the set is yours:** it can be reordered or
      condensed. "Applied in your dev volume" is not "published".

### Step 2 — Reversibility and indexes

- [ ] `up()` and `down()` present; `down()` with real operations, not empty or a generic throw.
- [ ] Every FK with its index (in the definition or a `CREATE INDEX`).
- [ ] Table with customer data → column **`tenant_id`**. ⚠ **Don't require `workspace_id`: it
      doesn't exist.** It appears exactly once in the whole repo, in a docblock describing a
      future dual-scoped-keys model. Requiring it would be inventing the schema.
- [ ] Composite index starting with `tenant_id` for tenant-filtered queries → if missing:
      `warn`.

### Step 3 — RLS

Grep for `ENABLE ROW LEVEL SECURITY`, `FORCE ROW LEVEL SECURITY`, `CREATE POLICY`:

- [ ] `ENABLE` **and** `FORCE` present. `FORCE` is what makes the table owner obey it too.
- [ ] The policy relies on **`current_tenant_id()`** (the fail-closed function that wraps
      `current_setting('app.current_tenant_id')`), not on the raw setting.
- [ ] Covers read and write, **or explicitly says why not**. ⚑ There's a documented and
      legitimate exception: `platform.event_log` is **write-check-only** (`WITH CHECK`, no
      `USING`) because its readers are trusted cross-tenant projectors (ADR-0031, with the
      reciprocal carve-out in ADR-0017 §7). Before marking `fail` for a missing `USING`, check
      whether the table is that case.

### Step 4 — ⚠ A migration runs as superuser, so RLS doesn't protect it

Migrations connect as the **bootstrap superuser** (`POSTGRES_USER`), never as the app role —
**in every environment, production included** (`docs/LOAD-BEARING.md` §1.7). A superuser
**bypasses RLS entirely**, with or without `FORCE`. Two consequences to check:

- [ ] ⛔ **No `NO FORCE ROW LEVEL SECURITY` wrapped around a data write.** It's a **no-op that
      reads like a guard**: RLS didn't apply anyway. It's in the **Never** list of
      `LOAD-BEARING.md` §2, along with why the obvious fix is also wrong if that role is ever
      narrowed down the line. Presence → `fail`, category `false-guard`.
- [ ] The correctness of a data write has to come from the **SQL itself** (its `WHERE`), not
      from RLS.

### Step 5 — Rows the domain later reads (authoring rule 6)

The costliest check to skip: in the last review, the one blocking finding came from here.

- [ ] **Enumerate the aggregate states the row falls under** — draft, in flight, terminal,
      superseded — and say what the row means **in each one**, on the **write** side as well as
      the read side. Reasoning only about "what a recipient can see right now" is exactly how
      that blocker slipped through.
- [ ] **A predicate that states the property, not an enumeration of today's states.**
      `sent_at IS NOT NULL` asks the real question (*"could anyone have read this already?"*);
      `status <> 'DRAFT'` reopens the hole the day a pre-send state gets added. Enumeration →
      `warn` with the proposed predicate.
- [ ] **Append-only model with no revocation path ⇒ a badly written row is permanent and
      unrepairable via the API.** If the backfill carries no state predicate, `fail`: the
      precedent is a backfill that turned every undeclared pair of a pre-existing draft into a
      permanent 409, leaving those envelopes neither sendable nor repairable.

### Step 6 — PHP enums ↔ what the column accepts

**There are no SQL ENUMs in this repo** (`CREATE TYPE ... AS ENUM`: zero). States travel as
`TEXT` and the type lives in a PHP backed enum. So the check isn't "do the two enums match?" but:

- [ ] If the column carries `CHECK (... IN (...))`, its values match the PHP enum's `case`s.
- [ ] **A new `case` in PHP doesn't break the column** (it's `TEXT`), and that's precisely the
      risk: what's checked is that **the read side knows how to parse it** — the repository
      mapping, the projection, and any exhaustive `match`. A writable value the read-side doesn't
      recognize is `fail`, category `unparseable-value`.
- [ ] If the enum is part of a published contract (it goes out through the API), the
      corresponding `#[OA\*]` lists it → if not: that's `contract-check-backend`'s job, it's
      reported and the data is passed along.

### Step 7 — Entities and repositories

Without redoing what Deptrac and the project's own PHPStan rules already watch (layer purity,
kernel placement):

- [ ] Aggregate root ⇒ has a repository; subordinate entity ⇒ **doesn't** have its own, it's
      modified through its root.
- [ ] ⚑ **`EntityReference` doesn't extend `EntityId`, and that's not duplication to clean up**
      — it's in `LOAD-BEARING.md`. Same with the row lock that isn't narrowed below the
      write-set of `save()`. Before "simplifying" anything about persistence, that document
      first.

## Report

```markdown
# doctrine-guard — TASK-NNN

**Status:** {PASS|FAIL|WARN} · **Issues:** {B} blockers, {W} warnings

## Blockers
- [{category}] {file} {message}

## Rows written and their future read
- {table}: aggregate states enumerated {yes/no} · predicate {the one used} · repairable via API {yes/no}

## Warnings
## Checks passed
```

## What it does NOT do

- Doesn't run migrations against the DB (that's `task-validate-backend`, with `--dry-run`).
- Doesn't validate business logic (unit tests).
- Doesn't audit SQL injection or authz (`security-audit-*`).
- Doesn't measure performance (`perf-smoke-backend`).
