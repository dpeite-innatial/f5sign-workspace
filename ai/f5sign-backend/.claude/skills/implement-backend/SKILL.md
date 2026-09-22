---
name: implement-backend
description: 'Implements a backend task (PHP/Symfony) from docs/tasks/ with property-driven TDD, respecting the domain kernel, the separation between BCs (only the other''s Contract/) and the authorship rules in CLAUDE.md. Stops and asks the user before making any cross-cutting decision — contradicting an accepted ADR, opening a new cross-BC dependency, touching Kernel/Foundation or editing deptrac/phpstan: it drafts the ADR as Proposed and waits for explicit acceptance, never marking it Accepted on its own. Reads the task''s .md (what already exists, the scope and the verification, located by intent rather than by section number), writes code + tests at the tier used by its siblings, annotates endpoints with Nelmio, and produces context-digest.md and plan.md. Only for repositories with a PHP/Symfony stack. Use it with /implement-backend TASK-NNN. Trigger with "implement backend TASK-NNN", "code PHP task...", "run backend implementation of...".'
---

# Implement (backend)

Implementation of a task via property-driven TDD.

> **Before writing code, read the [CLAUDE.md authorship rules](../../../CLAUDE.md).** They exist
> because the failure each one describes **happened in this repo, on a branch with `make qa` green**, and no
> gate sees them. This skill references them; it does not duplicate them, because a copy goes out of sync.

## Invocation

```
/implement-backend TASK-NNN
/implement-backend {path to the .md}
/implement-backend TASK-NNN --amplified-context
```

**No model selection via `Complejidad`**: that field doesn't exist in this task format. It inherits the
session's model; escalate only after a repeated failure with a diagnosis that justifies it.

## Inputs

