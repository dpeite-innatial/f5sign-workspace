# TASK-020 — Derive the deferral index instead of maintaining it

| | |
|---|---|
| **Status** | **Phase 1 done (§8) · Phase 2 stopped by decision · §9 is buildable now.** ⚑ **2026-08-18: the task has construable work again** — the user assigned it the three document lints (§9), including the `Status`-freshness check that fired three times that day. A lint generates nothing, so §9 does **not** un-park what §4 stopped. ⛔ **Phase 2 step 3 still must not be built:** The user decided 2026-08-18 to leave `BACKLOG.md` hand-maintained as it is (§4), so step 3 — the generated view replacing the *Open* table — **must not be built**: §8.6.6 measured that it would delete 34 rows whose only home is the index. Steps 1–2 are legal but are the input to a generator nobody may run, so the task rests here. ✅ Separately answered the same day: **`docs/tasks/` stays in this repo** (§3), discharging the precondition that had gated the TASK half for three weeks as an unwritten question. The census landed 2026-08-18 on `chore/derive-deferral-index` (`cc80e2a`, merged to local `develop`): 82 files read, **718 deferrals** classified, **no index rows written** — deliberately, because §4's boundary call decides what a row *is* and writing rows first settles it by accident. ⚑ **The census falsified half of §1's core claim, and it is the half Phase 2 rests on:** corpus→index holds (598 of 718 deferrals are in their ADR/TASK homes), but index→corpus fails — 47 of the 96 open `BL-` rows are `fold pending` and **34 are mentioned nowhere in the corpus**, so §3 Phase 2 step 3 as written would **delete them** (§8.6.6). Phase 2 is also **ADR-side only** until §3's precondition is answered, and its cost is not what §3 assumes: only **52 of 432** ADR deferrals sit under a deferral-named heading, so step 2 is locating ~379 items in prose, not retro-fitting headings. §2's measurements were re-run at `f779baa` and §2/§7 corrected (`82ee47e`, `7f0fa78`). The diagnosis and the feasibility claims are **measured**, not estimated; every number has its command. |
| **Type** | Corrective + enabling. Restores the one question [`docs/BACKLOG.md`](../BACKLOG.md) exists to answer, and removes the drift surface rather than guarding it. |
| **Why** | The index captured **nothing between 2026-06-16 and 2026-07-28** while 15 ADRs were minted (**29 by 2026-08-18** — §2 carries the command; this figure is prose and had to be swept by hand, which is the point). Its capture rule is disciplinary with no forcing function, so it fails silently — the file still *looks* maintained. *(The 2026-07-28/29 rows now in `BACKLOG.md` are a one-off **hand** backfill from the workspace-artifact review, not the capture rule working and not this task's Phase-1 census. The forcing function is still absent, which is what this task is for.)* |
| **Decision record** | No ADR yet. Phase 2 changes an authoring convention ([`../adr/AUTHORING.md`](../adr/AUTHORING.md)) and adds a composer script; if the section convention becomes load-bearing it wants its own ADR at that point. |
| **Delivery bar** | ⚑ **Per phase, because they are not one deliverable and the second is gated** (§7 states each falsifiably). **Phase 1** is done when every ADR and TASK touched since 2026-06-16 has had its deferral surface read and classified against §4's two-sided question, with counts — knowledge, not rows. **Phase 2 (ADR side only** while §3's precondition is unanswered**)** is done when `composer backlog` regenerates the index from `## Deferred` sections and **re-running it produces no diff**, which is the only bar that proves the drift surface is gone rather than guarded. ⛔ Writing the index rows themselves is **not** in either bar: §4's scope-boundary call decides what a row *is*, and it is explicitly not to be settled before the census. |
| **Sibling** | ⚑ **[TASK-019](TASK-019-requirement-traceability-and-per-tier-gates.md) is the same problem in a second location** — see §5. Do not scope these independently. |

---

## 1. The problem

[`docs/BACKLOG.md`](../BACKLOG.md) states its own single purpose in its header:

> *"The distributed convention (ADR "Deferred" / TASK "§N Open follow-ups") gives every deferral a
> durable, agent-visible home-of-truth — **but no cross-cutting view; you can't ask 'show me everything
> we've deferred.'** This index supplies that view without a second source of truth."*

**It could not answer that question.** As of 2026-07-28, before this changeset's own capture pass: three
open entries, **all surfaced 2026-06-16** — one day. (The `2026-07-22` stamp in the file is a
verification note inside a *Closed* row, not a capture.)

⚠ **The table has since grown — ~30 open rows at the time of writing, 96 by 2026-08-18 (§2) — and that does
not close this gap** — those rows were
placed **by hand**, in bulk, by the 2026-07-28/29 workspace-artifact review. A one-off manual backfill
is the opposite of a forcing function: it proves the index *can* be filled when someone spends a week
looking, not that it fills itself. Read the argument below against the capture *rule*, not the row count.

Since that date the backend shipped DBAL-only persistence, the event-log substrate, sequential PAdES,
the testing standard, the Notification BC, and E&A Stage-0. Every one deferred things. None reached the
index.

<!-- OFFREPO: the 2026-07-28 scratchpad audits were session-local working files, never committed to any
     repo and not reachable from a checkout. Their one load-bearing finding is restated in the sentence
     below; nothing here needs them read. -->

**The distributed half of the convention works.** The deferrals genuinely are in their ADR/TASK homes —
independently confirmed by the 2026-07-28 scratchpad audits, which repeatedly found a deferral properly
homed and *only* missing from the index. It is the index half that failed.

**Root cause: "Capture here, decide there … add a one-line entry the moment something is deferred" is a
discipline rule with no forcing function.** Nothing fails when you skip it, and the failure is invisible
— a stale index reads exactly like an accurate one that happens to be short.

## 2. Measurements (2026-07-28 at `develop`; re-measured 2026-08-18 at `f779baa`)

The extractor's feasibility turns on whether a structured surface exists to extract *from*. It does not.

⚑ **Re-measured 2026-08-18 at `f779baa`. Every command still runs; every number moved, none reversed
direction, and the case is stronger on all six axes.** Both columns are kept because the *drift itself* is
evidence — a record whose numbers were three weeks old is the same failure mode as the index it indicts. Do
not delete the 2026-07-28 column; re-run and add a column if you read this later.

| Measure | 2026-07-28 | **2026-08-18** | Command |
|---|---|---|---|
| ADRs with a `Deferred`-style **heading** | 3 of 38 | **6 of 52** | `rg -l '^#{2,3}.*[Dd]eferred' docs/adr/*.md \| wc -l` — ⚠ same glob hazard as row 3: `docs/adr/*.md` is **54** files (it sweeps `README.md` and `AUTHORING.md`), so the denominator here is `ADR-*.md`. Harmless today because all 6 hits are ADRs, and it stops being harmless the day either of those two gains the heading |
| ADRs mentioning deferral **anywhere in prose** | 27 of 38 | **37 of 52** | `rg -li 'deferred\|defer ' docs/adr/ADR-*.md \| wc -l` |
| TASKs with a follow-ups **heading** | 8 of 20 | **11 of 29** | `rg -l '^#{2,3}.*([Oo]pen follow\|[Ff]ollow-ups)' docs/tasks/*.md \| wc -l` — ⚠ the glob counts `README.md`, so the raw command returns 12 of 30; the figure here excludes it |
| Distinct heading shapes in use | ~20 | **29** | `rg -o '^#{2,4} .*([Dd]eferr\|[Ff]ollow-up\|[Oo]pen).*' docs/adr/*.md docs/tasks/*.md \| sed 's/.*md://' \| sort -u \| wc -l` |
| ADRs minted since the last capture (2026-06-16) | 15 | **29** | `for f in docs/adr/ADR-*.md; do grep -m1 '^\| \*\*Date\*\*' "$f" \| grep -oP '\d{4}-\d{2}-\d{2}' \| head -1; done \| awk '$1>"2026-06-16"' \| wc -l` — first is ADR-0024 (2026-06-18) |
| `BACKLOG.md` rows | ~30 open | **96 `Open` of 127** (19 `Folded`, 12 `Closed`) | `grep -cE '^\| BL-[0-9]+' docs/BACKLOG.md` for the total; per status, `grep -E '^\| BL-[0-9]+' docs/BACKLOG.md \| grep -c '\| Open \|'` (and `Folded`, `Closed`) — ⚠ give the breakdown its own command: the first draft of this row said `10 Closed`, which was both wrong and did not sum to 127 |

⚠ **The `15` is also hard-coded in this record's `Why` field and in `BACKLOG.md`'s own gap notice**, both
*outside* this command-backed table — so a reader who re-runs the table still meets a stale 15 twice. That is
authoring rule 1's "the diff is not the search surface" in miniature: the number was swept where it had a
command beside it and missed where it was prose. It is now **29**.

Observed heading vocabulary includes `## 4. Deferred` · `## 5. Deferred` · `## Deferred (tracked, not
decided)` · `## Deferred (Proposed-within / owed)` · `## 8. Open follow-ups (track, don't solve here)` ·
`## 9. Follow-ups (still out of scope)` · `## 5. Open items / follow-ups` · `## 6. Open follow-ups this
task surfaces`. **There is no surface to extract from today.** That is the work.

## 3. The plan — two phases, deliberately in this order

**Phase 1 — the census (manual backfill).** Read the deferral surface of every ADR and TASK touched since
2026-06-16 and write the missing index rows by hand.

⚑ **Phase 1 is not a stopgap — it is the specification-gathering for Phase 2.** BACKLOG's own convention
already puts the substantive record in the ADR/TASK home, so a hand backfill is *literally a manual
execution of the extractor Phase 2 automates*. You cannot design a section convention that absorbs ~20
heading shapes without having read all of them; the census is what forces that reading. Doing Phase 2
first would mean designing the convention against a guess.

