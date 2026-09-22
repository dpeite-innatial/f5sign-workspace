---
name: task-runner
description: 'Single orchestrator for the backend task-execution skill stack. Runs a docs/tasks/ task end-to-end by invoking specialized skills (spec-lint, implement-backend, task-validate-backend, security-audit-core, etc.), managing gates, the workspace at var/task-runner/TASK-NNN/, the git branch, and the final PR. Use it with /task-runner TASK-NNN or /task-runner {path to the .md}. Trigger with phrases like "run TASK-024", "run task X", "task runner on...".'
---

# Task Runner

Orchestrator for the backend's task-execution skill stack.

> **Task convention: [`docs/tasks/README.md`](../../../docs/tasks/README.md).** It's the source of truth
> for the format, how an id is coined, and what each field of the header table means. If this skill and
> the README disagree, the README wins.

## Invocation

```
/task-runner TASK-NNN                 # e.g.: /task-runner TASK-024
/task-runner {path to the .md}
/task-runner TASK-NNN --auto          # unsupervised (default: supervised)
/task-runner TASK-NNN --resume        # resume existing workspace
```

If no argument is passed, ask the user for the id or the path.

## Preconditions

Verify, and **stop with a clear message** if it fails:

1. The task's `.md` exists at `docs/tasks/TASK-NNN-*.md` and is readable.
2. `git status` clean on the current branch.
3. The base branch is **`develop`** (`master` is the release one). **Branch from the ref**:
   `git checkout -b <branch> develop`. In a linked worktree, `git checkout develop` is impossible, because the
   main checkout already has that branch.
4. **The stack is up**, checked from `../f5sign-infra` and never with `docker compose` from this repo
   (repo rule 5): `make -C ../f5sign-infra worker-status` responds, or `docker ps` shows
   `f5sign-php-fpm`. If not → stop with *"environment not available: `make -C ../f5sign-infra up`"*.
5. **Validation harness.** All test and gate runs go through the `test-runner` agent, which chooses only
   between the main checkout and the `wt-backend` lane (rules in `CLAUDE.md` § *Running tests*). Note in the
   `run.log` and in the summary **which harness it used**: a validation whose target wasn't your tree reads
   as green. ⛔ No manual containers for the suite: they share the Postgres cluster and give false reds in
   the relay (BL-138).

## Who runs each phase, and on what model

Each child skill has its **subagent** at `.claude/agents/<name>-runner.md`, which declares the model,
preloads the skill (`skills:`), and fixes tools and context. **List that directory** to see each phase's
model; this skill doesn't repeat the list.

- ⛔ **When calling them, do NOT pass `model:` in the `Agent` call**: the call's parameter overrides the
  agent's frontmatter and silently voids what it declares. There's also no need to tell it to read the
  `SKILL.md`: it already has it loaded.
- ⛔ **Child skills are ALWAYS launched with `Agent`, using their phase's literal block.** They're not
  loaded with the `Skill` tool nor read from here: they'd run in the orchestrator's context, with the
  session's model, and fill it with code and reports. The orchestrator reads each phase's JSON and, if a
  gate fails, its `*.report.md`. Nothing else.
