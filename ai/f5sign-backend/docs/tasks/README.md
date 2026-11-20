# `docs/tasks/` — what a task record is, and how to write one

A task record is the **durable, in-repo home for one unit of work**: why it exists, what it may touch,
what decides it is done, and what it deliberately leaves undone. It is written to be **picked up cold**
by someone (or something) with only this repository — no chat history, no design repo, no author to ask.

This file is the convention, derived from the 20 records that already exist rather than prescribed ahead
of them. When a record and this file disagree, prefer the record and fix this file.

---

## 1. What belongs here, and what does not

| Surface | Holds | Home of truth for |
|---|---|---|
| `docs/tasks/TASK-NNN-*.md` | One unit of work: forward build, corrective slice, or groundwork | The plan, its scope, its acceptance bar, its follow-ups |
| [`docs/adr/`](../adr/) | One cross-cutting **decision** | Why the shape is what it is; a task *cites* an ADR, never restates it |
| [`docs/BACKLOG.md`](../BACKLOG.md) | The cross-cutting **index of deferrals** | Nothing on its own — every row points at its ADR/TASK home |

The split that matters: **a task may not be the only place a decision lives.** If the work changes a
cross-cutting contract, that is an ADR ([repo rule 7](../../CLAUDE.md)), and the task's `Decision record`
field says which one. If the work *defers* something, the deferral's home is the task's own
`Open follow-ups` section, and the BACKLOG row is the index entry pointing here.

**Finished work does not need a task.** A record written after the fact is archaeology, not a plan — for
work already built, the durable trace is the commit, the ADR amendment it owed, and the BACKLOG row it
closes or narrows. Write a task when there is something left to decide or to hand over.

### The `Planning/` tree in the design repo is legacy input, not a plan

