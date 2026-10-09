---
name: plan-backend
description: 'Plans a backend task from docs/tasks/ before any code is written, on the top model, once (or amends that plan when the orchestrator asks): reads the record and the code it lands on, stops for a cross-cutting decision (drafts the ADR as Proposed and waits), and cuts the work into small fixed-format slices, each one implemented later by a fresh agent on a cheaper model. Writes plan.md, constraints.md, slices/NN.md and context-digest.md under var/task-runner/TASK-NNN/. Launched by /task-runner Phase 2a through the plan-runner agent.'
---

# Plan (backend)

Writes the plan of a task and cuts it into slices. A slice is implemented by a fresh agent that reads **only its
slice and `constraints.md`** — never the task or the whole plan — so the slice has to carry everything that agent
needs, and nothing it would have to decide.

> **Before planning, read the [CLAUDE.md authorship rules](../../../CLAUDE.md).** The slices are where they get
> applied: an implementer on a cheaper model follows the slice, so a rule the slice does not carry is a rule
> nobody applies.

## Inputs

- The task's `.md`, in full. Three sections govern the work: **what already exists** (reuse, don't
  rebuild), **the scope** (what is touched and what isn't) and **the verification** (the bar).
  ⚠ **Locate them by intent, not by number.** Records place the scope and the verification at different
  section numbers, and "what already exists" appears as *What was built*, *What will be built*, *Design grounding*, *Locked decisions*
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

All under `var/task-runner/TASK-NNN/`:

- `plan.md` — the plan (Step 2).
- `constraints.md` — what binds every slice: the governing ADRs (one line each, `ADR-NNNN §x.y — binding line`),
  the non-negotiable rules of `implement-backend` Step 4 that apply to this task, what the task declares **Out**,
  the branch, the worktree's absolute path and the lane commands, and an empty `## Landed so far` section that
  the orchestrator fills after each approved slice. Short: every implementer reads it.
- `slices/NN.md` — one per slice (Step 2), numbered in execution order.
- `context-digest.md` (Step 3).
- Last line, JSON: `{"status":"pass|fail|awaiting-adr-acceptance","summary":"…","slices":N,"tiers":{"mechanical":N,"standard":N,"critical":N},"coverage":{"AC-1":["01","03"]},"diagnosis":"…"}`. In amend mode, add `"amended":["04","07"]`.

## Execution

### Step 1 — Context

1. Read the full `.md`.
2. Read what §2, `Builds on` and `Decision record` cite.
3. Read the fixed references above.
4. The code census (callers of a symbol, the siblings of a directory, `rg -l` evidence for a "first instance")
   goes to `Explore` with `model: "haiku"`; you read what it points at.
5. ⚑ **If you're going to write a class modeled on an existing one: `ls` the directory and read ALL the
   siblings**, not just the first one that fits. Where two siblings differ, the difference is a bug in one
   or a decision — figure out which before copying (authorship rule 3; here a new controller copied the
   wrong sibling and reintroduced a 500 that had already been fixed and documented).

### Step 2 — Plan and slices

`plan.md`:

```markdown
# Plan — TASK-NNN

## Criteria → slices
| Criterion | Slices | Harness |
|---|---|---|

## Harness per property
| Property | Tier | Does the harness reach it? |
|---|---|---|

## Slices
| # | Title | Tier | Covers | Depends on |
|---|---|---|---|---|

## Sweep terms
Retired terms, symbols whose behaviour changes, losing alternatives. Seeded from the record's `Concepts re-cut`
line; the orchestrator appends each slice's `termsChanged`.

## Decisions made
## Deviations
Appended by the orchestrator, one line per item with the slice id: departures from the plan and from the record,
and the ruling on any finding left unfixed.
```

**Criteria.** From TASK-055 on, the record's verification section (located by intent) is a table of `AC-n` / `S-n` ids, with sub-ids for a row that
says "every" or "each" ([`docs/tasks/README.md`](../../../docs/tasks/README.md) §8). For an earlier record, give
each claim of its verification section a local id here (`V-1`, `V-2`…) and use those; the citation form is the
same. ⛔ **Every criterion is covered by at least
one slice**; one that no slice covers is a gap in the plan, not in the task.

**The "Harness per property" table is not optional.** It's where it's decided, *before* writing the test,
whether the chosen tier can see the property: `Integration/` runs one connection under DAMA rollback (it
cannot distinguish lock from no-lock), `async_events` is `in-memory://` (nothing gets redelivered),
Infection only looks at `src/F5Sign` and doesn't see code with no callers. A property whose harness can't
reach it needs another tier or a probe
([`ProbesRowLocks`](../../../tests/F5Sign/Support/ProbesRowLocks.php) already exists).

**Each slice, `slices/NN.md`, in this form and no other** (at most about 90 lines):

```markdown
# Slice NN — <what is true once it lands>

| Tier | mechanical / standard / critical |
| Covers | AC-1, AC-4 |
| Depends on | slice NN, or none |

## Goal
One or two sentences.

## Why
Verbatim from the record, at most 6 lines: the reason the behaviour is wanted.

## Files
- Touch: `path` — `Symbol` (create | modify)
- Do not touch: …

## Registers
The file and tag or route this slice must change so its handler, subscriber, listener, controller or command is
reached, or `none`. The slice that adds one owns its wiring and verifies it with
`wt-backend-sf cmd="debug:container --tag=…"` or `debug:router`.

## Reference instance
`path` — `Symbol`: what to imitate, and what differs here. If the slice is the first of its shape, say so and
give the `rg -l` evidence that no instance exists.

## Prose to write
Each docblock, `#[OA\*]` string and migration comment the slice adds, written here by the planner, or `none`.

## Claims you may NOT copy
Rationale in the reference instance's docblocks that is not true here.

## Tests, written first
| Test (`file` — `method`) | Criterion | Asserts | Discriminates (the two values that differ) | Guard that must fire (symbol/exception) | Fails today because |
|---|---|---|---|---|---|

## Sabotage
| Guard line | Test that must go red | Expected red message |
|---|---|---|

## Verify
`make -C ../f5sign-infra wt-backend-test src=<worktree> only='<regex>'` → OK, N tests.

## Stop and report if
- <what this slice must not decide; add to the list in implement-backend Step 1>
```

**How to cut.** One to three criteria per slice, a handful of files, one test class or two. Each slice leaves the
tree green on the fast tier, so the next one starts from a known state. Name exact paths, symbols, test methods
and what they assert; leave the bodies to the implementer unless the signature and the tests leave a choice
open, in which case the slice makes the choice, not the implementer.

- **A change that adds a required member, parameter or case to a type used in N places is ONE `critical` slice,
  however many files**, and its callers are migrated inside it through the replicator. Prefer expand-then-contract
  (optional, then mechanical caller slices, then a final slice removes the default) when every step can stay
  green. The plan states which it chose, and `Files` states `rg -l '<Symbol>' src tests` = N. Never cut so that a
  slice is red on `phpstan` or `fast`; there is no "red until slice K".
- Adjacent mechanical slices of the same shape may be merged (up to about 8 files) only if the result stays green.

**Tier — it decides the model**:

| Tier | What | Implementer · reviewer |
|---|---|---|
| `mechanical` | Replicating a shape that already exists and is pinned by a test: cases 2..N, the same method across fakes, a signature at every caller | sonnet · sonnet |
| `standard` | New code that follows a named reference instance and touches none of: a lock or transaction boundary, an attempt/charge/consent counter, tenant-scoped SQL or RLS, event payload keys, `_authn`/security config, a `Contract/` port, a refusing guard | sonnet · sonnet |
| `critical` | Anything where a wrong choice is silent: a migration, a guard of the domain or of security (auth, tenant, attempts), Kernel/Foundation, signing/crypto, locks and concurrency, the **first** instance of a shape (the slice's Reference section carries the `rg -l` evidence), any of the `standard` exclusions above | opus · opus |

A test that pins a critical guard belongs to that guard's slice. A `standard` slice that writes `#[OA\*]` strings stays `standard`, but the orchestrator runs its **review** on
opus: those strings are emitted verbatim into the spec the frontend ratifies. The number of
files never decides the tier; whether the slice needs judgement does. When in doubt, `critical`: a cheaper model
that has to think takes more turns than it saves.

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
   discarded, and **what it forbids from now on**. Silence is not acceptance; return
   `status: awaiting-adr-acceptance` and stop there.
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
### Step 3 — `context-digest.md`

≤150 lines, read by the gates of Phase 3: a `## Task summary` first, then what will be implemented · business
rules applied · data model touched · contracts affected (API and events) · invariants preserved · decisions made
and why · binding ADRs · what's left out (with task id if it exists). The orchestrator refreshes it from the slice
reports and `changes.diff` once the slices have landed (task-runner Phase 2c); deviations live in
`plan.md § Deviations`, not here.

### Step 3b — Amend mode

The orchestrator calls you again with `Amend: <reason>; do not touch ticked slices`. You then:

- draft the ADR an implementer's `BLOCKED` named (Decision gate: `Proposed`, return `awaiting-adr-acceptance`);
- re-cut the **unticked** slices that depend on what changed, keeping the slice format and the ids of ticked ones;
- write a fix slice from a Phase 3 gate report or from the Closing review, and the Closing slice (critical;
  Files = whatever the sweep hits);
- update `plan.md` (coverage, Sweep terms) and `constraints.md`, and return the JSON with `amended`.

Never edit a ticked slice or rewrite a landed commit.

### Step 4 — JSON

Last line of the response: the JSON of *Outputs*.

## What it does NOT do

- Doesn't write production code or tests: the slices do.
- Doesn't accept an ADR: it drafts it as `Proposed` and returns `awaiting-adr-acceptance`.
- Doesn't explore beyond what the task cites and the code it lands on: if context is missing, `status: fail` with
  a diagnosis.