<!-- OFFREPO: the question below was raised verbally by other team members on 2026-07-28 and has no artifact
     outside this repo — no ADR, no `notes/` file, nothing in either repo's git log. In-repo it is recorded
     in exactly two places: this section and `docs/BACKLOG.md` BL-7. It is restated in full here, which is
     all a reader needs; there is nothing external to go and read. -->

> ### ⚠ Do not start Phase 2 before checking one thing
>
> **There is an open question about moving the tasks and related tracking files out of this repo**
> (raised by other team members, 2026-07-28). If that lands, most of Phase 2 is wasted: the
> `composer backlog` extractor below reads `## Deferred` sections *in `docs/tasks/`*, and
> `docs/BACKLOG.md` is itself a tracking file. **The ADR half survives either way** — ADRs stay.
>
> ⛔ **Checked 2026-08-18, and the answer is worse than "still open": nobody ever wrote it down.**
> Swept 52 ADRs, 29 TASKs + their README, 127 `BACKLOG.md` rows, both `CLAUDE.md` files, `notes/`,
> `repos.manifest`, and the full `git log --all` of this repo *and* the workspace repo. **An absence of
> record is not a decision**, so the constraint stands and **Phase 2 is ADR-side only** until someone
> answers it.
>
> ⚑ **This was the task's own thesis biting it, and the fix is the thesis working.** Until 2026-08-18 this
> blockquote was the *only* occurrence anywhere: a blocking constraint on a piece of infrastructure, living
> in the record it blocks, with no index row — invisible to exactly the cross-cutting view this task exists
> to restore. It is now also carried by [BL-7](../BACKLOG.md), which is where a reader scanning the index
> meets it. **So do not mint a new BL row for it** — that row exists.
>
> ✅ **ANSWERED 2026-08-18 by the user: `docs/tasks/` and the tracking files STAY IN THIS REPO.**
> So the precondition is discharged and **Phase 2 is no longer restricted to the ADR side** — the TASK half is legal
> to build. ⛑ Recording it here (and in [BL-7](../BACKLOG.md)) is the point: the constraint had survived three weeks
> as an unwritten question that silently gated a piece of infrastructure, which is the failure this whole task is
> about. **Do not re-derive this from practice; it is now a decision with a date.**
>
> ⚠ One indirect counter-signal, recorded as practice rather than as an answer: [`README.md`](README.md)
> landed 2026-08-17, three weeks *after* the question was raised, and commits to *"the plan of record for
> backend work is here"*. That is somebody building on `docs/tasks/` staying, not a decision that it stays.
>
> So if the question is still open when you pick this up: **build the ADR-side extraction only**, and
> leave the TASK-side convention until the repo layout is settled. Phase 1 (the census) is safe regardless
> — it produces knowledge, not infrastructure. §6 Q1 below is affected the same way: the `docs/tasks/`
> lifecycle question only exists while the directory does.

**Phase 2 — structure the source, then generate.**
1. Add a uniformly-named, required `## Deferred` section to the ADR template in
   [`../adr/AUTHORING.md`](../adr/AUTHORING.md), and the TASK equivalent in [`README.md`](README.md).
   ⛔ **Corrected 2026-08-18: this step used to say *"there is no TASK authoring guide today"*. There is** —
   `docs/tasks/README.md` landed 2026-08-17 and its spine already names `## 6. Open follow-ups`, so the TASK
   half is **uniformity plus a forcing function** (11 of 29 files conform, in 8+ wordings), not authoring a
   guide. ⚠ And see §7.2 for a constraint this step does not cost: `AUTHORING.md`'s template is a numbered
   §1–§9 spine with §§7–9 optional and the same never-renumber rule, so a mandatory section lands either as
   **§10** or as a **decimal nested under an existing slot**, and that choice fixes what the extractor greps
   for across 52 files.
2. Retro-fit the heading across the existing corpus, using the Phase-1 census as the worklist.
3. Add a `composer backlog` script that extracts those sections into the index. The generated view
   replaces the hand-maintained *Open* table; `docs/BACKLOG.md` keeps its header, conventions, and the
   *Closed* history.
4. Decide the enforcement question: does a missing/empty `## Deferred` section fail a gate, or is the
   generated index simply authoritative and a missing section means "nothing deferred"? The second is
   cheaper and probably sufficient — the point is to remove the *capture* step, not to add a new rule to
   forget.

## 4. Scope boundary — decide before Phase 1 writes rows

⛔ **DECIDED 2026-08-18 by the user: leave `BACKLOG.md` exactly as it is for now** (*“dejalo como está de momento”*).
The index stays **hand-maintained**, the boundary question below stays open, and **§3 Phase 2 step 3 must not be
built** — that step replaces the hand-maintained *Open* table with a generated view, and §8.6.6 measured what that
would cost: **34 rows whose only home is the index would be deleted**, `BL-6` (`UuidGenerator::v5()` has no test,
while its test docblock claims otherwise) and `BL-8` (the event-log relay worker has none) among them. Those are
review findings, and a review has no ADR of its own to write them into.

⚑ **So the task stops after Phase 1.** Steps 1–2 (a uniform `## Deferred` section, and the retro-fit) are legal but
pointless on their own — they are the *input* to a generator nobody is allowed to run yet, and §8.6 measured that
retro-fit at ~379 prose items. Re-open when the 34 orphans have a home, or when the generator is allowed to keep a
“no upstream” section instead of replacing the table.


`docs/BACKLOG.md` already excludes substrate/design gaps (they route to the design-repo trackers). A
sharper narrowing is worth considering **as part of Phase 1, using real examples rather than in the
abstract**: should the index hold *only* deferrals with **no** natural ADR/TASK home?

`BL-3` is exactly that shape today ("doc hygiene (no ADR)"). Under that narrowing everything with a home
routes there and never appears here — a much smaller file that stays true by itself, at the cost of the
cross-cutting view the header argues for. **Phase 1 should surface how many entries fall on each side,
then the call gets made on evidence.** Do not settle it before the census.

## 5. ⚑ The sibling problem — do not scope these independently

This is the **second** hand-maintained cross-cutting index found drifting in the same 2026-07-28 review.
The first is the Tier-A requirement-traceability column in [`../../tests/README.md`](../../tests/README.md),
diagnosed in [TASK-019 §1.3](TASK-019-requirement-traceability-and-per-tier-gates.md) — same shape, same
silent drift, same root cause (a hand-maintained projection of data that already exists elsewhere).

