---
name: task-runner
description: Single orchestrator for the task-execution skill stack. Runs a Planning/ task end-to-end by invoking specialized skills (spec-lint, implement, task-validate, security-audit, etc.), managing gates, the workspace at var/task-runner/T{id}/, the git branch, a single commit, and the final PR. Use it with /task-runner T{id} or /task-runner {path to the .md}. Trigger with "run T02.1.1", "run task X", "task runner on...", "run the next task in planning".
---

# Task Runner

Stack orchestrator. See the full design in `Implementación/Skills de Ejecución de Tareas/common/01 - Task Runner.md`.

## Invocation

```
/task-runner T{id}                    # e.g.: /task-runner T02.1.1
/task-runner {absolute path to the .md}
/task-runner T{id} --auto             # unsupervised mode (default: supervised)
/task-runner T{id} --resume           # resume an existing workspace
```

If no argument is passed, ask the user for the ID or path.

## Preconditions

Before starting, verify (and stop with a clear message if it fails):

1. The task's `.md` exists and is readable
2. `git status` is clean (no uncommitted changes on the current branch)
3. **The project's base branch** — today `develop` in backend and signer, `master` in infra and docs; read it
   from the repo's `CLAUDE.md` instead of assuming it. ⚑ **Branch from the *ref*, not from the checkout**:
   `git checkout -b <branch> <base>`. It is equivalent in any environment and is the only form that works in
   a **linked worktree** —the environment precondition 5 talks about—: there, `git checkout <base>` is
   *impossible*, because the main checkout already has that branch checked out and git refuses to have the
   same branch checked out twice. ⚠ **Fixed 2026-08-25, and this precondition used to say "checkout to base
   before creating the new branch"**: worded that way it blocked itself exactly where it's needed most.
4. **The stack is up, and it's checked from `../f5sign-infra`, never with `docker compose` from this
   repo.** ⚠ **Fixed 2026-08-25: this used to say `docker compose ps` and listed «postgres, rabbitmq, redis»
   as the essential services.** Both halves were false. The stack is defined by `f5sign-infra` and its
   targets, not each repo — and in the backend, Symfony Flex also generates its own `compose.yaml`, which is
   disabled and gitignored, so a `docker compose` from the repo points at something else. And **redis is
   not essential**: its two consumers are the `cache.rate_limiter` pool and `LOCK_DSN`, and in `test` that
   pool is replaced by `cache.adapter.array`, so no test run needs it.
   Check: `make -C ../f5sign-infra worker-status` responds, or `docker ps` shows the `f5sign-*`
   containers. If not → stop with *"environment not available: `make -C ../f5sign-infra up`"*.
5. ⚑ **Are you in a linked worktree? Then the normal targets validate SOMEONE ELSE's tree, and report
   green for it.** `f5sign-infra/docker-compose.override.yml` bind-mounts `../f5sign-signer` and
   `../f5sign-dashboard` — the **main** checkouts, written by hand. A worktree is never mounted, so
   `make test-signer` and its siblings run against whatever branch the main checkout is sitting on: your
   edits are not inside the container and **nothing warns you**. The run passes, the numbers are
   plausible, and the answer is about a different branch.
   - **Check before trusting a run:** `git rev-parse --git-dir` — a path containing `/worktrees/` means
     you're in one. `git worktree list` names the main checkout, which is the tree those targets actually
     validate.
   - **From a worktree, the ephemeral lane, which DOES mount *your* tree:**
     `make -C ../f5sign-infra wt-signer src=$(pwd)`. It spins up a lane isolated by `STACK_NS=wt-<lane>`,
     with no ports to the host, runs lint + typecheck + unit (**no E2E**), and tears itself down when done.
     `flock` caps it at **2 signer lanes** at a time (`WT_CAP_SIGNER`). The backend equivalent is
     `wt-backend`, with cap 1 and `WT_GATES` to pick gates; its own `/task-runner` documents it in detail.
   - ⛔ **`wt-dashboard` does not exist.** The dashboard has no lane or suite yet (it arrives with EP26),
     so from one of its worktrees **there is no isolated validation path today**. State it as such in the
     report; do not run `test-signer` from there and call it green.
   - **Pick a path and state it in the report.** A validation whose target wasn't your tree is worse than
     none, because it reads as green. Measured in the backend on 2026-08-17: a session in a worktree ran
     the suite, got `OK (16 tests)` and **inferred from that number** that 8 tests from the file it had
     just edited weren't being picked up — and reported it as a defect that failed a task's acceptance
     bar. The container was running a different branch, whose copy of that file has 6 tests. The same
     session had already reported "PHPStan green" for edits PHPStan never saw.

