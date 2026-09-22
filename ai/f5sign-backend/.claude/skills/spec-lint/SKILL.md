---
name: spec-lint
description: 'Mechanical completeness validation of a task''s .md under docs/tasks/ before implementing it. Checks the header table (Status, Type, Why, Decision record), that Status and Decision record are falsifiable, that a task touching cross-cutting surfaces (deptrac, phpstan.dist.neon, the baseline, Kernel/Foundation, cross-BC dependencies) cites an ADR, that Builds on resolves, numbered sections, self-containment (OFFREPO, relative links, zero line-number citations), id uniqueness across branches, and absence of uncertainty markers. Use it with /spec-lint TASK-NNN or /spec-lint {path-to-.md}. Trigger with "lint task", "validate definition", "verify task X", "review task .md".'
---

# Spec Lint

Entry gate. Deterministic checklist over a task's `.md`.

> **The convention it validates is [`docs/tasks/README.md`](../../../docs/tasks/README.md).** If this skill and
> that README disagree, the README wins and this skill is the bug.

## Invocation

```
/spec-lint TASK-NNN                 # resolves via Glob under docs/tasks/
/spec-lint {path to the .md}
```

## Inputs

- Path to the `.md` (resolved from the argument). Tasks root: **`docs/tasks/`** — not `Planning/`, which is
  legacy from the docs repo (README §1).

## Outputs

- `var/task-runner/TASK-NNN/spec-lint.report.md`. ⚠ **`var/` may be owned by root and not let you create the
  directory** (checked 2026-08-17: `mkdir` from the host gives *Permission denied*, because the tools
  run in containers as root). This skill is the first in the flow, so it's the one that hits it:
  if it happens, create the directory inside the container or write the report to the session's scratchpad, and
  **say in the summary where it ended up**.
- Last line: JSON `{"status":"pass|fail","summary":"...","issues":[{"severity":"fail|warn","category":"...","message":"..."}]}`

## Execution

### Step 1 — Read the .md

If it doesn't exist or doesn't parse → `fail`, category `file`.

### Step 2 — Header table

It's a two-column table between the title and the first `---`/`## `. **There's no YAML frontmatter, nor
`Story Points`, `Tipo`, `Complejidad`, `Tags` or `Depende de`** — those fields belonged to the `Planning/` format.

Required:

- [ ] `Status` — present and not empty
- [ ] `Type` — present; free text, but must state *what kind of work this is* (forward build, corrective,
      enabling, groundwork) and not just repeat the title
- [ ] `Why` — present; must state the failure or gap, in a way that it can be **disagreed with**
- [ ] `Decision record` — present and **falsifiable like `Status`** (Step 3b), with the same age
      condition as `Why`. A missing field is a task that hasn't answered *"what decision governs
      this?"*, the question repo rule 7 depends on.

⚑ **`Why` and `Decision record` only block on tasks not yet implemented.** The condition is a
property, not a list: if `Status` does **not** claim existing code, the record is still an
editable plan and both fields are required (`fail`). If it already claims code, they're `warn` — because filling in
the *why* of already-closed work is inventing it after the fact, and an invented `Why` is worse than an absent one.
**Measured 2026-08-17: `Why` is present in 6 of 21 records and `Decision record` in 12**, so requiring them
across the board would fail 15 of 21 and the linter would be stricter than the corpus it claims to derive from.

Optional, and their absence isn't penalized: `Builds on`, `Scope`, `Delivery bar`, `Sibling`.

### Step 3 — Falsifiable `Status`

The field that rots the most, so it's validated by content, not by presence:

- [ ] If it claims code exists (`merged`, `landed`, `in progress`, `shipped`, `✅`) → **names a branch or
      a commit**. If not → `fail`, category `status-unverifiable`.
- [ ] If it says `Not started` and the branch diff already touches the §Scope files → `warn`, category
      `status-stale`.
- [ ] If it contains a date, it must be absolute (`2026-08-17`), never relative (*"last week"*) →
      `fail`, category `date-relative`.

### Step 3b — Falsifiable `Decision record`

Two valid forms, and no others:

1. **Cites an ADR** (`[ADR-NNNN](../adr/ADR-NNNN-*.md)`) → the link must resolve (Step 6). If it also says
   that this task *contradicts* or *reverts* something from that ADR, check that it declares **where the
   new ADR lands** (this task or which one) → if it doesn't say so: `fail`, category `decision-unlanded`. An
   accepted ADR isn't silently contradicted.
2. **`No ADR yet` + what would force one.** The second half isn't optional: *"there's no ADR"* without a
   trigger condition is indistinguishable from *"I haven't asked myself the question"*. → without it: `fail`,
   category `decision-record-unfalsifiable`.

