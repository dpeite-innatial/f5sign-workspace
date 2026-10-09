---
name: implement-backend
description: 'Implements ONE slice of a planned backend task (PHP/Symfony) with property-driven TDD: reads only its slice file and constraints.md, writes the slice''s tests first, watches them fail, implements, sabotages the guard, commits, and returns one of DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED. Stops instead of deciding when the code does not match the slice or a cross-cutting decision appears. Launched by /task-runner Phase 2b through the slice-implementer agent; the plan comes from plan-backend.'
---

# Implement (backend) — one slice

You implement one slice of a task that `plan-backend` already planned. The slice says what to build, which
files, which reference to imitate, which tests to write and how to verify. **Design decisions were made in
the plan; your job is to carry them out exactly, and to stop when one is missing.**

> **Before writing code, read the [CLAUDE.md authorship rules](../../../CLAUDE.md).** They exist
> because the failure each one describes **happened in this repo, on a branch with `make qa` green**, and no
> gate sees them. This skill references them; it does not duplicate them, because a copy goes out of sync.

## Inputs

The orchestrator names, by absolute path:

- the slice: `var/task-runner/TASK-NNN/slices/NN.md`;
- `var/task-runner/TASK-NNN/constraints.md`;
- the worktree you work in;
- on a fix round, the path of the findings file (`slices/NN.findings.md`) and, when the orchestrator escalated, a
  `Model: opus` line.

Read those, and the files the slice names. ⛔ **Not the task's `.md` and not `plan.md`**: what you need from them
is in the slice and in `constraints.md`, and reading the rest is the context growth this split exists to avoid.

## Outputs

- Commits on the task's branch.
- `var/task-runner/TASK-NNN/slices/NN.report.md`, with these sections: `## Step 1 check` (3 lines: file opened,
  symbol expected, found), tests written, red reason seen, sabotage performed, files changed, `## Delegated`,
  `## Claims`, `termsChanged`, `registers`, anything you noticed outside the slice. A fix round appends
  `## Round N` and does not rewrite the report.
- Last line, JSON: `{"status":"DONE|DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED","slice":"NN","summary":"…","commits":["sha"],"covers":["AC-1"],"testsAdded":N,"concerns":[],"question":"…","delegated":[],"termsChanged":[],"registers":[{"symbol":"…","wiredIn":"…"}]}`
  (`termsChanged`: retired terms and symbols whose behaviour changed; `registers`: what this slice wired, per
  its *Registers* section).

## Execution

### Step 1 — Check the slice against the code before writing anything

Open the reference instance and every file the slice says to modify. If what you find does not match what the
slice says — a symbol that is not there, a reference that does something else, a test that already passes —
**stop**: `NEEDS_CONTEXT`, with what the slice expected, what is there, and why it matters. Don't adapt the
plan on your own. If the slice is unclear before you have edited anything, return `NEEDS_CONTEXT` with no
commits.

Also stop, whatever the slice says, if doing it would:

- need a choice between two shapes that the slice does not make;
- touch a file outside the slice's *Files*;
- trigger any item of the decision gate (`plan-backend` § Decision gate: an accepted ADR contradicted, a new cross-BC
  dependency, Kernel/Foundation, deptrac/phpstan/baseline, a new realization pattern). That is `BLOCKED`, with
  the decision named. You never draft the ADR here.

### Step 2 — TDD loop

For each test of the slice, in the order the slice lists them:

1. **Write the test** in the tier used by its siblings (`ls` the BC's test directory; being the only
   `*UseCase.php` with no `*UseCaseTest.php` next to it is the signal, and it has always been right). It
   must carry:
   - `#[CoversClass]` or `#[CoversNothing]` — `phpunit.dist.xml` has `requireCoverageMetadata="true"`
   - `#[UsesClass]` for collaborators, **including the exceptions the test asserts**
   - The criterion it proves, cited in the method's docblock as `@criterion TASK-NNN AC-2a S-1` (grammar:
     [`docs/tasks/README.md`](../../../docs/tasks/README.md) §8; the plan's `V-n` use the same form), beside the
     `P-§` citation if the property is catalogued (`tests/README.md`). A row split into sub-ids is cited per sub-id.
