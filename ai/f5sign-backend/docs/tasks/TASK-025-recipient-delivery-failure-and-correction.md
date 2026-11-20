# TASK-025 — When a recipient cannot be reached: the return path to Envelope, and the correction that follows

| Field | Value |
|-------|-------|
| **Status** | ✅ **Implemented on `feat/recipient-delivery-failure-2`; all four §6 decisions answered and honoured.** ⛔ **Read §6 before changing anything here** — the plan as originally written **did not compile**, and §6 is the record of why. Landed: `3323161` (the return path, the outcome, the correction and its route), `0ee1444` (the eleven findings from the three validations). ⚑ **The finding that mattered most was behavioural, not coverage**: correcting a `PENDING` recipient in a not-yet-activated step minted a 7-day token and mailed them the signing link **ahead of their turn** — the use case it mirrors has that gate, this one was written without it, and its 22 Not-Covered mutants meant nothing would ever have said so. ⚑ **Every mechanical gate was green before the fixes**; what was missing was that nothing proved the thing the task exists for — Infection reported the whole return path and the whole HTTP correction chain as Not Covered, so bars 1, 2 and 4 rested on nothing. **Merged tree: 1616 tests / 6696 assertions · PHPStan 0 · Deptrac 0/0 · composer arch 0/0 · php-cs-fixer 0/794 · Infection covered-MSI 86% overall, 98% over this task's nine surfaces.** 13 sabotages, each reverted and re-verified. ⚑ **Harness:** container route over this worktree against an isolated `f5sign_test_wt`, **never** `../f5sign-infra`'s make targets, which bind-mount the main checkout ([BL-112](../BACKLOG.md)). **What did NOT land:** asynchronous hard bounces are still invisible (the receipt seam is a separate [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) deferral), and the remaining correction budget is not readable from the read model — the sender learns it is exhausted from the 409. |
| **Type** | **Repair, then build.** It closes a hole that is open in production today and then supplies the recovery the hole has never had. |
| **Why** | An occasion that cannot be delivered records [`NotificationFailed`](../../src/F5Sign/Notification/Contract/Event/NotificationFailed.php) — **and nothing subscribes to it.** Invitations go out over a real SMTP transport, so this is live: when one is refused, the fact is written, the sender is never told, and the envelope waits for a recipient who will never arrive. There is no sender-side recovery, because there is nothing to recover *from* — the state does not exist. |
| **Builds on** | [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) — its **decision 7** already fixes the shape of this seam and its Consequences name the return path as deferred. This task discharges that deferral rather than deciding anything new about it. |
| **Decision record** | [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) decision 7. **No new ADR is owed**: the cross-BC direction, the reason it is a command rather than a subscription, and the layer that may not be depended upon are all already decided there and restated on the event's own docblock. If implementation contradicts any of it, that is an ADR change, not a silent edit. |
| **Delivery bar** | An envelope whose invitation is refused shows its recipient as `DELIVERY_FAILED` to the sender over HTTP; correcting the contact returns that recipient to `PENDING` and a fresh delivery goes out. Driven end to end, `make qa` green. |
| **Sequencing** | **First of the current group**, ahead of [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md). It shares no substrate with the two-gate work and fixes something already broken, so it is not gated by any of it. [TASK-022](TASK-022-delivered-codes-over-email.md) **depends on it**: [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.7 forbids channel fallback, so without this path an undeliverable one-time code strands the envelope outright. |

---

## 1. Why this task exists

[ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) shipped the Notification BC end to end, and named three things it deliberately did not finish. One of them is this: *"the return path is designed but unbuilt, so a permanently undeliverable recipient is recorded here"* — and only here.

The consequence is easy to state and easy to miss. `Notification` records `NotificationFailed` when its [`DeliveryPolicy`](../../src/F5Sign/Notification/Domain/ValueObject/DeliveryPolicy.php) can no longer be satisfied. The fact is durable, correct, and read by nobody. Envelope's [`RecipientOutcome`](../../src/F5Sign/Envelope/Contract/Type/RecipientOutcome.php) carries `PENDING`, `COMPLETED`, `DECLINED`, `DELEGATED` and `SKIPPED` — **there is no state meaning "we could not reach this person"** (envelope-domain-model divergence D5). So the recipient stays `PENDING` forever, which is indistinguishable from *has not got round to it yet*, and that is exactly the wrong reading for the sender to have.

This was written as a prerequisite of delivered one-time codes because that is the slice where it becomes fatal — [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.7 refuses channel fallback, so an undeliverable code has no recovery at all. But the hole is not the OTP's: it is already open on every invitation the platform sends. Building it here, first, prices it against what it actually fixes.

## 2. What gets built

**The reaction lives in Notification and calls outward.** Deptrac grants **no** layer a dependency on Notification — the one-way direction that makes it a supporting BC — so Envelope cannot subscribe to `NotificationFailed`. The seam runs the other way, exactly as [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) decision 7 fixes it: an internal reaction in Notification consumes the fact, reads the occasion's subject and addressee references, and calls into Envelope's own published write port, in Envelope's own vocabulary. It is the write-side twin of the `EnvelopeQueryInterface` jump this BC already makes at creation.

**"Command" here means a port method, not a bus DTO, and the distinction is enforced.** [`Command`](../../src/F5Sign/Kernel/Command/Command.php)'s own docblock scopes the kernel category to the bus-dispatched record and carves out *synchronous port-method commands in the hexagonal sense* — naming [`EnvelopeCommandInterface::appendDocumentArtifact()`](../../src/F5Sign/Envelope/Contract/Command/EnvelopeCommandInterface.php) as its example, which is the port this extends. Taking the other reading fails twice over: `KernelTypePlacementRule` gives a bus `Command` exactly one home, `Application/Command/`, so it cannot be published in `Contract/`; and dispatching Envelope's own `Application` command from Notification is a Deptrac violation, since `NotificationApplication` is granted `EnvelopeContract` and nothing deeper. The legal shape already ships and needs no new rule — which is what keeps this task's *Decision record* row honest when it says no ADR is owed.

Two things the port shape then owes an answer, and neither is a decision so much as a discipline. The call is **synchronous and inside the reaction's transaction**, so a refusal must roll the whole reaction back rather than half-flip a recipient; and it must fail through Envelope's **`Contract` exceptions only**, per [ADR-0004](../adr/ADR-0004-cross-bc-anti-corruption-layer.md) — a domain exception leaking across the boundary would make Notification depend on Envelope's internals through the error channel, which no ruleset checks.

This is also why the fact stays a thin pointer carrying no reason text: the cross-context payload belongs to the call that translation produces, not to the fact.

**The trigger is `NotificationFailed`, not `DeliveryFailed`.** One channel being refused is not the same as the occasion being undeliverable: an `ANY` occasion survives until its last channel is refused, and only the failure that crosses the policy line records the terminal fact. Reacting to the per-channel event would flip a recipient to failed while a live channel was still trying.

**Envelope gains the state and the correction.** `RecipientOutcome` gains `DELIVERY_FAILED`, closing half of divergence D5. `CorrectRecipient(recipientId, contactPatch)` patches the contact under the **max-3-corrections** rule the envelope domain model specifies, returns the recipient to `PENDING`, and re-triggers delivery. Both the outcome and the correction are recorded facts; a corrected recipient is not a silently edited one.

**The correction needs a door.** A command with no route is unreachable code. `CorrectRecipient` gets a route on the machine-key authoring surface alongside the rest of `config/routes/api/envelope.php`, so an integrator can act on the failure their own read of the envelope told them about.

**And the sender has to be able to see it.** `DELIVERY_FAILED` surfaces on the envelope read model behind `GET /api/v1/envelopes/{id}`, per recipient. A failure state nobody can read is the same envelope dying quietly that this task exists to prevent — the fix would be invisible without it.

⚠ **What this catches, and what it does not.** Today a failure is a **synchronous refusal at hand-off**: the transport rejects the message and [`TransmissionOutcome`](../../src/F5Sign/Notification/Domain/ValueObject/TransmissionOutcome.php) reports it. A real-world hard bounce is frequently **asynchronous** — the relay accepts the message and the receiving MTA rejects it seconds or hours later — and there is no seam for that at all: the receipt seam (`DELIVERED` plus hard bounce) is a *separate* [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) deferral and is **not** built here.

So this task makes every failure the system can currently detect recoverable, and leaves a class of failure it cannot detect still invisible. That is a real limit and it is worth stating in those words rather than letting "delivery failure is handled now" be inferred. Whether the receipt seam is the next increment is a separate decision, taken against a provider and a webhook that do not exist yet.

## 3. Scope

**In scope:** the Notification-side reaction on `NotificationFailed` and its translation into an Envelope command; `RecipientOutcome::DELIVERY_FAILED`; `CorrectRecipient(recipientId, contactPatch)` under the max-3-corrections rule, returning the recipient to `PENDING` and re-triggering delivery; the machine-key route for it; `DELIVERY_FAILED` on the envelope read model and its OpenAPI coverage; **the migration for the correction counter** — ⛔ **corrected 2026-08-18, and it is the inverse of what this line used to say.** It said *“the migration for the new outcome value”*; there is nothing to migrate for that — `envelope.recipient.outcome` is `TEXT` with no `CHECK` and the repo has no `CREATE TYPE` anywhere ([ADR-0019](../adr/ADR-0019-database-schema-conventions.md) §5), so adding an enum case is a pure code change. The migration this task actually needs is the one it never named: **a `corrections_made SMALLINT NOT NULL DEFAULT 0` on `envelope.recipient`**, without which bar 5's max-3 budget has nowhere to live (§6.3). ⚠ A column default is right here and wrong in TASK-027's case: `0` is the true state of every existing row — nobody has been corrected — whereas a locale default would have invented a language nobody chose; the D5 divergence note updated to record which half closed; tests per §5.

**Out of scope:**
- **The receipt seam** — asynchronous hard bounces, delivery receipts, and the provider webhook they arrive on. A separate [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) deferral, and undecidable before a provider exists.
- **Correcting anything but the contact.** A patch changes where a recipient is reached, not who they are, what they may see, or where they sit in the workflow.
- **A phone number to correct.** There is no phone column until the SMS slice; correction extends to it there.
- **Retrying automatically.** A refused delivery does not retry itself on the same channel and never falls back to another one ([ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.7). Recovery is sender-mediated by design.
- **The dashboard rendering of a failed recipient.** The state and the command are exposed here; drawing them is frontend work in another repo.
- **OTP-specific behaviour.** That a corrected contact must receive a *new challenge* rather than a re-delivery is [TASK-022](TASK-022-delivered-codes-over-email.md)'s bar, because it only arises when the payload is a code.

## 4. Key decisions

- **Extracted rather than left inside the OTP slice.** It is not an OTP prerequisite; it is an open production hole that the OTP slice would have been the first to trip over. Pricing it against the feature that exposed it would have deferred a fix every envelope already needs behind one nobody has asked for.
- **Sequenced first.** It shares no substrate with the two-gate work and no decision with it, so nothing is gained by waiting and one thing is lost by it.
- **The reaction goes in Notification, not Envelope.** Not a preference — deptrac permits nothing else, and [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) decision 7 already reasoned it out. Restated here because a reader reaching for the obvious subscription will find it forbidden and should find the reason at the same time.
- **`DELIVERY_FAILED` is a recipient outcome, not an envelope status.** One unreachable recipient does not fail an envelope; the sender decides whether to correct, skip or void.
- **The limit is stated, not hidden.** Asynchronous bounces stay invisible after this ships. Saying so is what stops the next reader concluding the problem is closed.

## 5. Acceptance bars

1. **A refused delivery reaches Envelope.** An occasion whose policy is defeated flips its recipient to `DELIVERY_FAILED`, driven from a real transport refusal rather than by invoking the reaction directly.
2. **A refused *channel* does not.** An `ANY` occasion with one channel refused and another still live leaves the recipient `PENDING`. This is the bar that separates the two failure facts, and the one a reader skimming the names is most likely to get backwards.
3. **The sender can see it over HTTP.** `GET /api/v1/envelopes/{id}` reports the recipient as `DELIVERY_FAILED`. Without this the rest of the task is unobservable.
4. **Correction restores the flow.** `CorrectRecipient` patches the address over its route, the recipient returns to `PENDING`, and a fresh delivery goes out — asserted end to end, not on the aggregate.
5. **The correction budget holds.** A fourth correction on the same recipient is refused. Bounded because the alternative is an unbounded rewrite loop over an addressee an envelope was legally addressed to.
6. **The direction is enforced, not merely observed.** Deptrac stays green with the reaction in Notification, and no Envelope class imports anything from it. A test that only exercised behaviour would pass with the dependency inverted. Same bar covers the shape: the return path is a method on Envelope's published write port, so `composer arch` and PHPStan are both green without a `Command` appearing anywhere under `Contract/`.
7. **Nothing regresses for a delivery that succeeds.** The happy path of both existing purposes is untouched — the regression bar for a change that reaches the shipped invitation flow.

`make qa` green: PHPStan L9, Deptrac 0, lint, full suite.

---

## 6. What already exists, and the three things that block this plan

⛔ **Written 2026-08-18 after a verification pass against the tree, on branch `feat/recipient-delivery-failure`
(no implementation landed). Two of these are decisions rather than gaps, so the task stops here rather than
being implemented around them.** Added as a new section; §1–§5 are unrenumbered because they are `§N` anchors.

**Blockers 1 and 2 both come from the same omission: nothing in §2 or §3 enumerates what already *reads*
`RecipientOutcome`.** That census is the missing *"What already exists"* work, and it is where the cost of
this task actually lives — not in the code §2 describes writing.

### 6.1 ⛔ A new outcome breaks a deliberately `default`-less `match` in another BC — and the answer is a wire decision

[`SigningSessionReader::status()`](../../src/F5Sign/Session/Application/Query/SigningSessionReader.php)
switches exhaustively over `RecipientOutcome` with **no `default`**, and its docblock says that is deliberate:
a new case must break the build *rather than silently defaulting into "open, go ahead and sign"*. So adding
`DELIVERY_FAILED` does not compile until the **Session** BC decides what a signing session reports for a
recipient who was never reached.

That is not a mechanical fix. The candidate answers are a refusal, an existing `SessionStatus`, or a **new**
one — and a new `SessionStatus` is a **published wire change for the deployed signer app**, which lives in
`f5sign-signer` (another repo, so two coordinated PRs by the workspace rule). §3 scopes **no** Session work
and no acceptance bar covers it.

✅ **DECIDED 2026-08-18 by the user: the recipient may still sign.** *“Que haya fallado el email no implica que no
pueda firmar.”* So `status()` maps `DELIVERY_FAILED` to `SessionStatus::AUTH_PASSED`, exactly as `PENDING` does —
**no new `SessionStatus` case, no wire change, no signer coordination, and no second repo.**

⛑ **The reasoning, because it generalizes past this case.** The signing token is minted and the link built
**before** delivery is attempted (`NotifyActivatedStepRecipientsUseCase` builds `{base}/<token>` and only then hands
the message to the transport). So the credential is the **token**, not the mailbox: a bounce says our channel failed,
not that the person holding the link is illegitimate. Someone who was read the link over the phone is a real flow.
Refusing them would punish a legitimate signer for an infrastructure failure of ours — and `DELIVERY_FAILED` is a
*recoverable* state that returns to `PENDING` the moment the sender corrects the contact.

⚠ **`AUTH_PASSED` is not a lie here, and the separation is the point.** It means *authenticated, may proceed*, and
they did authenticate — they hold a valid token. Whether the invitation reached them is a **sender-side** fact, and
it belongs on the envelope read model where the sender looks, not in the signing session where the recipient does.
The two views answer different questions and are allowed to disagree.

### 6.2 ⛔ `DELIVERY_FAILED` would arrive *terminal*, and would close quorum steps over people never reached

[`RecipientOutcome::isTerminal()`](../../src/F5Sign/Envelope/Contract/Type/RecipientOutcome.php) is
`$this !== self::PENDING`. That is **correct today** — every non-`PENDING` case really is terminal — and it
silently becomes wrong the moment a *recoverable* non-terminal case exists, which is exactly what
`envelope-divergences.md` D5 and `envelope-domain-model.md` classify `DELIVERY_FAILED` as.

The consequence is not cosmetic: `StepCompletionEvaluator::evaluateQuorum`'s `allMembersTerminal` would treat
a step whose remaining members are **all** `DELIVERY_FAILED` as complete, **advancing the workflow past
recipients nobody ever reached** — the precise failure this task exists to prevent, reintroduced by the fix
for it. Two further call sites in `Envelope.php`.

⚑ **Bar 7 cannot catch this**, and that is the instructive part: it pins the *happy path*, which by
construction never produces a failed recipient. This is [`CLAUDE.md`](../../CLAUDE.md) authoring rule 5 —
a predicate whose exempted set is *"everything not yet listed"*. Whether `DELIVERY_FAILED` is terminal is
itself listed as **`Lean: needs decision` / `Status: 🔴 open`** in D5's own record.

✅ **DECIDED 2026-08-18 by the user: a third predicate.** Not *terminal*, and not folded into `isTerminal()`'s
current meaning either — `DELIVERY_FAILED` gets its own predicate for *“not terminal, but not in flight either”*, and
each call site picks the one it actually means. ⛑ **This repeats a move the repo already made** rather than inventing
one: `isCompletionTerminal()` exists for exactly this reason — its docblock separates COMPLETED (completion-terminal)
from DECLINED/DELEGATED/SKIPPED (terminal, not completion-terminal), and the non-quorum branch already uses it.

⚠ **Three call sites, and the middle one is worse than the quorum bug this entry was written about.**
`StepCompletionEvaluator`'s `allMembersTerminal` and `Envelope`'s step-closure filter both close a step over unreached
people. But `Envelope::markCompleted()` **returns early when the outcome is terminal** — so on a *terminal* reading a
real signature from that recipient is **swallowed in silence**: the PAdES seals and the aggregate records nothing.
That is decisive rather than theoretical, because the signing token is minted **before** delivery is attempted, so a
recipient whose email bounced can still hold a valid link and sign.

### 6.3 ⛔ The named migration is a no-op, and the persistence bar 5 actually needs has no home

§3 scopes *"the migration for the new outcome value"*. There is nothing to migrate: `envelope.recipient.outcome`
is `TEXT NOT NULL` with **no `CHECK`**, and there is no `CREATE TYPE`/`CREATE DOMAIN` anywhere in
`migrations/` — [ADR-0019](../adr/ADR-0019-database-schema-conventions.md) §5 mandates exactly that. Adding a
case is a pure code change.

The inverse is the real gap: **bar 5 ("a fourth correction is refused") requires a persisted correction
count, and no column exists** — `envelope.recipient` gained only `locale` (`Version20260817000001`) — while
`CorrectRecipient` and `RecipientCorrected` appear **nowhere** in `src/` or `tests/`. So the one migration the
task does need is the one it does not name. Unlike §6.1 and §6.2 this is a spec error rather than a decision,
and a column plus a recorded fact would settle it.

### 6.4 Smaller corrections owed, none of them blocking

- **The read-model bar is already met.** `EnvelopeJsonPresenter` emits `'outcome' => $recipient->outcome->value`,
  so bar 3 passes with **zero** code change. The real target is the **closed enum** at
  `config/packages/nelmio_api_doc.yaml` (`Recipient.outcome`), which the record calls only *"its OpenAPI
  coverage"* and never locates — and being YAML rather than an `#[OA\*]` attribute, it is the surface
  authoring rule 1 names as forgotten.
- **The max-3-corrections rule does exist** — `docs/ddd/envelope-domain-model.md`, §Lifecycle transitions,
  the `CorrectRecipient` bullet — so it is not unfalsifiable. But it is cited by prose with no link, and the
  record **drops the `PENDING` half** of its precondition: the model permits correcting a `PENDING` recipient
  too, which is the difference between a recovery command and a general contact-edit command.
- **[ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) decision 7 and `NotificationFailed`'s docblock
  both say the reaction *"dispatches a command into Envelope's `Contract` surface"*** — literally the shape §2
  proves illegal (`KernelTypePlacementRule` gives a bus `Command` one home, `Application/Command/`). §2 states
  the legal reading; correcting those two source texts is owed in the same changeset under authoring rule 1.
- **Bar 1's *"a real transport refusal"* names no tier**, and is ambiguous between the real SMTP transport and
  a throwing double. §2 establishes only a *synchronous* hand-off refusal is detectable at all.
- **§3 excludes the dashboard rendering** without naming the repo: it is `f5sign-dashboard`.

### 6.5 Verified sound, so nobody re-checks these

`Builds on` ADR-0037 decision 7 exists and says what is claimed, deferral included · `Command`'s port-method
carve-out and its `appendDocumentArtifact()` example both verified verbatim · deptrac verified both ways (no
layer lists `Notification*`; `NotificationApplication` grants `EnvelopeContract` and no deeper Envelope layer)
· the Notification→`EnvelopeContract` edge is **already live** (`NotifyActivatedStepRecipientsUseCase` imports
`EnvelopeQueryInterface`), so this opens no new cross-BC edge and the **`No new ADR is owed` claim survives**
· all 13 links resolve · no id collision.


### 6.6 ⛔ The plan never distinguishes WHICH email failed, and one of the two must not trigger it

Found 2026-08-18, from the user's question *“which email do you mean?”* — which is exactly the right question,
because there are **two** and the record treats them as one. §2 says *“an occasion whose policy is defeated flips its
recipient to `DELIVERY_FAILED`”*, and `NotificationPurpose` has two cases:

- **`RECIPIENT_INVITATION`** — carries the signing link. If this is undeliverable, the recipient genuinely cannot be
  reached to sign, and the whole task applies.
- **`ENVELOPE_COMPLETED`** — the *“this is finished”* notice, sent **after** the recipient has already signed.

⛔ **On the second, flipping the recipient to `DELIVERY_FAILED` is simply wrong**: they are `COMPLETED`. And under the
third-predicate decision above it is worse than cosmetic — a non-terminal `DELIVERY_FAILED` **blocks step closure**, so
a bounced completion notice would leave a fully-signed envelope unable to close. The reaction must filter on purpose.

⛑ **State it as a predicate, not as an exclusion of today's other case** ([`CLAUDE.md`](../../CLAUDE.md) authoring
rule 5): the trigger is *“the notification that carries the means to act”*, and ~47 purposes are planned. A guard
reading `purpose !== ENVELOPE_COMPLETED` admits every future purpose by default, which is the shape that rule forbids.
