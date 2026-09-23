---
name: task-validate-backend
description: 'Hard gate for functional quality in backend (PHP/Symfony): runs the suite (composer test), PHPStan level 9, Deptrac, lint, and measures structural strength with Infection''s covered-MSI instead of a line-coverage percentage. Watches the diff of deptrac.yaml/phpstan and checks that the ruleset''s four load-bearing shapes stay intact — the gate does catch a forbidden dependency, but it can''t catch someone extending the allowlist to permit it — reporting the delta and requiring the ADR that declares it, and checks that an ADR that lands does so complete. Checks that the properties declared in the task''s §Verification are actually executed, and that the diff doesn''t stray outside its §Scope. Only for repositories with a PHP/Symfony stack. Use it with /task-validate-backend TASK-NNN. Trigger with "validate backend task", "run phpunit", "check PHPStan and deptrac".'
---

# Task Validate (backend)

Hard gate for functional quality. Always invoked.

## Invocation

```
/task-validate-backend TASK-NNN
```

## Inputs

- `var/task-runner/TASK-NNN/changes.diff`
- The task's `.md` — its **scope** and **verification** sections, located by intent: they are not
  reliably in `§3` and `§5` (measured: scope in §3 in 13 of 21; verification in §5 in 7 of 21)

## Outputs

- `var/task-runner/TASK-NNN/validate.report.md`
- `var/task-runner/TASK-NNN/test-results.xml` (JUnit) — ⚠ **only if explicitly requested**:
  `phpunit.dist.xml` has no `<logging>` block and `composer test` doesn't pass `--log-junit`, so Step 1's
  command as it stands **produces no file**. To cross-check against the verification section, add
  `--log-junit var/task-runner/TASK-NNN/test-results.xml` to the phpunit invocation, or read the names
  from stdout
- JSON: `{"status":"pass|fail","summary":"...","issues":[...],"harness":"...","msi":0.91,"propertiesUnproven":[]}`

## Critical precondition — declare the harness, and check it points to YOUR tree

The services the suite needs (Postgres, RabbitMQ, MinIO, Mailpit) are brought up by
`../f5sign-infra`. **Never `docker compose` from this repo** (rule 5). And before running anything:

⚑ **`f5sign-infra/docker-compose.override.yml` mounts `../f5sign-backend`.** If you're working in a
linked worktree, `make test` validates the other tree and its green says nothing about your code. Choose
a route and **write it in the JSON's `harness` field**:

| Route | Good for | Notes |
|---|---|---|
| `make -C ../f5sign-infra test` (+ `phpstan` / `lint` / `composer cmd=…`) | The main checkout | Validates `../f5sign-backend`, never a worktree |
| `make -C ../f5sign-infra wt-backend src=$(pwd)` | A worktree | Its own Postgres, MinIO, RabbitMQ and Mailpit, plus the shared `eu-dss`: the full suite runs there. Reuses the worktree's lane if `wt-backend-up` left it up (`make -C ../f5sign-infra wt-ls`). Gates via `WT_GATES="lint arch phpstan test infection"` |
| `make -C ../f5sign-infra wt-backend-test src=$(pwd) only=<regex>` | A worktree, named tests | PHPUnit only, on the kept lane; seconds |

⛔ **Never a hand-rolled `docker run` on `f5sign-net`** for the suite or Infection, whatever an older
version of this skill said: it shares the stack's Postgres cluster, and `pg_snapshot_xmin` is cluster-wide,
so the relay tests go red for reasons that are not the code (BL-138). An hour of diagnosing a regression
that does not exist is the usual cost.

If a service is down during the run → `status: fail`, `summary: "infrastructure unavailable: X"`.
**Don't retry automatically, and don't mistake it for a code failure:** the classic symptom is
`Connection could not be established with host` (Mailpit disconnected from the network) or
`Could not resolve host: minio`. Both are environment, not regression.

## Execution

### Step 1 — Suite

⚑ **Reuse the implementation's full run when it covers the tip.** The orchestrator passes
`last_green_run` (`sha`, counts, harness) from `implement-backend`, whose last act is a full run of every
tier. If `git rev-parse --short HEAD` equals that `sha`, the working tree is clean, and the harness was a
full run of **your** tree (the worktree lane, or `make test` in the main checkout), cite it and **do not
run the suite again**: a second full run on the same commit proves nothing new and costs ~5 minutes. Any
commit after it, or a dirty tree, and you run it:

```bash
make -C ../f5sign-infra wt-backend src=$(pwd)     # worktree (WT_GATES default: lint arch phpstan test)
make -C ../f5sign-infra test                     # main checkout
```

This repo's tiers are **directories**, not scripts (ADR-0035): `Unit/`, `Application/` (hermetic),
`Integration/` (real DB, DAMA rollback), `Acceptance/` (HTTP). ⚠ **To narrow it down, use `--filter`,
not `--testsuite`**: `phpunit.dist.xml` declares exactly two suites, `default` (all of `tests/`) and
`phpstan-rules` (`phpstan/tests`), and **neither one is a tier**. `tests/README.md` records the per-tier
suites as *"(target)"*, i.e. not yet built: `--testsuite Unit` errors out.

- [ ] Exit code 0.
- [ ] The tests the verification section names **exist and have been run**. Cheapest check: run them by
      name, `make -C ../f5sign-infra wt-backend-test src=$(pwd) only='<Name1|Name2|…>'`, and confirm each
      is counted (a filter matching nothing prints *No tests executed*). A test named in the task and absent
      from the run is `fail` category `property-unproven`.

### Step 2 — Structural strength: covered-MSI, not line percentage

```bash
WT_GATES="infection" make -C ../f5sign-infra wt-backend src=$(pwd)   # worktree (reuses the kept lane)
make -C ../f5sign-infra composer cmd="infection"                    # main checkout
```

**This repo has no line-coverage threshold and one must not be invented.** The gate is Infection's
covered-MSI (ADR-0035). `composer coverage:text` / `coverage:clover` exist for inspection, not as a bar.

- **There are TWO gates and `composer infection` fails on either one.** `infection.json5.dist`
  declares `minCoveredMsi` (depth: of what's covered, how much survives) **and `minMsi`** (breadth:
  includes what isn't covered). Read both numbers from there, not from here or from memory.
- ⛔ **If `minMsi` drops, don't fix it by attributing the broad flows.** The file itself warns about
  this: *"the cheapest way to raise MSI is to attribute the broad flows"* — and that undoes ADR-0035's
  two-tier rule. The fix is a test, not attribution.
- ⚠ **Infection doesn't see code with no callers**, and its `source` is `src/F5Sign` only. A new
  artifact with no caller scores as if it didn't exist, and the test of a custom PHPStan rule (which
  lives in `phpstan/`) is its **only** guard. If the diff adds surface in those areas, say so in the
  report instead of letting the MSI speak for it.

### Step 3 — Static analysis and architecture

```bash
composer phpstan     # level 9
composer arch        # Deptrac: visibility contract between layers and BCs
composer lint        # PHP-CS-Fixer in check mode
```

In a worktree these three are the lane's `lint arch phpstan` gates, already part of Step 1's
`wt-backend` run (or `WT_GATES="lint arch phpstan"` alone if Step 1 was reused). In the main checkout:
`make -C ../f5sign-infra phpstan` / `lint` / `composer cmd="arch"`.

- [ ] PHPStan with no new errors. **Don't extend `phpstan-baseline.neon` to pass the gate**: every entry
      in the baseline is a design finding with its *why* written down. Adding one is a decision, not a fix.
- [ ] Deptrac with no violations. **It has no baseline**: a violation is reported as a finding, not silenced.
- [ ] Lint clean.
- [ ] If the diff adds tests: they carry `#[CoversClass]` or `#[CoversNothing]` (`phpunit.dist.xml` has
      `requireCoverageMetadata="true"`), and `#[UsesClass]` for collaborators, including the exceptions
      the test asserts.

### Step 3b — Domain separation, asserted instead of counted

`composer arch` answers *"are there violations?"*, and there are two ways it can answer **no** without
the property actually holding. This step covers both.

**a) The allowlist delta.** If the diff touches [`deptrac.yaml`](../../../deptrac.yaml) (layers or
ruleset), `phpstan.dist.neon`, or adds entries to `phpstan-baseline.neon`:

- [ ] **Report the delta in prose**, not just "file touched": which layer gains which dependency, which
      rule is relaxed, which finding is silenced. It's the only way a reviewer will see it.
- [ ] **Require an ADR cited in the changeset** → if there isn't one: `fail`, category
      `undeclared-decision`. Extending the allowlist so the gate passes **is the decision**, not the fix
      (`implement-backend` Step 2b).

