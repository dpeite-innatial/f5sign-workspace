# TASK-050 — A step says how much agreement it needs, and its deadline releases whoever never acted

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/step-policy`** (tip `469bdf2e`), joined with TASK-049 and TASK-040 into the package branch `feat/task-048-how-an-envelope-ends` at `f48b14e2`, 2026-09-29, in two sessions on one package; the package branch was merged into `develop` on 2026-09-30 at `e6a0af5e` (⛑ corrected 2026-10-01; this read "pending review, and **not merged to `develop`**"). Built by the first session: step authoring and the `send()` refusals (`a3a524b2`); the one predicate wired, informational members never holding and their commit refused by name (`1cc5ef0e`); the decline retirement (`8f42995d`); per-release revocation (`480faab9`); the copy-ready notice and the reads it needs (`c8e404c4`, `70593ec2`); `envelope_outcome` (`21dc9a4a`, `901fd813`); claims bounded in time; the step deadline core (`deadline_at` stored at activation and the sweep funnel `3be2c390`, the clock's releases judged at its own instant and the sender's `STEP_DEADLINE_PASSED` `5b5212e7`, the recipient's `LEG_CLOSED` past a deadline `eb686c5f`, the stories played through `applyClocks()` `d618c20b`); delivery-bar cases (a)(b)(c)(f)(i) (`0e499567`) and (g)(h) (`e72ce6ad`). Built by the second session on `feat/close-now` and `feat/deadline-bars`: close-now (`6717d021`..`da3d3071`, `664dffa5`), the late-opening fix under the row lock (`fb875674`), the synchronous read cut (`9d4531ae`), the `ENVELOPE_NO_LONGER_LIVE` reword (`70a0e89d`), delivery-bar cases (d)(e) (`1ceb44b3`) and (j) (`ed7abad9`), and the expiry same-facts census (`07316515`); joined by `c12d4602`, `9d6d1d0b` and `469bdf2e`, and the package by `f48b14e2`. **Harness for the last green run:** `make -C ../f5sign-infra wt-backend ... src=<worktree>`, the kept lane `wt-f5sign-backend-step-policy` on `feat/step-policy` at `469bdf2e`: fast tier 4260 tests plus 78 filtered Integration/Acceptance. **Full suite on the joined package (`f48b14e2`): pending.** Infection covered-MSI not run. **Not built or not proven** (§7): the two-process races of an opening and a commit against a step deadline; the `SENT` rows migrated onto this predicate; the waiting `AT_LEAST` step end to end over HTTP; the migration assertions and `down()` against real data; a running worker consuming the `envelope_clocks` schedule. |
| **Type** | **Forward build.** Steps gain a completion policy (`ALL` \| `AT_LEAST n`, with an optional veto) and a deadline; informational members stop holding steps; a recipient's `RELEASED` outcome (born in TASK-048 with every `release_reason`) gains the releases at a step's deadline and by close-now; a decline inside a policy step stops being refused; the ending causes become specific. |
| **Why** | On the Factor5 waybill the consignees sign in one parallel step, each on their own document and schedule. Under [ADR-0070](../adr/ADR-0070-an-envelope-ends-in-agreement-or-is-voided-and-sealed.md) §2.3 every `SIGNER` is blocking, so one consignee's refusal voided the envelope for everyone (development stack, envelope `01a0c962…`, 2026-09-23). A claimable slot nobody claims stalls its step (ADR-0057 §2.11; [`BL-192`](../BACKLOG.md)). Other domains need the opposite: an objection that stops a board's written resolution or a two-parent consent, where everyone must have had the chance to object. |
| **Builds on** | Reused unchanged: `Step`'s storage (`min_signatures` carries `n`) and `StepView` as a starting point · ADR-0057 §2.12's claim predicate. |
| **Scope** | The step policy (policy, veto, deadline) at authoring and `send()` validation; the one step predicate, its docblock and the same-facts property test; securing under each policy; informational members never holding a step, and their commit refused by name; decline and veto; unreached members in a veto step; the specific ending causes; release at a step's deadline and by close-now (`released_by` `STEP_DEADLINE` / `SENDER_CLOSED`; the reasons are TASK-048's); a step holding `DELEGATED` or `SKIPPED` failing closed; per-recipient revocation; close-now; claims bounded in time; read side, events and notices. Out of scope (§6): advancing at the minimum, mixed mandatory/optional steps, agreements, a delegated decline, extending a step's deadline. |
| **Decision record** | **[ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md)**, drafted `Proposed` on 2026-09-24 and re-cut through 2026-09-28, before implementation. This task exercises its §2.1 (the informational-commit refusal), §2.2 (securing per policy, close-now), §2.4 (the property test), §2.6, §2.7, §2.8 (release at a step's close, `released_by` `STEP_DEADLINE` and `SENDER_CLOSED`, per-release revocation), §2.10 and §2.15 (the copy-ready notice); case (j) of its bar exercises TASK-049's §2.12 mechanism on a policy only this task builds. |
| **Delivery bar** | Over HTTP. **The waybill as authored** — shipper and carrier in `ALL` steps, three consignees in a last `AT_LEAST 1` step with a 2-day deadline: (g) A signs on day 0 → `EnvelopeAgreed`, a sender void refused; B signs on day 1; C never opens; past the deadline → C `RELEASED` · `SENT_NO_RESPONSE` · `STEP_DEADLINE`, `COMPLETED`/`AGREED`. **With a fourth step** (the shipper's closing signature), so the envelope stays open while step 3 is judged: (a) C declines, A and B sign → step 4 opens; at the end `AGREED` with C listed as declined; (b) all three decline → `NOT_AGREED`/`MINIMUM_UNREACHABLE`; (c) the carrier declines → `NOT_AGREED`/`RECIPIENT_DECLINED` with the carrier; (d) A signs, C declines, B's invitation sent and never opened; past the deadline → B `RELEASED` · `SENT_NO_RESPONSE` · `STEP_DEADLINE`, step 4 opens, and while the envelope is open B's link answers a closed leg and issues no one-time code; (e) one consignee an unclaimed slot, the other two decline → waits; at the deadline the slot `RELEASED` · `UNCLAIMED` · `STEP_DEADLINE` and `NOT_AGREED`/`STEP_DEADLINE_MISSED`; the shipper of step 4, never activated, `RELEASED` · `NOT_REACHED` · `ENVELOPE_CLOSED`. **A board step**, `AT_LEAST 3` of 5 with veto: (f) three sign, a fourth declines → `NOT_AGREED`/`RECIPIENT_VETOED` with that director, whatever the order of arrival; (h) three sign, one silent (sent), one whose invitation failed; past the deadline → the silent one `RELEASED` · `SENT_NO_RESPONSE` · `STEP_DEADLINE`, the other `RELEASED` · `DELIVERY_FAILED` · `STEP_DEADLINE`, and `NOT_AGREED`/`MEMBER_NOT_REACHED`. Releases are written *outcome · `release_reason` · `released_by`*. **A contract with a courtesy copy**: (i) two `ALL` signers then a `VIEWER` step; both sign → the viewer step activates and closes at once, `COMPLETED`/`AGREED` without waiting; the viewer, who never opened, is `RELEASED` · `NOT_REQUIRED` · `ENVELOPE_CLOSED` when the envelope closes, passes the gate and reads the sealed copy. **The waybill with no deadline on the consignee step**: (j) A signs → `EnvelopeAgreed`; B and C never act; at expiry → B and C `RELEASED` · (`SENT_NO_RESPONSE` or `LINK_EXPIRED` by their link validity) · `EXPIRY`, `COMPLETED`/`AGREED` — never left open. |
| **Sibling** | **[TASK-048](TASK-048-what-an-unagreed-envelope-keeps.md)** and **[TASK-049](TASK-049-an-envelope-expires.md)**, built before this task on the same branch and consumed by it: admission, securing and closing, `acceptsActs()` and the gate rule, the lifecycle and events, the closed-leg answer and the sweep command (not under *Builds on*, since they are not built yet). **The signer and the dashboard**: handoffs for the policy fields, `RELEASED` with `release_reason` and `released_by`, the causes, the decline consequence, the two refused roles. |

---

## 1. Why this task exists

Measured on `develop` at `3bda20a`, 2026-09-24:

- `POST /api/v1/envelopes/{id}/steps` (`AddStepRequest`) accepts an ordinal only, so `min_signatures` can never be
  authored; `Envelope::recordRecipientDecline()` throws for a quorum step and `SigningSession`'s decline refuses it
  with `DECLINE_NOT_OFFERED_IN_QUORUM_STEP`, a published `ProblemCode`.
- The live step predicate is `Envelope::advanceAfterRecipientTerminal()`: a step closes when every member's leg is
  terminal, blocking or not. `StepCompletionEvaluator` implements a different one and has no production caller.
- Nothing writes `RecipientOutcome::SKIPPED`; `SigningSessionReader` answers it `STEP_NOT_ACTIVE` (ADR-0066 §2.4).
- `SigningSessionReader::role()` refuses `IN_PERSON_HOST` and `CERTIFIED_DELIVERY` as not interactive.
- `RecipientDeliveryTrace` keeps one `{state, observedAt}` per **destination**, with no purpose, and
  `PropagateDeliverySuccessUseCase` forwards access-code deliveries as well as invitations; `DELIVERED` has no writer.
- `NotifyActivatedStepRecipientsUseCase` skips an unclaimed slot before minting, so a slot is never invited.
- Nothing revokes a single recipient's session; the only revocation (`OnEnvelopeVoided`) is envelope-wide.

Since then TASK-048 changed two of these: `Envelope::advanceAfterRecipientTerminal()` is gone, and the aggregate
runs `StepCompletionEvaluator` through `Envelope::evaluator()`/`advance()` in the transitional
`InformationalMembers::HOLD_THEIR_STEP` mode; `Envelope::recordRecipientDecline()` is the relayed, convergent path
and refuses nothing by step policy. The only refusal of a quorum-step decline left is `SigningSession::guardDecline()`,
reached twice from `DeclineSignatureUseCase` (its pre-check and `SigningSession::decline()`).

## 2. What already exists (reuse, do not rebuild)

- `Step` (`minSignatures`, `signedCount`, `declinedCount`, `quorumReachedAt`), its row and `StepView`.
- `EnvelopeRosterDeclared`'s `RosterStepShape` — gains members; `min_signatures` keeps its published meaning.
- `CompletionDriver` / `Envelope::completesOn()` — landing still drives the chain-tip guarantee.
- The delivery trace (`SENT`, `FAILED`), `authenticated_at`, and the signing link's fixed `LIFETIME`.

## 3. What gets built

### 3.1 Authoring and validation

The step route accepts `completion` (`ALL` default, or `AT_LEAST` with `n ≥ 1`), `veto` (only with `AT_LEAST`, off
by default) and an optional deadline (a duration of at least 24 hours). `n` is stored in the existing
`min_signatures` (`ALL` ⇔ null), whose published meaning is kept; the veto and the deadline are new columns. No
route sets `min_signatures` today; the migration asserts no step carries it. `send()` refuses, naming the condition: `n` equal to or above the counting members (equal is unanimity: send `ALL`, maintainer 2026-09-28); more than one blocking role in an `AT_LEAST` step (informational members
beside it are allowed); no blocking member in the envelope; an `IN_PERSON_HOST` or `CERTIFIED_DELIVERY` member. The step route's `#[OA\*]` strings and the handoffs say that an `AT_LEAST` step without a deadline waits for every member, so one that is not the last should carry a deadline, and that a veto step without one resolves only at the envelope's expiry, close-now refused until then; both are accepted without one (maintainer, 2026-09-28). The policy travels in `EnvelopeRosterDeclared`: `min_signatures` as today, the veto and the deadline as new members.