2. **Run it and watch it fail for the right reason** (not a syntax error, not a missing class), directly
   with `make`, not through `test-runner` (see *Validation cadence* below):
   `make -C ../f5sign-infra wt-backend-test src=$(pwd) only='<Class>::<method>' | tail -30`. Compare the red
   reason with the slice's *Guard that must fire* column: a test red for another reason does not prove the guard.
   ⛔ Never a hand-rolled `docker run` on `f5sign-net`: it shares the Postgres cluster and gives false
   reds in the relay (BL-138).
3. **Write the minimal production code.** A docblock states only what the slice's *Prose to write* gives you or
   what you verified in the tree this session; never copy the reference's rationale. List each
   X-because-Y you wrote in the report's `## Claims` (claim → `file:symbol`).
4. **Green.**
5. ⚑ **Sabotage the guard and watch the test fail for the right reason; restore it.** This is the step
   that catches tests that can't fail, and without it the property isn't proven — it's just asserted.
6. Regressions around what you touched: `… wt-backend-test src=$(pwd) changed=1 fast=1 | tail -30`.

#### Validation cadence

Measured 2026-09-23: the hermetic tiers (Unit/, Application/, PHPStan rule tests) are 2594 of 3293 tests
and run in ~23 s; Integration/ and Acceptance/ are 95 % of the suite's time (~4-5 min on their own). So the
slow tiers run **once, when the task is complete**, not per commit.

| When | What | How |
|---|---|---|
| Once, at the start (worktree) | check the lane is up | `make -C ../f5sign-infra wt-ls`; if it is absent → `BLOCKED` |
| Every red/green step | the test you are writing — **whatever its tier**, Acceptance included | `wt-backend-test src=$(pwd) only=<regex>` (~8 s), directly |
| Before each commit | static gates + hermetic tiers | `WT_GATES="lint arch phpstan test" WT_TIERS=fast make -C ../f5sign-infra wt-backend src=$(pwd) \| tail -40`, directly |
| All slices landed | full suite + gates, every tier | the orchestrator, through `test-runner` (Phase 2c), not you |

- A commit validated this way is green on the **fast tier only**. Say so in its body; the branch's green is
  the orchestrator's final full run.
- From the main checkout instead of a worktree, the same split with the shared stack:
  `make -C ../f5sign-infra test-db-setup` once, then `make -C ../f5sign-infra composer cmd="test -- --filter <X>"`.
- ⛔ Never Infection and never `qa` here: Infection runs once, in `task-validate-backend`.
- The lane is the orchestrator's: it is already up. Don't bring it up or tear it down.
- **Turn budget:** no green test after about 60 tool calls → `NEEDS_CONTEXT` or `BLOCKED`, with what you tried.
- ⛔ **Wait for a subagent (`test-runner` or any other) by its completion notification, never by polling
  its output file.** That file stays empty — the result arrives as a notification — so a loop such as
  `until grep -q reported <task>.output; do sleep 10; done` never matches and holds the whole task until the
  shell times out. On TASK-046 it held the finished implementation for 10 minutes after the run it waited on
  had already gone green. Launch the agent and keep working, or end the turn; you are re-invoked when it
  reports. A long **shell** command is the same: `run_in_background`, and wait for its notification.
- ⛔ **Return with nothing of yours still running.** Before the final JSON, every background command and
  agent you launched has finished or been stopped. On TASK-046 two wait loops outlived the agent that
  started them by over an hour, and kept notifying the orchestrator about work that was already done.
### Step 2b — Delegate replication

**Only when the slice says `Tier: critical` or the fix-round brief says `Model: opus`**; on sonnet,
doing the edit yourself costs the same as briefing another sonnet. The owner's priority is token cost, and part of every task is the same shape repeated: the cases 2..N of a
table, the same method in every fake and spy of a port, a changed signature at every caller. That
repetition goes to the `replicator` agent (`.claude/agents/replicator.md`, which declares its own model).
Call it **without `model:`**.

⛔ **Never a fork to delegate.** A fork inherits the launcher's model, ignoring `model:`, and re-reads the
whole conversation on every turn, so it costs more than doing the edit yourself. The `replicator` takes a
closed brief. If the work needs your context to be understood, it was not mechanical and is not delegable.