That investigation reached the same conclusion and proposed the same fix. ⛔ **Corrected 2026-08-18: this
section used to say TASK-019 *"does not carry"* that fix, and to instruct the reader to treat the paragraph
below as its missing §4.6. Both were wrong, and wrong from the start** — TASK-019 **§4.6 "Generate the
carrier column"** exists, carries this fix, cites this section back, and already says to scope the two
together. As of `f779baa` — i.e. before this correction added a second commit to *this* file — `git log --all`
gave each file exactly one commit, the same one (`61322da`), and `git show 61322da` already contains §4.6, so
this was never true rather than having rotted. (Check it with `git show 61322da:docs/tasks/TASK-019-requirement-traceability-and-per-tier-gates.md`,
which does not depend on either file's later history.) Following the old instruction would
have written a *second* §4.6 over a live anchor. The fix is restated below as the shared statement of it, not
as something missing from over there:

> **"Generate, don't maintain."** Delete the hand-maintained carrier column from the traceability matrix
> and print requirement → tests from the `#[Group('eIDAS-…')]` attributes on demand (`composer
> traceability-matrix`). The markdown then keeps only requirement → ADR — the part that **isn't**
> derivable. The reasoning that makes it the right move: *the column is a projection of the attributes*,
> so it is the only proposal that **removes** the drift surface rather than adding a guard over it.

TASK-019 carries both halves: the diagnosis that the column drifts (§1.3, §1.4), the PHPStan-rule guard (§4),
**and** removal as §4.6. So the two records agree and each points at the other; neither is missing anything.
⚑ **What that costs the reader is the opposite of what this section used to warn about:** the risk is not a
gap to fill but a *duplicate* to keep in step — two statements of one fix, in two files, which authoring
rule 1 says will drift unless a change to either sweeps both.

**Two independent instances of one pattern is a signal about the pattern.** Both want the same shape of
solution (a `composer <thing>` that projects from structured source), and doing them together is most of
the cost of doing either. Sequence them as one piece of work.

## 6. Open questions

⚑ **This heading is itself an entry on Phase 2 step 2's retro-fit worklist, and it is left that way
deliberately.** [`README.md`](README.md) §2 puts `## 6. Open follow-ups (track, don't solve here)` in the
spine; this record says `## 6. Open questions`, so the document arguing for a uniform heading does not carry
one — it is one of the 18 of 29 that do not. Renaming it now would move a live markdown anchor for a
cosmetic gain *before* the convention is decided (§7.2 shows the ADR-side heading is still an open choice
between a new section and a decimal). It gets renamed by the retro-fit, with everything else, once there is
something to rename it *to*.

1. ⚑ **Is a TASK doc a living document or an as-built record? Answer this before Phase 2.**
   `docs/adr/AUTHORING.md` exists; there is **no TASK equivalent**, and `docs/ddd/README.md`'s lifecycle
   section fixes the ADR (point-in-time, never rewritten) vs domain-model (living, updated in place)
   contrast precisely while saying nothing about `docs/tasks/`. The task docs self-declare
   inconsistently — TASK-006/007/008 call themselves *"As-built record — documented after the build"*,
   TASK-010 *"Build plan (forward)"*, TASK-003 *"Agent-delegable implementation task"*.
   **Two things depend on the answer.** (a) A mandatory `## Deferred` section cannot be imposed on docs
   whose kind is undefined — an as-built record's deferrals are historical, a living doc's are current,
   and the generated index must not mix them. (b) A number of task-doc **bodies** still describe the
   retired ORM or the `domain.*` schema in the present tense; whether that is *rot to fix* or *history
   to preserve* is the same question. **Enumerate them rather than trusting a list here** —
   `rg -l -e '\bORM\b' -e 'EntityManager' -e 'ClassMetadata' -e 'Embeddable' -e 'domain\.(envelope|document|step|recipient|signing)' docs/tasks/*.md`
   — ⛔ **fixed 2026-08-18; it was written `rg -lE '…|…'`, which does not run.** ripgrep parses `-E` as
   `--encoding`, so it exits with *"unknown encoding"* rather than matching anything. A command whose whole
   purpose is *"enumerate rather than trusting a list here"* that errors out is worse than the list it
   replaced, because the error reads as a tooling problem rather than a broken instruction. The form above
   returns **11** files (verified: TASK-001, -002, -003, -008, -009, -012, -015, -017, -018, -020, README.md)
   — then read each hit, because the grep cannot tell a live-voice claim from a correctly-dated
   historical one (TASK-012's single hit is explicitly annotated *"the ORM adapter is gone (ADR-0018)"*
   and is not rot). A hand-kept membership list here would be the very artifact this task exists to
   retire. A 2026-07-20 corpus reconcile
   updated their Status rows and deliberately stopped at the bodies, which is why they still read that
   way; TASK-003 was not touched at all.
2. **Output format** — does `composer backlog` rewrite `docs/BACKLOG.md` in place (reviewable in a diff,
   but a generated file in git) or print to stdout (no drift possible, but not browsable on the web)?
   In-place-with-a-generated-marker is the likelier answer; the diff *is* the review surface.
3. **Does `Status` survive generation?** The current vocabulary (`Open`/`Folded`/`Landed`/`Closed`)
   partly encodes "is the home-of-truth written yet" — which becomes meaningless once the home *is* the
   source. Probably collapses to open-vs-closed.

---

## 7. Verification — how you know each phase is done

⚑ **Added 2026-08-18.** §§1–6 are unrenumbered: they are cited by id from [`BACKLOG.md`](../BACKLOG.md) BL-7
and from [TASK-019](TASK-019-requirement-traceability-and-per-tier-gates.md) §4.6, and this record's whole
subject is what happens when a cross-document pointer stops resolving.

**Why it was missing is worth one line, because it is this task's own thesis again:** a record arguing that
*"nothing fails when you skip it, and the failure is invisible"* had no bar of its own, so nothing failed when
it shipped without one — and a plan with no bar reads exactly like a plan whose bar is obvious.

### 7.1 Phase 1 — the census

| Property | How it is checked |
|---|---|
| The census output has a **durable home in the repo**, named before Phase 1 starts | ⛔ The one bar with no default. *"Knowledge, not rows"* is not a licence to leave it in a scratch file — this repo has already had to reconstruct *"eight deferrals that lived only in an untracked memo"*. It is not `BACKLOG.md` (those are the rows §4 gates), so it is a new `## 8` here or a file under `docs/`. **Named 2026-08-18: `## 8. Phase 1 — the census`, in this file.** Chosen over a new file under `docs/` because the census is specification-gathering *for §3 Phase 2*, so it belongs beside the plan it specifies, and because a new tracking file is the one thing §3's unanswered precondition argues against creating |
| Every ADR and TASK touched since 2026-06-16 had its deferral surface **read** | The worklist is the §2 commands re-run at census time, not a list written here — a hand-kept membership list is the artifact this task exists to retire. Checked by the count of files read matching the count those commands return, at census time |
| Each deferral found is **classified** against §4's question: does it have a natural ADR/TASK home, or not? | A count on each side, which is the *evidence §4 says the boundary call must be made on* |
| Deferrals already present in the index are distinguished from ones missing from it | Otherwise the census measures the corpus rather than the gap |
| No index rows are written | ⛔ Deliberate. §4's call decides what a row *is*; writing rows first settles it by accident |

⚠ **Phase 1's output is a classification, not a patch.** It is done when the boundary question can be
answered from evidence — and answering it is **not** Phase 1's job.

### 7.2 Phase 2 — structure, then generate

| Property | How it is checked |
|---|---|
| **Idempotence — the load-bearing bar.** `composer backlog` twice in a row produces no diff on the second run | The only property that distinguishes *removing* the drift surface from *guarding* it. A generator whose output drifts from its own source has reproduced the problem with more steps |
| Every `## Deferred` section in `docs/adr/` is represented in the generated view | Drop one section, re-run, and the row must disappear — a generator nobody has seen fail is not known to read anything |
| Hand-written content survives generation | `BACKLOG.md` keeps its header, Conventions block and `Closed` history (§3 Phase 2 step 3). Assert on the file, not on the generator's intent |
| The ADR template change does not renumber | See below — it lands as §10 |
| **The TASK half is NOT built** | Gated on §3's precondition. Its absence is the expected state, not an incomplete run |

⚠ **A shape decision the plan does not cost, found 2026-08-18:** [`../adr/AUTHORING.md`](../adr/AUTHORING.md)'s
§Section template is a **numbered §1–§9 spine with §§7–9 optional** and the same never-renumber rule. So a
*mandatory* `## Deferred` has two possible homes, and they are not equivalent: a new **§10**, which sits
behind three optional sections, or a **decimal nested under an existing slot** — the template explicitly
provides for that (*"a section outside these nine nests as a decimal under the slot it serves"*, giving
`### 2.8` and `### 5.4`), which would put it under §3 Risks or §5. ⚑ **Decide it deliberately.** An extractor
keys on the heading, so the choice fixes what the generator greps for across 52 files and is expensive to
revisit. (An earlier draft of this note said §10 was the *only* option; that was wrong — it had not read the
nesting rule two lines further down.)

⚠ **And the TASK half is smaller than §3 step 1 says**, because that step is stale: it claims *"there is no
TASK authoring guide today"*, but [`README.md`](README.md) landed 2026-08-17 and serves that role, its spine
already naming `## 6. Open follow-ups`. The residue is **uniformity plus a forcing function** — 11 of 29 task
files conform, in 8+ wordings — not authoring a guide from scratch.

### 7.3 What is explicitly out of both bars

Answering §3's repo-layout precondition · answering §4's boundary question · answering §6's three open
questions · the enforcement decision in §3 Phase 2 step 4, which **becomes ADR-owing if the answer chosen is
a PHPStan rule or a `phpstan.dist.neon` edit** — the `Decision record` field's trigger clause already covers
that, and it is the one route by which this task acquires an ADR.

---

## 8. Phase 1 — the census (2026-08-18)

⚑ **Run 2026-08-18 at `7f0fa78`, against §7.1's five properties.** §7.1 names this section
`## 8. Phase 1 — the census`; the parenthesised date is a run stamp, not a rename — re-running the census
adds a dated sub-section, it does not retitle this one. §§1–7 are untouched: they are cited by id from
[`BACKLOG.md`](../BACKLOG.md) BL-7 and from
[TASK-019 §4.6](TASK-019-requirement-traceability-and-per-tier-gates.md).

⛔ **No `BACKLOG.md` row was added, edited or removed by this pass, and none should be until §4's call is
made.** That is §7.1's last bar and it is the one with a live temptation attached: **637** of the items
below have no index row, and each looks like a one-line entry waiting to be typed. Typing them settles §4
by accident, which is the one thing §4 says must not happen.

### 8.1 How the worklist was derived — and where §2's derivation is wrong

Every number below is from a command re-run at census time, not from a list in this record. The commands
and what they returned:

| # | Command | Returned |
|---|---|---|
| 1 | `ls docs/adr/ADR-*.md \| wc -l` | **52** (the `docs/adr/*.md` glob returns 54 — `README.md` + `AUTHORING.md`) |
| 2 | `ls docs/tasks/*.md \| wc -l` | **30** (29 `TASK-*` + `README.md`) |
| 3 | `for f in docs/adr/ADR-*.md; do grep -m1 '^\| \*\*Date\*\*' "$f" \| grep -oP '\d{4}-\d{2}-\d{2}' \| head -1; done \| awk '$1>"2026-06-16"' \| wc -l` | **29** minted since the last capture, first `ADR-0024` (2026-06-18) — §2's figure, confirmed |
| 4 | `for f in docs/adr/ADR-*.md; do git log --format=%ad --date=short -1 -- "$f"; done \| awk '$1<="2026-06-16"'` | **empty** — *every* one of the 52 ADRs was **touched** since 2026-06-16, and so was every task file. §7.1's worklist phrase is "touched since", so the worklist is the whole corpus: **82 files** |
| 5 | `rg -l '^#{2,3}.*[Dd]eferred' docs/adr/ADR-*.md \| wc -l` | **6** — §2's figure, and see the correction below |
| 6 | `rg -li 'deferred\|defer ' docs/adr/ADR-*.md \| wc -l` | **37** — §2's figure, and see the correction below |
| 7 | `rg -l '^#{2,3} +([0-9]+\.? +)?(Deferred\|Open follow-ups\|Follow-ups\|Open items\|Open questions\|Open decisions)' docs/tasks/*.md \| wc -l` | **19** of 30 task files (**18** of 29 with the `TASK-*.md` glob), against §2's `11 of 29` |
| 8 | `grep -cE '^\| BL-[0-9]+' docs/BACKLOG.md` + per-status | **127** rows: **96 Open**, 19 Folded, 12 Closed — §2's figures, confirmed |
| 9 | `grep -E '^\| BL-[0-9]+' docs/BACKLOG.md \| grep -c 'fold pending'` | **47** — every one of them `Open`. §8.5 is mostly about this number |
| 10 | `rg -o 'BL-[0-9]+' docs/adr/ADR-*.md docs/tasks/*.md \| sed 's/.*://' \| sort -u` | **56 distinct** ids cited back from the corpus, across **31** files |

⚠ **Pipes in the cells above are written `\|` because a markdown table requires it — unescape them before
running.** Said out loud because this record has already shipped one command that could not run (§6 Q1's
`rg -lE`), and a copy-pasted `\|` fails the same way: as a tooling error rather than as a broken
instruction.

⛔ **Correction 1 — command 5 is 4/6 false positives, and the true structured surface is two files.** Of
the six heading hits, only **`ADR-0022` (`## Deferred (tracked, not decided)`)** and **`ADR-0027`
(`## Deferred (Proposed-within / owed)`)** are deferral *sections*. The other four are decision headings
that happen to contain the word — `ADR-0018` *"Phase C … realizes ADR-0019 §1's deferred enforcement"*,
`ADR-0039` *"§4. Append-only; revocation is deferred"*, `ADR-0045` *"§2.7 Publication, and the deferred
leak-notification endpoint"*, `ADR-0051` *"§2.5 A durable command queue is deferred…"*. §2's glob-hazard
note guards the denominator and misses this, which is the larger error: the row is read as *"6 ADRs
already have the section Phase 2 wants"* and the real number is **2**.

⛔ **Correction 2 — command 6 is not a valid membership filter, and the census had to widen past it.**
Nine ADRs match neither command 3 nor command 6 (`ADR-0001, -0002, -0005, -0006, -0007, -0009, -0013,
-0014, -0020`). They were read anyway, as a control. They carry **60 deferrals**. The vocabulary those
records use is `queued` · `not built` · `unbuilt` · `Candidate rule` · `◯ planned` · `Not realized` ·
`discipline-until-built` · `pending` · `left open` · `Open question` · `Reopening clause` · `gated` — the
word *defer* appears in two of the nine and in both it is incidental. **An extractor keyed on the word
finds none of `ADR-0013`'s sixteen or `ADR-0014`'s thirteen.**

⛔ **Correction 3 — the deferral surface in ADRs is not under headings at all.** `## Risks` is a real
heading in **9** of 52 ADRs; **39** carry `**Risks**` as a *bold label* inside `## Consequences`
(`rg -l '^#{2,3} .*Risks' docs/adr/ADR-*.md` vs `rg -l '^\*\*Risks' docs/adr/ADR-*.md`). Same for
`**Deferred**` / `**Negative / deferred**`, which is a bold label in **10** ADRs and a heading in none of
them. Anything greping `^#{2,3} ` over `docs/adr/` sees a fraction of what is there.

**The unit.** A *deferral* here is one distinct thing a record says is **owed, unbuilt, out of scope,
open, or pending** — the widest defensible reading, because a narrower one would beg §4's question. A
decision that was *taken*, an item recorded as landed/closed/discharged, and a historical note about an
earlier cut are all excluded; where a record struck a bullet or stamped it `RESOLVED`/`(done)`, it was
skipped. Under this unit the corpus carries **718** deferrals against 96 open index rows, so the unit is
finer than a `BL-` row: several census items would fold into one row. That cuts the *ratio* below by some
factor; it does not move it near 1.

**The classification rule, stated so it can be disagreed with.** An item is **HAS-HOME** when the record
it was found in — or another ADR/TASK that record explicitly names — is where a future decision on it
would be written. It is **NO-HOME** when its subject belongs to no ADR and no TASK: off-repo application
code, off-repo infrastructure, a legal or vendor gate, repo tooling and dependencies, prose hygiene, or a
cross-cutting subject the record itself says has no owner. The rule is deliberately about *where the
decision would land*, not about *who does the work* — an item can be entirely someone else's to build and
still have a home here, which is why ADR-0049's six §2.11 cases are NO-HOME while ADR-0037's twelve
deferred capabilities are not.

**How it was read.** All 82 files were read in full, ten batches in parallel, each batch emitting one line
per deferral with its section, its classification and any `BL-` id in the surrounding text; §8.2's numbers
are the tallies of those lines. The mechanical figures (§8.1's ten commands, §8.4's `←` column, §8.5's
`fold pending` intersection) are reproducible exactly; the classification is a judgement against the rule
above and a re-run should expect to move individual items, not the 83/17 split.

**Why the table is per record rather than per item.** 718 rows would be a hand-maintained list of exactly
the kind this task exists to retire, and unreadable besides. §8.2 gives one row per record with the item
count, the enumeration in the last column, and the classification as counts — so every count below is
auditable from the table. §8.3 then enumerates the **NO-HOME** side item by item, because that is the side
§4's question is actually about, and it is the small one.

### 8.2 The corpus, record by record

`n` = deferrals found · `§` = how many sit under a heading or bold label naming *deferred / follow-ups /
open questions / open decisions / out of scope* (the rest are inline prose) · `H` / `N` = has-home /
no-home per §4's question · `←` = items whose own text cites a `BL-` id.

| Record | n | § | H | N | ← | What it defers |
|---|--:|--:|--:|--:|--:|---|
| ADR-0001 | 3 | 0 | 3 | 0 | 0 | thin-delegation, attribute-presence, generic-bound and paired-use-case rules all queued; split held by review |
| ADR-0002 | 3 | 0 | 3 | 0 | 0 | `ReactorDispatchOnlyRule` + four sibling reaction-integrity rules queued; dispatch-only is discipline |
| ADR-0003 | 3 | 0 | 3 | 0 | 0 | audit/aggregate atomicity if the stores ever split; the projector that reads the materiality marker; chain-at-projection-time |
| ADR-0004 | 5 | 0 | 4 | 1 | 0 | `ContractSurfaceKernelGroundedRule`; a deptrac ban on Domain/Contract→OtherBC; `CrossBcAdapterThrowsPublishedExceptionRule`; checked-exception analysis; the design-repo doc cascade |
| ADR-0005 | 3 | 0 | 3 | 0 | 0 | restoring `readonly` on composites; composite immutability is lint-only; the reflection-write gap |
| ADR-0006 | 1 | 0 | 1 | 0 | 0 | Step's mint moves to command-carry if Step becomes externally addressable |
| ADR-0007 | 2 | 0 | 2 | 0 | 0 | the four-item reopening bar for a composite-identity sub-category; overcorrection guarded only by that bar |
| ADR-0008 | 5 | 0 | 5 | 0 | 0 | list/pagination + activity-log read verticals; write-side published exceptions; `findContextForSE` duplication; `ReadRepositoryReturnRule` |
| ADR-0009 | 16 | 0 | 15 | 1 | 3 | part-6 redaction layer absent; Sentry/OTel absent; correlation propagation (part 4); observability port (part 5); ECS field divergence (part 7); `/healthz` (part 8); async half of part 3; five queued tests/rules; no `elastic/ecs-logging-php` |
| ADR-0010 | 5 | 0 | 5 | 0 | 0 | `LogCommand` middleware; the order-assertion test; the in-transaction port check; the empty authorization slot; per-message tenant scope on workers |
| ADR-0011 | 4 | 0 | 4 | 0 | 0 | the naming lint candidate; the act-owner exception it must encode; prefix-registry maintenance |
| ADR-0012 | 5 | 0 | 5 | 0 | 0 | validation of externally-signed documents (explicitly unhomed); the shared DSS transport adapter; "no DSS client outside SE"; `SealService`/`XAdESSignerInterface` |
| ADR-0013 | 16 | 0 | 16 | 0 | 0 | `DEPLOYMENT_MODE` selector + DI overlay; plan-limit and metering adapters; secrets adapters; the Sentry/OTel and TSA matrix rows; matrix-currency check; mode-branch rule |
| ADR-0014 | 13 | 0 | 13 | 0 | 0 | Layer 3 (`Idempotency-Key` edge filter, replay/409/TTL); the per-operation fail-open policy; the delta-verb rule; the redelivery-convergence roster |
| ADR-0015 | 12 | 4 | 12 | 0 | 1 | circuit-breaker semantics; timeout budgets; native `RetryableHttpClient` swap; worker-death reclaim; the claim lease; per-kind retry curves; permanent-vs-transient classification; DLQ alerting; the produce/consume gaps TASK-026 owns |
| ADR-0016 | 8 | 0 | 8 | 0 | 0 | the compliance-class domain model; presigned-direct upload; per-object retention/legal-hold; explicit `parentHash`; the class→profile mapping test; the pre-first-write swap window |
| ADR-0017 | 3 | 0 | 3 | 0 | 0 | the contract's application by Session/SE/E&A/Legal; system context above RLS; schema-per-tenant revisit |
| ADR-0018 | 11 | 0 | 10 | 1 | 1 | D1 lock-vs-write-set re-check + per-intent writes; D2 draft child-edit; D3 `rehydrate` altitude; D4 relationship contract; D5 residual mutants; enum-orphan check; 409 mapping; per-BC roles; the infra `[ERROR]` guard |
| ADR-0019 | 7 | 0 | 6 | 1 | 0 | UUID case-folding; the `CASCADE` tier of the referential check; enum-subset guard; soft-delete shape; `db_`/`sys_` adoption; conformance-test growth; the unprovisioned erasure role |
| ADR-0020 | 3 | 0 | 3 | 0 | 0 | shared `StringValue` base at rule-of-three; the duplicate base meanwhile; reopening the Subject axis |
| ADR-0021 | 5 | 1 | 5 | 0 | 0 | system/bootstrap routes above RLS; `/api/health`; route-schema ratification; a richer same-BC read view; the un-extracted tenant-scope helper |
| ADR-0022 | 12 | 5 | 12 | 0 | 0 | `Idempotency-Key`; CORS; the `page`/cursor shape; correlation + rate-limit headers; presigned response shape; the unratified response shapes and their un-pinned presenter test; absolute URLs; route-name constants; the `ActorContext` seam, its interim resolver, and the authorization model |
| ADR-0023 | 7 | 0 | 6 | 1 | 1 | B-T/B-LT/B-LTA + QES; the early non-B-B guard; async/breaker hardening; the stage-3 dispatch adapter; the no-DSS-client rule; unlifted `Extend*`/`Digest*` DTOs; the trusted seal cert |
| ADR-0024 | 7 | 0 | 5 | 2 | 0 | the async command path; versioning-as-capability; the payload-purity rule; a relay poison test; correlation/causation propagation; the `App.`→brand routing-key rename; the design-repo drift ledger |
| ADR-0025 | 5 | 1 | 5 | 0 | 0 | the problem-type registry and resolvable `type` URIs; `request_id`; `documentation_url`; the nested `error {}` shape; values pending frontend ratification |
| ADR-0026 | 6 | 4 | 6 | 0 | 0 | Swagger UI (needs TwigBundle + Asset); production doc-endpoint auth; date-based versioning; §A3's unratified shapes; hand-written component schemas; the presence-only coverage guard |
| ADR-0027 | 3 | 1 | 3 | 0 | 0 | an active `SEALING` state + async seal command; multi-document fan-out; the cross-BC `SEALING` write |
| ADR-0028 | 12 | 5 | 11 | 1 | 0 | the richer auth ceremony and its states; the E&A evidence-packet handoff; token revocation and mint-time validation; the concurrent-open upsert (500 today); batch/offline sessions; a per-recipient SE aggregate; replay in the 7-day window; the un-attestable dev secret; the tamper-evident chain; the signer-frontend contract reconciliations |
| ADR-0029 | 2 | 0 | 2 | 0 | 0 | the unminted auth-refusal kind; default-422 masking of a future 409/404 refusal |
| ADR-0030 | 4 | 0 | 4 | 0 | 0 | ADR-0003's retirement; the observation/transition storage fork collapse; detached append + tenant-agnostic scope; the preparatory slice |
| ADR-0031 | 18 | 0 | 16 | 2 | 7 | `subject_tenant_id`; Merkle + external anchoring; Path-A cipher; process isolation; the queue-command trap; partitioning and its two unmeasured premises; archival/Merkle co-design; a per-stream gapless counter; checkpoint rewind; surgical replay; golden-bytes fixtures + their census; the `ActorId` payload drift; the missing second realizer; the write-time `category` column; watermark-stall remedies; two docblocks owed a correction |
| ADR-0032 | 15 | 0 | 9 | 6 | 0 | the whole log-carrier (keystore, tombstone/crypto-shred, `erased`, `PayloadCipher`); the projector-topology ADR; the missing `RecipientAdded`; the open rehydration state; decrypt authorization; the two-implementations round-trip; the `Erasable` marker home; three legal sign-offs; managed KMS ×2; crypto-shred vs backup retention |
| ADR-0033 | 11 | 0 | 10 | 1 | 0 | the `recipient.email` carrier and its expand/backfill/contract recut; `RecipientFieldCipher` and its call sites; the blind index; `BYTEA` as production form; the backfill console command; per-request key caching; key rotation; the `Pii`-must-be-enciphered rule; substrate rot with no caller; the managed-KMS provider |
| ADR-0034 | 4 | 2 | 3 | 1 | 0 | per-party certificates / QES; `padesTargetProfile` B-T/B-LT/B-LTA; the async seal inherited from ADR-0015; the self-signed dev keystore |
| ADR-0035 | 11 | 0 | 8 | 3 | 1 | the per-tier covered-MSI gate; `beStrictAboutCoverageMetadata`; `Proposed` until both go green; generative property testing; the suite migration; threshold tuning; Eris immaturity; PCOV; judgement calls owed to `tests/README.md`; `phpstan/tests/` naming |
| ADR-0036 | 3 | 0 | 3 | 0 | 0 | the bare-`@var` rule candidate; the narrowing-prune pass; boundary rule 1 only partly enforced |
| ADR-0037 | 20 | 10 | 19 | 1 | 0 | the receipt seam + provider choice; the `NotificationFailed` return path; channels beyond EMAIL; preference-driven selection; OTP delivery; `NotificationSent` as an audited fact; the purpose catalog + i18n; async transmit; at-rest contact PII; `BoundedContextId`; the un-indexed "which failed" query; the catalog's home; the envelope-shaped trigger; `DELIVERED` unreached and hard bounce unmodelled; the unversioned slot-supplier; the resend window; the production SMTP transport |
| ADR-0038 | 9 | 0 | 9 | 0 | 0 | ICU `MessageFormat` as a deferred-not-rejected engine; rendered-bytes vs copy; slot-supplier drift; append-only typo versions; untyped `parts`; pre-rendered-PII archiving; the undriven JSONB branch; the unenforced frozen constants; tenant-in-seed cost |
| ADR-0039 | 9 | 4 | 7 | 2 | 1 | grant revocation as soft-delete; read-side access audit; retiring `envelope.document.visible`; per-recipient completion delivery; pushing the predicate into SQL; the one-line key-removal revert; the SINGLE_SEAL backfill gap; the off-repo sender prefix; the dashboard cutover |
| ADR-0040 | 18 | 0 | 18 | 0 | 9 | retiring `document_assignment_placement`; the field-removal surface; the send-time text-tag resolver; the `signs` re-check at `send()`; `lock_config`/FieldMDP; the `FieldType` vocabulary clash and its inert members; Smart Routing's `ON_FIELD_CHANGE`; the `NoRawDeleteRule` exemption; whether field authoring mints events; the placement backfill; sparse-ordinal read order; generalizing from unbuilt consumers; NUL truncation; unvalidated `pattern` |
| ADR-0041 | 16 | 0 | 14 | 2 | 13 | the mutation and removal surfaces; the text-tag resolver; the commit-time value write; BL-54's counter-climb half; `value` as PII; a fill stamping an unseen document; `save()` write amplification; three uncommunicated wire breaks; the duplicated geometry trait; a lossy `down()`; unverified ordinal renumbering; the frontend conventions nothing can enforce |
| ADR-0042 | 7 | 0 | 4 | 3 | 2 | ADR-0014 Layer 3 as the accepted exposure; the missing removal surface for a duplicate; the surviving upsert rewrite; the owed write-path audit; the missing "app-minted key must not originate at the edge" rule; the signer cutover; payload strictness |
| ADR-0043 | 6 | 0 | 3 | 3 | 3 | Y-axis banding; a sender-chosen order as a nullable override; the non-existent grid-snapping editor; the signer's array-order cutover conversation; that nothing can enforce a cross-repo consumer; BL-44's two-source unification |
| ADR-0044 | 12 | 3 | 12 | 0 | 0 | authorization and entitlements; identity aggregates and their persistence; email uniqueness scope; whether `ActorKind` grows; the silent Foundation deptrac cap; four properties held by review; the unconverted signing-token path; call-site issuer picking |
| ADR-0045 | 11 | 2 | 9 | 2 | 2 | which artifact publishes the grammar; the leak-notification endpoint + auto-revocation; the recipient token's non-conformance; the 43-char vs six-digit conflict; four enforcement residues (family test, per-kind tests, plaintext-nowhere, over-length refusal); the environment marker; the signer cascade; the absent limiter |
| ADR-0046 | 6 | 0 | 5 | 1 | 0 | the producer-less `user:` arm; an uncensused attribution column; the exemption list ADR-0019 must now maintain; two properties held by review; whether the shape suits other party records |
| ADR-0047 | 7 | 3 | 5 | 2 | 3 | where the declared subject and per-request access fact are recorded; the evidence-vs-telemetry store category; whether a declared reference ever resolves; validate-then-discard held by a docblock; the `Pii` marking nothing forces; the dashboard-sf cascade; the integrator's residual obligation |
| ADR-0048 | 5 | 0 | 5 | 0 | 1 | the fourth credential kind; the deferred "who may read Request" rule; route-kind vs controller-assumption; a resolver that throws instead of returning null; the hand-run seam audit |
| ADR-0049 | 24 | 6 | 13 | 11 | 4 | six §2.11 out-of-scope cases (claimable, delegation, batch, in-person, `CHANGE_AUTH`, `SubstituteAuthMethod`); the strength ordering nobody defines; `CERTIFIED_DELIVERY`; the four-level policy override; cumulative-failure projection; attempt-row cleaning; the missing phone column, SMS channel and limiter; the recipient-correction path; the `/v1` no-bump; watermark-stall; plaintext OTP and invitation links in `notification.variables`; four permanently review-held properties |
| ADR-0050 | 12 | 0 | 12 | 0 | 1 | the six owed acceptance bars; access/one-time codes; the signing-token conversion; promoting `lcobucci/jwt` to a direct requirement; the signable-after-void guard; the unspecified grace window; the sabotage test for reuse-after-grace; vacuous claim-set/algorithm assertions; two-secret separation as convention; the un-forced 12-hour cap |
| ADR-0051 | 8 | 1 | 4 | 4 | 1 | the durable command queue and the reminder capability that would force it; five owed bars; the one-edit-wide `Contract/Command` grant; a port doing more than a write in-transaction; watermark stall; the never-exercised relay→SMTP path; the post-commit Foundation seam; ADR-0037's now-inexact absolute |
| ADR-0052 | 9 | 0 | 8 | 1 | 1 | the whole §2 build; the "Twig never receives a recipient-bearing type" rule; "no HTTP route renders Twig"; the mandatory `{% verbatim %}` sabotage test; ICU for the substitution seam; the two-engine split's `LOAD-BEARING.md` entry; tenant-editable Twig; ADR-0038's eventual supersession; `CLAUDE.md`'s now-false TwigBundle line |
| **ADR subtotal** | **432** | **52** | **379** | **53** | **55** | |
| TASK-001 | 3 | 2 | 3 | 0 | 0 | the system/bootstrap RLS branch; per-message tenant scope on workers; `LogCommand` still unbuilt |
| TASK-002 | 3 | 3 | 3 | 0 | 0 | `LogCommand`; provisioning above RLS; RLS for future non-Envelope aggregates |
| TASK-003 | 7 | 5 | 3 | 4 | 0 | SE mirror Doctrine types; the ADR-0019 to-dos; the detached `StringValue` base; the design-repo prose cascade; `ContractSurfaceKernelGroundedRule`; `BoundedContextId` placement; the `DECISIONS.md` close-notes |
| TASK-004 | 7 | 5 | 2 | 5 | 0 | the real auth swap; where request-edge tenancy belongs; composite-create reconciliation; workspace-vs-tenant; rate limiting; provisional `/v1` naming; an OFFREPO tag owed a clean-up |
| TASK-005 | 15 | 11 | 9 | 6 | 0 | B-T + TSA; async sealing; `MockSignUseCase` retirement; the no-DSS-client rule; QES two-step; a persisted SE aggregate; `SealService`; the unlifted DTOs; EP10's real cert and the unwired keystore alias; stage-3 through the signer; per-user certificates; validation-of-arbitrary-documents; a skill run |
| TASK-006 | 10 | 8 | 8 | 2 | 1 | presigned-direct + client hash; per-object retention; the zone class→profile model; a console/HTTP seal trigger; the non-B-B guard; async sealing; the SE aggregate; the operator in the pre-signature trust path; stage-3 through the signer; accumulating WORM test objects |
| TASK-007 | 2 | 1 | 2 | 0 | 0 | active `SEALING` + a distinct async seal command; the persistent audit sink |
| TASK-008 | 7 | 6 | 6 | 1 | 0 | richer auth methods and states; the E&A evidence handoff; unvalidated token minting; the opaque-credential migration; `BatchSigningSession` and the internal entities; a real per-recipient SE aggregate; a dev volume predating `f5sign_relay` |
| TASK-009 | 10 | 0 | 9 | 1 | 0 | the projector itself; the PLATFORM biometric key vs uniform RLS; the v2 biometric custodian; audit-trail XAdES-B-LTA; the `(emittingContext, type)` catalog; poll-vs-trigger wake-up; the kernel commitments to re-evaluate; Path A vs B; guard 3; per-event-type evidential under-specification |
| TASK-010 | 1 | 1 | 1 | 0 | 0 | removing `AuditableEvent`, deferred to the projector |
| TASK-011 | 6 | 4 | 5 | 1 | 0 | Path-A cipher; Merkle/anchoring; partitioning; reader projections; tamper-evident ≠ tamper-proof; an off-repo scratchpad's markers |
| TASK-012 | 7 | 7 | 7 | 0 | 0 | Merkle; cipher-at-capture; partitioning; the projector; `correlation_id`/`causation_id`; `AuditableEvent`'s fate; multi-worker relay scaling |
| TASK-013 | 14 | 12 | 11 | 3 | 0 | the eight §3 "out (later/deferred)" items incl. CDC escalation and archival; the low-water-mark adversarial test; the `OutboxBrokerRoundTripTest` call; `AuditableEvent`; `EventRelay`'s uncovered defensive lines; DB backup/DR; a live-system drain-and-verify cutover |
| TASK-014 | 31 | 15 | 27 | 4 | 0 | fourteen ranked open decisions (incl. the parked Art. 17(3) sign-off, read-side authz, projector role, anchoring timing, decline outcomes); the whole §6 staging; Stage-6 v2; the `AuditableEvent` reduction; the in-flight tamper window; `CONSENT_RECORDED`; the preservation deadline; three §2 ground-truth gaps; the evidence-side model doc and the projector ADR; the unwritten Scenario 03b; the design-repo stub; the unhomed event-surface catalog; the Foundation privacy-at-rest axis |
| TASK-015 | 8 | 6 | 8 | 0 | 0 | the Session revocation reactor (commit 2) and the signable-after-void gap; the unverified terminal-envelope assumption; the accepted async window; the alternative read-view home; explicit token revocation; whether the reactor wants its own ADR; widening voidable states |
| TASK-016 | 4 | 4 | 4 | 0 | 0 | rendering `{{Reservas_*}}` onto the PDF; attachments as evidence; per-good association; true decline-to-participate |
| TASK-017 | 16 | 5 | 13 | 3 | 0 | `padesTargetProfile`'s dead end; per-party certs/QES; DRAFT-PATCH endpoints; decline-to-participate; the multi-drop end-to-end case; validity untestable without a real cert; TASK-002's four sibling tables; the un-rendered `renderMark`; appearance tuning; the visual template's engine; the biometric scribble (closed by TASK-053); a baselined `DocumentArtifact` finding |
| TASK-018 | 6 | 4 | 3 | 3 | 0 | appearance tuning (`signerTextPosition`, scaling, padding); `padesTargetProfile`/TSA; the biometric scribble (closed by TASK-053); template-coupled coordinates; a placement calibrator |
| TASK-019 | 17 | 6 | 17 | 0 | 0 | the whole task (six slices §4.1–§4.6); six §6 open questions incl. the Tier-A source list, `RelayEventLogCommand`'s tier, the n=1 measurement and the tag-naming rename; the three §1 diagnoses |
| TASK-020 | 7 | 6 | 5 | 2 | 1 | the three §6 open questions (doc kind, output format, `Status` survival); §7.3's boundary and enforcement calls; the unrecorded repo-layout question; eleven task bodies describing the retired ORM |
| TASK-021 | 14 | 4 | 12 | 2 | 2 | the whole slice; `envelope-divergences` D4; the override resolver; per-method TTLs; the void-ends-sessions reactor; no rehash-on-verify; the `Retry-After` contract; attempt-row cleanup; the evidence handoff; six §2.11 cases; ADR-0035's Tier-A list; bar 8's unwritable half; the dashboard unlock control; the signer PR |
| TASK-022 | 11 | 5 | 10 | 1 | 1 | the whole slice; Twig as a production dependency; three absent prerequisites (`symfony/rate-limiter`, Redis, a cache pool); plaintext OTP retention; loud fail-open; metering; sender-side visibility; anti-automation; the `OTP_EMAIL` over-claim; two review-held bars; the dashboard authoring warning |
| TASK-023 | 9 | 4 | 6 | 3 | 0 | the whole slice; the unnamed billing-persistence feature; ADR-0033's cipher's first caller; WhatsApp/voice; wider column encipherment; provider failover; data residency; sender-ID registration; spend alerting with no owner |
| TASK-024 | 10 | 7 | 9 | 1 | 2 | the parked ICU-catalogs chain; the ICU apostrophe guard's new home; retiring the archive; dropping `platform.template`; ADR-0038 → Superseded; the tenant-copy record; ICU-data drift; the rendering-identical relaxation; TASK-022's Twig authoring; TwigStan |
| TASK-025 | 11 | 4 | 9 | 2 | 2 | the two blocking decisions (§6.1 unreachable-recipient report, §6.2 `DELIVERY_FAILED` terminality); the correction-budget column; four smaller owed corrections; the receipt seam; phone correction; a new challenge after correction; the dashboard render |
| TASK-026 | 12 | 6 | 4 | 8 | 5 | checkpoint rewind; `event_dead_letter` as an incident log; the ADR-0015/0031 realization updates; permanent-vs-transient classification; the RabbitMQ policy variant; BL-32's completeness check; the never-live Notification path; the `ActorId` grammar repair; the infra DLX PR; ordering-dependent reactors; immutable queue args; the worktree lane's skipped properties |
| TASK-027 | 17 | 11 | 11 | 6 | 10 | eleven §6 follow-ups (tenant-default write path, audit-vs-notification locale, ICU chain, tenant copy, unserveable-locale signal, the ADR-0019 §5 length bound, the un-normalized tag, the inert tenant tier, `fallbackLocale()`, the `lang=` escape, dashboard/signer adoption); `addRecipient` overwrite; ten composer advisories; unencrypted PII at rest; public `doc.json`; no limiter; no CI |
| TASK-028 | 10 | 1 | 7 | 3 | 2 | five §4 decisions (kind marker, expiry mechanics, revocability, schema, cutover); ADR-0050's session credential; TASK-029's grep; the signer regex; the infra secret + stale runbook; the token in `notification.variables` |
| TASK-029 | 10 | 3 | 5 | 5 | 0 | TASK-021's whole two-gate model; the signing-token conversion; the signable-after-void guard; ADR-0035's Tier-A list; five uncovered routes; five signer-app obligations |
| tasks/README | 1 | 0 | 0 | 1 | 0 | the convention is derived from 20 records and self-corrects against them |
| **TASK subtotal** | **286** | **156** | **219** | **67** | **26** | |
| **Total** | **718** | **208** | **598** | **120** | **81** | |

### 8.3 The NO-HOME side, enumerated

These 120 are the whole of the BL-3-shaped population the corpus carries — the items for which **no ADR
and no TASK is the natural home-of-truth**, so a decision on them would be written nowhere. They fall into
six kinds, and the kind matters more than the count: three of them — (a), (b) and (c) — are not things
this repo can decide at all. ⚠ **The kinds are a grouping, not a partition, and they are deliberately given without per-kind
counts** — a dozen items sit honestly in two of them (an off-repo frontend chore that is also a contract
gap; a keystore that is also a procurement), and six numbers that could not be reproduced from the table
above would be exactly the false precision authoring rule 1 warns about. The only count here that is
derived rather than assigned is **120**, which is the `N` column of §8.2.

**(a) Off-repo application code — the signer app, the dashboard, `dashboard-sf`.** The signer's
`signingToken.ts` fail-closed regex, its two-credential storage, its twelve `SigningApi.real.ts` methods,
its single-flight renewal, its session-reuse middleware, its `AuthResponse` type (TASK-029 ×5, TASK-028);
the array-order/interleaving cutover conversation (ADR-0043 ×2, ADR-0041 ×2, ADR-0042); the biometric
scribble (TASK-017, TASK-018; closed by TASK-053, 2026-10-07); the visual template's rendering engine and its placement calibrator
(TASK-017, TASK-018 ×2); template-coupled mark coordinates (TASK-018); stage-3 through the signer
(TASK-005, TASK-006); the dashboard's locked-session unlock control (TASK-021); its failed-recipient
render (TASK-025); its authoring-time channel warning (TASK-022); ADR-0039's coordinated route cutover;
ADR-0045/ADR-0049's signing-token cascade; ADR-0047's `dashboard-sf` header adaptation; composite-create
reconciliation and workspace-vs-tenant (TASK-004 ×2); TASK-027's dashboard/signer locale adoption.

**(b) Off-repo infrastructure — `f5sign-infra`, the broker, the keystore, CI.** The dead-letter
exchange PR and the RabbitMQ policy variant (TASK-026 ×2); immutable queue args and the drain-first
operation (TASK-026, TASK-013); watermark-stall remedies and relay-lag observability (ADR-0031,
ADR-0049, ADR-0051); the never-exercised relay→SMTP path (ADR-0051, TASK-026); the trusted seal
certificate and the unwired `f5sign-dev-seal` alias (ADR-0023, TASK-005 ×2, ADR-0034); managed KMS and
the keystore's loss surface (ADR-0032 ×2, ADR-0033); the infra `[ERROR]` guard that misses `[critical]`
(ADR-0018); the erasure role's provisioning (ADR-0019); a dev volume predating `f5sign_relay`
(TASK-008); accumulating WORM test objects (TASK-006); DB backup/DR for the permanent log (TASK-013);
the absence of CI and the worktree lane's skipped properties (TASK-027, TASK-026); ADR-0039's sender
prefix, bounded by an access restriction that lives outside this repo and appears in no in-repo config.

**(c) Legal, vendor and procurement.** Art. 17(3) sign-off on mid-life erasure refusal and on the
ciphered WORM artifact (ADR-0032 ×3); crypto-shred vs backup retention (ADR-0032); SMS data residency and
the processor agreement, alphanumeric sender registration, spend alerting with no owner (TASK-023 ×3);
the production EMAIL transport's Outlook SMTP/OAuth2 credentials (ADR-0037).

**(d) Repo tooling, dependencies and dev ergonomics.** PCOV adoption and `phpstan/tests/` naming
(ADR-0035 ×2); the missing `elastic/ecs-logging-php` dependency (ADR-0009); TwigStan (TASK-024); ten
standing composer advisories (TASK-027); `ContractSurfaceKernelGroundedRule` as a phpstan-tree item
(TASK-003); `EventRelay`'s uncovered defensive lines (TASK-013); a baselined `DocumentArtifact` finding
(TASK-017); the `/eidas-compliance` skill run (TASK-005); rate limiting with no owning record (TASK-004,
ADR-0045); `GET /api/doc.json`'s public exposure (TASK-027).

**(e) Documentation and cross-document prose hygiene.** ADR-0035's value-driven-selection judgement
calls, which drift unless pinned in `tests/README.md`; the design-repo doc cascade and its
`DECISIONS.md` close-notes (ADR-0004, TASK-003 ×2); the design-repo drift ledger and `conventions.md`
§5.5 stub (ADR-0024, TASK-014); an off-repo scratchpad's `§10.x`/`D1–D7` markers (TASK-011); two
`EventRelay`/`ListEventLogDeadLetters` docblocks (ADR-0031); `CLAUDE.md`'s now-false TwigBundle line
(ADR-0052); ADR-0037's "nothing may depend on Notification" absolute, no longer literally true
(ADR-0051); a `max-3-corrections` citation with a dropped precondition (TASK-025); an OFFREPO tag owed a
clean-up (TASK-004); eleven task bodies describing the retired ORM in the present tense (TASK-020);
`tasks/README.md`'s self-correcting convention.

**(f) Cross-cutting subjects with no owner *inside* the model.** This is the kind that matters,
because it is the only one a repo decision could fix. ADR-0049's six §2.11 out-of-scope cases and the
`AuthMethod` strength ordering "owed by two consumers and defined by neither"; plaintext OTP and live
invitation links in `notification.variables` (ADR-0049 ×2, TASK-028); the post-commit Foundation seam
(ADR-0051); payload strictness as a contract decision (ADR-0042); the field-removal surface (ADR-0042)
and the two-source unification (ADR-0043); whether ADR-0046's shape suits the declared subject or other
party records; the integrator's residual opacity obligation (ADR-0047); `BoundedContextId` placement
(TASK-003); per-event-type evidential under-specification (TASK-009); the Foundation privacy-at-rest
axis and the unwritten Scenario 03b (TASK-014 ×2); the unhomed event-surface catalog (TASK-014);
validation of arbitrary signed documents, which ADR-0012 calls "explicitly unhomed" (TASK-005); per-user
cloud certificates (TASK-005); provisional `/v1` naming (TASK-004); BL-32's shared completeness check and
the `ActorId` grammar repair, both owned by a `BACKLOG.md` row alone (TASK-026 ×2); ordering-dependent
reactors, which nothing documents (TASK-026); `Envelope::addRecipient()`'s id overwrite (TASK-027); the
repo-layout question §3 blocks on, which "nobody ever wrote down" (TASK-020) — plus the residue of (a)–(e)
where the subject is genuinely shared.

⚑ **Read (f) against §4's premise.** `BL-3`, the row §4 names as the shape, is a *doc-hygiene* row — kind
(e), and one of the two kinds with the least at stake. The kind a repo decision could actually fix is (f):
real modelling gaps with no owning record. A narrowed index defined as *"deferrals with no natural ADR/TASK
home"* holds (a)–(f) indiscriminately, so an off-repo frontend chore would sit beside *"nothing anywhere
defines the strength ordering over `AuthMethod`"*. That is a different file from the one §4 describes, and
the difference is not size.

### 8.4 The four counts — the §7.1 evidence

|  | **INDEXED** | **MISSING** | total |
|---|--:|--:|--:|
| **HAS-HOME** | 60 | 538 | **598** |
| **NO-HOME** | 21 | 99 | **120** |
| total | **81** | **637** | **718** |

**How INDEXED was decided, and why it is a floor.** An item counts as indexed when its own text names the
`BL-` row that carries it — mechanical, greppable, and immune to the judgement call that "this row is
probably about that paragraph". A second, looser reading is worth stating because it bounds the answer
from above: `docs/BACKLOG.md` has **60 rows** that are `Open` or `Folded`, name a specific ADR/TASK as
home, and do **not** say `fold pending` — i.e. rows whose substance is written in a record. (Coincidence
worth flagging so it is not read as one number: that 60 is a *row* count from `BACKLOG.md`, unrelated to
the 60 *census items* in the HAS-HOME × INDEXED cell.) If every one
of those indexed a census item that does not cite back, INDEXED would be at most **141** and MISSING at
least **577**. **Either bound says the same thing: between 80% and 89% of the corpus's deferral surface
has no index row.** The gap §1 diagnoses is not narrower than it looked; it is an order of magnitude
wider.

**And the counts that answer §4 do not depend on that bound at all.** The home split is **598 / 120 —
83% has a home, 17% does not**, and it holds at both ends of the corpus: 379/53 across the ADRs (88%
homed), 219/67 across the tasks (77% homed).

### 8.5 What the evidence suggests for §4 — and the call is *not* made here

⛔ **§4's question is not answered in this section. §7.1's last bar is that Phase 1 produces the
classification and stops.** What follows is the argument each way, stated so the call can be taken from
evidence rather than from the abstract.

**For the narrowing (index only what has no home).** Three findings point at it. *(i)* The ratio is
lopsided enough that the narrowing is not a trim but a change of subject: a generated index of everything
would carry ~718 entries and shrink to ~120 under the narrowing, so the current file — 96 open rows — is
already far closer to the narrowed shape than to the full one. *(ii)* The index is **already** the
no-home file in practice, by a route nobody chose: **47 of the 96 open rows say `fold pending`** — home
not yet written — and **34 of those 47 have no mention anywhere in the ADR/TASK corpus**
(`comm -23` of the fold-pending ids against `rg -o 'BL-[0-9]+' docs/adr/ADR-*.md docs/tasks/*.md`). Those
34 are review findings that were never written into any record; the index is their only home. *(iii)* A
~718-row generated table cannot be read, and an unreadable answer to *"show me everything we've deferred"*
is not an answer.

**Against it.** *(i)* The header's stated purpose is the cross-cutting view; the narrowed file answers a
different question — *"show me everything deferred that nobody owns"* — and the 598 homed items become
visible only by opening 82 files. Nothing else in the repo would answer the original question, which is
what BL-7 exists to restore. *(ii)* §8.3 shows the no-home population is **not** one kind. Three of its six
kinds — off-repo application code, off-repo infrastructure, and legal/vendor gates — are work this repo
cannot decide at all, so a large part of the narrowed index would be items whose next action belongs to
another team, sitting beside genuine modelling gaps with nothing distinguishing them. `BL-3`, the row §4
offers as the shape, belongs to the prose-hygiene kind, which is not the kind the narrowing would mostly
collect. *(iii)* The `fold pending` finding cuts both ways: it says the index's
real job today is holding what has no home *yet* — which is a **staging** semantic, not a **scope**
semantic. Narrowing by "has a home" would evict a row the moment someone folds it, which is exactly when
the row stops being a duplicate and starts being a pointer.

**The shape the evidence actually argues for, offered as an option rather than a decision.** The two
sides disagree about *scope* but agree about *volume*, and the volume problem is the coarseness of the
unit, not the breadth of the set: 718 census items against 96 rows means a `BL-` row is already ~7 census
items wide. A generated index at *record* granularity — one row per ADR/TASK carrying its deferral count
and section link, with the no-home items listed individually because they have nowhere else to be — keeps
the cross-cutting view, is ~82 + ~120 rows, and needs no scope decision at all. **That is a third option
§4 does not currently consider, and naming it is as far as Phase 1 goes.**

### 8.6 What the census changes for Phase 2, and what it corrects in this record

1. ⛔ **Phase 2 step 2 is not a retro-fit of headings; it is authoring sections that do not exist.** §3
   step 2 says *"retro-fit the heading across the existing corpus, using the Phase-1 census as the
   worklist"*, which reads as renaming ~20 heading shapes. On the ADR side — **the only side Phase 2 may
   build**, per §3's precondition — there are **two** deferral sections in 52 files (§8.1 correction 1),
   and **52 of 432 ADR deferrals** sit under any deferral-named heading or label at all. The other **379
   must be found in prose and moved**, across `Status` rows, `## Consequences` bold labels, `## Enforced
   by (in-repo)`, `## Realized in (in-repo)` and `## Counterpoint`. That is the dominant cost of Phase 2
   and the plan does not carry it.
2. ⛔ **The TASK side is the healthy one, and it is the side that is blocked.** 156 of 286 task deferrals
   (55%) already sit under a deferral-named section, against 12% on the ADR side. §3's precondition
   parks the half that is nearly done and keeps the half that is nearly all work. That does not change
   the precondition — an absence of record is still not a decision — but it should be priced.
3. ⚠ **§2 row 3's `11 of 29` is one pattern's answer, and §7.2 repeats it as the retro-fit's size.** The
   §2 grep matches only `Open follow|Follow-ups`. A number-tolerant pattern that also admits `Deferred`,
   `Open items`, `Open questions` and `Open decisions` returns **18 of 29** task files (19 of 30 with
   `README.md`) — command 7 in §8.1. Both figures are true of their own predicate; the record states one
   of them as the corpus's conformance, which reads as *"18 files to convert"* when it is 11.
4. ⚠ **§7.2 contradicts itself about where the mandatory section lands.** Its table row says *"The ADR
   template change does not renumber | See below — it lands as §10"*, and the ⚠ note below it says the
   choice between a new §10 and a decimal nested under an existing slot is open and must be decided
   deliberately. One of the two has to go; the note is the one with the reasoning.
5. ⛔ **A live mis-citation, found by the census and deliberately left unfixed.**
   [TASK-026](TASK-026-event-path-silent-drops.md) §6.1 ends *"Indexed as BL-113"*. `BL-113` is the
   plaintext credential in `notification.notification.variables`; the row that indexes the checkpoint-rewind
   command is **`BL-110`**. It is not repaired here because §7.1 forbids this pass from touching index
   rows and repairing the pointer means deciding which row it should have named — but it is exactly the
   failure this task predicts, in the wild, in a record written the day before: a hand-written pointer
   into a hand-maintained index, wrong on arrival, and invisible to every gate.
6. ⚑ **§1's core claim is true in one direction and false in the other, and the false direction is the
   one the plan rests on.** *"The distributed half of the convention works — the deferrals genuinely are
   in their ADR/TASK homes"* holds **corpus → index**: 598 of 718 census items have a natural home and
   almost all are written in it. It fails **index → corpus**: 47 of 96 open rows declare their home
   unwritten, and 34 of those have no trace in any record. So the convention works for what a record's
   *author* defers, and not at all for what a *review* finds. Phase 2 generates from the homes, so it
   would reproduce the first set faithfully and drop the second — 34 rows whose only home is the file the
   generator overwrites. **§3 Phase 2 step 3 says the generated view "replaces the hand-maintained *Open*
   table". Under this finding that step deletes data**, and needs either a preserved hand-written region
   or a rule that a row must be folded before the generator runs.
7. ⚑ **Verified, not corrected:** §2's `29 ADRs minted`, `127 rows / 96 Open / 19 Folded / 12 Closed`,
   and §6 Q1's eleven-file `rg` enumeration (`TASK-001, -002, -003, -008, -009, -012, -015, -017, -018,
   -020, README.md`) all reproduce exactly at `7f0fa78`.

---

## 9. The document lints — new scope, 2026-08-18

✅ **Decided by the user 2026-08-18.** Appended as §9; §§1–8 are unrenumbered, being `§N` anchors cited
from [`BACKLOG.md`](../BACKLOG.md) BL-7, [TASK-019](TASK-019-requirement-traceability-and-per-tier-gates.md)
§4.6 and [BL-137](../BACKLOG.md).

**Why here rather than in a new task.** [`CLAUDE.md`](../../CLAUDE.md) already assigns two lintable rules to
this record — *"`docs/BACKLOG.md` id-uniqueness and ADR template conformance are both lintable, and both are
recorded as owed (TASK-020)"*. So this task is **already the home for mechanical checks over documents**, and
BL-137 is a third of the same family. Minting a task for it would be the third place for one problem, which
is the defect this record is about.

⚑ **And it does not un-park what §4 stopped.** The user's decision there was that generating the *Open*
table must not happen, because §8.6.6 measured that it would delete 34 rows whose only home is the index.
A lint **generates nothing and replaces nothing** — so this scope is buildable today while §3 Phase 2 step 3
stays stopped. **That is the point of putting it here: the task has construable work again.**

### 9.1 The three checks, and what each is falsifiable against

| Check | The property | Falsifiable against |
|---|---|---|
| **`Status` freshness** ⭐ new | If a task's `Status` names a branch or commit, and that commit is an **ancestor of `origin/develop`**, the `Status` may not read `not started` / `not merged` / `pending review` | `git merge-base --is-ancestor` |
| **`BL-` id uniqueness** | No id appears twice in `docs/BACKLOG.md` | the file itself |
| **ADR template conformance** | An ADR carries the header fields and `## ` sections [`AUTHORING.md`](../adr/AUTHORING.md) §Section template requires | the template |

**Why `Status` is the one that earned the check.** It fired **three times on 2026-08-18 alone**, always in the
same direction: TASK-020 read *not started* with its census landed, TASK-025 read *blocked on two decisions*
with both answered, TASK-027 read *pending review, not merged* while another session had spent hours building
on its code. ⚑ **The reason nobody catches it is that an under-claim breaks nothing** — an over-claim gets
contradicted by the tree, an under-claim just sits there. Authoring rule 7 names this the *realization
mirror* and observes the error is always in the under-claiming direction; this is why.

⚠ **A fourth instance is already recorded and points the other way**: TASK-022's prerequisite row claimed a
Redis client was missing when the extension had been in the image all along ([`TASK-022`](TASK-022-delivered-codes-over-email.md)).
That one **over**-claims what is missing rather than under-claiming what is done, and its cost is a task that
reads as more expensive than it is and gets parked for it. Whether one check can cover both directions is an
open design question — a prerequisite is not falsifiable against git the way a `Status` is.

⚑ **A fifth instance, 2026-08-19 — the first one measured *after* this check was scoped, and it is the cheapest shape for the check to catch.** [TASK-026](TASK-026-event-path-silent-drops.md)'s `Status` read *"Slice 3 is NOT started and is deliberately out"* while that slice had landed the previous day as `7e9f610` — an ancestor of `origin/develop`, so §9.1's `git merge-base --is-ancestor` arm decides it without reading a word of prose. Two things it adds to the case above. **(1) The contradiction was already inside the same table**: the `Decision record` field of that same header table said *"✅ Slice 3 landed 2026-08-18"*, so the record disagreed with itself and shipped that way — a `Status` does not always need an external source to be falsified against, and a check reading only the header table would have fired on this one. **(2) What it cost, stated as what actually happened rather than as what it might have cost:** a session enumerating remaining work read this `Status` while deciding what was available to pick up, and what stopped it routing there was noticing the neighbouring field disagree — not the record being right. Under-claiming does not break the build, so nothing but a reader's attention stands between it and a misrouted session.

### 9.2 Two things to get right, both learned the hard way tonight

⛔ **Report-only first.** [TASK-019](TASK-019-requirement-traceability-and-per-tier-gates.md) §4 states the
rule and it applies unchanged: *a gate introduced red is a gate people learn to ignore.* All three checks
fail on today's corpus. Land them printing, fix the corpus, then gate.

⛔ **The `Status` check must state which side it is asserting.** *"This commit is not an ancestor"* is a fact
about `origin/develop` at the moment it runs — and `origin/develop` was frozen for hours tonight while the
push was broken, so every landed-but-unpushed task would have failed a naive version. **Compare against local
`develop`, or say plainly which ref was used**; a check that silently means "not pushed yet" while reading
"not merged" is the same defect it exists to catch.