### 3.2 One predicate

**Already built, ahead of this task (2026-09-28):** `StepCompletionEvaluator` was rewritten as the single predicate, with `EnvelopeEndingEvaluator` over it as the pure ending rules and `ReleaseReasons`; they are run against `tests/F5Sign/Envelope/Testing/Scenario/EndingScenarioCatalog.php` (every case of this bar) and the same-facts census in `StepCompletionEvaluatorTest`. This task **wires them into the aggregate** — the aggregate calls them and never keeps a second predicate — and the catalog stays green at every level, the HTTP bars included. What the predicate does: counting admitted commits of blocking members, it answers whether the step is closed (every blocking leg closed: admitted, or its outcome terminal; or an admission made its policy impossible, which ends the envelope at once and releases the rest `ENVELOPE_CLOSED`), not agreed (`ALL`: a blocking member
declined or was released; `AT_LEAST`: admitted plus reachable below `n`, a veto, or — with veto — a member released with `release_reason` `NOT_REACHED`, `DELIVERY_FAILED` or `UNCLAIMED`), and, for the last step holding a blocking member, whether the agreement is secured (TASK-048's rule; trailing informational-only steps never gate it). Informational members (`VIEWER`, `REVIEWER`, `EDITOR`) never enter it; a step of informational
members only closes at activation. In the same change TASK-048's admission refuses an informational role's commit
by name — the two go together, because until informational members stop holding a step a `VIEWER` ends its leg
only by committing; the signer's handoff says the read-only roles no longer commit. A step holding a `DELEGATED` or `SKIPPED` member makes it fail (no writer
exists; [`BL-183`](../BACKLOG.md) and ADR-0066 §2.4 give them an outcome when they build one), and the census pins
that. Its docblock states ADR-0073 §2.4: every clock only closes a step and evaluates it here. This task adds the
`docs/LOAD-BEARING.md` entry ADR-0073 §2.4/§5 asks for, forbidding a special evaluation for expiry or any new clock;
none exists yet.

