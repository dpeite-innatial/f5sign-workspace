---
name: task-runner
description: 'Single orchestrator for the backend task-execution skill stack. Runs a docs/tasks/ task end-to-end by invoking specialized skills (spec-lint, plan-backend, implement-backend per slice, task-validate-backend, security-audit-core, etc.), managing gates, the workspace at var/task-runner/TASK-NNN/, the git branch, and the final PR. Use it with /task-runner TASK-NNN or /task-runner {path to the .md}. Trigger with phrases like "run TASK-024", "run task X", "task runner on...".'
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
/task-runner TASK-NNN --plan-only     # stop after the plan is approved (Phase 2a)
```

If no argument is passed, ask the user for the id or the path.

## Preconditions

Verify, and **stop with a clear message** if it fails:

1. The task's `.md` exists at `docs/tasks/TASK-NNN-*.md` and is readable.
2. `git status` clean on the current branch. If the only dirty path is the task's own record, stop with:
   *commit the record on its branch first* (`/task-author` commits it on the task's branch; a record written
   by hand is committed before the run, because a worktree branches from a commit and would not contain it).
3. The base branch is **`develop`** (`master` is the release one). **Branch from the ref**, never by
   checking `develop` out: in a linked worktree that is impossible, because the main checkout has it.
   A task whose record `/task-author` committed already has its branch and worktree: Phase 0 step 4 reuses them.
4. **The stack is up**, checked from `../f5sign-infra` and never with `docker compose` from this repo
   (repo rule 5): `make -C ../f5sign-infra worker-status` responds, or `docker ps` shows
   `f5sign-php-fpm`. If not → stop with *"environment not available: `make -C ../f5sign-infra up`"*.
5. **Validation harness.** All test and gate runs go through the `test-runner` agent — except the TDD loop
   inside each slice's `implement-backend`, which runs filtered tests directly (its *Validation cadence*) — which chooses only
   between the main checkout and the `wt-backend` lane (rules in `CLAUDE.md` § *Running tests*). Note in the
   `run.log` and in the summary **which harness it used**: a validation whose target wasn't your tree reads
   as green. ⛔ No manual containers for the suite: they share the Postgres cluster and give false reds in
   the relay (BL-138).

## Who runs each phase, and on what model

Each child skill has its **subagent** under `.claude/agents/` (`<name>-runner.md`, plus `slice-implementer` and
`slice-reviewer` for Phase 2b), which declares the model,
preloads the skill (`skills:`), and fixes tools and context. **List that directory** to see each phase's
model; this skill doesn't repeat the list.

- ⛔ **When calling them, do NOT pass `model:` in the `Agent` call**: the call's parameter overrides the
  agent's frontmatter and silently voids what it declares. There's also no need to tell it to read the
  `SKILL.md`: it already has it loaded.
- ⛔ **Child skills are ALWAYS launched with `Agent`, using their phase's literal block.** They're not
  loaded with the `Skill` tool nor read from here: they'd run in the orchestrator's context, with the
  session's model, and fill it with code and reports. The orchestrator reads each phase's JSON and, if a
  gate fails, its `*.report.md`. Nothing else.
- **Phase 2b and 2c pass `model:` on purpose**, the one place a call overrides an agent's model: `model: "opus"`
  for a critical slice (implementer and reviewer), for the review of a standard slice that writes `#[OA\*]` strings, for an escalated fix round, and for the Closing review. No runner, on purpose:
  `pr-ready` (Phase 8). `eidas-compliance` is launched by `security-audit-core` with its model fixed.
- ⛔ **A subagent's result is waited for by its completion notification, never by polling its output
  file.** The file stays empty and the result arrives as a notification, so a `grep` loop on it never
  matches: on TASK-046 the implementation agent spent 10 minutes in `until grep -q reported <task>.output`
  after the run it waited on had gone green. The same holds for your own waits: launch, keep working or end
  the turn, and act on the notification. Long shell commands go with `run_in_background`.