**What may be delegated. This is the whole list, not examples:**

| Kind | Agent |
|---|---|
| Replicate a shape that already exists **and is pinned by a passing test**: the remaining cases of a table, the same method in each fake, spy or implementation of a port | `replicator` |
| Propagate a changed signature to every caller PHPStan names | `replicator` |
| Add an attribute or annotation to a list you have already censused (`#[SensitiveParameter]`, `#[UsesClass]`, `services.yaml` entries) | `replicator` |
| Edit prose from an explicit before/after list | `replicator` |
| Read a large file or log and return what matters | `Explore` with `model: "haiku"` |

⛔ **Never delegated:**
- domain, use cases and guards;
- migrations;
- the **first** instance of any shape;
- sabotages;
- `#[OA\*]` strings;
- deciding which claim is stale;
- anything that needs a choice between two shapes.

**Threshold: 3 targets or more.** Below that, writing the brief costs more than the edit.

**The loop:**
1. **You write the brief.** It names:
   - the reference instance (file and symbol);
   - the exact list of targets (file and symbol);
   - the rule that maps the reference onto each target;
   - what must not be touched;
   - the filtered test command that must pass.
2. **The `replicator` edits and returns the list of what it changed.** It has no Bash, so it cannot run
   tests, touch git or commit.
3. **You review its `git diff`, run the filtered test, and commit.** The authoring rules stay yours. Read
   every hunk: a copied docblock copies its claim (the repo's authoring rule 2).
4. **Two failed rounds and you do it yourself.** A third brief costs more than the edit.

Record each delegation in the report's `## Delegated` and in the final JSON's `delegated`.

**Retry policy:** 3 edit-test iterations per test. After that, stop: `BLOCKED` with what you tried and what
you saw (Step 6).
### Step 3 — OpenAPI (if you touch `UI/Http/` or `config/routes/`)

- `#[OA\Response]` for every **reachable** HTTP code, `#[OA\RequestBody]`, DTOs with typed
  `#[OA\Property]`, security scheme if the route is protected.
- ⚠ **The strings in `#[OA\*]` are emitted literally into the spec the frontend team ratifies.** They
  aren't internal comments: one of them ended up telling clients to send a value the endpoint doesn't
  accept. They're covered by the rule 1 sweep.
- Verify: `make -C ../f5sign-infra sf cmd="nelmio:apidoc:dump --format=json"` completes without error.
- The strings come from the slice's *Prose to write*; you write none of your own.
### Step 4 — Non-negotiable rules

- **The domain doesn't import Symfony or Doctrine.** Deptrac (`composer arch`) and the PHPStan placement
  rules watch this; if you spot it before they do, redo it.
- **Between BCs, only the other's `Contract/` is visible.** `deptrac.yaml` says so explicitly (count its
  layers there, not here): `EnvelopeApplication` can see
  `SessionContract`, `SignatureExecutionContract`, `IdentityAccessContract`… and **no other BC's `Domain`
  or `Infrastructure`**. `Kernel` depends on nothing (`Kernel: []`). If you need data that only lives in
  another BC's `Domain`, the answer is a read port in its `Contract/` (ADR-0008), not an import — and
  **that is a decision**: `BLOCKED` (Step 1), not something settled while implementing.
- ⚑ **Notification is a support BC: nothing can depend on it** (ADR-0037, category (c)). The gate **does**
  catch this: deptrac's `ruleset` is a **positive allowlist** and the repo runs with `Uncovered 0`, so a
  class that depends on a disallowed layer produces `DependsOnDisallowedLayer`. What it **can't** catch
  going red is **adding the entry to the allowlist**: that doesn't violate anything, it just stops
  watching. So the question when reviewing isn't *"does deptrac pass?"* but *"does this diff touch
  `deptrac.yaml`?"* — and if it does, that is a decision: `BLOCKED` (Step 1), not something settled while implementing.