- The task's `.md`, in full. Three sections govern the work: **what already exists** (reuse, don't
  rebuild), **the scope** (what is touched and what isn't) and **the verification** (the bar).
  ⚠ **Locate them by intent, not by number.** Measured 2026-08-17 across the 21 records: the scope is
  in §3 in 13 of 21 (also in §4 and §6), the verification in §5 in only 7 (also §4, §6, §9), and "what
  already exists" appears as *What was built*, *What will be built*, *Design grounding*, *Locked decisions*
  or *The model*. `docs/tasks/README.md` §2 explicitly says the headings vary with the work, so
  addressing by `§N` is the closed list that the convention itself forbids.
- Whatever its `Builds on` and `Decision record` fields cite.
- Fixed references, always:
  - [`CLAUDE.md`](../../../CLAUDE.md) — conventions + authorship rules
  - [`docs/LOAD-BEARING.md`](../../../docs/LOAD-BEARING.md) — what looks like duplication and isn't, plus
    the **Never** list of changes already proposed and rejected, with their reason
  - [`docs/adr/`](../../../docs/adr/) — the decision that governs the area you touch (repo rule 7)
  - The docblocks of `src/F5Sign/Kernel/` for the categories you use: they are the canonical definition
    (`grep -rnE "Kernel (sub-)?category" src/F5Sign/Kernel/` to enumerate them)
  - [`tests/README.md`](../../../tests/README.md) — tiers, layout and the `P-§` convention

## Outputs

- Code + tests committed on the task's branch.
- `var/task-runner/TASK-NNN/plan.md` and `context-digest.md`.
- Final JSON: `{"status":"pass|fail","summary":"...","filesChanged":N,"testsAdded":N,"attempts":N,"diagnosis":"..."}`

## Execution

### Step 1 — Context

1. Read the full `.md`.
2. Read what §2, `Builds on` and `Decision record` cite.
3. Read the fixed references above.
4. ⚑ **If you're going to write a class modeled on an existing one: `ls` the directory and read ALL the
   siblings**, not just the first one that fits. Where two siblings differ, the difference is a bug in one
   or a decision — figure out which before copying (authorship rule 3; here a new controller copied the
   wrong sibling and reintroduced a 500 that had already been fixed and documented).

### Step 2 — Plan

`var/task-runner/TASK-NNN/plan.md`:

```markdown
# Plan — TASK-NNN

## Execution order (TDD)
1. [TEST] tests/F5Sign/<BC>/<tier>/...Test::<name>  — property: {P-§ or the claim in §5}
2. [CODE] src/F5Sign/<BC>/...
...

## Harness per property
| Property | Tier | Does the harness reach it? |
|---|---|---|

## Decisions made
## Deviations from the .md
## Final status
```

**The "Harness per property" table is not optional.** It's where it's decided, *before* writing the test,
whether the chosen tier can see the property: `Integration/` runs one connection under DAMA rollback (it
cannot distinguish lock from no-lock), `async_events` is `in-memory://` (nothing gets redelivered),
Infection only looks at `src/F5Sign` and doesn't see code with no callers. A property whose harness can't
reach it needs another tier or a probe
([`ProbesRowLocks`](../../../tests/F5Sign/Support/ProbesRowLocks.php) already exists).

**Plan gate:** if ambiguity that can't be resolved with the available context shows up while planning →
return `status: fail` with an explicit `diagnosis` (`"spec contradictorio"` / `"contexto insuficiente"`)
and **implement nothing**.

### Step 2b — Decision gate: an ADR is not skipped, and it is not coined alone either

⛔ **Stop and ask the user if the work does any of these things.** This is not a list of suspicious
cases: it is the operative definition of "cross-cutting decision" in this repo (rule 7).

| Trigger | Why it is a decision |
|---|---|
| Contradicts an **accepted** ADR | Contradicting it is an ADR change, never a silent edit |
| Opens a new **cross-BC** dependency | Access between BCs is only through `Contract/`; extending it changes the map |
| Changes a contract of `src/F5Sign/Kernel/` or `src/F5Sign/Foundation/` | It's substrate: everything inherits it |
| Edits the ruleset or layers of [`deptrac.yaml`](../../../deptrac.yaml), `phpstan.dist.neon`, or adds to `phpstan-baseline.neon` | **You are editing the rule that judges you** |
| Introduces a new realization pattern (use case shape, adapter, reactor) | The next one will copy it |

**What to do, in this order:**

1. **Stop before writing the code the decision governs.** Not "implement first, document later": the
   ADR is the input to the code, not its record.
2. **Draft the ADR as `Proposed`**, with the section template from
   [`docs/adr/AUTHORING.md`](../../../docs/adr/AUTHORING.md) — including `Consequences` with its three
   sublists (**Risks is not optional**) and `Counterpoint` if there's a credible alternative. The id is
   coined with the `AUTHORING.md` sweep, **run at that moment and from the repo root**.
3. **Present it to the user and wait for explicit acceptance.** What is decided, what alternative is
   discarded, and **what it forbids from now on**. Silence is not acceptance; `status: fail` with
   `diagnosis: "awaiting-adr-acceptance"` and stop there.
4. ⛔ **Never write `Accepted` on your own.** In this set *Accepted* means **exercised**, not
   agreed ([`AUTHORING.md`](../../../docs/adr/AUTHORING.md) § status): an ADR that no one has exercised
   yet stays `Proposed`, and setting it to `Accepted` falsifies the state of the repo.
5. **If the user rejects it**, the decision is not yours: trim the scope or change approach and go back
   to the plan gate. Don't implement it "in a smaller way" so the ADR isn't needed.
6. **When the ADR lands, it lands complete — that's FIVE places**, and `AUTHORING.md` § *Maintenance when
   adding an ADR* lists them: (1) index row, (2) relationship graph and (3) crosswalk row in
   [`docs/adr/README.md`](../../../docs/adr/README.md), plus the `Crosswalk` field in the header and the
   sections the template requires; (4) **making the ADR reachable from the code it governs** with
   `(ADR-NNNN)` references in the docblocks —*"only the pair makes the decision discoverable in both
   directions"*—; and (5) **reconciling the affected domain model** in `docs/ddd/` and its status row in
   `docs/ddd/README.md`. The last two are what AUTHORING calls *"each conditional but each easy to
   forget"*, and they are exactly the ones this list used to omit.

⚑ **The case that slips through most often: extending the allowlist to make the gate green.** If
`composer arch` fails, the answer is **not** to add the layer to the list of allowed dependencies — that
edit *is* the decision, and it silences the one thing that was watching it. Same with a new entry in
`phpstan-baseline.neon`: every entry in that file is a design finding with its *why* written down, not
a suppressor.

### Step 3 — TDD loop

For each property in the verification section, in order:

1. **Write the test** in the tier used by its siblings (`ls` the BC's test directory; being the only
   `*UseCase.php` with no `*UseCaseTest.php` next to it is the signal, and it has always been right). It
   must carry:
   - `#[CoversClass]` or `#[CoversNothing]` — `phpunit.dist.xml` has `requireCoverageMetadata="true"`
   - `#[UsesClass]` for collaborators, **including the exceptions the test asserts**
   - The `P-§` citation in the docblock if the property is catalogued (`tests/README.md`)
2. **Run it and watch it fail for the right reason** (not a syntax error, not a missing class):
   ```
   docker run --rm --network f5sign-net -v $(pwd):/var/www/html -w /var/www/html \
     f5sign/backend:dev sh -c 'vendor/bin/phpunit --filter=<Clase>::<metodo>'
   ```
   (or `make -C ../f5sign-infra test` if you're working in the checkout that mounts the stack — see
   `task-validate-backend`, precondition.)
3. **Write the minimal production code.**
4. **Green.**
5. ⚑ **Sabotage the guard and watch the test fail for the right reason; restore it.** This is the step
   that catches tests that can't fail, and without it the property isn't proven — it's just asserted.
6. Module suite, for regressions.

**Retry policy:** 3 edit-test iterations per test. After that, diagnosis:
`"poorly written test"` → fail; `"spec contradictorio"` / `"contexto insuficiente"` → fail **without
escalating**; `"exceeds the model"` → fail with `diagnosis: "escalate"`.

### Step 4 — OpenAPI (if you touch `UI/Http/` or `config/routes/`)

- `#[OA\Response]` for every **reachable** HTTP code, `#[OA\RequestBody]`, DTOs with typed
  `#[OA\Property]`, security scheme if the route is protected.
- ⚠ **The strings in `#[OA\*]` are emitted literally into the spec the frontend team ratifies.** They
  aren't internal comments: one of them ended up telling clients to send a value the endpoint doesn't
  accept. They're covered by the rule 1 sweep.
- Verify: `make -C ../f5sign-infra sf cmd="nelmio:apidoc:dump --format=json"` completes without error.

### Step 5 — Non-negotiable rules

- **The domain doesn't import Symfony or Doctrine.** Deptrac (`composer arch`) and the PHPStan placement
  rules watch this; if you spot it before they do, redo it.
- **Between BCs, only the other's `Contract/` is visible.** `deptrac.yaml` declares **38** layers (37 with
  an entry in `ruleset` plus `Vendor`) and says so explicitly: `EnvelopeApplication` can see
  `SessionContract`, `SignatureExecutionContract`, `IdentityAccessContract`… and **no other BC's `Domain`
  or `Infrastructure`**. `Kernel` depends on nothing (`Kernel: []`). If you need data that only lives in
  another BC's `Domain`, the answer is a read port in its `Contract/` (ADR-0008), not an import — and
  **that's Step 2b**, not a decision made while implementing.
