---
name: task-author
description: 'Writes a new backend task record under docs/tasks/ together with its owner: takes what they want built and the criteria they already have, researches what exists and what the change must also satisfy, proposes the missing acceptance criteria marked as such, and writes the record only once the owner has confirmed every one, in a new branch and worktree cut from develop. Then runs spec-lint and the claims check on it and, once the owner confirms the final record, commits it on that branch. Interactive: runs in the main session. Use it with /task-author "<what to build>". Trigger with "write a task", "define a task", "new task for…", "spec this out".'
---

# Task author

Turns a request into a task record that `/task-runner` can execute. The format is
[`docs/tasks/README.md`](../../../docs/tasks/README.md) — §2 anatomy, §4 id, §5 self-containment, §6 harness,
§8 the criteria table. This skill does not restate it: read it before writing.

**It runs in the main session**, because it has to ask the owner and wait. Research goes to cheaper agents;
choosing the criteria stays here.

## Step 1 — Intake

From the request, and one round of questions only where the answer changes the record:

- **What the work must achieve**, as the owner would say it.
- **The criteria the owner already has.** They go into the table as they are, origin `owner`. Restate a criterion
  only to make it testable, and show the owner the restated form.
- What is explicitly out, if the owner knows.

Do not ask what the code can answer. That is Step 2.

## Step 2 — Research, delegated

Launch these in **one message**, each with `model` set, and each returning facts with `file:symbol`, not
prose:

| Question | Agent |
|---|---|
| What already exists for this: classes, ports, use cases, routes, events, and the tests beside them | `Explore`, `model: "haiku"` |
| Which ADRs govern the area: the index of `docs/adr/README.md`, then the bodies that match | `Explore`, `model: "haiku"` |
| Open items that touch it: `docs/BACKLOG.md` rows (grep, never read whole), other tasks' `Open follow-ups`, frontend handoffs | `Explore`, `model: "haiku"` |

What comes back is what the record's §2 (what already exists) is made of. A claim you cannot point at a file for
does not go into the record. Cap each return (the brief names a maximum number of facts).

## Step 3 — Derive the criteria the request did not state

This is the judgement step, and it is where the records of this repo have failed before. For the change being
specified, work through each item and write a criterion where it applies:

- **One criterion per refusal** of every guard the change adds or modifies.
- **The whole set a predicate exempts**, classified member by member: roles, envelope or leg states, enum
  members. `CLAUDE.md` authoring rule 5 is the reason; census the set from the code, don't list two examples.
- **Rows that already exist** when there is a migration: what each state reads after it (authoring rule 6), and
  the migration's `down()` and whether the old code tolerates the new schema.
- **Closed key sets** of any event or payload the change adds or extends, and how an old payload decodes
  (`schema_version`).
- **Tenant isolation** for anything that reads or writes per-tenant data.
- **Idempotency and charging**: a retried request, an attempt counter, a paid send, and an event redelivered
  (a convergent no-op).
- **An external dependency failing** (EU DSS, the SMS or mail provider): what the system records and what it
  retries.
- **Concurrency** where two actors can meet. Name the harness that can see it (`docs/tasks/README.md` §6:
  `Integration/` cannot see a row lock).
- **Every reachable HTTP code** of an endpoint the change adds, as an `#[OA\Response]`.
- **Wiring**: the handler, listener, route or tagged service that must be registered for the change to run.
- **ADR status**: which accepted or `Proposed` ADR the change exercises, or contradicts.
- **What must not change** (a regression criterion), and a PII field that must be **absent** from a payload.
- **One `app_now()` per write** where the change stamps more than one timestamp.

Propose a row only where a prompt applies; a prompt that does not apply produces nothing.

Each derived criterion gets origin `proposed — <source>`: the ADR, test, census or rule it came from.

**Size check.** Count top-level rows only (sub-ids do not count). If the record would carry more than about 15
criteria or span more than one bounded context's domain, propose splitting it into tasks linked by `Sibling`.
This threshold is a starting point, not a measurement.

## Step 4 — The owner confirms

Show the criteria table grouped by source, each group with a keep or drop recommendation: the owner's rows first,
then the proposed ones with their source. The owner may answer "confirm group A, drop 7, edit 12".

- **Group confirmation** is allowed only for rows citing one accepted ADR section or the owner's own text.
  Census-derived and rule-derived rows are confirmed one by one.
- A confirmed row's origin becomes `derived — <source>`; silence is not confirmation.
- Ids are assigned at Step 5, so a criterion added late costs nothing. A change after confirmation is shown again
  as a diff.

⛔ Do not write the record with a `proposed` row left; `spec-lint` would refuse it anyway.

If the work is cross-cutting (repo rule 7: an accepted ADR contradicted, a new cross-BC dependency,
Kernel/Foundation, deptrac/phpstan/baseline), say so now. The `Decision record` field then names the ADR to be
written, or it is `No ADR yet` plus what would force one. The decision itself is the owner's.

## Step 5 — Write the record, on its own branch

- Coin the id with the README §4 sweep, **re-run immediately before the Write**, from the repo root.
- Create the branch and worktree exactly as `task-runner` Phase 0 step 4 does (type and slug from the work,
  from `develop`, never the main checkout):
  ```
  git worktree add -b <type>/<slug> ../f5sign-backend-<slug> develop
  echo '/f5sign-backend-<slug>/' >> ../.gitignore
  ../bin/sync-ai.sh
  ```
  Write the record in `../f5sign-backend-<slug>/docs/tasks/`.
- Status: `**Not started** — written <date>.`
- §2 from Step 2's facts, §3 the scope including what is out and a `Concepts re-cut: <terms>` line (retired
  terms and symbols whose behaviour changes; it seeds the plan's sweep), §5 the confirmed table, §6 follow-ups.
- Self-containment per README §5: every outside fact restated and tagged `OFFREPO`, no line numbers.

## Step 6 — Check it

Launch both in one message (they declare their own models; no `model:`):

```
Agent({ subagent_type: "spec-lint-runner", description: "spec-lint on TASK-NNN",
  prompt: "Task: {mdPath}. Workspace: {scratchpad}. Return the JSON summary as the last line." })
Agent({ subagent_type: "spec-claims-runner", description: "claims check on TASK-NNN",
  prompt: "Task: {mdPath}. Decision record: {ADR or none}. Workspace: {scratchpad}. Return the JSON summary as the last line." })
```

Fix what is the author's to fix, and re-run `spec-claims-runner` on the changed passages: an edit made to answer
a check is unchecked until the check runs again. A finding that changes an `owner` criterion goes back to the
owner.

## Step 7 — Commit, only after the owner confirms the final record

Show the owner the record. Only once they confirm it, commit it on the task's branch, from the worktree, with a
subject such as `docs(task-NNN): <what the task asks for>` (workspace `CLAUDE.md` § *Commits*; no trailer). Then
tell them: the branch and worktree are ready for `/task-runner TASK-NNN` run from that worktree, which finds the
record committed; nothing is committed to `develop`, and merging is theirs.

## What it does not do

- Does not implement or plan slices: that is `/task-runner`.
- Does not commit to `develop`, push, or open a PR.
- Does not accept an ADR on the owner's behalf.
- Does not rewrite records written before TASK-055 into the new §5 form.