### 3.3 Decline, veto and causes

Both refusals of a decline in a quorum step — `SigningSession::guardDecline()` at `DeclineSignatureUseCase`'s pre-check and again inside `SigningSession::decline()` — are removed (`var/task-runner/TASK-048/task-050-quorum-decline-retirement.patch` holds the change); `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` is retired from the
published `ProblemCode` enum, the `#[OA\*]` strings and the signer (a recorded contract change). A decline is
evaluated at its admission. A step that cannot be agreed settles the envelope through TASK-048 with the specific
cause: `RECIPIENT_DECLINED` (party), `RECIPIENT_VETOED` (party), `MINIMUM_UNREACHABLE`, `STEP_DEADLINE_MISSED`,
`MEMBER_NOT_REACHED`. One cause, first match (ADR-0073 §2.6): a cause decided at an admission stands; at a clock's
close, `MEMBER_NOT_REACHED`, else the clock that closed the step (`STEP_DEADLINE_MISSED` or `EXPIRED`).
`Step::isQuorumStep()` (also called by `Step::isQuorumMet()`; no production caller otherwise — `StepCompletionEvaluator` works over `StepSnapshot` and never touches `Step`) and
`EnvelopeContextView::recipientStepIsQuorum()` (carried through `GetEnvelopeContextForRecipientHandler`,
`RecipientEnvelopeContextView`, `RecipientAuthContext`, its reader, `DeclineSignatureUseCase` and the
`$stepIsQuorum` parameter of `SigningSession`'s decline) serve the two refusals removed here; each carrier goes with them unless the predicate reuses it.

### 3.4 Release at a step's close

When a step closes by its deadline (TASK-049's command, before the expiry), every blocking member of it neither
admitted nor closed is **`RELEASED`** with `released_by: STEP_DEADLINE`; close-now releases every member still
open with `released_by: SENDER_CLOSED` (§3.5). The `release_reason` is TASK-048's, from the facts recorded at the release and by the same first match (ADR-0073 §2.8; a delivery fact observed later never rewrites it) — nothing here chooses a reason, so the veto rule reads `release_reason` alone
and never depends on what released the member. An ending that the deadline causes releases the members outside
the closing step `released_by: ENVELOPE_CLOSED`, as any ending does. Every release takes the member's row lock
before reading the opening columns (TASK-048 §3.6), so an opening racing a step's deadline is either recorded
before the release or refused. `RecipientReleased` (TASK-048) now also triggers Session's revocation of that
member's sessions, asynchronously — new here: until now the only revocation (`OnEnvelopeVoided`) is
envelope-wide; an informational member passes the gate again to read. Reads follow the role, never
`release_reason` or `released_by` (close-now releases a viewer who never opened `RELEASED` · `NOT_REQUIRED` · `SENDER_CLOSED`,
and they still read).

### 3.5 Close now

A sender route closes an envelope whose agreement is secured, whatever is pending: under the root lock, pending members are released with `released_by: SENDER_CLOSED` and the envelope closes `AGREED`, as its own fact, `EnvelopeClosedBySender`
(the sender as `ended_by`, no `end_cause`), excluded from ADR-0064 §2.4's webhook catalog: the end reaches integrators as `envelope.completed` with `outcome: AGREED` (maintainer, 2026-09-28). Refused by name when the agreement is not secured or the envelope is
closed.

### 3.6 The sweep reaches step deadlines

TASK-049's funnel widens to tenants with a due step deadline, and its per-envelope command's slot for closing due
steps is filled here, before it evaluates the expiry.

### 3.7 Claims, read side, notices

A claim is refused once the envelope is closed or the slot's step deadline has passed. The step view publishes its
policy, veto and deadline; the read side and `EnvelopeCompleted` publish declined and released recipients with
ids and enums (`release_reason`, `released_by`). Notices never tell a decliner or a released member the envelope was signed. Informational recipients are told their copy is ready, with a newly minted link (the invitation's lives seven days): with `outcome: AGREED`, every informational member, whether or not their step activated; with `NOT_AGREED`, only those whose step activated; and only when a sealed document exists — someone engaged — so an envelope voided before anyone engaged announces nothing (ADR-0073 §2.15). The notice's purpose — today `NotificationPurpose::ENVELOPE_COMPLETED`, classified as carrying no means to act — is reclassified, or a purpose of its own is added, in every exhaustive predicate of that enum.

## 4. Key decisions (maintainer, 2026-09-24/25)

- **D1** — Per step: `ALL` or `AT_LEAST n` (`n ≥ 1`); the waybill's consignees are `AT_LEAST 1`.
- **D2** — A veto switch, off by default; with veto, a member never reached makes the step not agreed.
- **D3** — Informational members never hold a step; they receive and may read the sealed copy.
- **D4** — One deadline per step from activation, at least 24 hours; expiry closes a step exactly as a deadline does.
- **D5** — `RELEASED`, not `SKIPPED`; each reason names the recorded fact it rests on; "delivered" never asserted.
- **D6** — Specific ending causes, a veto attributed like a decline.
- **D7** — Close-now is the sender's decision whatever is pending.
- **D8** — A member whose `signs_via` is delegated (today `MACHINE_KEY`: the integrator signs for them) who never acts is `INTEGRATOR_NO_ACT`
  and counts as reached; a delegated decline stays deferred.
- **D9** — `DELEGATED` and `SKIPPED` have no writer: a step holding either fails closed rather than taking an
  invented outcome (maintainer, 2026-09-25).
- **D10** — One cause per ending, first match, facts before clocks; `n` lives in `min_signatures` (maintainer,
  2026-09-25).
- **D11** — `DELIVERY_FAILED` judges invitation failures only; an informational role cannot commit (maintainer,
  2026-09-25).
- **D12** — Unanimity has one encoding, `ALL`; `AT_LEAST n` with `n` equal to the counting members is refused at
  `send()` (maintainer, 2026-09-28).
- **D13** — A non-last `AT_LEAST` step without a deadline is accepted and waits for every member; the API
  documentation and the handoffs warn, nothing refuses it (maintainer, 2026-09-28). So is a veto step without a
  deadline, which resolves only at expiry (maintainer, 2026-09-28).
- **D14** — In a veto step, a member invited whose link expired (`LINK_EXPIRED`, a reason of its own) was reached: silence past the link's life is no objection; only `NOT_REACHED`, `DELIVERY_FAILED` and `UNCLAIMED` make the step fail as not reached (maintainer, 2026-09-28).

## 5. Verification

- The delivery bar, cases (a)–(j), with `app_now()` pinned.
- **The scenario catalog** (`EndingScenarioCatalog`) stays green with the aggregate calling the rules, and each of its stories that has a route by then also runs over HTTP as this bar.
- **Same facts, same outcome** (ADR-0073 §2.4): for every policy × veto × member outcome × role × reachability
  combination, closing the step by its deadline and by expiry give the same outcome; drop a combination from the
  census and it fails naming it; add a special path for expiry and it fails.
  Among them the simplest: an `ALL` step with one signature and one silent member ends `NOT_AGREED` whether a step
  deadline or expiry closes it.
- **The migrated `SENT` rows**: a row whose step waits only on a `VIEWER` is moved on by TASK-048's post-deploy
  command, with this task's predicate.
- **An opening racing a step's deadline** (two processes): either the opening is recorded and the reason is `OPENED_NO_ACT`, or it is not recorded and — the member being blocking — the gate refuses and no credential is minted. A released informational member still passes.
- **Informational commit**: a `VIEWER`'s commit is refused by name, and a step it sits in does not wait for it.
- **The copy-ready notice**: on an agreed envelope closed by close-now with a later `VIEWER` step never activated, that viewer receives the notice with a working link and reads; on an envelope ended by a decline in step 1, a `VIEWER` of a step never activated receives nothing, and one of an activated step receives the notice; an envelope voided before anyone engaged sends no notice at all; every link is minted at `COMPLETED`, never the invitation's.
- **Admitted counts**: a signature admitted but not landed while the others decline keeps the minimum reachable.
- **The waiting `AT_LEAST` step, as documented**: a non-last `AT_LEAST 1` step with no deadline, one member signs and another stays silent → the next step never activates, and at expiry `NOT_AGREED` · `EXPIRED`; the published step description states it.
- **One encoding for unanimity**: `AT_LEAST n` with `n` equal to the counting members is refused at `send()`, with and without veto, naming `ALL`; `n` one below is accepted.
- **Fixtures that disagree**: an informational member pending while the minimum is met (never holds); mixed roles,
  no blocking member and each refused role (refused at `send()`).
- **Two processes**: a commit admitted just before the deadline command counts and is not released; the reverse
  order refuses the commit.
- **Two columns, never one**: the same member released by `STEP_DEADLINE`, by `SENDER_CLOSED` and by `ENVELOPE_CLOSED` carries the same `release_reason` each time; a veto step's `MEMBER_NOT_REACHED` follows `release_reason` alone.
- **Closed leg while open**: case (d) with the outcome removed from `RecipientAuthContext` fails.
- **Contract census**: the retired `ProblemCode`, `RELEASED`, `release_reason`, `released_by` and the causes appear in the published
  OpenAPI spec exactly as emitted. The event members (the roster's policy, `EnvelopeCompleted`'s declined and
  released recipients, `RecipientReleased`, `EnvelopeClosedBySender`) are pinned by serialization tests: no event
  spec is published here.
- **Fail closed**: a step holding a `DELEGATED` or a `SKIPPED` member makes the predicate fail, naming it.
- **Cause precedence**: a veto step at its deadline with a member unreached and the minimum out of reach ends
  `MEMBER_NOT_REACHED`; the same step closed by expiry ends the same.

## 6. Open follow-ups (track, don't solve here)

- Advancing at the minimum, freezing and operator powers, mixed steps, per-recipient veto, weighted votes,
  agreements, a per-document or delegated decline, extending a step's deadline — ADR-0073 §2.18.
- Building `IN_PERSON_HOST` and `CERTIFIED_DELIVERY`; delivery receipts; [`BL-306`](../BACKLOG.md),
  [`BL-308`](../BACKLOG.md), [`BL-309`](../BACKLOG.md); `DELEGATED` in the closed-leg answer ([`BL-183`](../BACKLOG.md)).
- **Filed by the close (2026-09-29), each with its row:** the envelope-first answers as a superseding record, ADR-0074 with TASK-051 ([`BL-328`](../BACKLOG.md)) · `AddStepRequest::ordinal` has no upper bound and answers 500 past the INT column ([`BL-333`](../BACKLOG.md)) · the `DELEGATED`/`SKIPPED` log-once of ADR-0073 §2.6, which TASK-049's sweep does not do ([`BL-334`](../BACKLOG.md)) · the delegated member `EnvelopeBuilder` cannot author, one catalog story excluded by name ([`BL-337`](../BACKLOG.md)) · `StepCompleted` recorded before its `RecipientReleased` events, pinned as recorded and not required ([`BL-338`](../BACKLOG.md)) · the veto end causes in the official handoffs ([`BL-341`](../BACKLOG.md)) · invitation failures and resends with no stored instant, the Q1 residual ([`BL-343`](../BACKLOG.md)).
- **Closed by this task, with the row that recorded each:** [`BL-283`](../BACKLOG.md) (a decline in a quorum step, refused by name), [`BL-355`](../BACKLOG.md) (`refusalsAtSend()` not wired), [`BL-231`](../BACKLOG.md) (the completion notice's missing slot guard); and, filed and closed in the same close, [`BL-329`](../BACKLOG.md), [`BL-330`](../BACKLOG.md), [`BL-331`](../BACKLOG.md), [`BL-332`](../BACKLOG.md), [`BL-335`](../BACKLOG.md), [`BL-336`](../BACKLOG.md), [`BL-339`](../BACKLOG.md) (folded into `BL-343`) and [`BL-340`](../BACKLOG.md). [`BL-202`](../BACKLOG.md) stays open: its expiry half closed with TASK-049, and `SEALING`, `CORRECTING`, `ROUTING_FAILED` and `SEALING_FAILED` still have no writer.
- **Unproven at close, each with its row** (§7 states each): the two-process race of an opening against a step deadline ([`BL-344`](../BACKLOG.md)) · the two-process race of a commit against it ([`BL-345`](../BACKLOG.md)) · the `SENT` rows migrated onto this predicate ([`BL-346`](../BACKLOG.md)) · the waiting `AT_LEAST` step's published description ([`BL-347`](../BACKLOG.md)) · the same-facts comparison of a deadline and an expiry at the HTTP tier ([`BL-348`](../BACKLOG.md)) · close-now with a never-activated `VIEWER` over HTTP ([`BL-349`](../BACKLOG.md)). The admitted-counts property: [`BL-350`](../BACKLOG.md).


## 7. Deviations & honest notes

*(Written at the close, 2026-09-29. The coordinator's note on a decliner's reads, recorded ahead of the close, follows at the end.)*

### Scope

Everything in the diff belongs to the task. Additions the task text did not name, each in service of a listed bar:
- `StepRedeclaredException` (409 `CONFLICT`) for re-adding an ordinal with a different policy: `addStep()` was idempotent by ordinal and would have silently discarded a different declaration (`a3a524b2`).
- `envelope_outcome` (`AGREED | NOT_AGREED | null`) on `GET /signing/session/auth` and on the read model `GET /signing/session` (`21dc9a4a`, `901fd813`), from maintainer decisions below.
- `RecipientEnvelopeContextView::stepHoldsTheRecipientBack()`, `publishedOutcome()` and `Session\Application\Service\RevocationSparesReaders`, shared by the per-release and the void revocation (`70593ec2`, `21dc9a4a`, `480faab9`).
- Upper bounds on `deadline_hours` (`a3a524b2`) and `min_signatures` (`b22dd37e`), after the security audit found the latter bounded below only.
- A `SEALED_COPY_READY` notification purpose of its own (the task allowed reclassifying `ENVELOPE_COMPLETED` or adding one), `c8e404c4`.
- Fixtures that used `CERTIFIED_DELIVERY` moved to `VIEWER` or an `AT_LEAST 1` step, since the role is `NOT_BUILT` and the predicate refuses to judge it (`1cc5ef0e`).
- `docs/LOAD-BEARING.md` section 1.21, asked for by §3.2 (`1cc5ef0e`); its "until an aggregate-tier clock exists" caveat was replaced by naming `EnvelopeEndingStoriesTest` (`d618c20b`).
- The second session's parts: close-now as a command and a route (`6717d021`, `859b36ce`, `dceeaeb7`, frozen payload bytes `da3d3071`, over HTTP `664dffa5`); the late-opening fix (`fb875674`); the synchronous read cut (`9d4531ae`); the `ENVELOPE_NO_LONGER_LIVE` reword (`70a0e89d`); the expiry same-facts census over every step combination reachable without a deadline (`07316515`).

### Decisions made during implementation

Maintainer decisions of 2026-09-29 unless stated, with the commit that realized each.

| # | Decision | Realized in |
|---|---|---|
| 1 | **Revocation spares a member whose gate still passes**, per release. Revocation exists to stop acting; revoking a reader only made the reopen answer `REVOKED` and renewal refuse. The skip asks the same gate predicate the readers use, never a role list; an unsent envelope keeps nobody's session and a context that no longer resolves revokes. | `480faab9` |
| 2 | **The same sparing on a void**: `RevokeEnvelopeSessionsUseCase` skips members whose gate still passes, through the shared `RevocationSparesReaders`. Security-audit warning 4 is this decision, not a defect. | `21dc9a4a` |
| 3 | **`envelope_outcome` on `/auth` and on the read model**: key always present, `null` until `closed_at` even when agreement is secured earlier. One method feeds both. | `21dc9a4a`, `901fd813` |
| 4 | **Outcome precedence on `/auth`**: `outcome` names this participation and a `REVOKED` session gives way to the envelope's name for a closed leg (`SessionStatus::outcomeAtTheGate()`), so a member released from an `AGREED` envelope no longer reads "cancelled". `POST /signing/session`'s `status` still carries the session's own `REVOKED` (legacy rows). | `21dc9a4a` |
| 5 | **`SESSION_CLOSED` changes in prose only**: ADR-0067's guard order stays; the published wording says the leg was released. The envelope-first reorder was decided in principle and deferred to ADR-0074 and TASK-051 ([`BL-328`](../BACKLOG.md)). | `aca35852` |
| 6 | **Two refusals at a step deadline.** Recipient side: `ActRefusal::STEP_DEADLINE_PASSED` maps to the existing `LEG_CLOSED` (no new signer code; a census over `ActRefusal::cases()` fails naming any member left unpublished). Sender side (Q2): void and close-now are refused with 409 `STEP_DEADLINE_PASSED` while an open step is past its deadline and the sweep has not run, ADR-0073 §2.12's rule extended; `ENVELOPE_EXPIRED` is named when both are due. ADR-0074 §2.5 supersedes the recipient mapping with two arms (`ENVELOPE_NO_LONGER_LIVE` where the deadline ends the envelope, else `LEG_CLOSED`), in TASK-051. | recipient `eb686c5f`; sender `5b5212e7` |
| 7 | **Q1: a clock's releases are judged at the clock's instant, not the sweep's**, for the step deadline and for `expires_at` alike, with no special path: `EnvelopeEndingEvaluator` passes `deadline_at` or `expires_at` as the instant `ReleaseReasons` judges. Pinned by a sweep that runs late while a link expires in between. Residual: the delivery-failure flag has no instant and the invitation instant is the latest, so a failure or resend recorded in the gap still counts ([`BL-343`](../BACKLOG.md)). | `5b5212e7` |
| 8 | **Q5: `deadline_at` is stored on the step at activation** (ADR-0073 §2.13), by rewriting the unpushed migration `Version20260929102747`; the CHECK `step_deadline_at_chk` holds it equal to `activated_at + deadline_hours`. The funnel migration is `Version20260929124418`, generated and not hand-named. | `3be2c390` |
| 9 | **`envelope_outcome` is visible before the gate on `/auth`**, accepted (security-audit warning 2): link holder is email holder, TASK-040 already emails `NOT_AGREED`, and `outcome` is already pre-gate. Recorded in ADR-0073 §2.15 ([`BL-330`](../BACKLOG.md)). | no code change |
| 10 | **A released or declined member's held credential is cut synchronously on the bytes** by the same gate predicate (security-audit warning 3); a decliner keeps reading `status: DECLINED` and gets no bytes (the coordinator's note below). | `9d4531ae` |
| 11 | **No full suite and no Infection per session** (package rule): one full suite and Infection over the joined package. | run at the join, pending |
| 12 | **Bar (f), an observed answer and not a decision**: after the veto, an act on a released member's opened session answers 409 `SESSION_CLOSED`, not `ENVELOPE_NO_LONGER_LIVE`, asserted as observed; this is the timing-dependent order decision 5 leaves for TASK-051. | `0e499567` |
| 13 | **The opening's lock timeout keeps the gate's earlier read** and logs at `warning` (Q4); a credential minted for a leg released in the wait is retired by the release's revocation and cut by the read and act guards. Answering 503 was rejected because the access-gate route commits its pass first. | `fb875674` |

Other departures, from the plans and commit bodies:
- **The predicate is named `isExpressibleByTheAggregate()`** (the catalog side called it `isWithoutClocksOrPolicyFlags()`, TASK-049's `isWithoutStepPolicyFlags()`): it excludes delegated members, roles not built and a life that is not whole days, and close-now stories play too. 34 of 35 catalog stories play; the one left cannot be authored by the builder ([`BL-337`](../BACKLOG.md)). `d618c20b`.
- **Event order is pinned as recorded, not as required**: `StepCompleted` before the step's `RecipientReleased` events; ADR-0073 states none between them ([`BL-338`](../BACKLOG.md)). `df31fd71`.
- **The funnel is a `UNION` of two branches, not `OR EXISTS`**, each on its own partial index (`step_due_deadline_idx`); `inScope()` asks the same predicate per tenant, and the step branch keeps the envelope's `closed_at IS NULL` because a voided envelope's deadline step stays open for ever. Grants and the `step_clock_sweep_visible` policy `TO f5sign_envelope_clock_sweep`. `3be2c390`.
- **No domain change for the deadline core**: `EnvelopeEndingEvaluator::clock()` already closed a due step; the core is the merge of the two step snapshots, `Step::policy()` in `snapshot()` (`b4fce49f`), the funnel and the stored instant.
- **Every release takes the member's row lock before reading the opening columns** was already met by TASK-049's `ApplyEnvelopeClocksUseCase`; the late opening that raced it is `fb875674`.
- **The decline retirement was ported by hand** from the patch rather than applied: the two refusals, the `ProblemCode` member, the `#[OA]` strings and the `recipientStepIsQuorum` carrier are gone (`8f42995d`), and `Step::isQuorumStep()` / `isQuorumMet()` went with their last caller (`48cf24ce`).
- **The migration asserts sent envelopes only** for `IN_PERSON_HOST` / `CERTIFIED_DELIVERY` (`sent_at IS NOT NULL AND completed_at IS NULL`); a closed-but-not-completed envelope is still asserted on. The maintainer confirmed no data violates either assertion. It writes no rows; the veto default is dropped at once. `a3a524b2`.
- **`Version20260929102747` was edited after generation** (for Q5), under repo rule 2's carve-out for a local, unpushed migration; **confirm it is still unpushed before the merge.** (⛑ The package merged into `develop` on 2026-09-30 at `e6a0af5e`; the migration is published from there, so repo rule 2's carve-out no longer applies to its SQL.)
- **Bar (f) is driven with `SEQUENTIAL_PADES`**, so every signature is a real revision and the ending is sealed through eu-dss, on a fresh tenant per run because the event log is append-only; sabotage-checked three ways. `0e499567`.
- **Lane incidents, nothing published**: a lane database migrated while the migration was still empty (re-run to recover); a lane rebuilt after the join because the sweep role is created by infra; TASK-049's test-database column default dropped by hand. None edited published SQL.
- **A reactor-wiring fact found by sabotage**: moving the void reactor's bus attribute stays green because `_instanceof` also tags every `MessengerEventSubscriber` on `event.bus`; the test docblock that claimed otherwise was corrected ([`BL-340`](../BACKLOG.md)).

### Decisions that needed an ADR

- [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md) is the record and stays `Accepted (enforcement partial)`; it was amended in place at the close, on 2026-09-29 (§2.4, §2.8, §2.12, §2.13, §2.15, §5, §6), because it was unmerged at the time (the package reached `develop` on 2026-09-30 at `e6a0af5e`). What this task made true is in its Status, §5 and §6. Which of its sections move to a full `Accepted` is the maintainer's call and was proposed, not applied.
- ADR-0066 §2.3 (from `closed_at` the ceremony routes do not ask the step) and ADR-0064 §2.4 (the census) carry amendments recorded in the same close.
- ADR-0074 (Accepted 2026-09-29, `feat/envelope-answers-first`) supersedes ADR-0067 §2.3/§7.3 and amends this task's recipient mapping at a step deadline; it belongs to TASK-051, not to this task.

### Declared and unproven properties

- **Opening racing a step's deadline, and a commit racing it (two processes)**: not built. `tests/F5Sign/Envelope/Integration/EnvelopeRaceActs.php` has no `clocks` act and `EnvelopeRootLockRaceTest` has no deadline case. What stands in for them: the opening refuses a closed leg under the recipient row's lock (`fb875674`, `RecipientOpeningWriteTest`, `GateRuleParityTest`), and the clock command locks the root and then every recipient row (TASK-049). The lock order is argued and single-process-tested, not raced. Opening: [`BL-344`](../BACKLOG.md); commit: [`BL-345`](../BACKLOG.md).
- **The `SENT` rows migrated onto this predicate** (a row waiting only on a `VIEWER` moved on by TASK-048's post-deploy command): `ReconcileEndingsCommandTest` predates `1cc5ef0e` and was not re-run against it as its own bar. Row: [`BL-346`](../BACKLOG.md).
- **The waiting `AT_LEAST` step's published description** (a non-last `AT_LEAST 1` step with no deadline, ending `NOT_AGREED` · `EXPIRED`): the ending is pinned over HTTP by `StepWithoutDeadlineExpiryHttpTest` (on the package branch, `ed7abad9`) and at the aggregate by TASK-049's stories; the step route's `#[OA]` prose that states it is asserted by no test. Row: [`BL-347`](../BACKLOG.md).
- **Admitted counts** (a signature admitted but not landed keeps the minimum reachable): pinned at the pure evaluator tier only. Row: [`BL-350`](../BACKLOG.md).
- **The same-facts comparison at the HTTP tier**: the pure census (`StepCompletionEvaluatorTest`), the aggregate stories, `EnvelopeExpirySameOutcomeTest` and `StepDeadlineGapTest` hold it; no HTTP case compares a deadline with an expiry on the same facts. Row: [`BL-348`](../BACKLOG.md).
- **Close-now for a `VIEWER` step never activated, end to end over HTTP**: the notice and the reads are pinned at their tiers (`NotifyCompletedEnvelopeRecipientsUseCaseTest`, `RecipientReadRulesTest`, `WhatEachRecipientReadsAfterTheCloseHttpTest`); `CloseEnvelopeNowHttpTest` releases the pending members of a secured `AT_LEAST` step but not that case. Row: [`BL-349`](../BACKLOG.md).
- **Migrations**: the assertions of `Version20260929102747` cannot run in the lane; `StepPolicyPersistenceTest` pins the CHECKs by name, and only a production run proves the assertions. `down()` of both migrations is symmetric by reading and was never executed by a gate.
- **A running worker consumes the `envelope_clocks` schedule** and so reaches step deadlines: inherited from TASK-049, checked at the package's stack validation.
- **Not verified by the security audit**: `ApiExceptionListener`'s mapping of the new `ActRefusal` cases to a stable problem body; `EnvelopeVoided` and `EnvelopeRosterDeclared` payloads staying pseudonymous; `OnRecipientReleased` retry behaviour (a redelivery revokes once, pinned in `RevokeRecipientSessionUseCaseTest`; the listener mapping is not).
- **Covered-MSI, the full suite and `composer audit`** were not run by this task.

### Debt left behind, and where it lives now

- The rows filed and closed by this close are listed in §6, under *Filed by the close* and *Closed by this task*; the open ones are [`BL-328`](../BACKLOG.md), [`BL-333`](../BACKLOG.md), [`BL-334`](../BACKLOG.md), [`BL-337`](../BACKLOG.md), [`BL-338`](../BACKLOG.md), [`BL-341`](../BACKLOG.md) and [`BL-343`](../BACKLOG.md).
- The unproven properties above are recorded as [`BL-344`](../BACKLOG.md) to [`BL-350`](../BACKLOG.md), which §6 lists.
- The frontend handoffs for this task are written by another session and are not part of this close.

### Coordinator's note (2026-09-29, recorded ahead of the close)

- **A decliner on an open envelope reads their state and no bytes** (coordinator, 2026-09-29, recorded ahead of
  the close). Once the synchronous read cut landed, `GET /api/v1/signing/session` still answers 200 `status: DECLINED`
  (published, pinned by `RecipientDeclineHttpTest`) while `GET /api/v1/signing/session/documents/{id}` refuses the
  bytes, because a decliner's gate is shut (ADR-0073 §2.3, §2.15). The download route's *"the two routes cannot
  disagree"* guarantee now excepts `status: DECLINED`. Refusing decliners on the read model with `LEG_CLOSED`
  instead was weighed and refused: it would retire a published status.


### Found at the package join (2026-09-29)

- **A real defect: invitation instants were stored in whole seconds.** The full suite on the joined package
  failed case (j) deterministically: B's re-sent invitation and C's original read back as the same instant.
  `DbalEnvelopeRepository` wrote `invitation_sent_at` and `invitation_failed_at` through DBAL's
  `datetime_immutable`, which floors to the second. The column is `timestamptz`; the precision was lost only at
  the bind. That fed `Recipient::recordInvitationSent()`'s only-forward comparison a floored value, and every
  link's life (ADR-0073 §2.8) ran from an instant up to a second early. Both columns now go through the
  repository's `instant()`, as the ending instants already did.
  `RecipientInvitationInstantPersistenceTest` pins the microseconds and a same-second resend; with the old
  binding it reads back `.000000`.
  The census of every other whole-second write (the repo's authoring rule 5) found none order-sensitive in the
  same way. The boundaries that are consistent today but floored are [`BL-351`](../BACKLOG.md).
  `step.activated_at` and `step.deadline_at` must keep one binding because of `step_deadline_at_chk`, and a
  comment at the upsert says so.
- **Case (j) re-cut under Q1.** As first written, it separated B (`SENT_NO_RESPONSE`) from C (`LINK_EXPIRED`)
  inside one envelope by re-sending B and pinning the sweep between the two link lapses. Q1, which landed later,
  judges an expiry's releases at `expires_at`, not at the sweep's instant. Both consignees are invited after the
  send, so at `expires_at` their links are both valid or both lapsed, and splitting them in one envelope would
  need `expires_at` between two SENTs that can be under a second apart: a race. (j) is now a data provider over
  the envelope's life. With 7 days, both read `RELEASED` · `SENT_NO_RESPONSE` · `EXPIRY`; with 8 days, both read
  `RELEASED` · `LINK_EXPIRED` · `EXPIRY`. The delivery bar's "(`SENT_NO_RESPONSE` or `LINK_EXPIRED` by their link
  validity)" is met across the two, and the same-second precision the resend exercised is held by the persistence
  test above.