## Execution flow

> **Performance — principles (a run shouldn't take ~1h):**
>
> 1. **Shared heavy validation, not repeated.** The orchestrator runs the repo's validation suite (lint +
>    static analysis/typecheck + unit + build, with the commands from the repo's CLAUDE.md) **exactly
>    once** after `implement` (see Phase 3.0) and dumps the results to the workspace; `task-validate` and
>    `perf-smoke` **consume those artifacts** instead of recompiling/retesting. Running the same
>    build/test 3-4 times (implement + task-validate + perf-smoke) is the biggest waste.
> 2. **Serialize the heavy stuff, parallelize the static stuff.** In repos with a single app container,
>    two simultaneous builds compete for CPU/cache and cause flakiness → don't parallelize build/test
>    commands. `security-audit`, on the other hand, is static analysis of the diff and DOES run in
>    parallel with `task-validate`.
> 3. **`implement` gives fast feedback.** During its TDD it runs only unit + lint + typecheck (fast); not
>    the full build at the end — that authoritative run is done once by `task-validate`. E2E is not run
>    by ANY phase: ⛔ **E2E is manual only** (owner, 2026-09-23): never launched while developing or validating a task — a full run is ~15 min and every browser on the machine. It runs only when the user explicitly asks for it.
> 4. **Tight gate prompts.** Each child skill receives the path to `changes.diff` and the exact list of
>    touched files; it's instructed not to re-explore the whole repo nor re-run build/test if the
>    workspace's shared artifacts already exist.

### Phase 0 — Preparation

1. **Parse the argument** → resolve the path to the task's `.md` (if an ID was given, look for
   `Planning/F*-*/EP*-*/S*-*/T{id}-*.md` with Glob)
2. **Read the frontmatter** of the `.md`:
   - `Story Points`, `Tipo`, `Complejidad`, `Tags`, `Depende de`
   - If any is missing → inform the user and abort (normally `spec-lint` catches this afterward, but
     there are minimum fields needed to decide the flow)
3. **Check dependencies**: for each task listed in `Depende de`, read its `.md` and check Estado:
   - `completed` → OK.
   - `review` (implemented and committed, but its PR not merged → its code lives on its branch, not on
     the base): in **supervised**, ask whether to **stack (stacked branch)** — create this task's branch
     FROM the dependency's branch and compute `changes.diff` against that branch's HEAD (not against
     `master`). In **auto**, abort.
   - Any other state → **abort** with the message "dependency T{X} in state {Y}; complete it first".
4. **Create workspace**: `var/task-runner/T{id}/`
   - If it already exists and `--resume` wasn't passed → ask: resume from the last `pass` phase or
     restart from scratch
   - If restarting → delete the workspace and create it again
5. **Check the git branch**:
   - Name: `feat/T{id}-{title-slug}` (kebab-case slug of the task title, max 40 chars, ASCII)
   - If it doesn't exist → create from base and checkout
   - If it exists → checkout
6. **If tag `critical-path`** (backend only): run `composer perf:seed` — if it fails, inform the user and
   ask whether to continue (perf-smoke will warn). In **frontend** repos this does NOT apply (no DB seed;
   `perf-smoke` measures bundle/Lighthouse directly) → skip this step.
7. **Initialize `run.log`** (JSON lines, one line per phase) with the entry
   `{phase: "prepare", status: "pass", at: ISO8601}`

### Phase 1 — `spec-lint` [Haiku, GATE]

