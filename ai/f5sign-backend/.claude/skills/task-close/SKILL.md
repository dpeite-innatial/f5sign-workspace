---
name: task-close
description: 'Closes a task''s documentation after implementation and validations, and owns the step nobody had: proposing the move of an ADR from Proposed to Accepted when the task exercises it, naming the artifact and waiting for your OK. It also updates its Status in the header table naming branch and commit, adds the deviations section at the end (without renumbering), and — most importantly — takes every deferral and every learning to a durable home in the repo (§Open follow-ups + a docs/BACKLOG.md row), never to a loose memo. Use it with /task-close TASK-NNN. Trigger with "close task", "update the .md", "consolidate learnings", "mark task as review".'
---

# Task Close

Documentation closure for the task. It's not a hard gate, but **it's the only step that keeps what was
learned from being lost**.

> Format convention: [`docs/tasks/README.md`](../../../docs/tasks/README.md). If it disagrees with this
> skill, the README wins.

## Invocation

```
/task-close TASK-NNN
```

## Inputs

- `var/task-runner/TASK-NNN/` — all `*.report.md`, `context-digest.md`, `plan.md`
  (⚠ if `var/` is owned by root and the reports ended up in the scratchpad, read them from there;
  `task-runner` Phase 0 says where they landed)
- The task's `.md`, to edit it

## Outputs

- The edited `.md`: `Status` + deviations section + completed `Open follow-ups`
- New row(s) in [`docs/BACKLOG.md`](../../../docs/BACKLOG.md) if deferrals came up
- `var/task-runner/TASK-NNN/task-close.report.md`
- JSON: `{"status":"pass|warn","summary":"...","mdSectionsUpdated":[...],"deferralsHomed":N}`

## Execution

### Step 1 — Read the reports