**b) The four load-bearing shapes of `deptrac.yaml`, read as data.**

⚠ **Corrected 2026-08-17, and the correction matters:** an earlier version of this step said these
rules *"can't go red"*. False. The `ruleset` is a **positive allowlist** and the repo runs with
`Uncovered 0 / Allowed 3755`, so a class that depends on a disallowed layer **does** produce
`DependsOnDisallowedLayer`. What can't go red is **extending the allowlist**: that doesn't violate
anything, it just stops watching. That's why the real check is (a) above —look at the file's diff— plus
checking that these four shapes stay intact:

- [ ] **`Kernel: []`** — depends on nothing.
- [ ] **`Foundation: [Kernel, Vendor]` and nothing else.** `LOAD-BEARING.md` §1.13 marks it as *"the most
      likely of all of these to come undone, and for a mechanical reason: a relaxed ruleset fails
      nothing"*. Adding a `…Contract` to it dissolves the dependency inversion ADR-0044 exists to force.
- [ ] **Between BCs, only `…Contract`** — no list names another BC's `Domain`/`Application`/
      `Infrastructure`/`UI`. And no layer outside Notification names a `Notification*` (ADR-0037).
- [ ] **`IdentityAccessApplication` and `IdentityAccessInfrastructure` have an EMPTY sibling list**
      (ADR-0044, `LOAD-BEARING.md` §1.11). *"Filling it in for symmetry"* —because it looks like an
      oversight next to eleven populated lists— is the documented mode of destruction.

⚑ **And the `Vendor` collector is a namespace allowlist**, so a vendor not in its regex belongs to no
layer and a `Domain/` can import it without violating anything. Today `Lexik\` is in `composer.json` and
**not** in the regex. If the diff adds a vendor dependency, check that its namespace is covered by the
collector.

### Step 3c — An ADR that lands, lands complete

If the diff adds or changes the status of a `docs/adr/ADR-*.md`:

- [ ] `Status` is not `Accepted` unless the decision is **exercised** in this very diff — in this set
      *Accepted* means exercised, not agreed.
- [ ] The **three** edits to [`docs/adr/README.md`](../../../docs/adr/README.md) are there: index row,
      relationship graph, crosswalk row. Missing any → `fail`, category `adr-index-incomplete`.
- [ ] And the **two that `AUTHORING.md` calls easy to forget**, because there are five places in total:
      the `(ADR-NNNN)` reference in the docblocks of the code it governs (*"only the pair makes the
      decision discoverable in both directions"*), and the reconciliation of the domain model in
      `docs/ddd/` **plus its status row** in `docs/ddd/README.md`.
- [ ] The `Crosswalk` header field and the sections `AUTHORING.md` requires are present
      (`Consequences` with **Risks**, `Enforced by`, `Realized in`).
- [ ] If the diff makes true something another ADR had marked pending, **that** ADR moves its
      `Status` / `Enforced by` / `Realized in` here and not later.

### Step 4 — Declared properties are actually proven

For each claim in the verification section, check that **the chosen harness can see it**. This is the
step that distinguishes this skill from "run the suite", and it exists because the repo has shipped
green guards that nothing executed (`CLAUDE.md` authorship rule 4):

- **Row locks**: `Integration/` runs **one connection** under DAMA rollback, so with and without
  `FOR UPDATE` is indistinguishable. A second connection is needed
  ([`ProbesRowLocks`](../../../tests/F5Sign/Support/ProbesRowLocks.php)).
- **Redelivery / retries**: `async_events` is `in-memory://` in test; nothing gets redelivered.
- **Identity after serialization**: a fake that returns the instance it saved proves nothing about
  `save()`.
- **Fixtures that don't discriminate**: if two variables always agree in the test data, a projection
  that filters on the wrong one still passes. Require the case where they **disagree**.

- **Redelivery / retries**: `async_events` is `in-memory://` in test… **but that's not the whole truth**:
  `when@test` also declares two real AMQP transports (`async_events_amqp`,
  `async_events_unroutable_amqp`) so broker tests can reach redelivery properties. Before declaring a
  property unreachable, check whether one of those serves it.
- ⚑ **The locks probe needs `#[SkipDatabaseRollback]`.** Its own docblock says so: without that
  attribute DAMA's static connection gives every "session" the same physical connection, **and a lock
  never collides with itself**. Adding it without that reproduces the green-that-proves-nothing this step
  exists to catch.