Invoke the skill via the Agent tool:
```
Agent({
  subagent_type: "general-purpose",
  model: "haiku",
  description: "spec-lint on T{id}",
  prompt: "Execute the spec-lint skill defined at .claude/skills/spec-lint/SKILL.md on task {mdPath}. Write the report to var/task-runner/T{id}/spec-lint.report.md. Return the JSON summary as the last line of your response."
})
```

Read the last message → extract the JSON. If `status: "fail"`:
- Supervised mode: show the report to the user, ask what to do (edit the `.md` and retry, or abort)
- Auto mode: abort with exit code 1

### Phase 2 — `implement` [Opus if Complejidad=alta, Sonnet if media/baja, GATE]

Decide the model according to the frontmatter's `Complejidad`.

Invoke the Agent with the corresponding model and prompt:
```
"Execute the implement skill defined at .claude/skills/implement-{stack}/SKILL.md on task {mdPath}   (implement-backend or implement-frontend depending on the repo).
Workspace: var/task-runner/T{id}/.
Model assigned: {haiku|sonnet|opus according to Complejidad}.
During TDD, run only unit + lint + typecheck in the container (fast feedback); do NOT run the full build at the end — that authoritative run is done once by task-validate (see Phase 3.0). Never run E2E: it is manual only, at the user's explicit request.
Commit changes as a single commit at the end. Produce context-digest.md, plan.md, and ensure changes.diff is generable.
Return the JSON summary."
```

If it fails with a diagnosis of type `"spec contradictorio"` or `"contexto insuficiente"` → do NOT
escalate, stop and ask the user to expand the `.md`.