- ⛔ **A phase is over when its agent's background work is too.** Every brief says it: return with nothing
  still running. If a notification arrives for an agent that already reported, check for leftover
  processes (`ps -eo pid,lstart,args | grep -E 'until |while '`) rather than waiting on it; and when you
  wait on a process yourself, match it so the matcher cannot match itself (`pgrep -f '[w]t-validate'`),
  since a plain `pgrep -f "<pattern>"` inside a loop whose command line contains that pattern never ends.

## Execution flow

### Phase 0 — Preparation

1. **Resolve the `.md`**: if an id was given, `docs/tasks/TASK-NNN-*.md` with Glob. If a path was given,
   use it. If the session is in the main checkout and the record is on a worktree's branch only, resolve it
   there (`git worktree list`).
2. **Read the header table** (README §2): `Status`, `Type`, `Why`, `Builds on`, `Scope`,
   `Decision record`, `Delivery bar`, `Sibling`. There's no `Complejidad`, `Tags`, or `Depende de`.
   - If `Status` or `Type` is missing → stop. `Why` is only required for tasks not yet implemented (see
     `spec-lint` Step 2).
   - Sections are **not** in fixed positions: locate scope and verification by intent, not by `§N`.
   - If there's a `Sibling` marked with ⚑ → **read it before starting**: the task can't be planned alone.
3. **Verify `Builds on`**: if a cited task is still `Not started` and ours reuses it as-is, or it lives in
   another branch that hasn't been merged → stop and say so.
4. **Branch, in a sibling worktree by default**: `<type>/<slug>` (`feat/notification-email-html`,
   `docs/task-conventions`), kebab-case, ASCII, from `develop` (precondition 3). **Without the task id in the
   name**: it goes in the PR body and in the `Status`.
   ```
   git worktree add -b <type>/<slug> ../f5sign-backend-<slug> develop
   echo '/f5sign-backend-<slug>/' >> ../.gitignore        # the workspace root's, per its Worktrees rule 1
   ../bin/sync-ai.sh                                       # or the worktree serves stale, committable AI files
   ```
   **If the record already lives on a linked worktree's branch** (`git worktree list`: `/task-author` created it
   with these same commands and committed the record there), do not create another: work from that worktree.
   Then work from `../f5sign-backend-<slug>`. **Why not branch in the main checkout:** the dev `worker`,
   `relay` and `custodian` bind the main checkout with `APP_DEBUG=0` and never recompile, so a branch that
   changes services, constructors or config runs new PHP against old wiring there, and the custodian's
   hourly sweep runs it against the dev database. A worktree also leaves the main checkout free, so two
   tasks can run at once. Stay in the main checkout only if the user asks for it, and then `make worker-down`
   for the task's duration.
5. **Workspace**: `{workspace}` = `<worktree absolute path>/var/task-runner/TASK-NNN/` (gitignored), the
   only one: every phase's brief, report and ledger live in the tree that is being validated. If it exists and
   there's no `--resume` → ask whether to resume or restart. ⚠ `var/` may be owned by root when tools ran in
   containers: if `mkdir` gives *Permission denied*, create it inside the container
   (`docker run --rm -v $(pwd):/var/www/html -w /var/www/html f5sign/backend:dev mkdir -p var/task-runner/TASK-NNN`).
6. **`run.log`** (JSON lines): `{phase: "prepare", status: "pass", at: ISO8601}`.
7. **Worktree lane**: from a worktree, `make -C ../f5sign-infra wt-backend-up src=$(pwd)` brings its lane
   up and **keeps** it, so every later run (baseline, TDD, gates) reuses it instead of paying the startup
   again. Tear it down after Phase 6: `make -C ../f5sign-infra wt-backend-down src=$(pwd)`; once the branch
   is merged, remove the worktree (`git worktree remove`) and its root `.gitignore` line.