- **Only aggregate roots have a repository.** Subordinate entities are modified through their root.
- **Commands through the bus; queries via direct call.** ADR-0008: **there is no QueryBus**, and a
  `QueryHandler` is realized with a direct `handle(Query): R` — its §Counterpoint expressly rejects
  putting an adapter in between. So a controller **does** inject a query handler and
  that's conformant; what it must not do is inject a *command* handler bypassing the bus, because the bus
  is where the transaction, the tenant and the issuer live (ADR-0010).
- **VOs: the shape depends on the type, and a blanket rule is wrong** (ADR-0005). A **wrapper** (a single
  field) is `final readonly`; a **composite** (several fields) is `final` and **not** readonly, with a public
  constructor. The model to imitate is
  [`Settings`](../../../src/F5Sign/Envelope/Domain/ValueObject/Settings.php), which says so in its own
  docblock: *"final (not readonly) per ADR-0005"*. Requiring `final readonly` across the board reintroduces
  the defect ADR-0005 exists to record. Named constructors yes, in both cases.
- **Domain events in the past tense** — ADR-0011, illustrated with events this repo really has:
  `EnvelopeCreated`, `EnvelopeSent`, `EnvelopeCompleted`, `StepCompleted`. ⚠ And the surface form is only
  half **cosmetic**: ADR-0011 says what's load-bearing is the **ownership partition** (the prefix belongs
  to a BC) and the **mirror**, and that the prefix↔BC lint is *candidate rule, not yet written*. Careful
  about reading it literally: `EnvelopeReadyToSeal` is not a past-tense verb and **is conformant** (name of
  a transition to a target state, §4), and ADR-0011 is `Proposed`, so under repo rule 7 it does not bind
  yet.
- **Persistence is DBAL only.** The ORM was retired (ADR-0018): `doctrine/orm` is not a dependency and
  there is no `*.orm.xml` anywhere. ⛔ **Don't write a docblock that justifies anything with ORM
  hydration/reflection, the outbox, or `AuditCommandInterface`**: these are already-retired mechanisms, and
  authorship rule 2 exists because they came back as a *reason* in prose after disappearing from the tree.
- **A schema change is a migration**, and if the migration writes rows the domain later reads,
  authorship rule 6 applies (enumerate the aggregate states the row falls under; prefer a predicate that
  states the property — `sent_at IS NOT NULL` — over one that enumerates today's states).
### Step 5 — Commits

**No single-commit policy.** This repo integrates multi-commit PRs and merges from `develop`; an
`--amend` on something already pushed forces `--force-with-lease` for no gain. Small, coherent commits,
each with a message that says *why*, and `git add` of specific files (never `git add .`).

Before the last commit:

1. `git status` must not bring in anything outside the slice's *Files*, nor anything `constraints.md` declares **Out**.
2. If the change re-scoped, renamed or re-gated a concept: rule 1 sweep, in one command —
   `rg -n '<retired-term>' src tests migrations docs config CLAUDE.md`. **The diff is not the search
   surface**: a file that still needs the edit shows up with an empty diff. And `CLAUDE.md` is part of the
   sweep: it's the one surface that doesn't just go stale but starts **giving bad instructions**.
3. If the task discharges an ADR deferral, or makes something an ADR had marked pending come true, that
   ADR's `Status` / `Enforced by` / `Realized in` go **in this changeset** (authorship rule 7).
### Step 6 — Report and status

| Status | When |
|---|---|
| `DONE` | Every test of the slice written, seen red for the right reason, green; sabotage done; committed |
| `DONE_WITH_CONCERNS` | Done, and something deserves a look before review: a docblock claim you could not verify, a smell outside the slice, a test that only reaches the property indirectly |
| `NEEDS_CONTEXT` | Step 1 found the slice and the code disagree, or the slice leaves a fact out |
| `BLOCKED` | A decision the slice does not make, a Step 1 stop, or the retry policy ran out |

`question` carries what you need, stated so the orchestrator can answer it or route it. Write the report, then
the JSON as the last line.

## What it does NOT do

- Doesn't plan, re-scope or decide between shapes: the plan did, or the orchestrator will.
- Doesn't audit security, compliance or performance.
- Doesn't touch documentation outside the code (that's `docs-sync`), except Nelmio's inline OpenAPI and
  the prose corrections rule 1 requires in the same changeset.
- Doesn't run the full suite or Infection: the orchestrator does, once all slices land.
