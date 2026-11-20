# TASK-043 — A refused commit names its condition

<!-- OFFREPO: the consuming half lives in the sibling repository `f5sign-signer`
(`app/composables/useSignFlow.ts`, `mapError`), read at `develop` `c894f88` on 2026-09-16. The one
behaviour this record depends on is restated in §1 and again in §3 #9; nothing here needs that repo
open, and nothing here can re-measure it. -->
<!-- OFFREPO: §5 D1 relies on facts about the sibling repository `f5sign-infra`: the Makefile targets
that run this repo's gates (`lint`, `phpstan`, `composer cmd=arch`, `test`, `qa`) and the per-worktree
lane (`wt-backend src=$(pwd)`), plus its committed `docker-compose.override.yml` binding
`../f5sign-backend` into the stack. Every command is spelled out where it is used, and D1 says which
checks re-derive the binding, so nothing here depends on opening that repo. -->
<!-- OFFREPO: the Status row's regenerated development DSS seal (valid to 2046-09-11) and the change to
how it is generated live in the sibling repository `f5sign-infra` (`docker/eu-dss/scripts/`), uncommitted
there when this record cited them on 2026-09-16. What this record depends on — that
`StorageLifecycleScenarioTest` passes against the running DSS — is observable from here by running the
suite. -->
<!-- OFFREPO: §7's release-order amendment of 2026-09-16 restates facts about the sibling repository
`f5sign-signer`, read in its clone that day: `app/composables/useSignFlow.ts` at `c894f88`
(`mapError` routes a 409 to the done page only for `ALREADY_SIGNED` or `CONFLICT`, its fallback branch calls
`reportError`, and `retry()` re-runs the whole flow), and `.output/public/_nuxt/builds/latest.json` in a local
build (keys `id` and `timestamp` only); the diff of `01ffece`, which drops `code === 'CONFLICT'` from that
condition; and `origin/develop` = `develop` = `7ce2958`, with `git log c894f88..origin/develop` listing six
commits. The joint deploy is the two maintainers' decision as relayed that day, not read in a tree. The two
informational findings about this repository's published spec in §7 come from their session's regeneration of
their contract snapshot (`7ce2958`, message read in that clone). -->

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `fix/conflict-taxonomy`** (`117f7d3` the last commit that changes code or published prose in `src/` — `git log --oneline 117f7d3..acb20d0^2 -- src` names the one docblock correction above it, and ⛑ this read *"the last commit that touches `src/`"* until 2026-09-16; enumerate this task's commits with `git log --oneline --no-merges acb20d0^1..acb20d0^2`), 2026-09-16 — **merged into `develop` at `acb20d0`, on top of [TASK-042](TASK-042-no-recipient-acts-before-their-step.md)'s merge `f490218`, and pushed to `origin/develop` the same day, with no PR. Not deployed**, and the release is **one deploy with the `f5sign-signer` change** (§7, [ADR-0067](../adr/ADR-0067-a-refused-commit-names-its-condition.md) §2.6 as amended that day). ⛑ **Corrected 2026-09-16, at the merge**: this read *"— **neither merged nor pushed**, and the branch carries TASK-042's 31 commits beneath this task's six"*, with both commands ending in `..HEAD` — which on `develop` also lists TASK-042's commits — and *"six"* matches the six commits named below, not the branch, which that range lists as nineteen. ⚑ **This row read *"Not started — forward plan, written 2026-09-16. Nothing below exists"*** and named three checks that would falsify it; all three are falsified now: `SigningSessionStateException` implements `ProblemCoded`, `SESSION_ALREADY_COMPLETED` / `SESSION_CLOSED` / `SIGNING_CHALLENGE_MISBOUND` are members of `components.schemas.ProblemCode` (33 → **36**, with `ALREADY_SIGNED` absent from the generated document), and `rg 'ALREADY_SIGNED' src/` returns nothing. The commits: `8e99f33` the exception + the catalog + the six `#[OA\*]` blocks, `7612d9c` the per-guard cases, `f6f6b7c` the acceptance case, `6e8d443` the frontend handoff, `360cbfc` the spent-code correction, and `117f7d3` the *how* behind the fresh-code remedy, answered to the consuming session **after** the run below. **Gates at `360cbfc`**, main checkout, through the infra Makefile per §5 D1 — `lint` *Found 0 of 1307 files* · `composer cmd=arch` *Violations 0 · Uncovered 0 · Allowed 7056* · `phpstan` *[OK] No errors* · `test` **`Tests: 3006, Assertions: 16244, Errors: 1, Failures: 1`**. ⛔ **That is not a green bar and is not written as one.** The two reds are the declared environmental pair and nothing else: `StorageLifecycleScenarioTest` (its frozen clock runs a year ahead of the wall clock, so its signing step falls past the development DSS signing certificate's `notAfter` and the live DSS answers 500) and `DocumentationLinkTest` (the `CLAUDE.md` symlink does not resolve inside the container). ⛑ **Corrected 2026-09-16**: the first parenthesis read *"the development DSS signing certificate has expired"*, and it had not — it was valid 2026-09-01 → 2027-09-01, and with a 365-day validity this test's signing step could never fall inside it, not even on the day the certificate was generated. [TASK-042](TASK-042-no-recipient-acts-before-their-step.md) §5 D1 had the mechanism right. The baseline taken before the first edit was `Tests: 2994, Assertions: 16151` with the same two, so the delta is **+12 tests / +93 assertions**, all added here. ⚑ **That red is gone since**: the development seal was regenerated with a longer validity, and a full suite run the same day printed `Tests: 3006, Assertions: 16685, Failures: 1`, the one red being `DocumentationLinkTest` ([`BL-251`](../BACKLOG.md)). ⛔ **§6.1's Infection bar was measured, but not through its sanctioned path, and is reported as that rather than as green.** `composer qa` aborts at `@test` and a plain `composer infection` refuses to start over a red suite — [`BL-251`](../BACKLOG.md), which predates this branch and blocks every branch alike. Run on 2026-09-16 over the `src/` of `60a968d`, identical at `d90004b` and therefore covering `117f7d3`, with **exactly one test excluded**: `DocumentationLinkTest::every_documentation_link_in_a_docblock_resolves`, which is `#[CoversNothing]` and so cannot move a mutant between the covered and not-covered populations — `--list-tests` went 3006 → 3005, and the initial run's junit reported 3005 tests with 0 failures. `composer infection -- --test-framework-options=--exclude-filter=DocumentationLinkTest::every_documentation_link_in_a_docblock_resolves` printed `12099 mutations … 6052 killed … 4773 not covered … 1265 covered mutants were not detected … 3 errors … 6 time outs`: **Covered Code MSI 82.73%** against `minCoveredMsi: 79` (+3.73pp), **MSI 50.095%** against `minMsi: 50` (about 11 mutants of headroom, [`BL-252`](../BACKLOG.md)), Mutation Code Coverage 60.55%, exit 0, 11m43s. ⛑ **Corrected 2026-09-16**: this sentence read *"§6.1's Infection bar was NOT measured, and is reported absent rather than green … so this tree has no covered-MSI number"*, which was true when written. ⚠ **The cited gates are behind the tip in `src/`, and that is stated rather than glossed**: `117f7d3` touches `src/` — two `#[OA\*]` description strings on the commit routes, prose only, no behaviour and no new carried literal — and it landed after the gates above were taken, so **they do not cover it**; one later commit corrects a docblock in `SigningSessionStateException` and nothing else, gated by lint, PHPStan and that exception's two test classes. ⚑ Infection's initial run does cover `117f7d3`, over a tree whose `src/` and `tests/` match the tip except for that docblock; that is Infection's own PHPUnit invocation with one test excluded, not the gates. ⛑ **Corrected 2026-09-16**: this read *"one `src/` commit behind the tip"* and *"match the tip"*, both true until the docblock commit. Merged into `develop` on 2026-09-16 (above); ⛑ this sentence read *"Pending review."* until that merge, and a `Status` naming a commit that is an ancestor of `origin/develop` may not say so ([`BL-137`](../BACKLOG.md), [TASK-020](TASK-020-derive-the-deferral-index.md)). [ADR-0067](../adr/ADR-0067-a-refused-commit-names-its-condition.md) is **`Accepted (exercised)`** since 2026-09-16, given by the maintainer (§8). ⚠ **Exercised is not deployed**, and merged is not deployed either: `develop` is not a deployment ([`docs/frontend-handoff/README.md`](../frontend-handoff/README.md) rule 4). ⛑ **Corrected 2026-09-16, at the merge**: this read *"the branch is still neither merged nor pushed"*. ⛑ **Corrected 2026-09-16, at the promotion**: this row ended *"ADR-0067 stays `Proposed`: its realization is in the tree and acceptance is the maintainer's call"*, and opened *"(tip `117f7d3`)"*, which was not the tip even when it was written — three documentation commits sat above it. |
| **Type** | **Corrective.** It adds no capability and no route. Four conditions that answer one term start answering four, one published term that nothing emits is retired, and six `#[OA\*]` blocks stop describing a collapse that no longer exists. |
| **Why** | ⚑ **Past tense since 2026-09-16 — this row and §1 are the record of the defect this task removed, not of how things are.** ⛔ **The signer's done page claimed a signature that never happened.** `POST /api/v1/signing/commit` answered a bare 409 `CONFLICT` for *already completed*, *envelope voided* and *signing challenge misbound* alike, so the signer application — which routed `CONFLICT` and `ALREADY_SIGNED` to `/s/{token}/done` — painted its success variant for two conditions in which nothing was signed. Reported from the consuming repository, which demonstrated it could not be closed there: the three were indistinguishable on the wire, and branching on `status` is what this API's own published prose forbids. [`BL-259`](../BACKLOG.md), closed by this task. |
| **Builds on** | **[ADR-0025](../adr/ADR-0025-rfc9457-error-shape.md) + [ADR-0029](../adr/ADR-0029-domain-exception-http-mapping.md)**: the `code` extension point and the `ConflictException` → 409 mapping, both reused unchanged. **[`ProblemCoded`](../../src/F5Sign/Kernel/Exception/ProblemCoded.php) and [`ApiExceptionListener`](../../src/F5Sign/Foundation/Http/ApiExceptionListener.php)**: the capability and the edge that prefers it over the status default — no boundary code is touched. **[ADR-0056](../adr/ADR-0056-terminal-state-on-pre-credential-routes.md) §2.5**: the criterion that decides which conditions get a code. **[TASK-042](TASK-042-no-recipient-acts-before-their-step.md)**: its contract check found [`BL-249`](../BACKLOG.md) and its signer session reported [`BL-259`](../BACKLOG.md); its §7 and its frontend handoff are the worked example of the release ordering §3 #9 repeats. |
| **Scope** | The boundaries that surprise: **the `f5sign-signer` change is not here** — this task writes the handoff and nothing in this repository can gate the other side. **No status moves**: `notAuthenticated()` stays a 409 and stays uncoded (ADR-0067 §2.4). **The two other over-claims on the delegated route** (`ENVELOPE_NOT_SENT`, `RECIPIENT_SLOT_NOT_CLAIMED`) stay open and belong to [TASK-033](TASK-033-delegated-signature.md)'s surface; only the `ALREADY_SIGNED` clause is ours. **No ruleset change** — ADR-0067 §2.7 states why none is needed, and a diff touching `deptrac.yaml`, `phpstan.dist.neon` or the baseline is out of scope. §4 carries the rest. |
| **Decision record** | **[ADR-0067](../adr/ADR-0067-a-refused-commit-names-its-condition.md)**, **`Accepted (exercised)`** since 2026-09-16 — drafted alongside this record and carried as `Proposed` until the maintainer promoted it. It governs the capability (§2.1), the partition of all five conditions (§2.2), why the otherwise-terminal arm gets a name of its own (§2.3), what stays uncoded (§2.4), where each code is published (§2.5), the additivity and release order (§2.6), the absence of any ruleset change (§2.7) and what stays open (§2.8). Promotion to `Accepted` was the maintainer's call, and belongs in the changeset that makes it so (`CLAUDE.md` authoring rule 7); it was given on 2026-09-16. ⚠ **This row said the call would come *"once §6 here is green"*, and §6 was not green when it was given**: the suite carried the two declared environmental reds, and §6.1's Infection bar had not been measured ([`BL-251`](../BACKLOG.md)). The evidence on the record when it was given is what §6.2 names, the cases and the fourteen sabotages, and nothing here claims more. ⛑ **Corrected 2026-09-16**: those two clauses read *"the suite carries"* and *"was never measured"*. Later that day `StorageLifecycleScenarioTest` stopped being red and the bar was measured, with one declared exclusion, at covered-MSI 82.73% (Status row); neither was on the record when the promotion was given. |
| **Delivery bar** | One acceptance case drives all four coded conditions over HTTP against `POST /api/v1/signing/commit` and asserts **four distinct `code` values** — `SESSION_ALREADY_COMPLETED`, `SESSION_CLOSED`, `ENVELOPE_NO_LONGER_LIVE`, `SIGNING_CHALLENGE_MISBOUND` — with a fifth request, a clean commit, still answering **200**. The sabotage is removing `implements ProblemCoded` from the exception: all four then answer `409` with `code: "CONFLICT"`, the case goes red **naming the collapsed code**, and `OpenApiSpecTest` goes red naming the three now-unemitted published members. ⛔ **The `SESSION_CLOSED` arm's fixture must drive the revocation, not merely void the envelope** — a fixture that stops at the void answers `ENVELOPE_NO_LONGER_LIVE`, so built that way the case cannot separate the two codes [ADR-0067](../adr/ADR-0067-a-refused-commit-names-its-condition.md) §2.3 exists to separate, and would report green about a distinction it never tested. ⚑ The 200 control is not decoration: without it the case passes on a system that refuses everybody. |
| **Sibling** | ⚑ The frontend handoff (§3 #9). It is not a follow-up: ADR-0067 §2.6 fixes the release order, so the handoff is owed **before** the merge rather than with it. ⛑ This read *"fixes the release order one way"* until 2026-09-16, when §2.6 was amended to one deploy of both sides (§7). |

---

## 1. Why this task exists

⚑ **Read this section in the present of 2026-09-16, BEFORE the realization** (`8e99f33`…`360cbfc`): it is the
state the decision answers, and every clause below is now past. The collapse is gone — each of the four
conditions names itself and `ALREADY_SIGNED` is published nowhere. What this section still records, and
what nothing else does, is *why* each of them was worth a term.

**The collapse, read from the tree.**
[`SigningSessionStateException`](../../src/F5Sign/Session/Domain/Exception/SigningSessionStateException.php)
extends `ConflictException` and implements no `ProblemCoded`, so
[`ApiExceptionListener`](../../src/F5Sign/Foundation/Http/ApiExceptionListener.php) derives `code`
from the status and every one of its refusals reaches the wire as `CONFLICT`.
[`CommitSignatureController`](../../src/F5Sign/Session/UI/Http/CommitSignatureController.php)'s 409
publishes that as a positive claim and argues for it: naming `ALREADY_SIGNED` for the other conditions
*"would replace an omission with a false claim"*. The argument is correct; what it justifies is coding
all of them, not leaving the omission.

**The consequence is the signer's done page.** Restated from the signer session's report and from
[`BL-259`](../BACKLOG.md): a 409 whose `code` is `CONFLICT` or `ALREADY_SIGNED` navigates to
`/s/{token}/done`, which paints its success variant unless the read model says `COMPLETED`. For a
voided envelope and for a misbound signing challenge nothing was signed. The signer cannot repair it:
the three are byte-identical, and the only other discriminator is `status`, which this API's own
published prose forbids branching on.

**The neighbouring route publishes a code that does not exist.**
[`CommitDelegatedSignatureController`](../../src/F5Sign/Session/UI/Http/CommitDelegatedSignatureController.php)'s
409 opens with *"`code` distinguishes the conditions — branch on it"* and lists `ALREADY_SIGNED`,
which no factory produces and which is not among the 33 members of `ProblemCode`. That is
[`BL-249`](../BACKLOG.md), found by TASK-042's contract check on a block TASK-042 deliberately left
alone — and its own cheapest detector was the sibling two files away, already saying in text why the
name was never added there.

**Five conditions, not three.** The published block names three. `commitSignature()` reaches five
refusals of this type: `sessionIsTerminal()` splits into an already-completed branch and an
otherwise-closed branch, plus `notAuthenticated()`, `envelopeNoLongerLive()` and
`signingChallengeMisbound()` raised two frames down in `consumeSigningChallengeFor()`. ADR-0067 §2.2
partitions all five; this task builds that partition, not the block's three.

## 2. What already exists (reuse, do not rebuild)

**The capability and the edge. Nothing in either is touched.**
[`ProblemCoded`](../../src/F5Sign/Kernel/Exception/ProblemCoded.php) is a kernel sub-category; an
exception implementing it supplies its own `code` and `ApiExceptionListener::problemCode()` prefers it
over the `STATUS_CODES` default. The edge enumerates no BC's terms and must not start — that bargain
is ADR-0025's and the listener's docblock defends it.

**The shape to copy, and it is two files away.**
[`AuthGateRefusedException`](../../src/F5Sign/Session/Domain/Exception/AuthGateRefusedException.php)
is a Domain exception implementing `ProblemCoded` with a private constructor taking the code beside
the message and five named factories each supplying its own literal. ⛔ **Read every sibling before
copying one** (`CLAUDE.md` authoring rule 3): `AssertedDocumentMismatchException` uses a single
`private const string CODE` because its three factories share one code deliberately, and that
difference is a decision rather than a bug.

**The catalog and its gate.** The codes live in `components.schemas.ProblemCode` in
[`nelmio_api_doc.yaml`](../../config/packages/nelmio_api_doc.yaml), hand-maintained and tied to the
source by
[`OpenApiSpecTest::every_problem_coded_refusal_names_its_code_in_the_spec()`](../../tests/F5Sign/Acceptance/OpenApiSpecTest.php),
which fails **both** ways. ⚠ **Its discovery reads every single-quoted UPPER_SNAKE literal in an
implementor's source**, deliberately over-approximating; the moment the exception implements
`ProblemCoded`, every such literal in that file is demanded in the spec. There are none today —
its messages are prose — but a literal added later is a build failure whose fix is the literal, not a
looser predicate. ⛔ **Do not centralize the codes into a PHP enum** to make the list greppable; that
is the repair the test's own docblock is built to avoid.

**The published surfaces.** Six `#[OA\*]` 409 blocks describe this exception's conditions today: the
two commit routes, plus [`SubmitAuthResponseController`](../../src/F5Sign/Session/UI/Http/SubmitAuthResponseController.php)
(*"Otherwise, with no `code`: the envelope is no longer live, or the session is already completed"*),
[`SendAuthOtpController`](../../src/F5Sign/Session/UI/Http/SendAuthOtpController.php) (*"Also the usual
conflict cases: …"*) and the two machine twins
([`SubmitRecipientAuthResponseController`](../../src/F5Sign/Session/UI/Http/SubmitRecipientAuthResponseController.php),
[`SendRecipientAuthOtpController`](../../src/F5Sign/Session/UI/Http/SendRecipientAuthOtpController.php)),
which forward readers to the first two. Enumerate them from the tree when you do the work rather than
from this paragraph.

**The test tiers, already populated.** `problemCode()` is asserted today at the Unit tier in
`SigningSessionAuthGateTest` and at the Application tier in `CommitSignatureUseCaseTest` and
`CommitDelegatedSignatureUseCaseTest` — the new cases go beside them, not in a new home.
[`OtpSendRefusalParityTest`](../../tests/F5Sign/Session/Unit/Application/Exception/OtpSendRefusalParityTest.php)
is the in-repo model for a test that pins codes on exception classes directly, including the trap
worth copying verbatim: ⛔ **no `#[UsesClass]` for `ProblemCoded`** — PHPUnit 11 rejects an interface
as a coverage target, the warning makes Infection treat the run as failed, and naming it takes the
mutation gate down.
[`DormantStepRefusedHttpTest`](../../tests/F5Sign/Session/Acceptance/DormantStepRefusedHttpTest.php)
is the model for the acceptance case: same BC, same routes, and it already seeds a sent envelope,
mints a session credential and asserts a `code` on the commit.

**The handoff directory and its conventions.** [`docs/frontend-handoff/`](../frontend-handoff/README.md)
is where a contract change is handed to the front ends, one file per change, in the shape its README
fixes; [`TASK-042-no-recipient-acts-before-their-step.md`](../frontend-handoff/TASK-042-no-recipient-acts-before-their-step.md)
is the most recent worked example and the one whose consumer is the same file in the same repository.

## 3. What gets built

1. **`SigningSessionStateException implements ProblemCoded`**, with a private constructor taking the
   code beside the message, per ADR-0067 §2.1 and in `AuthGateRefusedException`'s shape.
2. **`alreadyCompleted()` carries `SESSION_ALREADY_COMPLETED`** (new member).
3. **The two paths to a dead envelope carry two different codes**, per ADR-0067 §2.3 — they are not
   one fact. `sessionIsTerminal()`'s non-`COMPLETED` branch carries **`SESSION_CLOSED`** (new): the
   signing session itself was closed when the envelope was voided. `envelopeNoLongerLive()` carries
   **`ENVELOPE_NO_LONGER_LIVE`** (existing): the envelope was not alive at the moment of the commit.
   ⚑ **Which one a voided envelope hits depends on whether the `EnvelopeVoided` reaction has drained**
   — before it does, `commitSignature()` reaches the `envelopeIsAlive` argument; after it does, the
   same act meets `isTerminal()` first. That hop is invisible from outside and is exactly what the two
   names make diagnosable.
4. **`signingChallengeMisbound()` carries `SIGNING_CHALLENGE_MISBOUND`** (new member).
5. **`notAuthenticated()` carries the status default**, which after #2–#4 is the only condition on this
   class reaching a bare `CONFLICT` (ADR-0067 §2.4). Written so the choice is visible at the factory
   rather than inferred from an absence.
6. **Three members added to `components.schemas.ProblemCode`** — `SESSION_ALREADY_COMPLETED`,
   `SESSION_CLOSED`, `SIGNING_CHALLENGE_MISBOUND` — in the same commit as #2 to #4, the rule
   `ProblemCoded`'s docblock states and `OpenApiSpecTest` enforces. Insert in the file's existing
   order rather than appending.
7. **The two commit routes' 409 blocks rewritten.** `CommitSignatureController`'s block stops being an
   argument for omission and becomes the partition with a remedy per code; `CommitDelegatedSignatureController`'s
   `ALREADY_SIGNED` clause becomes `SESSION_ALREADY_COMPLETED` and the block gains the other three —
   which closes [`BL-249`](../BACKLOG.md) by making the route's opening promise true rather than by
   deleting the clause. ⛔ **Re-read each whole block, not the lines changed**: both are closed
   enumerations emitted verbatim into the spec the frontend ratifies, which is the surface
   [`BL-209`](../BACKLOG.md) exists for and that no symbol sweep reaches.
8. **The four gate routes' 409 blocks corrected** (§2 lists them). Two assert an absence that stops
   holding; two forward to those. ⚠ Whether those arms are reachable there or are shadowed by the
   coded Application refusals is **not** what the edit turns on — a sentence asserting an absent `code`
   is wrong either way (ADR-0067 §2.5).
9. **The frontend handoff**, in `docs/frontend-handoff/`, following its README's shape. It carries the
   three new code names, the four remedies, the route list, and the ordering: `f5sign-signer` ships its
   branches **first**, because until it does the already-completed arm falls from its done page to its
   generic failure screen. ⚑ Their routing is written and uncommitted, and they are waiting on the
   names — so this is the deliverable that unblocks the other repository, not a courtesy. Worth saying
   in it: `ENVELOPE_NO_LONGER_LIVE` is the fourth code on the route and is already published on three
   others, so they may already have a branch for it.
10. **Docblock corrections in the same changeset**, found by the §6.4 sweep: `commitSignature()`'s
    docblock cites *"the signer contract's 409 ALREADY_SIGNED"*; `sessionIsTerminal()`'s docblock
    argues a non-disclosure line narrower than the wire now is (ADR-0067 §2.3); the class docblock
    describes the type as uncoded.

## 4. Scope

- **Not the signer change.** Another repository, another PR. This task owes the handoff and the code
  names, and nothing here can gate what happens over there.
- **Not a status change.** `notAuthenticated()` stays 409 and stays uncoded. Moving it is a decision
  about `ConflictException`'s boundary (ADR-0067 §2.8).
- **Three new members, not two.** The otherwise-terminal arm gets `SESSION_CLOSED` of its own rather
  than folding into `ENVELOPE_NO_LONGER_LIVE`; the reuse was considered and is preserved as the
  rejected alternative in ADR-0067 §7.3.
- **Not `BL-209`.** The per-route completeness gate is still not built, and the six blocks of §3 #7–#8
  stay held by review.
- **Not TASK-033's two over-claims.** `ENVELOPE_NOT_SENT` and `RECIPIENT_SLOT_NOT_CLAIMED` on the
  delegated route stay as they are.
- **No ruleset, layer or baseline change.** ADR-0067 §2.7 states why none is needed: `deptrac.yaml`
  already grants `SessionDomain` the `Kernel` layer and eight Domain exceptions already implement this
  interface. A diff touching those files is out of scope and needs the maintainer, not this record.
- **No migration, no schema change, no new route, no new response member.**

## 5. Key decisions

**D1 — Harness.** ⛔ Check `git rev-parse --git-dir` first. From the **main checkout**, the infra
Makefile targets validate this tree: `make -C ../f5sign-infra lint | phpstan | composer cmd=arch |
test`, then `qa` for Infection. From a **worktree** they validate somebody else's branch and report
green for it — use `make -C ../f5sign-infra wt-backend src=$(pwd)`. Both stacks are exclusive, so say
which one you are taking before running.

**D2 — The partition is derived from the factories, never from the published block.** The block names
three conditions and there are five. A change scoped to what the prose listed would leave the
otherwise-terminal arm uncoded — which is the arm a voided envelope actually lands on once the
`EnvelopeVoided` reaction has drained, i.e. the dangerous case `BL-259` is about, left half-fixed and
reported as closed.

**D3 — The catalog edit ships in the same commit as the code that carries it.** Not a follow-up and
not a tidy-up: `OpenApiSpecTest` fails either way round, and the reason it fails is `BL-181` — a code
that reaches production before the spec is one an integrator discovers by provoking it with a user
waiting.

**D4 — Every guard is sabotage-checked, and the check names which guard fired.** ⛔ Several guards sit
in series on both commit paths — a retired credential and a dormant step answer **before** the
aggregate is asked (`CommitSignatureUseCase`), and on the delegated path two assertion refusals and the
step guard answer before `commitSignature()` at all. A fixture that is also dormant, or dead, or
carrying the wrong assertion shape, is refused upstream and stays green with the code deleted. Every
fixture for §6.2 is otherwise a sent, live, step-active, credential-valid recipient.

**D5 — `notAuthenticated()`'s uncoded-ness is asserted, not assumed.** A test that asserts the other
four conditions says nothing about the fifth. The factory census (§6.2 row 3) is what makes the remainder a
closed set rather than *everything not yet listed*.

## 6. Verification

### 6.1 Gates

Per D1, from the main checkout: `lint`, `phpstan`, `composer cmd=arch`, `test`, then `qa` for
Infection. Infection is judged on **covered-MSI** against the `minCoveredMsi` floor in
`infection.json5.dist` — read the floor there, not from a number written here. Quote what each run
printed. ⚠ Before citing a green run, check its sha is the branch tip: a later commit touching `src/`
invalidates it.

### 6.2 Tests and sabotages

Each sabotage is applied, run, observed red **for the stated reason**, and restored.

| # | Tier / file | Case | Sabotage → expected red |
|---|---|---|---|
| 1 | Unit, beside `SigningSessionAuthGateTest` | `commitSignature()` on a `COMPLETED` session raises the exception with `problemCode()` `SESSION_ALREADY_COMPLETED`; on a `REVOKED` one, `SESSION_CLOSED`; with `envelopeIsAlive: false`, `ENVELOPE_NO_LONGER_LIVE`; with a verified challenge bound to a different document set, `SIGNING_CHALLENGE_MISBOUND`. | Swap any two codes → red naming the swapped case. Remove `implements ProblemCoded` → red on all four. |
| 2 | Unit, same file | ⛑ **The discriminating pair, and it is what §3 #3 turns on**: a `REVOKED` session whose envelope is **alive** answers `SESSION_CLOSED`, and an `AUTH_PASSED` session whose envelope is **dead** answers `ENVELOPE_NO_LONGER_LIVE`. ⛔ A fixture in which the session is revoked **and** the envelope is dead — the state a real void reaches — cannot separate them, because the terminal check answers first; that is the fixture whose variables always agree. | Give both arms one code → red on both halves, naming which. Reorder the two checks in the aggregate → red on the envelope-dead-and-revoked case, which is the ordering assertion. |
| 3 | Unit, `tests/F5Sign/Session/Unit/Domain/Exception/` (new, sibling of `OtpSendRefusalParityTest`) | **Factory census**: every public static factory on the class is exercised and its code classified against a declared disposition — coded with the expected literal, or deliberately on the status default. An unclassified factory fails **naming itself**. | Add a sixth factory without classifying it → red naming it. Delete a known row → red naming the missing one. |
| 4 | Unit, same file | **Terminal-status census** over `SessionStatus`: every member answering `isTerminal()` is classified as either `COMPLETED` → `SESSION_ALREADY_COMPLETED` or closed-by-the-sender → `SESSION_CLOSED`; an unclassified terminal member fails naming itself, so a decline or an expiry asks ADR-0056 §2.5's question instead of inheriting `SESSION_CLOSED` in silence (ADR-0067 §3.3, risk 2). | Add a terminal case to the enum without a disposition → red naming it. |
| 5 | Application, `CommitSignatureUseCaseTest` | Each of the four reachable conditions is caught and its `problemCode()` asserted, with the session **not** saved and no `SessionCompleted` pending. | Code the condition wrongly → red; move the guard after `save()` → red on the no-effect assertion. |
| 6 | Application, `CommitDelegatedSignatureUseCaseTest` | The same four, plus: a relayed `SIGNING_PLATFORM` recipient on an `AUTH_PENDING` session reaches `notAuthenticated()` and gets a **bare `CONFLICT`** (D5). | Give `notAuthenticated()` a code → red on the bare-`CONFLICT` assertion. |
| 7 | Acceptance, new `CommitRefusalsNameTheirConditionHttpTest`, modelled on `DormantStepRefusedHttpTest` | §6.3. | §6.3. |
| 8 | Acceptance, `OpenApiSpecTest` (existing, no edit) | The three new members are published and all three emitted; `ALREADY_SIGNED` is absent from the catalog and from every `#[OA\*]`. | Remove one member from the yaml → red naming it. Leave `ALREADY_SIGNED` in the delegated block → not caught by this test, which is why §6.4's sweep is a separate step. |

### 6.3 The acceptance case

One sent, live, single-step envelope per arm; a session credential minted the way
`DormantStepRefusedHttpTest` mints one; every fixture otherwise clean per D4.

1. **Already completed** — commit once (200), commit again on the same still-valid credential →
   `409` with `code: "SESSION_ALREADY_COMPLETED"`.
2. **Envelope dead, revocation not yet drained** — void the envelope after the recipient
   authenticated and commit **without** letting the `EnvelopeVoided` reaction run → `409` with
   `code: "ENVELOPE_NO_LONGER_LIVE"`.
3. **Session closed, revocation drained** — the same void with `RevokeEnvelopeSessions` actually
   applied to the session, then commit → `409` with `code: "SESSION_CLOSED"`. ⛔ **This is the step
   the case is easiest to build wrong.** Stopping at the void gives step 2's code, which passes a
   weaker assertion while proving nothing about the distinction ADR-0067 §2.3 mints the member for.
   Check *which* code came back, not that a 409 did; ⚠ `async_events` is `in-memory://` in test, so
   nothing drains on its own and this arm has to drive the revocation deliberately.
4. **Challenge misbound** — a recipient with a declared signing gate, a verified challenge bound to a
   different document set, commit → `409` with `code: "SIGNING_CHALLENGE_MISBOUND"`.
5. **The four codes are asserted distinct from one another** in the same test method, not only equal
   to their literals — that is the property `BL-259` asks for and the one a per-arm assertion does not
   state.
6. **Positive control** — a clean recipient commits and gets **200**.
7. **The sabotage for the delivery bar**: remove `implements ProblemCoded`, re-run, observe all four
   answer `code: "CONFLICT"` and the distinctness assertion go red naming it. Restore.

### 6.4 The sweep, immediately before each commit

```bash
rg -n 'ALREADY_SIGNED|CONFLICT|SESSION_ALREADY_COMPLETED|SESSION_CLOSED|SIGNING_CHALLENGE_MISBOUND|ENVELOPE_NO_LONGER_LIVE|BL-249|BL-259' src tests migrations config docs CLAUDE.md
```

Read every hit for **tense**, and re-read each whole prose block you edit rather than the lines you
changed. ⛔ **Run it last, before each commit, not once as a phase** — a change made after a sweep
invalidates the sweep (`CLAUDE.md` authoring rule 1). ⛔ **Also sweep the names that LOST**, because
stale prose points at the shape that was not built and no symbol sweep reaches it:
`AUTH_CHALLENGE_MISBOUND` (ADR-0067 §7.2), `SESSION_REVOKED` (the name §2.3 rejected for
`SESSION_CLOSED`), `ALREADY_SIGNED` (§7.1) — and the **reuse shape** of §7.3, which retires no name at
all, so the only way to find prose still describing one code for both dead-envelope arms is to read
every hit of `ENVELOPE_NO_LONGER_LIVE` for what it claims the code covers.

## 7. Open follow-ups (track, don't solve here)

- **`f5sign-signer` and this backend ship in one deploy.** ⛑ Headed *"`f5sign-signer` must branch on the three
  new codes before this merges"* until 2026-09-16, when this merged into `develop` at `acb20d0` and the order
  changed; the amendment at the end of this bullet says why. Their routing is written
  and uncommitted and they are waiting on the names — `SESSION_ALREADY_COMPLETED`, `SESSION_CLOSED`,
  `SIGNING_CHALLENGE_MISBOUND`. Until it ships, the already-completed arm falls from
  their done page to their generic failure screen — the safe direction of the same defect, and stated
  rather than discovered (ADR-0067 §2.6). Nothing in this repository can gate it; the handoff (§3 #9)
  is the whole mechanism, and [`BL-235`](../BACKLOG.md) is the row that says why the gate cannot live
  here. ⚑ **The handoff landed 2026-09-16** as
  [`TASK-043-a-refused-commit-names-its-condition.md`](../frontend-handoff/TASK-043-a-refused-commit-names-its-condition.md)
  (`6e8d443`), before the merge rather than with it, and the consuming session was told the partition is
  green. **The signer change itself was still owed at that point** (⛑ *"is still owed"* until 2026-09-16), and so
  was a second signal they asked for by name:
  they remove their `CONFLICT` compatibility branch when this is **deployed**, not when it is merged, and
  they check the served `doc.json` rather than our word for it (that directory's README rule 4).
  ⚑ **Their side closed the same day**: `639a788` routes both handoffs, `2f4e721` forces a fresh mint on
  `SIGNING_CHALLENGE_MISBOUND`, `eb5ac02` turns their assumption about an expired challenge into a read fact and
  `1638c6b` moves their citations off *"the backend told us"* and onto our published 409 — green on their lint +
  typecheck + 2938 unit, verified against the live `doc.json` rather than against our word. **Signal 2 is the only
  thing outstanding**: the deploy, which is when they delete `code === 'CONFLICT'`. ⚑ **That exchange produced one
  more commit here**, `117f7d3`: both 409 blocks told a client to obtain a fresh signing code and neither said that
  the default way of asking hands the same one back — see §8. ⛑ **Qualified 2026-09-16**: *closed* above means
  **committed on their `develop` and not pushed** — read in their clone, where all four sit in
  `origin/develop..develop` — so their push comes before the deploy signal can. The frontend handoff's `Status`,
  which still read `Pending`, now says the same. ⛑ **Superseded 2026-09-16, later the same day: pushed.** Read in
  the same clone, `origin/develop` = `develop` = `7ce2958`, and `git log c894f88..origin/develop` lists six
  commits — the four above, then `01ffece` (below) and `7ce2958`, which regenerates their contract snapshot from
  this repository's `develop`.
  ⛔ **Amended 2026-09-16, after the merge: the release is ONE deploy of both sides, and *Signal 2* above no
  longer describes it.** Confirmed by the maintainer. The signer removed `code === 'CONFLICT'` before either
  side deployed — `01ffece`, pushed; ⚠ its sha changed before the push, when its message was amended, so any
  other sha for it is stale — so the compatibility that made *signer first* safe is gone, and the dependency
  runs both ways. A new signer sends the old backend's bare `CONFLICT` for *already completed* to its generic
  failure. The old signer does the same with this backend's `SESSION_ALREADY_COMPLETED`: a *could not sign*
  screen over a signature that exists, with a retry that cannot succeed and a Sentry event on every retry.
  That arm is a **regression**, not the safe direction this bullet's opening calls it; `SESSION_CLOSED` and
  `SIGNING_CHALLENGE_MISBOUND` fall to the same useless retry, coming from a false *signed*. Neither side may
  ship without the other, and the maintainers of both repositories decided to push and deploy them together.
  ▶ **Done means both served artifacts carry it, not both branches.** (1) The served backend includes
  `acb20d0`. This backend serves no commit id — no route in `config/routes.yaml` or `config/routes/` returns
  one — so from outside, the evidence is that deployment's `doc.json` listing
  `SESSION_ALREADY_COMPLETED` in `components.schemas.ProblemCode`. (2) The served signer bundle includes `01ffece`,
  proven by the **content** of the served bundle: some chunk carries `SESSION_ALREADY_COMPLETED` (present since
  `639a788`) and no chunk carries the literal `"CONFLICT"` (gone exactly at `01ffece`, being `mapError`'s old
  condition). It proves behaviour rather than a sha, which is what closure needs, and it fails closed: a
  dependency that later ships the literal reads NOT PROVEN, never a false PROVEN. The probe script and the
  signer side's measurements of it (a real negative, a positive over HTTP, a re-injected negative) live in
  [the TASK-043 handoff](../frontend-handoff/TASK-043-a-refused-commit-names-its-condition.md), under the
  closure check, rather than being copied here. ⚑ **Corrected 2026-09-16**: this read *"checked against that
  deployment's `/_nuxt/builds/latest.json`"*, and that file carries only `{"id", "timestamp"}` — it says which
  bundle is served, not what it contains, so a date comparison was a hint and not a proof. Nothing is
  deployed on either side today.
  [ADR-0067](../adr/ADR-0067-a-refused-commit-names-its-condition.md) §2.6 carries the amendment.
- **Per-route code completeness is still ungated.** [`BL-209`](../BACKLOG.md) is the check that would
  fail a route whose `#[OA\*]` enumerates a subset of what it emits. This task edits six such blocks by
  hand and leaves them held by review, which is exactly the shape that row exists for. ⚑ **The six landed**
  in `8e99f33`, and one false clause inside them survived the per-symbol sweep and was caught a commit
  later by the whole-block re-read (`360cbfc`, §8) — which is the measurement that makes *held by review*
  a stated cost rather than a formula.
- **`notAuthenticated()` is a 409 whose remedy is *prove something*.** ADR-0067 §2.8 leaves it, and §2.4
  records that it is reachable on the delegated twin rather than nowhere. What would force it: an
  integrator reporting a 409 they cannot act on, or a second condition joining the bare `CONFLICT` —
  which §6.2 row 3 turns red. ⚑ **That census exists now**:
  `SigningSessionStateRefusalCensusTest::exactly_one_condition_wears_the_status_default` (`8e99f33`), so a
  sixth factory inheriting the default reddens naming itself instead of landing in silence.
- **The two remaining over-claims on the delegated 409** (`ENVELOPE_NOT_SENT`,
  `RECIPIENT_SLOT_NOT_CLAIMED`) stay open on [TASK-033](TASK-033-delegated-signature.md)'s surface,
  beside the `ALREADY_SIGNED` clause this task closed. ⚑ **Corrected 2026-09-16**: this bullet ended
  *"[`BL-249`](../BACKLOG.md) names all three and should be narrowed rather than closed when this
  lands"*, and the narrowing was done by **splitting the row rather than by editing its subject**. That
  row's subject — a published `ALREADY_SIGNED` that nothing emits — is discharged, so it is `Closed`;
  the two that remain are indexed as [`BL-266`](../BACKLOG.md), minted at close so the cross-cutting view
  does not lose them the moment the only row that mentioned them stops being open. Their home-of-truth is
  unchanged: [TASK-042](TASK-042-no-recipient-acts-before-their-step.md) §7 and TASK-033's surface.
- **Rows owed when this lands.** ⚑ **Corrected 2026-09-16**: this bullet opened *"and deliberately not
  made in the drafting changeset"* and listed the three [`docs/adr/README.md`](../adr/README.md) edits
  ADR-0067 needs among them. Those three — index row, relationship graph, crosswalk row — were made, in
  `6960c15`, the same commit that wrote this sentence. What is genuinely owed is the rest: a
  [`docs/BACKLOG.md`](../BACKLOG.md) pass over `BL-249` and `BL-259` read for
  **tense**, since both describe the defect in the present; and ADR-0066 §2.8's bullet on the signer's
  commit routing, which this decision changes the terms of. ⚑ **All of that was done at close on
  2026-09-16**, in the same commit as this sentence: `BL-249` and `BL-259` are `Closed` with their bodies
  read for tense and the commits named, `BL-266` carries what `BL-249` did not discharge, and ADR-0066
  §2.8's last bullet carries a dated note saying a 409 on the commit is no longer one undifferentiated
  term.
- **ADR-0067's promotion to `Accepted` was owed, and the maintainer gave it on 2026-09-16.** ⚑ **Added at
  close 2026-09-16**, headed *"ADR-0067's promotion to `Accepted` is owed, and it is the maintainer's"*.
  The decision is exercised and the artifacts can be pointed at rather than asserted (§8); its `Status`
  **value** was deliberately not changed at close, exactly as ADR-0066's was not on the branch beneath this
  one. What moved then was the evidence under it, and §5/§6, which were written in the negative and would
  otherwise have told the next reader to build what is already in the tree. What would force the
  promotion: the maintainer's word, and nothing else. ⛑ **Given 2026-09-16**: ADR-0067's header, its
  `docs/adr/README.md` index row, this record's header and the frontend handoff's *Origen* row now carry
  `Accepted (exercised)`. ⚠ **Exercised is not deployed**, so the joint deploy this section's first bullet
  now describes is still outstanding. ⛑ This read *"the deploy signal in this section's first bullet"* until
  2026-09-16, when that bullet was amended to one deploy of both sides.
- **This changeset's covered-MSI number came from outside the sanctioned path.** ⚑ **Added at close
  2026-09-16**, headed *"This changeset has no covered-MSI number"*, and saying §6.1's Infection bar was
  **absent** because `composer qa` aborts at `@test` and `composer infection` refuses to start, *"both
  because of the two environmental reds"*. ⛑ **Corrected 2026-09-16, later the same day**: one of the two
  reds is gone and the number exists — covered-MSI **82.73%** against a floor of 79, measured with
  `DocumentationLinkTest`'s one method excluded (Status row). [`BL-251`](../BACKLOG.md) is still the row,
  because a plain `composer infection` still refuses over that test, and a number that needs an exclusion
  re-derived per run is not a gate. The structural strength of the twelve new cases still rests on the
  fourteen sabotages: the figure is whole-tree and cannot say which of them it speaks for. What would
  force it: BL-251's own trigger.
- **Two findings about this repository's published spec, surfaced by the consumer rather than by us.**
  ⚑ **Added 2026-09-16**, from `f5sign-signer`'s regeneration of its contract snapshot against this
  `develop` (their `7ce2958`). Neither is this task's defect; both are recorded so the next reader does not
  re-derive them. **(a) `MACHINE_KEY_ASSERTED` was unknown to the signer's types.** It is the recorded-only
  member [ADR-0055](../adr/ADR-0055-delegated-signature.md) added to the published auth-method enums, and it
  is documented there and in those enums' descriptions, but `rg MACHINE_KEY_ASSERTED docs/frontend-handoff`
  returns nothing: no handoff ever named it. They added it to their union as record-only — no gate accepts
  it, so the client gains no branch — which leaves nothing to hand off, so no row is filed.
  **(b) Eight standing warnings: response objects that declare no `required`.** Their check reports them
  against the 201 of `POST /api/v1/signing-tokens`, the 200 of `POST /api/v1/signing/commit` and several
  nested objects of the 200 of `GET /api/v1/signing/session`. Read here: the `OA\JsonContent` of the first
  two carries no `required` at all, and `components.schemas.SigningSession` in `nelmio_api_doc.yaml` lists
  its top-level members as required while most of its nested objects list none. A generated client then
  types every such member optional. [ADR-0026](../adr/ADR-0026-openapi-documentation.md) names `required`
  only for request DTOs. Nothing tracked it; indexed as [`BL-267`](../BACKLOG.md). What would force it: a
  consumer that treats an unpromised member as possibly absent, or the first response member that
  genuinely becomes optional and cannot be told apart from these.

## 8. Deviations & honest notes

Written at close on 2026-09-16, alongside §7's disposition. It is the **last** section and nothing above
it was renumbered, because the `§N` here are anchors cited from
[ADR-0067](../adr/ADR-0067-a-refused-commit-names-its-condition.md), from [`docs/BACKLOG.md`](../BACKLOG.md)
and from this record's own text.

### Scope

- **The six `#[OA\*]` blocks landed in the SAME commit as the code** (`8e99f33`), not in a second one as
  the plan had them. Folded in because that code falsifies all six: a commit that publishes *"Otherwise,
  with no `code`: the envelope is no longer live, or the session is already completed"* while its own
  exception emits four codes ships prose its own changeset disproves, and repairing it one commit later
  does not make the intermediate state honest. ADR-0067 §2.5 says *changeset*, so nothing in the record
  forbids either split; this one simply has no self-falsifying intermediate state.
- **[`docs/frontend-handoff/README.md`](../frontend-handoff/README.md) was edited as well as the new
  handoff file** (`6e8d443`). §3 #9's boundary named *"the new handoff under `docs/frontend-handoff/`"*;
  the directory's index row belongs to the same deliverable, and re-reading the block it sits in turned
  up the hand-maintained counter beneath it — *"estas tres entradas son tres de los diecinueve
  ficheros"*, true on 2026-09-01 and made wrong by this entry. It now reads **four of twenty**, dated in
  place, and names [`BL-254`](../BACKLOG.md), the row that proposes the list stop being maintained by
  hand at all.
- **Three assertions in `GatedSigningCeremonyHttpTest` changed** (`8e99f33`), which §6.2 does not list: a
  second commit, an auth submit over a voided envelope, and a commit over a voided envelope each asserted
  a bare `'CONFLICT'`, and this change makes all three false. ⚑ **Found by grepping the retired literal
  over `tests/`, not from the diff** — the file needed no edit for any other reason, so its diff across
  the re-cut was empty right up until the grep found it, which is `CLAUDE.md` authoring rule 1's *an empty
  diff means never revisited*. They would otherwise have been three reds outside the declared baseline.
- **[`EnvelopeNoLongerLiveException`](../../src/F5Sign/Session/Application/Exception/EnvelopeNoLongerLiveException.php)'s
  docblock was corrected** (`8e99f33`), which §3 #10 does not list. It argued that the split between it
  and its Domain sibling was *"what keeps this a non-breaking change … Making that class `ProblemCoded`
  would give them a finer code, which is a breaking wire change"*. That was a true description of
  [TASK-038](TASK-038-terminal-envelope-closes-the-ceremony.md)'s scope and stopped describing this tree
  the moment ADR-0067 landed. ⛔ **The mechanism was replaced and the reason kept** (authoring rule 2):
  the split survives for the reason the paragraph above it gives, and it was never what made that change
  non-breaking.
- Nothing else. No migration, no schema change, no new route, no new response member, and no
  `deptrac.yaml`, `phpstan.dist.neon` or baseline edit — ADR-0067 §2.7 says why none is needed and §4 puts
  a diff touching them out of scope.

### Decisions taken during implementation

- **`notAuthenticated()` returns the literal `CONFLICT` rather than an absence.**
  `ProblemCoded::problemCode()` returns a `string`, and once the class implements the interface the edge
  prefers its answer over `STATUS_CODES` for every instance — so "uncoded" has to be spelled. Written as
  a named constant so the choice is visible at the factory instead of inferred from an absence (§3 #5);
  the wire is byte-identical to what it was. ⚠ `CONFLICT` carries no underscore, so `OpenApiSpecTest`'s
  discovery regex does not demand it in the catalog — checked, not assumed.
- **Two new Unit files rather than additions to `SigningSessionAuthGateTest`**, the shape
  `SigningSessionRevocationTest` already uses: same aggregate, different guarantee.
- **The distinctness assertion runs BEFORE the per-arm map, and the order is load-bearing.** PHPUnit
  stops at the first failed assertion, so a per-arm equality map placed above it answers for it: under
  the delivery bar's sabotage all four arms collapse to `CONFLICT`, the map reddens first, and a total
  collapse gets reported as a naming slip on one arm while the line that states the property is never
  reached. ⛔ **That is the guards-in-series trap one level up** — what fires is not what you think you
  are testing — and it was measured here rather than reasoned about.
- **The misbound arm rewrites one column** (`bound_document_set`) to express *the documents moved under
  the verified proof*, the same kind of arrangement as the cooldown rewind next door. The state is one
  the domain guard exists for, and no route produces it today because what a recipient signs is authored
  before the send.
- **The `SESSION_CLOSED` arm drives the revocation** — `RevokeEnvelopeSessions` on the command bus, the
  same command the `EnvelopeVoided` reactor dispatches — rather than stopping at the void. `async_events`
  is `in-memory://` under `when@test` and the worker is down, so nothing drains on its own, and a fixture
  that stops at the void answers `ENVELOPE_NO_LONGER_LIVE`: a weaker assertion that passes while proving
  nothing about the distinction ADR-0067 §2.3 mints the member for.
- **No `P-§` number was minted.** The property catalogs are design-repo and this record mints none; the
  new docblocks cite ADR-0067 §§ instead, which is what `DormantStepRefusedHttpTest` does with ADR-0066.

### Decisions that needed an ADR

- **None new.** ADR-0067 was drafted alongside this record (`6960c15`) and amended to the maintainer's
  three-code decision before any code was written; the implementation contradicted none of it.
- ⛑ **One clause of it was measured FALSE by the implementation, and is corrected at close.** §2.2's
  condition column said `signingChallengeMisbound()` covers a proof that *"has been spent"* (⛑ this read
  *"remedy column"* until 2026-09-16; the clause sat in the condition column, as `6960c15` shows). It does not:
  `SigningSession::consumeSigningChallengeFor()` skips anything failing `isVerifiedAndUnspent()`, so a
  replay never reaches that factory and is refused **401 `AUTH_NO_OPEN_CHALLENGE`**, pinned by
  `SigningSessionAuthGateTest::a_spent_signing_challenge_cannot_authorise_a_second_act`. The docblock,
  both published 409 strings and the frontend handoff were corrected in `360cbfc`; the ADR's own table was
  outside that changeset's boundary and carries the dated correction now. ⚠ **Harmless in a docblock and
  not harmless in the spec**: published on two routes it would have told clients a spent code answers 409,
  which is a value neither route sends.
- **ADR-0067's `Status` value was unchanged at close, deliberately, and the promotion came after it.**
  ⛔ At close this bullet read *"`Accepted` means *exercised* in this set and it is exercised — but the
  promotion is the maintainer's, and taking it here would be this phase deciding something it is only
  allowed to propose"*. What moved then was the evidence under the label, plus §5 and §6, which were
  written in the negative and would otherwise instruct the next reader to build what is already there
  (authoring rule 7's mirror: only *landing* an ADR has a checklist). ⚑ **The promotion was given on
  2026-09-16**, and the form is `Accepted (exercised)`, the same as ADR-0066's. `Accepted (enforcement
  partial)` is not the form: ADR-0067 §5 names a case for each bar it enforces and lists what it holds by
  review as review, three of those items since the record was drafted (`6960c15`) and the fourth since
  the realization measured that `OpenApiSpecTest` cannot see prose. ⚠ **Exercised is not deployed**: the
  branch is merged into `develop` at `acb20d0` and pushed, and nothing serves the four codes yet. ⛑ **Corrected
  2026-09-16, at the merge**: this read *"the branch is neither merged nor pushed"*. [`AUTHORING.md`](../adr/AUTHORING.md)
  has maintenance sections for adding and superseding an ADR and none for promoting one, so the surfaces
  edited at the promotion were found by `rg -n 'ADR-0067' docs src tests`, not by a checklist.

### Properties declared and not proved

- **§6.1's Infection bar was measured only off its sanctioned path.** ⛑ **Corrected 2026-09-16**: this
  bullet read *"§6.1's Infection bar was not measured … both because of the two declared environmental
  reds … Covered-MSI for this changeset is **absent, not green**"*. It has since been measured with one
  declared exclusion — covered-MSI 82.73% against 79, MSI 50.095% against 50 (Status row) — but
  `composer qa` still aborts at `@test` and `composer infection` still refuses over `DocumentationLinkTest`
  ([`BL-251`](../BACKLOG.md)), so it is a number and not a green gate. The structural strength of the
  twelve new cases rests on the fourteen sabotages — each applied, observed red for its stated reason,
  restored, and each restoration verified by an empty `git diff` against the committed file.
- **`ALREADY_SIGNED`'s absence from every `#[OA\*]` is not gated.** `OpenApiSpecTest` cannot see it: it is
  prose, not a literal a `ProblemCoded` implementor carries. The retirement is held by §6.4's sweep and by
  review, which is exactly the surface [`BL-209`](../BACKLOG.md) exists for.
- **Whether the four gate routes can actually reach these arms is not measured.** ADR-0067 §2.5 says the
  edit does not turn on it — a published sentence asserting an absent `code` is wrong either way — so the
  claim this changeset makes is about the sentences, not about the reachable set.
- **The remedies are claims about what the domain will accept next**, not restatements of what it refused.
  `SIGNING_CHALLENGE_MISBOUND` telling a signer to obtain a fresh code is held by the acceptance case and
  by nothing else (ADR-0067 §3.3).

### What the validation caught that no gate could see

- **A false clause found by the whole-block re-read, AFTER the sweep that had cleared the rest** — the
  *"or has already been spent"* above. ⛔ **A change made after a sweep invalidates the sweep**, and this
  one was worse than that: the clause names no symbol this branch retired and no code, so the per-symbol
  pass could not have reached it at all. Only re-reading the whole prose block did.
- **The three `GatedSigningCeremonyHttpTest` assertions**, above: a file that still needed the edit and
  showed an empty diff across the re-cut.
- **A second post-sweep correction, and the consuming repository found it rather than this one** (`117f7d3`,
  2026-09-16, after §7 above had already been written). Both commit routes instructed a client to *obtain a FRESH
  signing code* and neither said how: this refusal checks the binding and throws **without** consuming the
  challenge, so the default `resend: false` — which means *ensure a code exists* — finds that same unusable one and
  answers `minted: false` with it. A remedy that names no mechanism is one a client executes into the exact loop the
  sentence beside it forbids. ⛔ **That is the second correction to those six blocks after the sweep that cleared
  them**, which makes the case for [`BL-209`](../BACKLOG.md) a measured one rather than a rhetorical one.
- **A closed enumeration inside the commit route's own 409**: it described the codes as *"the two families
  below"*, a split that block does not make. Dropped in `360cbfc` for a statement that carries no count.

### Debt left, and where it lives now

| What | Where it lives |
|---|---|
| The deploy signal `f5sign-signer` asked for by name. Their change is pushed on their `develop`, `c894f88..7ce2958`, with the `CONFLICT` removal in `01ffece`. ⛑ This cell read *"The `f5sign-signer` change, and the deploy signal they asked for by name"* until 2026-09-16, and then *"committed on their `develop` and not pushed (`639a788`, `2f4e721`, `eb5ac02`, `1638c6b`)"* until they pushed, the same day. ⚑ **Since 2026-09-16 the signal is one deploy of both sides**, not a signal after ours (§7) | §7, *`f5sign-signer` and this backend ship in one deploy* (headed *`f5sign-signer` must branch…* until 2026-09-16) + [`BL-235`](../BACKLOG.md) + the handoff |
| Per-route `#[OA\*]` completeness; six blocks now held by review | §7, *Per-route code completeness…* + [`BL-209`](../BACKLOG.md) |
| `notAuthenticated()`'s bare `CONFLICT`, and whether 409 is its status | §7, *`notAuthenticated()` is a 409…* + ADR-0067 §2.8 |
| The two remaining over-claims on the delegated 409 | §7, *The two remaining over-claims…* + [`BL-266`](../BACKLOG.md), minted at close so closing `BL-249` does not lose them |
| A covered-MSI number that only an excluded test makes obtainable. ⛑ This cell read *"No covered-MSI number for this tree"* until 2026-09-16 | §7, *This changeset's covered-MSI number came from outside the sanctioned path* + [`BL-251`](../BACKLOG.md) |
| ADR-0067's promotion to `Accepted` | **Discharged 2026-09-16**: the maintainer gave it, as `Accepted (exercised)`, and §7, *ADR-0067's promotion…* records it. This cell read *"proposed here, not taken"* |