If it fails for another reason (3 attempts of the assigned model) and the diagnosis justifies escalation
→ re-invoke the Agent with `model: "opus"` and **expanded context** (parent story README + parent epic
README + dependencies' `.md` + event catalog + cross-cutting-concerns + level-1 diagnosis).

If level 2 also fails → abort with a recommendation to enrich `Contexto requerido`.

Generate `changes.diff`: `git diff {base}..HEAD > var/task-runner/T{id}/changes.diff` where `{base}` is
the commit common with `master`.

### Phase 3 — Conditional validations

#### Phase 3.0 — Shared heavy validation (once only)

Before invoking the gates, the orchestrator runs the repo's heavy suite **once** and saves the artifacts
in the workspace so the child skills can reuse them (performance principle 1). Commands per the repo's
CLAUDE.md, **always in the container, never on the host**:

Dispatch by the `stack:` in `.claude/skills-config.yaml`, and by **whether or not you're in a worktree**
(precondition 5) — not by the repo's name:

| `stack` | Main checkout | Linked worktree |
|---|---|---|
| `frontend` (signer) | `make -C ../f5sign-infra test-signer` + `build` in the container | `make -C ../f5sign-infra wt-signer src=$(pwd)` |
| `frontend` (dashboard) | ⛔ no suite yet (EP26) | ⛔ no lane; declare "not validated" |
| `backend` | `make -C ../f5sign-infra test` | `make -C ../f5sign-infra wt-backend src=$(pwd)` |
| `common` (infra) | n/a — no app suite | n/a |

Dump to `var/task-runner/T{id}/docker-validate.log`; the `build` leaves `.output/` for `perf-smoke`.

⚠ **Fixed 2026-08-25: this used to say «Frontend (f5sign-signer/dashboard): `make -C ../f5sign-infra
test-signer`».** It lumped the dashboard into a target that only exists for the signer — `test-dashboard`
isn't in infra's Makefile, and the dashboard's own `CLAUDE.md` says its suite arrives with EP26 —, and it
didn't account for the worktree, which is the case where that command validates someone else's tree. And
this file is also the `/task-runner` of `f5sign-infra`, which has neither a frontend nor a PHP suite:
with `stack: common` this phase **does not apply** and is skipped, stating so, instead of hunting for a
command.

If this run already fails at lint/typecheck/unit/build → it's a hard gate failure: treat it as such
(stop/retry) without spending agents on gates that depend on a healthy build.

#### Phase 3.1 — Parallel gates

Determine which skills to invoke based on the frontmatter's tags and invoke them **in parallel**
(multiple Agent calls in a single message). Each one is passed the path to `changes.diff`, Phase 3.0's
artifacts, and the list of touched files, with the instruction **not** to recompile/retest what's already
covered nor re-explore the whole repo:

- `task-validate` [Haiku] — **always**, GATE (stack-specific skill: `task-validate-backend` /
  `task-validate-frontend`). Consumes `docker-validate.log` + `.output/` from Phase 3.0 and only adds
  what's missing (reading coverage/AC). Does not repeat lint/typecheck/unit/build, and does not run E2E.
- `security-audit` [Sonnet] — **always**, GATE. Static analysis of the diff → runs in parallel with
  `task-validate` (it barely touches Docker; no longer sequential).
  - If tags include `signing`, `crypto`, or `eidas`: `eidas-compliance` [Opus] will be invoked inside
    security-audit
- `doctrine-guard` [Haiku] if tags include `db`, `migration`, `rls`, `tenancy` (backend)
- `contract-check` [Haiku] if tags include `api` or `event` (stack-specific skill:
  `contract-check-backend` / `contract-check-frontend`)
  - Backend prerequisite: run `bin/console nelmio:apidoc:dump --format=json > var/task-runner/T{id}/openapi-snapshot.json` (if tag `api`)

Wait for all of them to finish. Consolidate the returned JSONs.

If any hard gate fails:
- Supervised mode: show the report, ask "retry implementation with the report as context" or "abort"
- If retrying: go back to Phase 2 passing the report as additional input (max 2 correction iterations)
- Auto mode: on the 1st hard gate failure that can't be auto-corrected, abort

### Phase 4 — Non-gate validations

- `perf-smoke` [Sonnet] if tag `critical-path` — non-blocking (stack-specific skill: `perf-smoke-backend`
  / `perf-smoke-frontend`)
  - **Reuses Phase 3.0's `.output/` (or build artifact)** (analyzes the already-built bundle); does NOT
    recompile. That's why it can be launched inside the same parallel block as Phase 3.1.
  - If high WARN: in supervised, ask whether to iterate

### Phase 5 — `docs-sync` [Haiku/Sonnet depending on activity]

Invoke if tags include `adr`, `config`, `breaking`, `event`, `worker`, `new-module`.

Model: Sonnet if the activity includes drafting an ADR; Haiku in any other case.

The changes are amended onto the existing commit: `git add <files-touched-by-docs-sync> && git commit --amend --no-edit`.

Not a hard gate: if it fails, warn and continue.

### Phase 6 — `task-close` [Haiku]

Always invoke. Edits the task's `.md` (Estado → review, Fin, Commit SHA, cleans up consolidated
tagMismatches, adds the Desviaciones section). Writes `notes.md` only if there are learnings.

### Phase 7 — Confirmation (supervised mode only)

Show the user:
- Summary of phases with status
- Changed files
- Added tests
- Covered AC
- Active warnings

Ask: open the PR now?

### Phase 8 — `pr-ready` [Haiku]

Invoke only if the user confirms (or auto mode).

> **The task's `.md` lives in `f5sign-docs` (a separate repo), NOT in the code repo.** Closing Seguimiento
> (Estado/Fin/Commit/PR) is a **separate commit in `f5sign-docs`**, never an `amend` to the code branch
> (cross-repo rule: mixing repos in one commit is forbidden). Stage only that task's `.md`.

1. Push the code branch.
2. Create the PR:
   - If `gh` is available: `gh pr create` with a title (conventional) and body (task + AC + validation
     table + test plan); mark it **draft** if there are active warnings.
   - If `gh` is **NOT installed** (the case for this environment): after the push, return the
     `…/pull/new/<branch>` link so the user can open the PR by hand (draft if there are warnings).
   - If the branch is **stacked** (dependency in `review`): warn to set the **PR's base** to the
     dependency's branch (not `master`) until it is merged.
3. Update the `.md`'s `PR/Branch` field (URL or creation link + stacking note) and **commit that change
   in `f5sign-docs`** (together with closing Seguimiento, in its own commit).