8. **Baseline before touching a single line**, on the hermetic tiers:
   `make -C ../f5sign-infra wt-backend-test src=$(pwd) fast=1` (Unit/, Application/ and the PHPStan rule
   tests). Note the **exact number of tests and asserts** in `run.log` and in the summary: without it, you
   can't separate your own reds from environment ones. **A red baseline doesn't abort: it's declared.**
   `{"phase":"baseline","status":"pass","tests":N,"assertions":M,"harness":"…"}`.
   ⚑ **Not the full suite:** `Integration/` and `Acceptance/` are 95 % of the suite's time and they run again at
   the end of the task regardless, so the full baseline was answering in advance a question that only
   matters if something ends up red. If a slow-tier test IS red at the end, attribute it then: a checkout
   of the merge-base and one filtered run of that class give the same answer the baseline would have.

### Phase 1 — `spec-lint` + claims check [GATE]

Both in the **same message**, alongside the baseline: they only read.

```
Agent({
  subagent_type: "spec-lint-runner",
  description: "spec-lint on TASK-NNN",
  prompt: "Task: {mdPath}. Workspace: {workspace}. Write the report to {workspace}/spec-lint.report.md. Return the JSON summary as the last line of your response."
})
Agent({
  subagent_type: "spec-claims-runner",
  description: "claims check on TASK-NNN",
  prompt: "Task: {mdPath}. Decision record: {ADR path from the header, or none}. Workspace: {workspace}. Return the JSON summary as the last line of your response."
})
```

`spec-lint` checks the record's shape; `spec-claims-runner` checks that what it says about **today's code**
is true and that its verification bars can go green. The second exists because TASK-046 passed the first
clean while carrying a false mechanism, a missing race and an unmeetable bar (2026-09-23). A `block` from it
is the user's to resolve — the record changes, or the decision does — before Phase 2; an `unmeasured-external`
capability is measured first, as the first step of Phase 2 at the latest.

The runner has no `Write`: it returns its findings, and **you** save them to
`{workspace}/spec-claims.report.md`.

⛔ **Resolving a block edits the record, and the edit is unchecked until `spec-claims-runner` runs again.**
Before Phase 2, re-run it on the edited record with the record's diff since its first run in the prompt
(*"Check these changed passages first; they were written to resolve your previous findings"*). A change made
after a check invalidates the check, and the edits written to answer it are the least checked text in the record.
Learned on TASK-053 (2026-10-07). The check found that the stated backstop, a session purge, did not exist. The
orchestrator replaced it with a reactor on "each of the envelope's terminal facts", written without opening one.
`EnvelopeVoided` and `EnvelopeClosedBySender` close an envelope without ending it, and
`EnvelopeCompleted` waits for every seal, so the failure case the new decision was built around could not occur.
The maintainer caught it in review.

If `status: "fail"` → supervised: show the report and ask (edit the `.md` and retry, or abort);
auto: abort.

### Phase 2 — Plan, then one slice at a time [GATE]

The task is planned once on the top model and implemented in small slices, each by a **fresh** agent that reads
only its slice and `constraints.md`. One agent implementing a whole task reread its whole growing context on every
turn: on TASK-048 that was 895 turns with the context reaching 966k tokens. A fresh agent per slice keeps each
turn small, and a plan precise enough lets most slices run on sonnet.

#### 2a — Plan

```
Agent({
  subagent_type: "plan-runner",
  description: "plan TASK-NNN",
  prompt: "Task: {mdPath}. Worktree: {absolute path}. Workspace: {workspace}. You cannot ask the user: if the skill needs a decision (a cross-cutting ADR), draft it as Proposed and return status \"awaiting-adr-acceptance\". Return the JSON summary as the last line of your response."
})
```

- ⛔ **If it returns `awaiting-adr-acceptance`, it's the user's turn.** There's a cross-cutting decision
  (it contradicts an accepted ADR, opens a cross-BC dependency, touches Kernel/Foundation, or edits
  `deptrac.yaml` / `phpstan.dist.neon` / the baseline) with the ADR drafted as `Proposed`. Present it —what it
  decides, what it rules out, what it forbids— and **stop**, even in `--auto`. Forbidden: accepting it on the
  user's behalf, re-running the plan to see if it passes, or trimming the change so the decision stops being
  needed.