- No runner, on purpose: `implement-backend` (inherits the session's model, Phase 2) and `pr-ready`
  (Phase 8). `eidas-compliance` is launched by `security-audit-core` with its model fixed.

## Execution flow

### Phase 0 — Preparation

1. **Resolve the `.md`**: if an id was given, `docs/tasks/TASK-NNN-*.md` with Glob. If a path was given,
   use it.
2. **Read the header table** (README §2): `Status`, `Type`, `Why`, `Builds on`, `Scope`,
   `Decision record`, `Delivery bar`, `Sibling`. There's no `Complejidad`, `Tags`, or `Depende de`.
   - If `Status` or `Type` is missing → stop. `Why` is only required for tasks not yet implemented (see
     `spec-lint` Step 2).
   - Sections are **not** in fixed positions: locate scope and verification by intent, not by `§N`.
   - If there's a `Sibling` marked with ⚑ → **read it before starting**: the task can't be planned alone.
3. **Verify `Builds on`**: if a cited task is still `Not started` and ours reuses it as-is, or it lives in
   another branch that hasn't been merged → stop and say so.
4. **Workspace**: `var/task-runner/TASK-NNN/` (gitignored). If it exists and there's no `--resume` → ask
   whether to resume or restart. ⚠ `var/` is usually owned by root (tools run in containers): if `mkdir`
   gives *Permission denied*, create it inside the container
   (`docker run --rm -v $(pwd):/var/www/html -w /var/www/html f5sign/backend:dev mkdir -p var/task-runner/TASK-NNN`)
   or write the reports to the scratchpad and **say in the summary where they ended up**.
5. **Branch**: `<type>/<slug>` (`feat/notification-email-html`, `docs/task-conventions`), kebab-case, ASCII,
   from `develop` (precondition 3). **Without the task id in the name**: it goes in the PR body and in the
   `Status`.
6. **`run.log`** (JSON lines): `{phase: "prepare", status: "pass", at: ISO8601}`.
7. **Baseline before touching a single line**: full suite with `Agent({ subagent_type: "test-runner", … })`,
   without `model:`. Note the **exact number of tests and asserts** in `run.log` and in the summary: without
   it, you can't separate your own reds from environment ones. **A red baseline doesn't abort: it's
   declared.** `{"phase":"baseline","status":"pass","tests":N,"assertions":M,"harness":"…"}`.

### Phase 1 — `spec-lint` [GATE]

```
Agent({
  subagent_type: "spec-lint-runner",
  description: "spec-lint on TASK-NNN",
  prompt: "Task: {mdPath}. Workspace: var/task-runner/TASK-NNN/. Write the report to var/task-runner/TASK-NNN/spec-lint.report.md. Return the JSON summary as the last line of your response."
})
```

If `status: "fail"` → supervised: show the report and ask (edit the `.md` and retry, or abort);
auto: abort.

### Phase 2 — `implement-backend` [GATE]

```
Agent({
  subagent_type: "general-purpose",
  description: "implement-backend on TASK-NNN",
  prompt: "Execute the implement-backend skill defined at .claude/skills/implement-backend/SKILL.md on task {mdPath}. Workspace: var/task-runner/TASK-NNN/. Produce context-digest.md and plan.md. You cannot ask the user: if the skill needs a decision (a cross-cutting ADR), draft it as Proposed and return status \"awaiting-adr-acceptance\". Return the JSON summary as the last line of your response."
})
```

No `model:`: it inherits the session's. Escalate only after a repeated failure with a diagnosis that
justifies it. If it fails with `"spec contradictorio"` or `"contexto insuficiente"` → **don't escalate**:
ask the user to expand the `.md` (its section on what already exists, or the scope one).

⛔ **If it returns `"awaiting-adr-acceptance"`, it's the user's turn.** There's a cross-cutting decision
(it contradicts an accepted ADR, opens a cross-BC dependency, touches Kernel/Foundation, or edits
`deptrac.yaml` / `phpstan.dist.neon` / the baseline) with the ADR drafted as `Proposed`. Present it —what it
decides, what it rules out, what it forbids— and **stop**, even in `--auto`. Forbidden: accepting it on the
user's behalf, retrying Phase 2 to see if it passes, or trimming the change so the decision stops being
needed.

`changes.diff`: `git diff $(git merge-base HEAD develop)..HEAD > var/task-runner/TASK-NNN/changes.diff`.

### Phase 3 — Conditional validations

The condition is **what the diff touches**, not a list of tags (an enumeration exempts everything not yet
on it):

| Skill | Subagent | Invoked if the diff touches |
|---|---|---|
| `doctrine-guard` | `doctrine-guard-runner` | `migrations/`, `src/**/Infrastructure/Persistence/`, or SQL/RLS in any file |
| `contract-check-backend` | `contract-check-runner` | `src/**/UI/Http/`, `config/routes/`, any `#[OA\`, or a `Contract/Event/` |
| `task-validate-backend` | `task-validate-runner` | **always** |

Prerequisite for `contract-check-backend` if there are endpoints:
`make -C ../f5sign-infra sf cmd="nelmio:apidoc:dump --format=json"` → save it in the workspace.

One block per gate, **all in the same message**:

```
Agent({
  subagent_type: "task-validate-runner",      // or "doctrine-guard-runner" / "contract-check-runner"
  description: "task-validate on TASK-NNN",
  prompt: "Task: {mdPath}. Workspace: var/task-runner/TASK-NNN/ (changes.diff is there). Harness: {the one from precondition 5}. Paths you may touch: {list}. Report anything outside them, do not edit it. Return the JSON summary as the last line of your response."
})
```

Rules for the split (parallel agents on the same tree):

- ⛔ **Each agent gets its list of paths and the order to report, not edit, whatever it sees outside them.**
  Without it, there's no telling whose delta each one is. And reporting what's outside is often the most
  valuable finding.
- ⛔ **Before splitting, go through `§Scope` and check that every surface it names has an owner; whatever
  doesn't have one is yours.** The lists keep agents from stepping on each other and make invisible whatever
  falls between them: a missing Messenger handler, or prose the task itself said to change. The unit that
  needs an owner is the **claim** that changes, not the file (`CLAUDE.md` authorship rule 1).
- **With agents still running, never `git add -A`**: it commits someone else's work half-done. Explicit
  paths, or wait until none are left.
- **The three gates and `security-audit-runner` don't have `Edit`**: they report, they don't fix. If a
  brief needs to sabotage a file to see a guard fail, use `general-purpose` for that agent, require it to
  restore and prove it with an empty `git diff`, and note it in the `run.log`.
- **If the diff adds a listener, a middleware, or a tagged service, check that it's registered**:
  `make -C ../f5sign-infra sf cmd="debug:event-dispatcher <event>"`, `debug:container --tag=<tag>`,
  `debug:messenger`. One that's not wired up is a silent no-op that the suite doesn't see, and no gate
  covers it.

After that, sequential and **always**: `security-audit-core`. It delegates to `security-audit-backend`, and
to `eidas-compliance` if the diff touches signing or crypto (`src/F5Sign/SignatureExecution/`,
`Foundation/Crypto/`, DSS, PAdES).

```
Agent({
  subagent_type: "security-audit-runner",
  description: "security-audit on TASK-NNN",
  prompt: "Task: {mdPath}. Workspace: var/task-runner/TASK-NNN/ (changes.diff is there). The diff {does|does not} touch signing/crypto. Return the JSON summary as the last line of your response."
})
```

If a hard gate fails → supervised: show the report and ask (retry Phase 2 with the report as context, max 2
iterations, or abort); auto: abort.

### Phase 4 — Non-gate validations

`perf-smoke-backend` **is not runnable**: it depends on `composer perf:seed`, which doesn't exist in
`composer.json`. Log `{"phase":"perf-smoke","status":"skipped","reason":"no perf:seed script"}`: a declared
skip, not a green.

### Phase 5 — `docs-sync`

If the diff touches ADRs, `config/`, `.env*`, a `Contract/Event/`, or adds a module. Its changes go in
**their own commit**. It's not a gate: if it fails, warn and continue.

```
Agent({
  subagent_type: "docs-sync-runner",
  description: "docs-sync on TASK-NNN",
  prompt: "Task: {mdPath}. Workspace: var/task-runner/TASK-NNN/ (changes.diff is there). No other agent is running. Return the JSON summary as the last line of your response."
})
```

### Phase 6 — `task-close`

Always. Updates the `Status` **naming branch or commit** (README §3) and adds the deviations **at the end**,
without renumbering (the `§N`s are anchors cited from other documents). Its real job is making sure
**nothing learned stays in `var/`**: every deferral goes to `§Open follow-ups` **and** to `docs/BACKLOG.md`;
every cross-cutting decision, to its ADR. If the task made an ADR true, its `Status` / `Enforced by` /
`Realized in` go in this changeset (`CLAUDE.md` authorship rule 7).

```
Agent({
  subagent_type: "task-close-runner",
  description: "task-close on TASK-NNN",
  prompt: "Task: {mdPath}. Workspace: var/task-runner/TASK-NNN/ (all phase reports are there). Branch: {branch}. Return the JSON summary as the last line of your response."
})
```

⛔ **A subagent can't ask the user**, and moving an ADR from `Proposed` to `Accepted` needs their OK. If the
runner returns `"awaiting-adr-acceptance"` with each ADR and its artifact, **you ask** (also in `--auto`).
If they accept, apply the status change in its own commit, without signing the commit.

### Phase 7 — Confirmation (supervised only)

Summary of phases, changed files, added tests, covered criteria, active warnings, and **which harness
validated**. Ask: open a PR?

### Phase 8 — `pr-ready`

⛔ **`gh` isn't installed** (neither on the host nor in `f5sign/backend:dev`), so the PR is opened by hand.
Say so in the summary, don't report it as a failure. Once `gh` is available: only if the user confirms (or
`--auto`), push, `gh pr create` against **`develop`**, and the URL to the `.md` in a follow-up commit. **No
single commit or `--amend`**: the repo merges multi-commit PRs.

## Contract with child skills

Each child skill receives `taskDir` (`var/task-runner/TASK-NNN/`) and `taskMdPath`, writes its
`*.report.md` to a predictable path, and returns as its last message `{ status, summary, issues?, metrics? }`.

## run.log

One JSON line per phase: `{"phase":"implement","status":"pass","attempts":1,"at":"2026-08-17T10:15:00Z"}`.

## Failure handling

- **status=fail**: hard gate → stop or retry; not a gate → warn and continue.
- **Agent fails** (network, timeout): retry once; if it fails again, report.
- **Git fails**: never `--force` or `reset --hard`; stop and ask for intervention.
- **A merge that touches `.claude/` or `CLAUDE.md` can abort** (symlinks to the store with `skip-worktree`):
  `bin/unlink-ai.sh` → merge → `bin/sync-ai.sh` at the workspace root.
- **Ctrl+C**: the workspace stays as it is; `--resume`.

## What it does NOT do

- Doesn't edit code.
- Doesn't interpret other skills' reports (only their JSON).
- Doesn't create tasks: they're written by hand following `docs/tasks/README.md`, coining the id with its
  §4 sweep at that moment and across all branches.
- Doesn't merge PRs.