**Two ways to contaminate the run that make a GREEN worthless** (`tests/README.md` § *Two ways to
get an untrustworthy run*):

- [ ] **`worker` or `relay` up during the suite**: consumers competing on the same broker eat the
      messages the test expects. `make worker-down`, confirm with `make worker-status`. `ensure-stack`
      **doesn't** check this.
- [ ] **Two `phpunit` runs at once against the same test DB**: DAMA's isolation is per *connection*, not
      per process — *"fails close to 100% of the time and looks exactly like a storm of flakes"*.
- [ ] Environment: `ensure-stack` requires `redis` (which the tests don't use, `LOCK_DSN=flock`) and
      **doesn't** require `minio` (which they do use), so `make test` can start green with storage down.

⚑ **Before redoing a structural check by hand, check whether a test already closes it.** Two exist and
none of these steps replace them:
[`OpenApiSpecTest`](../../../tests/F5Sign/Acceptance/OpenApiSpecTest.php) closes the spec's key set
**in both directions**, with positive control, and audits every published enum; and
[`SchemaConformanceTest`](../../../tests/F5Sign/Integration/SchemaConformanceTest.php) asserts
per-tenant scoping and the canonical RLS against the live DB, with its exemption taxonomy. **Run them
and read their output instead of reproducing them**; if a case is missing, add it there.

Whatever can't be proven with this harness goes to `propertiesUnproven` and is `fail` if the task
declared it proven.

### Step 5 — The diff doesn't stray outside the declared scope

This task format **doesn't carry a "files to create/modify" table** (that was the legacy `Planning/`).
The target is the prose of the scope section, with its **In** and **Out** lists:

- `git diff --name-only $(git merge-base HEAD develop)..HEAD`.
- [ ] Nothing in the diff falls under something declared **Out** → if it does: `fail` category
      `out-of-scope`.
- [ ] Files outside what was anticipated but not forbidden: `warn` category `undeclared-file`.
- ⚑ If the change re-scopes or renames a concept, check the rule 1 sweep:
      `rg -n '<retired-term>' src tests migrations docs config CLAUDE.md`. A file that still needs
      the edit shows up with an **empty diff**, so the diff is not the search surface.

### Step 6 — Migrations (if the diff touches `migrations/`)

⛔ **Not with `make sf`.** Three reasons: it mounts `../f5sign-backend`, so in a worktree it validates
**a different tree**; it uses the `f5sign_app` role, which is not a superuser (the Makefile's `migrate`
target uses `$(PHP_ADMIN)`); and `--dry-run` **only prints SQL**, so it says nothing about `down()`. Use
the one-off container with the admin URL, as in the precondition.

- [ ] `up()` applies without errors against a freshly migrated `postgres-test`.
- [ ] **`down()` is actually exercised** — `--dry-run` doesn't prove it; either it's applied and
      reverted, or the report explicitly states that reversibility was left unchecked.
- [ ] If the migration **writes rows the domain later reads**, `doctrine-guard` is the one that audits it
      (authorship rule 6); here it's enough to flag it in the report so it isn't lost.

## Report

```markdown
# task-validate-backend — TASK-NNN

**Status:** {PASS|FAIL}
**Harness:** {the chosen route, literal}
**Tests:** {passed} passed, {failed} failed, {skipped} skipped
**Covered-MSI:** {%} (ADR-0035 threshold)
**PHPStan:** {N} new errors · **Deptrac:** {N} violations · **Lint:** {N}

## Domain separation
- Contract-only between BCs: {ok | layer X gains Y}
- Nothing depends on Notification: {ok | X → NotificationZ}
- `Kernel: []`: {ok | depends on X}
- Relaxed rules in this diff: {none | the delta in prose + the ADR that declares it}

## Declared and unproven properties
- {claim from the verification section} → the harness doesn't reach it because {reason}

## Outside §Scope
- {list or "none"}

## Unavailable services
- {list or "none"} (environment, not regression)
```

## What it does NOT do

- Doesn't audit security, compliance or performance.
- Doesn't write missing tests — only detects that they're missing.
- Doesn't fix code or tests.
- Doesn't extend baselines to pass.

## Correction protocol

If `task-runner` retries with this report as input, the instruction is *"fix the issues without
changing the scope"*. Maximum 2 automatic iterations; on the third attempt, human intervention.
</content>