- If it fails with `"spec contradictorio"` or `"contexto insuficiente"` → ask the user to expand the `.md`.
- **Plan check, before the user sees the plan.** Scripted where possible, otherwise `Explore` with
  `model: "haiku"`: every AC/S/V id and sub-id is in a slice's `Covers` and in a Tests row; every scope-`In` path
  is in a slice or listed as untouched; every new handler, listener, controller or route has `Registers`; the
  trigger words (`migrations/`, a lock, `_authn`, `Contract/`, RLS) imply `critical`; no TBD or placeholder;
  method names are consistent across slices. A failure goes back to `plan-runner` once, in amend mode. No Opus
  plan review: this check and the approval view below catch what such a review would.
- **Supervised: show the plan before any slice runs.** The view carries: the slices with tier and a one-line
  reason for the tier; the criteria → slice matrix with uncovered ids highlighted; the decisions the plan made
  that the record did not; and `plan.md § Sweep terms`. The user approves, corrects or re-cuts; to override a
  tier they say "NN critical" or edit `Tier:` in `slices/NN.md`, and the runner reads the tier from the slice
  file at launch. `--auto` goes on.
- Create the ledger `{workspace}/progress.md`. First line: `plan: approved <date> | record sha1 <hash>`
  (`git hash-object` of the record). Then one line per slice:
  `- [ ] NN title (tier) | commits a..b | round N | findings slices/NN.findings.md`.
  **The ledger, not your memory of the conversation, says what is done**: after a compaction or a `--resume`,
  continue at the first unchecked slice and trust the checked ones (`git log` confirms their commits).
- **`--plan-only` stops here.** Running 2b in a fresh session with `--resume` (or `/compact` after 2a and after
  2c) keeps the orchestrator's context small; the ledger makes that safe.

#### 2b — Each slice: implement, review, fix

In the ledger's order, one slice at a time (a worktree's lane takes one run at a time, so slices don't run in
parallel). ⛔ **Never Read a `*.report.md` or `*.review.md` in full unless its status is not a pass**: consume the
JSON. Findings travel by file, not through your context.

```
Agent({
  subagent_type: "slice-implementer",
  description: "TASK-NNN slice NN",
  model: "opus",            // ONLY for a critical slice; omit it otherwise so the agent's sonnet applies
  prompt: "Slice: {workspace}/slices/NN.md. Constraints: {workspace}/constraints.md. Worktree: {absolute path}. Write your report to {workspace}/slices/NN.report.md. Return the JSON as the last line."
})
```

Act on its status:

| Status | What you do |
|---|---|
| `DONE` | Review it (below) |
| `DONE_WITH_CONCERNS` | Read the concerns. One about correctness or scope is fixed before review; an observation goes to `plan.md § Deviations` |
| `NEEDS_CONTEXT` | Answer from the task or the plan if you can, by fixing the slice file, and launch a fresh implementer. If the answer changes the plan, it is the user's (supervised) or an amend (below) |
| `BLOCKED` | Something has to change before a retry: more context, the stronger model, a smaller slice, or a corrected plan. ⛔ **Never relaunch the same model on the same slice unchanged.** A decision (ADR) or a mis-cut slice goes to `plan-runner` in amend mode; an ADR it drafts goes to the user as in 2a |

**Caps** (`NEEDS_CONTEXT` and `BLOCKED` are not free loops):

| What | Cap |
|---|---|
| `NEEDS_CONTEXT` + `BLOCKED` relaunches | 2 per slice |
| Amends of the plan | 1 per task, plus 1 per Phase 3 fix slice (the existing maximum of 2) |

Past a cap: supervised → ask the user; `--auto` → stop with the state saved (ledger and workspace intact), never
abort or delete.

Then the review, by a reviewer who sees only the slice, `constraints.md`, the report and the diff:

```
Agent({
  subagent_type: "slice-reviewer",
  description: "review TASK-NNN slice NN",
  model: "opus",            // ONLY for a critical slice, or a standard slice that writes #[OA\*] strings
  prompt: "Slice: {workspace}/slices/NN.md. Constraints: {workspace}/constraints.md. Report: {workspace}/slices/NN.report.md. Review file: {workspace}/slices/NN.review.md. Worktree: {absolute path}. Range: {first commit of the slice}^..HEAD. Return the JSON as the last line."
})
```