⚑ **And if the task's scope touches any of these surfaces, form 2 doesn't count.** ⚠ *Scope*
here is **the section**, not the header's `Scope` field: that field exists in 2 of 21 records and Step 2
declares it optional, so gating on it would leave the check empty in almost all of them. If there's neither
field nor scope section, say so as `warn` (`scope-unstated`) instead of assuming it touches nothing. Surfaces:
the ruleset or layers of [`deptrac.yaml`](../../../deptrac.yaml), `phpstan.dist.neon`, `phpstan-baseline.neon`,
a contract in `src/F5Sign/Kernel/` or `src/F5Sign/Foundation/`, or a new cross-BC dependency. All of these are
cross-cutting decisions by definition and require an ADR → `fail`, category `decision-required`, naming the surface.

### Step 4 — `Builds on` and `Sibling`

⚑ **The two fields aren't validated the same way, and confusing them produces a false blocker.** `Builds on` is
a real dependency ("I reuse its output without changing it"); `Sibling` is a heads-up to a human ("don't plan
these two separately"). A task that honestly declares that its sibling lives on another branch is doing exactly
what the format asks for, and penalizing it punishes the correct behavior.

**`Builds on` — blocks:**

- [ ] Every cited task exists as `docs/tasks/TASK-NNN-*.md` on **this** branch. If it doesn't exist here but does
      on another (`git ls-tree -r --name-only <branch> -- ':(top)docs/tasks/'`) → `fail`, category
      `dependency-offbranch`, naming the branch: you can't build on something that isn't in the tree.
- [ ] If its `Status` is `Not started` → `fail`, category `dependency`.
- [ ] It can cite ADRs in addition to tasks; for those it's enough that the link resolves (Step 6).

**`Sibling` — never blocks:**

- [ ] If it's flagged with ⚑ → `warn`, category `sibling-flagged`, noting that they aren't planned
      independently.
- [ ] If it lives on another branch → **the same `warn`, naming the branch**, and say what happens if this
      task runs before that one is integrated. Never `fail`.

### Step 5 — Sections

Sections are numbered (`## 1. …`) and cited as `§N` from other documents.

- [ ] At least one section whose heading talks about **scope** and another about
      **verification/acceptance/definition of done**. ⚑ Check by *intent*, not against a closed
      list of headings: the 21 records on this branch use legitimate variants —scope appears in §3, §4 and §6;
      verification in §4, §5, §6 and §9— and an enumeration exempts "anything not yet on the list"
      (authoring rule 5).
- [ ] Numbering with no gaps or repeats, and **starting at 1**.
- [ ] No empty sections (heading followed immediately by another heading).

### Step 6 — Self-containment

- [ ] Every relative link resolves on disk → if not: `fail`, category `link-broken`.
- [ ] Every reference to something outside the repo carries a nearby `<!-- OFFREPO: ... -->`, and the fact
      taken from there is **restated** in the `.md` → if the tag is missing: `fail`, category `offrepo-untagged`.
- [ ] **Zero line-number citations**: links with `#L\d+` or paths with `:\d+` → `fail`, category
      `line-number-citation`. Cite by symbol or grep pattern instead.
- [ ] Wildcard paths (`src/**/UI/`) aren't validated on disk; they're conceptual.

### Step 7 — Id uniqueness

Run the README §4 sweep **at the moment**:

```bash
for b in $(git branch -a --format='%(refname:short)' | grep -v HEAD); do
  git ls-tree -r --name-only "$b" -- ':(top)docs/tasks/' 2>/dev/null | grep -oE 'TASK-[0-9]{3}'
done | sort -u
```

⚠ **`':(top)'` isn't decorative, and without it this check fails open.** A git pathspec is relative to the
**cwd**, so `-- docs/tasks/` run from `docs/tasks/` — the directory you're precisely in
when you're writing a task — resolves to `docs/tasks/docs/tasks/` and returns **zero ids**. Zero ids reads as
"the id is free", in the one check whose job is to prevent a collision. Measured 2026-08-17: **0 ids** without
`:(top)` from `docs/tasks/`, and **24** with it (or from the root). ⚑ And don't copy that 24 anywhere: it's the
count for that day, not a constant. An earlier version of this line said 21 —the file count for
*one* branch— and that error propagated to two documents before an audit caught it.

- [ ] The `.md`'s id doesn't appear on any other branch with a **different** slug → if it does: `fail`,
      category `id-collision`, naming the branch. This has actually happened: `TASK-021…023` live on
      `docs/two-gate-signer-auth` and are invisible from any other branch.

### Step 8 — Uncertainty markers

Grep for `PENDIENTE`, `[NEEDS CLARIFICATION`, `TBD`, `???`. Any occurrence → `fail`, category
`clarification`.

⚠ **Deliberate exception:** an *Open follow-ups* section **must** contain unresolved items — that's
its function (README §7). Don't penalize there; just require that each point say *what* is undecided and *what*
would force it.

## Report

```markdown
# spec-lint — TASK-NNN

**Status:** {PASS|FAIL}
**Issues:** {N} ({B} blocking, {W} warnings)

## Blockers
- [{category}] {message}

## Warnings
- [{category}] {message}

## Checks passed
- {list}
```

## What it does NOT do

- Doesn't validate semantic quality (only format, resolution, and existence).
- Doesn't modify the `.md`.
- Doesn't run tests or code.
- Doesn't resolve issues — only reports them.