`f5sign-docs/Planning/` holds ~347 prototype-era task records (`T{phase}.{epic}.{n}`). They are **product
input** — catalogs, copy, locale rules, per-notification subjects — and were written against a design this
codebase has since superseded: an ORM-era namespace (`Innasign\`), provider seams that were never built
(`EmailProviderInterface`, a SendGrid adapter), use cases that do not exist (`SendEmailUseCase`), and test
tiers this repo does not have (`composer test:unit` / `test:integration` / `test:e2e`).

Mine them for *what the product must say and do*. Do not follow their file lists, their dependency graph,
or their acceptance criteria. The plan of record for backend work is here.

---

## 2. Anatomy

````markdown
# TASK-NNN — <what the work achieves, as a sentence fragment>

<!-- OFFREPO: <only if the record leans on something outside this repo; see §5> -->

| Field | Value |
|-------|-------|
| **Status** | <see §3 — the field that rots first> |
| **Type** | Forward build / Corrective / Enabling / Groundwork — and one clause on what that means here |
| **Why** | The failure or gap that justifies the work, stated so a reader can disagree with it |
| **Builds on** | Tasks + ADRs whose output this reuses **unchanged** (omit if none) |
| **Scope** | Only when the boundary is surprising — what is explicitly *not* ours |
| **Decision record** | The governing ADR, or `No ADR yet` + what would force one |
| **Delivery bar** | The one observable outcome that means "done" (omit if §Verification carries it) |
| **Sibling** | ⚑ Another record that must not be scoped independently of this one (omit if none) |

---

## 1. Why this task exists
## 2. What already exists (reuse, do not rebuild)
## 3. Scope
## 4. Key decisions
## 5. Verification
## 6. Open follow-ups (track, don't solve here)
````

**Sections are numbered and cited as `§N`** from other records, from ADRs, and from `CLAUDE.md`. That makes
the numbering a cross-document anchor: **add sections at the end, never renumber.**

The six headings above are the spine, not a template to pad. Vary them when the work does — the existing
records carry `What was built`, `Design leans`, `Constraints`, `Deviations & honest notes`,
`ADR / doc reconciliation done here`, `Definition of done`, `Test plan & acceptance`,
`Acceptance criteria (properties)`. A record with nothing to say under a heading omits the heading.

**From TASK-055 on, §5 carries its criteria as a table with stable ids** — §8 says how. Records before
that keep their prose verification and are not rewritten.

**§2 is the highest-value section and the one most often skipped.** Enumerating what already exists is what
stops the next slice rebuilding a port that is already there — several records earn their length here alone.

---

## 3. `Status` is the field that rots, so write it to be falsifiable

State what is true and how to check it, not a mood. The existing records are the model:

- `**Not started** — forward plan, written 2026-08-10.`
- `**Not started — groundwork only.** The diagnosis is complete and the feasibility claims are measured
  (§2), not estimated. Nothing here is built.`
- `**✅ Merged to master** (`feat/sequential-pades`) — both slices landed and green.`

Two rules with teeth:

- **Name the branch or commit when the status claims code exists.** "In progress" with no ref is
  unverifiable six weeks later, which is exactly when it is read.
- ⚑ **Realizing a record is the mirror of landing one.** When the last item completes, `Status` — plus the
  ADR's `Status` / `Enforced by` / `Realized in`, if the task discharged an ADR deferral — belongs in **that
  changeset**, not a later tidy-up. `CLAUDE.md`'s authoring rule 7 records three separate branches that
  shipped the work and left the record saying *not yet*; the error is always in the under-claiming
  direction, which is why nobody chases it.

---

## 4. Minting an id: re-derive it by grep, at the moment you create the file

An id is claimed by **a file on a branch**, so `ls docs/tasks/` on your own branch is not the answer and
neither is the highest number you remember.

```bash
for b in $(git branch -a --format='%(refname:short)' | grep -v HEAD); do
  git ls-tree -r --name-only "$b" -- ':(top)docs/tasks/' 2>/dev/null | grep -oE 'TASK-[0-9]{3}'
done | sort -u | tail -3
```

⚠ **Keep the `':(top)'`.** A git pathspec is relative to the **cwd**, so the same loop written
`-- docs/tasks/` and run *from* `docs/tasks/` — where you are when you write a task — resolves
`docs/tasks/docs/tasks/` and prints **nothing**. Nothing reads as "the id is free", in the one check whose
entire job is to prevent a collision. Measured 2026-08-17: 0 ids from `docs/tasks/`, 21 from the root.
The same fix applies to the `docs/adr/` sweep in [`AUTHORING.md`](../adr/AUTHORING.md).

⚠ **This is not a hypothetical.** On 2026-08-17 the tree said `TASK-020` and the sweep above said
`TASK-023`: three ids live on `docs/two-gate-signer-auth`, invisible from every other branch. The same
sweep over `docs/adr/` found `ADR-0049` on that same branch while a session running from `develop` had
just concluded `0049` was free. Run it, on both trees, when you write the row — not earlier in the session.

**Never renumber an existing id.** They are cited from ADRs, from `docs/LOAD-BEARING.md`, from
`CLAUDE.md`, and from each other.

The filename is `TASK-NNN-<kebab-case-slug>.md`, slug derived from the title, ASCII.

---

## 5. Self-containment

A record must be actionable with only this repository open.

- **Every fact taken from outside gets restated here.** Not summarized-and-linked — restated, so the
  record still works when the outside thing is unreachable.
- **Then tag the reference** with `<!-- OFFREPO: ... -->`, naming what it is and that nothing here depends
  on reading it. [TASK-018](TASK-018-visible-signature-mark.md) is the worked example: it mines another
  team's WIP patch and restates every coordinate fact it took.
- **Cite by symbol or grep pattern, never by line number.** A line number is a pointer that rots on the
  next edit, and replacing a rotted pointer with a fresh one is not a fix.
- **Links are relative in-repo paths** (`../adr/ADR-0037-...md`), so they resolve in a plain checkout.

---

## 6. Verification: name where the property lives before claiming a green run

`§Verification` states **which harness proves each claim**, because this repo has properties its default
harness cannot see. The failure mode is a green suite that never executed the thing under test:

- `Integration/` runs **one connection** under DAMA rollback, so a row lock and no row lock are
  indistinguishable to it.
- `async_events` is `in-memory://` in test, so nothing redelivers.
- Infection's `source` is `src/F5Sign` only, and it cannot see code with no callers at all.
- ⚠ **This bullet used to say the per-worktree lane brings up *"postgres only — no MinIO, no RabbitMQ, so
  storage tests fail there and broker tests skip"*, and every clause of that was false.** Corrected
  2026-08-19 against `f5sign-infra`'s `docker-compose.wt.backend.yml`: `make wt-backend` brings up its own
  `postgres-test`, `minio` + `minio-init`, `rabbitmq`, `mailpit` and `php-fpm-wt`, so storage and broker
  tests **pass** there. Enumerate today's members from that file rather than from this sentence. And the
  *skip* half was false twice over — `rg -n 'markTestSkipped' tests/` returns **nothing**, so a missing
  dependency turns a test **red**, never skipped. The real trap the bullet was reaching for is the one
  `CLAUDE.md` states: from a worktree, the *main-stack* make targets validate a **different checkout** and
  report green for it.

So: **sabotage the guard, watch the test fail for the right reason, restore.** A task whose verification
section says "suite green" and names no harness has not stated a bar. See
[`tests/README.md`](../../tests/README.md) for the tiers and [`CLAUDE.md`](../../CLAUDE.md) authoring
rule 4 for why each of the above bit us once already.

---

## 7. Open follow-ups are a deliverable, not a courtesy

Anything the task decided **not** to do goes in `§Open follow-ups`, with enough context to act on cold:
the fact, why it was deferred, and what would force it. That section is the home of truth for the
deferral; [`docs/BACKLOG.md`](../BACKLOG.md) only indexes it.

⚑ Deferrals recorded nowhere are the failure this repo has already paid for twice — eight of them lived
only in an untracked memo until `docs(backlog): file eight deferrals that lived only in an untracked memo`
went in. If it was decided and not done, it gets written down here before the PR.

---

## 8. Verification criteria: an id per criterion, so each one can be traced to its test

**Applies to a record whose verification section is a table with an `Id` column — every record from TASK-055 on.**
Earlier records keep their prose verification and are not rewritten.

The verification section keeps its heading, wherever the record numbers it (`§5 Verification` in the anatomy of
§2, `Acceptance bars` in some records), and its job (§6 above still holds: every criterion names the harness
that proves it). What changes is the form: each criterion is a row with an id that never changes.

```markdown
## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | A `[DRAW]` recipient with no visible placement makes the send refuse | owner | Unit | drop the send check |
| AC-2 | Every refusal of the commit answers 422, admits nothing and charges no attempt (members AC-2a…n) | derived — one per guard of §3 #3 | Acceptance | see *Notes on AC-2* |
| S-1 | A SEQUENTIAL_PADES envelope with three recipients signs end to end; each mark matches its setting | owner | Acceptance, live DSS | — |

- **Gates:** suite, PHPStan, deptrac and lint, under the lane that mounts this tree.

**Notes on AC-2**
- AC-2a — the commit of a closed envelope refuses. Sabotage: drop the closed-envelope guard.
- AC-2b — the commit past the attempt limit refuses. Sabotage: drop the limit guard.
```

- **`AC-n`** is one behaviour, stated so a test can fail on it. **`S-n`** is an end-to-end scenario over HTTP.
  They are not called *use cases*: in this repo a use case is an `Application/` class.
- **Origin** is `owner` (the person who asked for the work said it), `derived — <source>` (the author worked it
  out and the owner confirmed it; the source is what it was derived from: an ADR, a sibling test, a census of a
  set), or `proposed — <source>` (derived and **not yet confirmed**). ⛔ A record with any `proposed` row is not
  ready to implement; `spec-lint` refuses it. The column says what to scrutinise: a wrong `derived` row is the
  author's to fix; changing an `owner` row is the owner's decision.
- **An id is never reused or renumbered.** A criterion dropped later stays in the table struck through, with
  why: `~~AC-3~~ — dropped 2026-10-12: the route no longer exists`. Plans, tests and other records cite the id.
- **Tests cite the id** on a method-level docblock line, `@criterion TASK-NNN AC-2a S-1` (several ids allowed;
  beside a `P-§` when the property is catalogued). A criterion of a record that predates the table, which the
  plan numbers `V-n`, is cited in the same form. The implementation plan says which ids each slice covers.
  `task-validate-backend` fails a task whose criterion no test cites, checking each live id and sub-id.
- **A row that says "every" or "each" lists its members as sub-ids** (`AC-2a…n`), each cited by its own test: one
  test citing a grouped row would cover N guards while proving one.
- **The table stays terse.** Detail goes in `Notes on AC-n` bullets under it: the members, the sabotage, and for
  a row restated from the owner `Owner said: "<verbatim>"`. The sabotage of a migration criterion is reverting
  its backfill.
- **`proposed` becomes `derived` only after an explicit owner reply.** `spec-lint` also checks that each
  `<source>` resolves: an ADR file that exists, `rule N` of the repo's authoring rules, or a path that
  exists.
- **The scope section carries a `Concepts re-cut: <terms>` line** when the work retires a term or changes a
  symbol's behaviour. It seeds the plan's sweep terms.
- Criteria derived from a set follow the repo's authoring rule 5: **one row per refusal of each new guard, and
  the whole set a predicate exempts**, classified — not two illustrative members.