**Mechanical slices are always reviewed, but together.** Consecutive `mechanical` slices are reviewed in one
`slice-reviewer` call (sonnet) over their combined diff, naming each slice file, before the next
non-mechanical slice starts.

**Fix loop, five rounds at most per slice.** Each round is one fix and one review.

- Write the open findings to `{workspace}/slices/NN.findings.md` and pass the **path**: `SendMessage` to the
  slice's implementer in rounds 1–3 (it already has the slice in context; keep the spawned agent's id), or a
  fresh `slice-implementer` brief that also names the report. If that agent can no longer be resumed (a crash,
  a new session), launch a fresh implementer with the findings and the report instead.
- Rounds 2+ review `Range = <tip before the fix>..HEAD` and also receive the open findings.
- **Escalation to Opus** on the first repeat of a finding about authoring rules 1, 2, 5 or 6 or about security,
  tenant or consent; otherwise after round 3. The fresh implementer gets `model: "opus"` and the brief line
  `Model: opus`.
- **Before round 4, diagnose.** If the findings say the slice is mis-cut, call `plan-runner` in amend mode
  instead of relaunching.
- After round 5, you rule on each finding left: fix it yourself if it is load-bearing, or record it in
  `plan.md § Deviations` with the ruling. In `--auto`, stop if any is about security, tenant or consent.

When the reviewer approves, **one Edit** does all of this: ticks the slice in `progress.md` (commit range, round),
appends the report's `termsChanged` to `plan.md § Sweep terms`, appends the slice's deviations to
`plan.md § Deviations` (one line per item, slice id first), and appends to `constraints.md § Landed so far` one
line per new or changed symbol: `Symbol — file — the one-line contract its docblock claims`. Add `delegated` and
`concerns` to the slice's `run.log` line. Next slice.

**Resume** (`--resume`, or after a compaction):
1. Re-run `make -C ../f5sign-infra wt-backend-up src=$(pwd)` (idempotent).
2. A slice with commits but unticked goes straight to review.
3. Continue the round counter from the ledger.
4. If the record's hash differs from the ledger's first line, list the changed ids and ask.

#### 2c — The whole branch, once

When every slice is ticked:

1. `test-runner` (no `model:`): full suite + gates, every tier, on the kept lane. Its result is
   `last_green_run`: `sha` = the `tree` field's short sha, tests and assertions from `counts`, plus the harness
   and the log. A red here is attributed and fixed as a new slice.
2. `changes.diff`: `git diff $(git merge-base HEAD develop)..HEAD > {workspace}/changes.diff`.
3. Refresh `context-digest.md` from the slice reports and `changes.diff`: contracts affected, data model
   touched, what was left out, and its `## Task summary` section.
4. **Closing review**: `slice-reviewer` with `model: "opus"`, `Range = merge-base..HEAD`, in its closing
   mode, writing `{workspace}/closing.review.md`. It gets `plan.md § Sweep terms`, `constraints.md § Landed so far`, every slice's `review.md` and the
   record. Every task gets it.
5. **Closing slice** (critical; Files = whatever the sweep hits), only if the plan lists a retired term or an
   ADR to land (the five places of `plan-backend` § Decision gate), the task adds a registration (a listener, a
   Messenger handler, a route or a tagged service), or the closing review returned `changes`. `plan-runner`
   writes it in amend mode; it then runs through 2b. After it, repeat 1–3 so `last_green_run` is the tip.
6. Log every slice in `run.log`: tier, model, rounds, turns, tokens, status (Phase 7 reads these).

### Phase 3 — Conditional validations

The condition is **what the diff touches**, not a list of tags (an enumeration exempts everything not yet
on it):