From each `*.report.md`: status, unresolved WARNs, open issues, and **the `harness` that
`task-validate-backend` declared** (needed for the Status; a green without a harness isn't a green).

### Step 2 — `Status`, falsifiable and naming the code

**There's no *Seguimiento* table, nor `Estado` / `Fin` / `Commit SHA` fields** — that was the `Planning/`
format. What exists is the **`Status`** field in the header table, and the README §3 rule: **if it claims
code exists, it names a branch or commit.**

Form to write:

```
| **Status** | **Implemented on `feat/<slug>`** (<short sha>), 2026-08-17 — suite green under
{harness}. Pending review. {what was left out, if anything}. |
```

- Date always **absolute**.
- ⛔ **Never write `merged` / `✅` from here.** This skill runs before the PR: claiming integration is
  falsifying the status, which is the error README §3 prevents.
- If the work was left half-done, say so in the `Status` instead of leaving it optimistic: the field gets
  read six weeks from now, which is exactly when optimism costs you.

### Step 3 — The deviations section goes **at the end**, and nothing gets renumbered

Sections are cited as `§N` from ADRs, from other tasks, and from `CLAUDE.md`, so **adding in the
middle breaks anchors**. Add `## N. Deviations & honest notes` as the **last** section (whatever number
that turns out to be), never insert it after another one or reshuffle the existing ones.

Content, and empty subsections are written as "None" instead of omitted:

```markdown
### Scope
- {diff files the scope didn't anticipate, or "None"}

### Decisions made during implementation
- {from context-digest.md; each with its why}

### Decisions that needed an ADR
- {ADR-NNNN, proposed and accepted by the user on YYYY-MM-DD — or "None"}

### Declared and unproven properties
- {from validate.report.md: the claim + why the harness doesn't reach it}

### Debt left behind, and where it lives now
- {each with its home: this task's §Open follow-ups, a BL-NNN row, or the ADR that records it}
```

### Step 4 — Every deferral and every learning, to a durable home

⚑ **This is the step that justifies the skill, and the one the previous version got wrong.** It wrote
learnings to a `notes.md` under `var/`, which is gitignored: a memo nobody will ever read again. This
repo already paid for that mistake twice — someone had to manually reconstruct *"eight deferrals that lived
only in an untracked memo"*. **A learning that only exists in `var/` is a learning that's lost.**

The real homes, by type:

| What came up | Where it lives |
|---|---|
| Something decided and **not done** | This task's `§Open follow-ups` (the real home) **+ a row in `docs/BACKLOG.md`** indexing it back here |
| A cross-cutting decision made | Its ADR. If it doesn't exist yet → that's `implement-backend` Step 2b, not a note |
| An ADR this task made true | That ADR's `Status` / `Enforced by` / `Realized in`, in this changeset (authoring rule 7) — see Step 4b, which is the one that executes it |
| A guard no harness reaches | A BACKLOG row, citing what harness would be needed |
| Prose that went stale in another file | Fixed now, not noted: that's the sweep from rule 1 |
| Process friction (environment, tooling) | `var/…/task-close.report.md` is fine **only** if it's ephemeral to this run; if it's going to repeat, it goes to BACKLOG |

For the BACKLOG row: **re-derive the id by grep at the moment**, across all branches, with the
absolute pathspec (`':(top)docs/BACKLOG.md'`) — the same fail-open bug the id sweeps had.

### Step 4b — Moving an ADR from `Proposed` to `Accepted` (this skill owns it, with your OK)

⚑ **Nobody owned this transition, and that's why ADR-0018 and ADR-0035 kept saying *not yet* while
their work was already in `master`.** `implement-backend` drafts the ADR as `Proposed` and stops; `docs-sync`
can't mark it `Accepted`; and this is finally where you know what turned out green. So the state change is
proposed **here**, and only here.

In this set, **`Accepted` means exercised**, not agreed upon. Therefore:

- [ ] Is the ADR's decision **exercised by something you can point to** — a test that proves it, a
      code path that applies it, a rule that enforces it? If not, it stays `Proposed`. *"It's already
      implemented"* isn't enough: you have to name the artifact.
- [ ] Fill in **`Enforced by (in-repo)`** and **`Realized in (in-repo)`** with those artifacts, by symbol or
      grep pattern, **never by line number**.
- [ ] **Propose it to the user and wait for their OK**, the same way `implement-backend` does when coining it:
      *"ADR-NNNN moves from Proposed to Accepted because {artifact} exercises it"*. ⛔ Without a response, the
      field isn't touched.
- [ ] If the task exercises **part** of the decision, there's a nuance for that: `Accepted (enforcement partial)`
      is a form in use in this repo (ADR-0045). Better that than an `Accepted` that promises more than what's there.

### Step 5 — The `Open follow-ups` the task already resolved

If the implementation closed any of the `§Open follow-ups` items, **mark it closed there and in its
BACKLOG row**, with a date. A follow-up that's still open on paper and closed in the code is the same
kind of lie as a stale `Status`, in the opposite direction.

### Step 6 — Commit

This skill **does commit its own edits** (`docs/` and the `.md`), like a normal documentation commit.
There's no `--amend` to wait for: `pr-ready` no longer rewrites history.

## Report

```markdown
# task-close — TASK-NNN

**Status:** {PASS|WARN} · **Sections edited:** {N} · **Deferrals with a home:** {N}

## Changes to the .md
- Status → {literal text written}
- Section {N} "Deviations & honest notes" added at the end

## Deferrals and learnings, with their home
- {what} → {§Open follow-ups | BL-NNN | ADR-NNNN}

## Process friction in this run
- {environment, tooling; and if it will repeat, the BACKLOG row that captures it}
```

## Failure handling

- An unreadable report → WARN, not FAIL.
- No commit on the branch → FAIL: `implement-backend` never got to run.
- `.md` not parseable → FAIL.

## What it does NOT do

- Doesn't open a PR (`pr-ready`).
- Doesn't **draft** ADRs (`implement-backend` proposes them, `docs-sync` writes them) — but it **is** the one
  that moves their state when the task exercises them, with your confirmation (Step 4b).
- Doesn't decide whether it gets published.
- Doesn't fix code or tests.