- ⚑ **Notification is a support BC: nothing can depend on it** (ADR-0037, category (c)). The gate **does**
  catch this: deptrac's `ruleset` is a **positive allowlist** and the repo runs with `Uncovered 0`, so a
  class that depends on a disallowed layer produces `DependsOnDisallowedLayer`. What it **can't** catch
  going red is **adding the entry to the allowlist**: that doesn't violate anything, it just stops
  watching. So the question when reviewing isn't *"does deptrac pass?"* but *"does this diff touch
  `deptrac.yaml`?"* — and if it does, that's Step 2b, not a decision made while implementing. Corrected
  2026-08-17: this bullet used to say the gate was blind to the dependency, which is the dangerous
  direction to be wrong in.
- **Only aggregate roots have a repository.** Subordinate entities are modified through their root.
- **Commands through the bus; queries via direct call.** ADR-0008: **there is no QueryBus**, and a
  `QueryHandler` is realized with a direct `handle(Query): R` — its §Counterpoint expressly rejects
  putting an adapter in between. So a controller **does** inject a query handler (three do today) and
  that's conformant; what it must not do is inject a *command* handler bypassing the bus, because the bus
  is where the transaction, the tenant and the issuer live (ADR-0010).
- **VOs: the shape depends on the type, and a blanket rule is wrong** (ADR-0005). A **wrapper** (a single
  field) is `final readonly`; a **composite** (several fields) is `final` and **not** readonly — 11 of the
  22 in the tree are, with a public constructor. The model to imitate is
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

### Step 6 — Commits

**No single-commit policy.** This repo integrates multi-commit PRs and merges from `develop`; an
`--amend` on something already pushed forces `--force-with-lease` for no gain. Small, coherent commits,
each with a message that says *why*, and `git add` of specific files (never `git add .`).

Before the last commit:

1. `git status` must not bring in anything the task's scope declares **Out**.
2. If the change re-scoped, renamed or re-gated a concept: rule 1 sweep, in one command —
   `rg -n '<retired-term>' src tests migrations docs config CLAUDE.md`. **The diff is not the search
   surface**: a file that still needs the edit shows up with an empty diff. And `CLAUDE.md` is part of the
   sweep: it's the one surface that doesn't just go stale but starts **giving bad instructions**.
3. If the task discharges an ADR deferral, or makes something an ADR had marked pending come true, that
   ADR's `Status` / `Enforced by` / `Realized in` go **in this changeset** (authorship rule 7).

### Step 7 — `context-digest.md`

≤150 lines: what was implemented · business rules applied · data model touched · contracts
affected (API and events) · invariants preserved · decisions made and why · binding ADRs ·
what's left out (with task id if it exists).

### Step 8 — `plan.md § Final status` and JSON

New tests and green, sabotages performed, module suite, files modified, deviations. Last
line of the response: the JSON.

## What it does NOT do

- Doesn't audit security, compliance or performance.
- Doesn't touch documentation outside the code (that's `docs-sync`), except Nelmio's inline OpenAPI and
  the prose corrections rule 1 requires in the same changeset.
- Doesn't open a PR (`pr-ready`) or update the task's `Status` (`task-close`).
- Doesn't explore beyond what the task cites: if context is missing, `status: fail` with a diagnosis.
</content>