| Skill | Subagent | Invoked if the diff touches |
|---|---|---|
| `doctrine-guard` | `doctrine-guard-runner` | `migrations/`, `src/**/Infrastructure/Persistence/`, or SQL/RLS in any file |
| `contract-check-backend` | `contract-check-runner` | `src/**/UI/Http/`, `config/routes/`, any `#[OA\`, or a `Contract/Event/` |
| `task-validate-backend` | `task-validate-runner` | **always** |
| `security-audit-core` | `security-audit-runner` | **always** (delegates to `security-audit-backend`, and to `eidas-compliance` if the diff touches signing or crypto: `src/F5Sign/SignatureExecution/`, `Foundation/Crypto/`, DSS, PAdES) |

Prerequisite for `contract-check-backend` if there are endpoints, **before** launching the gates: the
OpenAPI dump of **this** tree into the workspace — from a worktree
`make -C ../f5sign-infra wt-backend-sf src=$(pwd) cmd="nelmio:apidoc:dump --format=json"` (the output
carries the lane's `==>` lines around the JSON: keep from the first `{` to the last `}`); from the main
checkout `make -C ../f5sign-infra sf cmd="nelmio:apidoc:dump --format=json"`.

One block per gate, **all in the same message**, `security-audit-runner` included: every one of them only
reads the tree and `changes.diff`, so none waits on another.

```
Agent({
  subagent_type: "task-validate-runner",      // or "doctrine-guard-runner" / "contract-check-runner"
  description: "task-validate on TASK-NNN",
  prompt: "Task: {mdPath}. Workspace: {workspace} (changes.diff is there). Harness: {the one from precondition 5}. infection: deferred (Phase 3b runs it once, at the end). last_green_run: {sha, tests, assertions, harness, log from Phase 2c}. Paths you may touch: {list}. Report anything outside them, do not edit it. {For every gate except task-validate:} Do not run tests on the lane: cite last_green_run; if you need a run it does not cover, say so in your report. Return the JSON summary as the last line of your response."
})
Agent({
  subagent_type: "security-audit-runner",
  description: "security-audit on TASK-NNN",
  prompt: "Task: {mdPath}. Workspace: {workspace} (changes.diff is there). The diff {does|does not} touch signing/crypto. last_green_run: {…}. Do not run tests on the lane: cite last_green_run; if you need a run it does not cover, say so in your report. Return the JSON summary as the last line of your response."
})
```

`last_green_run` lets `task-validate-backend` skip a second full suite on the commit Phase 2c already ran
it on (its Step 1). Pass it verbatim; the gate checks that the `sha` is still the tip.

Rules for the split (parallel agents on the same tree):

- ⛔ **Each agent gets its list of paths and the order to report, not edit, whatever it sees outside them.**
  Without it, there's no telling whose delta each one is. And reporting what's outside is often the most
  valuable finding.
- ⛔ **Before splitting, go through `§Scope` and check that every surface it names has an owner; whatever
  doesn't have one is yours.** The lists keep agents from stepping on each other and make invisible whatever
  falls between them: a missing Messenger handler, or prose the task itself said to change. The unit that
  needs an owner is the **claim** that changes, not the file (`CLAUDE.md` authorship rule 1).
- ⛔ **Only `task-validate` runs tests on the lane in this phase.** A worktree's lane takes one run at a
  time, and the gates run in parallel: whichever asks for it while Infection holds it waits for Infection.
  On TASK-046 `contract-check` sat queued for over ten minutes that way. So `doctrine-guard`,
  `contract-check` and `security-audit` **cite `last_green_run`** (sha, counts, log) when they need a test
  to have passed, after checking its sha is the tip; a run it does not cover goes in their report, and you
  launch it **after** `task-validate`, not beside it. What runs no tests (the OpenAPI dump, a
  `wt-backend-sf` wiring check) is done **before** the phase starts.
- **With agents still running, never `git add -A`**: it commits someone else's work half-done. Explicit
  paths, or wait until none are left.
- **The three gates and `security-audit-runner` don't have `Edit`**: they report, they don't fix. If a
  brief needs to sabotage a file to see a guard fail, use `general-purpose` for that agent, require it to
  restore and prove it with an empty `git diff`, and note it in the `run.log`.
- **If the diff adds a listener, a middleware, or a tagged service, check that it's registered**:
  `debug:event-dispatcher <event>`, `debug:container --tag=<tag>`, `debug:messenger`. From a worktree run
  them with `make -C ../f5sign-infra wt-backend-sf src=$(pwd) cmd="…"`; `make sf` answers about the main
  checkout's wiring, so a listener only your branch adds reads as missing there. One that's not wired up is a silent no-op that the suite doesn't see, and no gate
  covers it.

If a hard gate fails → supervised: show the report and ask (a fix slice, written by `plan-runner` in amend mode
from the report and run through Phase 2b — max 2 iterations, or abort); auto: abort.

⚑ **Every brief names the workspace and the tree by ABSOLUTE path** (`{workspace}` is one): a subagent resolves a
relative path against the session's own directory, which may not be the worktree.

### Phase 3b — Infection, once, on the tip nothing will change

Phase 3 launches `task-validate-runner` with **`infection: deferred`**. Infection, about 35 minutes here, runs **only
after**:
- every gate has passed;
- every fix round (a fix slice run through Phase 2b with a gate's report) is committed;
- no blocker, no warning you chose to fix, and no unrecorded deviation is left.

Then launch `task-validate-runner` once more with **`infection: final`** and the tip's `last_green_run`. If that tip
changes `src/` again afterwards, Infection runs again: the covered-MSI you cite is the one measured on the tip you
merge.

Learned on TASK-054 (2026-10-08): Infection ran beside a `contract-check` that found a blocker, and the fix round made
its 84% stale before anyone read it.

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
  prompt: "Task: {mdPath}. Workspace: {workspace} (changes.diff is there). No other agent is running. Return the JSON summary as the last line of your response."
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
  prompt: "Task: {mdPath}. Workspace: {workspace} (all phase reports are there). Branch: {branch}. Return the JSON summary as the last line of your response."
})
```