4. Return the URL/link to the user.

## Contract with child skills

Each child skill:
- Receives `taskDir` (var/task-runner/T{id}/) and `taskMdPath` as part of the prompt
- Reads what it declares it needs; doesn't re-read if it already exists in the workspace
- Writes its `*.report.md` to a predictable workspace path
- Returns structured JSON as the last message (parseable): `{ status, summary, issues?, tagMismatches?, metrics? }`

## run.log

After each phase, append a JSON entry to `run.log`:
```json
{"phase": "implement", "status": "pass", "model": "sonnet", "attempts": 1, "tokens_estimated": 12500, "duration_s": 145, "at": "2026-04-13T10:15:00Z"}
```

## Failure handling

- **Skill returns status=fail**: act according to the gate (hard → stop/retry; non-gate → warn and
  continue)
- **Agent tool fails** (network error, timeout): retry once with the same model; if it fails again,
  report to the user
- **Git fails** (conflict, rejected push): never use `--force` nor `reset --hard`; stop and request
  manual intervention
- **User's Ctrl+C**: the workspace stays in its current state; it can be resumed with `--resume`

## What it does NOT do

- Does not edit code
- Does not interpret reports from other skills (only reads their returned JSON)
- Does not invent tags, complejidad, or dependencies
- Does not create tasks (that's `/planning-scaffold`)
- Does not merge PRs
- Does not edit the per-repo copies of the skills (`<repo>/.claude/skills/`): they are **symlinks** to
  the workspace store. The source is `ai/shared/<skill>/` (or `ai/<repo>/.claude/skills/<skill>/` if it's
  specific to the repo) in the workspace's root repo, and it's distributed with `bin/sync-ai.sh`. Editing
  through the symlink writes the real file, which is correct — but **the change belongs to the root
  repo**, so `git add` from the subrepo sees nothing.
  ⛔ **Fixed 2026-08-25, and this line used to say the copies are "generated", that the source is
  `f5sign-docs/skills-library/`, and that it's propagated with `scripts/sync-skills.sh`.** Both files
  still exist, and that's why it needs to be said here: `skills-library/` has been **retired and frozen
  since 2026-06-01**, and `sync-skills.sh` does an `rm -rf` of the destination followed by `cp -r`.
  Running it today **deletes the symlinks, writes real AI files inside the subrepo** —which breaks the
  zero-AI-trace rule that this whole architecture is built on— **and reverts the skills to June**. Do not
  run it. The script itself has aborted since 2026-08-25 if attempted.

## Environment (F5Sign monorepo)

- **Tests/lint/typecheck/build ALWAYS in the container, never on the host** (see the repo's CLAUDE.md).
  Frontend: `make -C ../f5sign-infra test-signer*` from the main checkout, `wt-signer` from a worktree
  (precondition 5); E2E runs in a dedicated Playwright image, because the app container is Alpine and
  Playwright doesn't support it.
- **The task's `.md` lives in `f5sign-docs`** (specs repo), not in the code repo → closing Seguimiento and
  updating `PR/Branch` are commits in `f5sign-docs`, separate from the code commit (cross-repo rule).
- **`gh` might not be installed** on the host: `pr-ready` does a `push` and returns the
  `…/pull/new/<branch>` link to open the PR by hand; do not assume `gh pr create`.
- **Centralized skills**: to change a skill, edit the workspace store —`ai/shared/<skill>/` for shared
  ones, `ai/<repo>/.claude/skills/<skill>/` for repo-specific ones— and re-run `bin/sync-ai.sh`.
  `task-runner` is **shared** by dashboard, infra, and signer; the backend has its own, which diverged and
  is a different skill. ⚑ This file is a single one for three repos: before writing something specific to
  a stack, check whether it belongs in Phase 3.0's table or whether the repo's `CLAUDE.md` is its place.

## References

- Full design: `Implementación/Skills de Ejecución de Tareas/common/01 - Task Runner.md`
- Stack index: `Implementación/Skills de Ejecución de Tareas/README.md`