⛔ **A subagent can't ask the user**, and moving an ADR from `Proposed` to `Accepted` needs their OK. If the
runner returns `"awaiting-adr-acceptance"` with each ADR and its artifact, **you ask** (also in `--auto`).
If they accept, apply the status change in its own commit, without signing the commit.

### Phase 7 — Confirmation (supervised only)

Summary of phases, changed files, added tests, covered criteria, active warnings, and **which harness
validated**. Add the cost table, from `run.log`:

| slice | tier | model | rounds | status | turns/tokens |
|---|---|---|---|---|---|

Turns and tokens come from the agent result's usage when it carries them; leave the cell empty otherwise.
`task-close` copies a five-line cost block (totals per model, rounds, escalations) into the record's
deviations section. After three tasks have run under this flow, re-measure against TASK-048 and TASK-054 and
write the comparison to the workspace root's `notes/`. Ask: open a PR?

### Phase 8 — `pr-ready`

⛔ **`gh` isn't installed** (neither on the host nor in `f5sign/backend:dev`), so the PR is opened by hand.
Say so in the summary, don't report it as a failure. Once `gh` is available: only if the user confirms (or
`--auto`), push, `gh pr create` against **`develop`**, and the URL to the `.md` in a follow-up commit. **No
single commit or `--amend`**: the repo merges multi-commit PRs.

## Contract with child skills

Each child skill receives `taskDir` (`{workspace}`) and `taskMdPath`, writes its
`*.report.md` to a predictable path, and returns as its last message `{ status, summary, issues?, metrics? }`.

## run.log

One JSON line per phase: `{"phase":"prepare","status":"pass","at":"2026-08-17T10:15:00Z"}`. One per slice and
agent: `{"phase":"slice","slice":"03","tier":"critical","agent":"implementer","model":"opus","rounds":2,"status":"DONE","turns":41,"tokens":512000,"delegated":[],"concerns":[],"at":"…"}`.

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
- Doesn't create tasks: `/task-author` does (or by hand, following `docs/tasks/README.md`).
- Doesn't merge PRs.
