# TASK-056 — What happens to an invitation comes back to Envelope as facts, and the sender can see them

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/delivery-facts`** (tip `94e41e04`, rebased on develop `5cc4da21`, which carries TASK-055), 2026-10-13 — not merged, not pushed. Full suite green on the `wt-backend` lane of this worktree (6488 tests, 75126 assertions at `9b1d16e5`, with lint, deptrac and PHPStan clean; later commits are docs and tests, each re-run filtered). [ADR-0078](../adr/ADR-0078-delivery-outcomes-come-back-as-facts.md) stays **Proposed** until it is accepted together with TASK-058 and TASK-059. Left out, with homes in §7: the integrator-delivered outcome has no writer until TASK-031, and §2.6's one-factor-twice warning is TASK-031's. See §8 for the deviations. |
| **Type** | **Forward build with a contract change** across Envelope (write port, two events, columns, invitation state, release reasons, read model) and Notification (a per-destination reaction; the call sites that skip a recipient). |
| **Why** | A permanent refusal of one channel beside a channel that landed is recorded nowhere the sender sees. An invitation that was never sent leaves no trace: the use cases skip a recipient with no email with a bare `continue`, so the envelope looks healthy while a step is stuck. The release reason `NOT_REACHED` cannot tell a dormant step from a recipient nobody could reach. The sender's read model shows neither invitation timestamp. And one method stamps `invitation_failed_at` on a recipient whose leg is already closed. |
| **Decision record** | [ADR-0078](../adr/ADR-0078-delivery-outcomes-come-back-as-facts.md) §2.1–§2.6 — **Proposed** on 2026-10-09; it moves to Accepted (with TASK-058 and TASK-059 for §2.7 and the trail half of §2.5) when the §6 bars below are green, under the repo's authoring rule 7. It extends [ADR-0065](../adr/ADR-0065-recipient-delivery-is-its-own-dimension.md), amends [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) decision 7 again (two more commands back to Envelope) and keeps [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md)'s rule that nothing reads Notification. |
| **Builds on** | [ADR-0065](../adr/ADR-0065-recipient-delivery-is-its-own-dimension.md) (the per-destination trace) · [TASK-040](TASK-040-cancellation-notice.md) §6 (an informational notice never touches the recipient) · [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md) §2.8 (`invitation_sent_at` / `invitation_failed_at`, release reasons) · [`EnvelopeCommandInterface`](../../src/F5Sign/Envelope/Contract/Command/EnvelopeCommandInterface.php) · [`ReleaseReasons`](../../src/F5Sign/Envelope/Domain/Service/ReleaseReasons.php) |
| **Order** | May be built in parallel with [TASK-055](TASK-055-delivery-reliability.md) or after it: its transient failure kind is coordinated rather than awaited (§5 D5). [TASK-031](TASK-031-channel-selection-beyond-email.md) needs both; [TASK-059](TASK-059-the-trail-shows-how-each-invitation-travelled.md) needs this task. |

---

## 1. Why this task exists (measured on the tree, 2026-10-09)

- **One method, three writes.** `Envelope::markRecipientDeliveryFailed()` writes the destination's trace,
  `invitation_failed_at` and `RecipientDeliveryFailed` together. Its only caller path is
  `OnNotificationFailed` → `PropagateDeliveryFailureUseCase`, which runs when the **whole occasion** is
  undeliverable, so under any policy with a second channel a refusal beside a landed channel is lost.
  `one_refused_channel_does_not_flip_the_recipient_while_another_is_still_live`
  (`PropagateDeliveryFailureUseCaseTest`) protects the verdict from firing early, and that protection is
  right; its trace half is what changes.
- **A defect in the same method.** It calls `$recipient->recordInvitationFailed($now)` **before**
  `Recipient::markDeliveryFailed()`, which is where a closed leg is refused (`outcome->isTerminal()`). A
  recipient who has already signed can still be stamped `invitation_failed_at`. Its success sibling has
  no closed-leg check at all, and its docblock argues that reaching a signer is harmless; a failure on a
  closed leg claims we never reached someone who demonstrably acted.
- **"Not invited" is not a fact.** `NotifyActivatedStepRecipientsUseCase`, `NotifyCorrectedRecipientUseCase`
  and `NotifyResentInvitationRecipientUseCase` skip `email === null` and write nothing.
  `ReleaseReasons` answers `NOT_REACHED` for `!$stepActivated || invitationSentAt === null`.
- **The success path is mute on purpose.** `Envelope::markRecipientDeliverySent()` documents that it
  "records no domain event, deliberately", and adds "if Evidence & Audit later wants *when did we reach
  them*, this is where the fact would be recorded". ADR-0078 is that decision.
- **The sender sees little.** `EnvelopeJsonPresenter` publishes `release_reason`, `released_by` and the
  `delivery` map, and no invitation timestamp or state (`RecipientView` already carries the two
  timestamps).

## 2. What already exists (reuse, do not rebuild)

- **The trace is the right store.** `RecipientDeliveryTrace` is per destination, with staleness and
  convergence inside it; `Recipient::markDeliveryFailed()` returns whether the trace changed, and
  `correctContact()` clears the corrected destination. A `FAILED` destination is only ever a permanent
  refusal today.
- **`NotificationPurpose::carriesMeansToAct()` and `isInvitation()`** already separate the three families
  (means to act · invitation · informational), each an exhaustive `match`.
- **The occasion's instant is shared.** Every delivery of an occasion carries the same `occurredAt` on
  `DeliveryFailed` (`OnDeliveryRequested` passes the occasion's time as `issuedAt`), which is what makes
  the existing path idempotent and what a per-destination path must keep.
- **`DeliveryFailed` has no consumer today**: no handler under `Notification/Infrastructure/Messenger`
  names it. The new reaction is a reactor plus its paired Messenger adapter (`OnDeliveryRequested` /
  `OnDeliveryRequestedHandler` is the shape; do not abstract the pair, `docs/LOAD-BEARING.md`).
- **`EnvelopeCommandInterface` has seven implementers**: `EnvelopeCommandAdapter` and six test doubles
  (`RecordingEnvelopeCommand` and five anonymous classes under `tests/F5Sign/`). Enumerate with
  `rg -n 'implements EnvelopeCommandInterface' src tests`; every new method lands in all of them.
- **The trail folds the whole stream** ([ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md)
  §2.2), requires a label for every release reason and every event type
  (`TypstTrailRendererTest`, the label census), and falls back to the raw code if one is missing.
- **`release_reason` has no value CHECK** (`Version20260928131928` pairs it with `released_by` and with
  `outcome = 'RELEASED'` only), so a new member needs no constraint; hydration is strict
  (`ReleaseReason::from`), so code deploys before data.
- **Veto steps consume `ReleaseReason::isUnreached()`** (`StepCompletionEvaluator`), and the published
  `#[OA\*]` text of `AddStepRequest` says a veto step's premise is "that everyone could object".

## 3. What gets built

**3.1 The trace-only path.** A new write-port method (`markRecipientDestinationRefused`) that moves only
the destination's trace and records `RecipientDestinationRefused`. A new reactor on `DeliveryFailed`
calls it for a delivery that failed **permanently** (TASK-055's kind), whose purpose
`carriesMeansToAct()`, and **only while the occasion is not itself undeliverable** (§5 D2).
`RecipientDeliveryFailed` and `invitation_failed_at` stay on the occasion path, unchanged in meaning.

**3.2 Invitation outcome facts.** Four outcomes, recorded when they happen: `SENT` (per delivery handed to
a provider, with its destination kind), `FAILED` (every channel failed), `NOT_SENT_NO_REACHABLE_CHANNEL`,
`DELIVERED_BY_INTEGRATOR`. `SENT` and `FAILED` extend the two existing methods; the two unsent outcomes
are a new method, `recordInvitationNotSent`, called by the use cases that today `continue` past a
recipient with no email. Delegated recipients and unclaimed slots stay silent: they are skipped by
design, not unreached. `DELIVERED_BY_INTEGRATOR` is built and tested here and emitted by
[TASK-031](TASK-031-channel-selection-beyond-email.md), the first task with a `[]` list.

**3.3 Storage.** `envelope.recipient` gains `invitation_unsent_at TIMESTAMPTZ` and
`invitation_unsent_kind TEXT` (CHECK: both null or both set), written forward-only like their siblings.
**No backfill** (§5 D4).

**3.4 Envelope events.** `RecipientInvitationOutcomeRecorded` (`outcome`, `purpose`: `INVITATION` |
`RESEND`, nullable `channel`, nullable `destination_kind`, step ordinal, `occurred_at`; **no address**;
`channel` and `destination_kind` are set for `SENT` and null for the other outcomes) and
`RecipientDestinationRefused` (`channel`, `destination_kind`, `purpose`: `INVITATION` | `RESEND`, the
family of the refused delivery's purpose). **`channel` is the fact that matters** (owner, 2026-10-09):
one phone may refuse WhatsApp and take an SMS, and only the channel tells them apart.
`destination_kind` is kept beside it because it is the key of the recipient's `delivery` trace and
the trail resolves the masked contact from it without reading Notification's channel mapping
(ADR-0037). Both are **open sets** in the published contract, and their descriptions say so: a
channel (WhatsApp, a voice call) or a destination kind (a landline) added later is a new value, not a
new shape, and a consumer that treats either as closed breaks on it. Inside Envelope `channel` is an **opaque, non-empty
string** that Notification fills from its own channel value: Envelope records and publishes it and
never branches on it, as `RecipientDeliveryTrace` keeps Envelope off Notification's channel vocabulary.
`DeliverySent` and `DeliveryFailed` do not carry the channel; the reactions read it from the `Delivery`
they already load. **No `CODE` member** (owner, 2026-10-09): a code travels on
one channel (ADR-0049 §2.7), so its refusal always makes the occasion undeliverable, §5 D2 leaves it to the
occasion path, and that path already records it as `RecipientDeliveryFailed`. A member nothing can emit
does not go into a published contract; adding one later is additive. Both are published contracts: their
`EVENT_TYPE` and payload key sets are fixed here. Each is recorded only on a real change of the state it
reports, as `RecipientDeliveryFailed` already is.

⛑ **Dated note, 2026-10-13.** Closed by [TASK-031](TASK-031-channel-selection-beyond-email.md) §3.13: `channel`
is `InvitationChannel` (`EMAIL`, `SMS`), a closed set, on both events; the wire values did not change
([ADR-0078](../adr/ADR-0078-delivery-outcomes-come-back-as-facts.md) §2.2, amended). `destination_kind` is
unchanged. TASK-031 is also the writer of the integrator-delivered outcome this record left without one (§7).

**3.5 The invitation state.** One Domain function derives it from the recorded instants and the step's
activation: the latest of `invitation_sent_at`, `invitation_failed_at` and `invitation_unsent_at` wins,
ties resolved sent over failed over unsent (the order `invitationFailed` already uses:
`failedAt > sentAt`); no fact on an activated step is `NOT_YET`; a delegated recipient, an unclaimed
slot and a recipient whose step has not activated have **no state** (`null`): no invitation is due to them
now (owner, 2026-10-09, for the last). `NOT_YET` is kept for "due and not yet recorded", the signal a sender
watches; which of the three a `null` is reads from the fields beside it (`steps[].activated_at`, the
delegation, the claim). It reads **no** contact, capability or list. The presenter and
`ReleaseReasons` both call it.

**3.6 Release reasons** per §5 D1.

**3.7 The read model.** Flat beside `outcome_recorded_at`, as the access trace is (TASK-034 argued the
container out): `invitation_state`, `invitation_sent_at`, `invitation_failed_at`,
`invitation_unsent_at`, `invitation_unsent_kind`, with the `#[OA\*]` descriptions stating that
`SENT` means handed to the provider, not received (carrier receipts are [BL-390](../BACKLOG.md)). A
handoff for the dashboard and the integrators in `docs/frontend-handoff/`
(`TASK-054-integrator-signature-modes.md` is the shape). The one-factor-twice `warnings` entry of
ADR-0077 §2.9 is TASK-031's, not this task's.

**3.8 The defect.** Move the closed-leg check ahead of `recordInvitationFailed()`.

**3.9 Docs: a rule-1 sweep.** `rg -n 'NOT_REACHED|Records no domain event|invitation_failed_at|isUnreached' src tests docs config`
and convert one file at a time: `Envelope::markRecipientDeliverySent()`'s docblock (its reason for
silence is superseded), `ReleaseReason` and `ReleaseReasons`, `AddStepRequest`'s veto sentence,
`EndingNoticeFamily`'s `MEMBER_NOT_REACHED` note, `docs/ddd/envelope-domain-model.md`,
`docs/LIVE_SCHEMA.md` (two columns, and it also omits `invitations_revoked_at`), the trail template's
label groups, ADR-0078's Status / Enforced by / Realized in.

## 4. Scope

**In scope:** §3.1–§3.9. **Out of scope:** the per-recipient message history route
([TASK-058](TASK-058-recipient-notification-history.md), ADR-0078 §2.7); rendering the facts in the
trail ([TASK-059](TASK-059-the-trail-shows-how-each-invitation-travelled.md)); the channel declaration
and its selection ([TASK-031](TASK-031-channel-selection-beyond-email.md)); retries and the transient
failure ([TASK-055](TASK-055-delivery-reliability.md)); webhooks for the new facts
([ADR-0064](../adr/ADR-0064-outbound-integrator-webhooks.md) is unbuilt).

Concepts re-cut: `NOT_REACHED`, `isUnreached`, `markRecipientDeliverySent` (no longer silent), `markRecipientDeliveryFailed` (closed-leg check moves first; occasion path only), `invitation_failed_at`.

## 5. Key decisions

**D1 — The release reasons (ADR-0078 §2.4 leaves the members to this task; decide this first, it
shapes the state, the columns and the veto rule).** Two sub-questions.

*(i) A recipient the platform could not reach.* (a) Keep `NOT_REACHED` for both a dormant step and an
unreachable recipient. (b) A new member `NO_REACHABLE_CHANNEL` for the activated-but-unsent case, and
`NOT_REACHED` narrows to "step never activated" (stored rows keep their value and the trail's label for
it stays true for both). **Decided by the owner on 2026-10-09: (b)**, `isUnreached()` true, so a veto step treats it as today.

*(ii) A recipient whose list is `[]`, invited by the integrator.* Envelope does not know when, or
whether, the integrator minted the link, so `LINK_EXPIRED` and `SENT_NO_RESPONSE` (both derived from
`invitationSentAt + link lifetime`) cannot be computed for them. (a) Leave `NOT_REACHED`: false. (b)
Reuse `INTEGRATOR_NO_ACT`: that member means the signature was *delegated* and the integrator was
expected not to act, which this recipient is not. (c) A new member `INTEGRATOR_DELIVERED_NO_RESPONSE`.
(d) Ask Session when a credential was minted: a new Envelope-to-Session edge, and there may be no
credential at all. (e) Judge it on the one evidence the platform holds — whether the link was opened. **Decided by the
owner on 2026-10-09: (e).** A `[]` recipient who opened the link and did not act is already
`OPENED_NO_ACT` (reached), which the existing first-match order gives before any of this; one who never
opened it gets a new member `INTEGRATOR_DELIVERED_NOT_OPENED` with `isUnreached()` **true**: nothing
proves the integrator's message reached them, so on a veto step their silence is not agreement —
exactly as for a recipient the platform could not reach. Option (c)'s `false` was rejected because it
records "did not veto" for someone who may never have known. `LINK_EXPIRED` and `SENT_NO_RESPONSE`
remain exclusively platform-sent. The derivation uses the **state** of §3.5, not the mere presence of
an unsent fact: a recipient unsent at 10:00 and sent at 11:00 is `SENT_NO_RESPONSE`. First-match order:
after `OPENED_NO_ACT` and `UNCLAIMED`, before `NOT_REACHED`. A way for the integrator to declare that it
delivered the link is tracked as BL-400.

**D2 — The verdict must not depend on the trace having moved.** `markRecipientDeliveryFailed()` records
`RecipientDeliveryFailed` only if the trace changed. Once a second path writes the same trace, the
verdict can silently vanish when the per-destination reaction marked the last destination first.
Options: (1) the per-destination reaction skips when the occasion is already undeliverable, leaving the
occasion path to mark every failed destination (all deliveries of an occasion share one instant, so the
earlier marks are no-ops there); (2) give the verdict its own idempotency basis; (3) record it
unconditionally and de-duplicate in the log. **Decided (owner, 2026-10-09): (1).** It is monotone: statuses never
leave a terminal state, so a late-running reaction reaches the same answer.

**D3 — A re-invitation after a correction has no purpose of its own in Notification**
(`NotifyCorrectedRecipientUseCase` requests `RECIPIENT_INVITATION` under a correction-keyed cause).
(a) The event's `purpose` is `INVITATION` | `RESEND`, and the trail places a re-invitation by its
position after `RECIPIENT_CORRECTED` (it already does this for contact uses). (b) Carry a kind through
the Notification aggregate. **Decided (owner, 2026-10-09): (a)**: no Domain change in a supporting context. ADR-0078
§2.5 lists "re-invitation" as a purpose; this reads it as a position, not a value.

**D4 — No backfill, and what a row without facts means.** Decided (owner, 2026-10-09). An activated step with no recorded outcome is
`NOT_YET`: it covers an invitation in flight and every row written before this task, and the two cannot
be told apart. Backfilling `NOT_SENT` onto the second would assert "nobody could reach them" about
invitations queued right now (authoring rule 6: state what the row means in each envelope state). A
closed envelope keeps whatever release reason it was judged with; nothing is rewritten.

**D5 — Ordering with TASK-055.** The reaction of §3.1 filters on a delivery's failure being permanent.
If this task merges first, every `FAILED` is permanent and the filter is vacuous; TASK-055's AC-19 and AC-20 then
extend to this path when it merges.

**D6 — Given, not open:** informational notices never mark the trace (owner, 2026-10-09; TASK-040 §6 and
`a_refused_completion_notice_flips_nobody` stand); informational outcomes are TASK-058's to show.

## 6. Acceptance bars

Tiers per [`tests/README.md`](../../tests/README.md); worktree lane only
(`make -C ../f5sign-infra wt-backend src=$(pwd)`). <!-- OFFREPO: the ephemeral per-worktree lane is a target of the sibling repository f5sign-infra's Makefile; it mounts the given tree into its own containers and runs this repo's own test suites there, so it validates this tree rather than the main checkout. -->

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | `ANY` occasion, SMS refused permanently, email sent: the Envelope double receives the trace-only call for `MOBILE_PHONE` and not `markRecipientDeliveryFailed` | derived — ADR-0078 §2.1 | Application | call `markRecipientDeliveryFailed` from the reactor (inferred) |
| AC-2 | Same case through the real aggregate: `delivery` shows `MOBILE_PHONE` FAILED and `EMAIL_ADDRESS` SENT, `invitation_failed_at` is null, one `RecipientDestinationRefused` is in the log, no `RecipientDeliveryFailed` | derived — ADR-0078 §2.1 | Integration | route the refusal through the occasion path (inferred) |
| AC-3 | Both channels refused, reactions run in both orders, both reactions delivered twice: exactly one `RecipientDeliveryFailed`, `invitation_failed_at` set, both destinations FAILED, in both orders | derived — ADR-0078 §2.1 | Integration, real aggregate (two paths share one trace) | delete the skip-when-undeliverable rule |
| AC-4 | With both channels refused, the first destination's reaction run before the second failure records one `RecipientDestinationRefused`; run after it records none | derived — ADR-0078 §2.1 | Integration, real aggregate | delete the skip-when-undeliverable rule |
| AC-5 | Each delivery whose purpose does not `carriesMeansToAct()` makes zero calls on either path (members AC-5a…g) | derived — ADR-0078 §2.1 | Application | drop the `carriesMeansToAct()` filter (inferred) |
| AC-6 | `a_refused_completion_notice_flips_nobody` and `a_refused_ending_notice_records_no_failure_against_the_recipient` stay green unmodified | derived — ADR-0078 §2.1 | Application (existing tests) | — (inferred: they are the guard) |
| AC-7 | One permanent plus one transient failure yields exactly one trace-only call | derived — ADR-0079 §2.3 | Application (inferred) | drop the permanent-kind filter (inferred) |
| AC-8 | Each recipient whose leg is closed (members AC-8a…e) receiving `markRecipientDeliveryFailed(invitation: true)` keeps `invitation_failed_at` null and records no event | derived — ADR-0078 §2.2 | Unit, Envelope aggregate | restore the old order; this case reddens |
| AC-9 | A recipient with an open leg receiving `markRecipientDeliveryFailed(invitation: true)` is stamped `invitation_failed_at` | derived — ADR-0078 §2.2 | Unit, Envelope aggregate | refuse stamping on every leg (inferred) |
| AC-10 | The `invitation_failed_at` column of a closed-leg recipient stays null across a persistence round trip | derived — ADR-0078 §2.2 | Integration | restore the old order (inferred) |
| AC-11 | A `SENT` outcome redelivered leaves one `RecipientInvitationOutcomeRecorded` event | derived — ADR-0078 §2.2 | Integration, real adapter and log | drop the change-only recording (inferred) |
| AC-12 | Two destinations sent at different instants leave two events | derived — ADR-0078 §2.2 | Integration, real adapter and log | key the event on the outcome alone, not the destination (inferred) |
| AC-13 | Each unsent-or-failed outcome redelivered records once (members AC-13a…c) | derived — ADR-0078 §2.2 | Integration, real adapter and log | drop the change-only recording (inferred) |
| AC-14 | An older observation on a destination arriving after a newer one is not recorded | derived — ADR-0078 §2.2 | Integration, real adapter and log | accept any observation regardless of order (inferred) |
| AC-15 | Each new Envelope event has a closed payload key set and carries no address (members AC-15a…b) | derived — ADR-0078 §2.5 | Integration (inferred) | add an address key to the payload (inferred) |
| AC-33 | Each invitation-family outcome carries the purpose of its family (members AC-33a…b) | derived — ADR-0078 §2.5 | Integration, real adapter and log | record `INVITATION` for every outcome |
| AC-16 | The invitation state is the latest of the recorded instants; an activated step with no fact is `NOT_YET` | derived — ADR-0078 §2.2 | Unit, table over instants and activation | pick the earliest instant (inferred) |
| AC-17 | Ties resolve sent over failed over unsent | derived — ADR-0078 §2.2 | Unit, table | reorder the tie-break (inferred) |
| AC-18 | Each recipient no invitation is owed to by design has state `null` (members AC-18a…b) | derived — ADR-0078 §2.2 | Unit, table | give that recipient a state (inferred) |
| AC-34 | A recipient whose step has not activated has state `null` | derived — ADR-0078 §2.2 | Unit, table | answer `NOT_YET` for any recipient with no fact |
| AC-19 | Each recorded state survives a later change of contact (members AC-19a…b) | derived — ADR-0078 §2.2 | Unit, table | derive from `email === null`; AC-19a reddens |
| AC-20 | Each invitation-family use case records `recordInvitationNotSent(NO_REACHABLE_CHANNEL)` once for a recipient with no email (members AC-20a…c) | derived — ADR-0078 §2.2 | Application | restore the bare `continue` (inferred) |
| AC-21 | Each invitation-family use case makes no call for a delegated recipient with no email (members AC-21a…c) | derived — ADR-0078 §2.2 | Application | drop the delegated exemption (inferred) |
| AC-22 | Each invitation-family use case makes no call for an unclaimed slot with no email (members AC-22a…c) | derived — ADR-0078 §2.2 | Application | drop the unclaimed exemption (inferred) |
| AC-35 | Each informational use case that skips a recipient with no email makes no `recordInvitationNotSent` call (members AC-35a…b) | derived — rule 5 (the set the new call exempts) | Application | replace the bare `continue` with the call in all five sites |
| AC-23 | An activated-but-unsent recipient is released as `NO_REACHABLE_CHANNEL`; `NOT_REACHED` means the step never activated | derived — ADR-0078 §2.4 | Unit, `ReleaseReasonsTest` | answer `NOT_REACHED` for both (inferred) |
| AC-24 | A `[]`-list recipient who never opened the link is released as `INTEGRATOR_DELIVERED_NOT_OPENED`; one who opened and did not act stays `OPENED_NO_ACT` | derived — ADR-0078 §2.4 | Unit, `ReleaseReasonsTest` (inferred) | swap the two in the first-match (inferred) |
| AC-25 | A recipient unsent then sent is released as `SENT_NO_RESPONSE` (the state, not the mere presence of an unsent fact, decides) | derived — ADR-0078 §2.4 | Unit, `ReleaseReasonsTest` | swap the two new members' order in the first-match; this case reddens |
| AC-26 | `isUnreached()` is an exhaustive `match` and returns the classification listed in *Notes on AC-26* | derived — ADR-0078 §2.4 | Unit, `ReleaseReasonsTest` | add a member without an arm (inferred) |
| AC-27 | Each new unreached member on a veto step leaves the step not agreed (members AC-27a…b) | derived — ADR-0078 §2.4 | Unit, `ReleaseReasonsTest` | flip `isUnreached()` for the member (inferred) |
| AC-28 | The label census in `TypstTrailRendererTest` is green with the new release-reason members and both event types labelled | derived — ADR-0078 §2.5 | Unit, `TypstTrailRendererTest` | remove a label (inferred) |
| AC-29 | The presenter publishes a closed key set for the five new read-model fields | derived — ADR-0078 §2.6 | Unit, presenter | publish an extra or missing key (inferred) |
| AC-30 | The `#[OA\*]` strings match what is emitted | derived — ADR-0078 §2.6 | `/contract-check-backend` | edit a description to disagree with the emitted field (inferred) |
| AC-36 | A handoff in `docs/frontend-handoff/` names the five new read-model fields and the two new release reasons | derived — ADR-0078 §2.6 | `/contract-check-backend` (handoff present) | omit a field from the handoff |
| S-1 | Each platform-produced invitation state is shown over HTTP (members S-1a…c) | derived — ADR-0078 §2.6 | Acceptance | — |
| AC-31 | Each trail check holds on a stream carrying the new events (members AC-31a…b) | derived — ADR-0078 §2.5 | Application, assembler over `Factor5TrailSources` | leave a new event out of the registry (inferred) |
| AC-32 | A recipient row inserted in the pre-migration shape on an activated step hydrates and presents `NOT_YET` | derived — rule 6 | Integration | backfill `NOT_SENT` onto old rows (inferred) |

**Notes on AC-3 and AC-4**
- The hazard is the two paths sharing one trace, which is why the real aggregate is used.
- The refusal events differ by order and are asserted per order. The test must redden naming whether the verdict vanished or doubled.

**Notes on AC-5**
- Census over `NotificationPurpose::cases()` where `carriesMeansToAct()` is false, taken on 2026-10-09: AC-5a `ENVELOPE_COMPLETED`, AC-5b `ENVELOPE_ENDED_SENDER_CANCELLED`, AC-5c `ENVELOPE_ENDED_SENDER_CANCELLED_WITH_REASON`, AC-5d `ENVELOPE_ENDED_DECLINED`, AC-5e `ENVELOPE_ENDED_TIME_RAN_OUT`, AC-5f `ENVELOPE_ENDED_OUT_OF_REACH`, AC-5g `SEALED_COPY_READY`. The test iterates the predicate, so a purpose added later is classified by it rather than by this list.

**Notes on AC-7**
- Applies once TASK-055's failure kind exists.

**Notes on AC-8**
- Members, every outcome `RecipientOutcome::isTerminal()` answers true for on 2026-10-09: AC-8a `COMPLETED`, AC-8b `DECLINED`, AC-8c `DELEGATED`, AC-8d `SKIPPED`, AC-8e `RELEASED`. The test iterates the predicate, so the guard is pinned to "closed", not to "signed".

**Notes on AC-10**
- Run `/doctrine-guard` with the round trip.

**Notes on AC-33**
- AC-33a — an outcome of `RECIPIENT_INVITATION_RESENT` carries `purpose: RESEND`. AC-33b — the outcome of the re-invitation `NotifyCorrectedRecipientUseCase` requests carries `purpose: INVITATION`; the trail places it after `RECIPIENT_CORRECTED` by log position (§5 D3).

**Notes on AC-14**
- The older-observation fixture is asserted not recorded so the known gap is a decision and not an accident.

**Notes on AC-35**
- AC-35a — `NotifyEndedEnvelopeRecipientsUseCase`. AC-35b — `NotifyCompletedEnvelopeRecipientsUseCase`. With AC-20a…c they are the five sites that skip `email === null` today (`rg -l 'email === null' src/F5Sign/Notification/Application`, 2026-10-09); only the three invitation-family ones record (§5 D6).

**Notes on AC-13**
- AC-13a — A `FAILED` outcome records once. Sabotage: drop the change-only recording (inferred).
- AC-13b — A `NOT_SENT_NO_REACHABLE_CHANNEL` outcome records once. Sabotage: drop the change-only recording (inferred).
- AC-13c — A `DELIVERED_BY_INTEGRATOR` outcome records once. Sabotage: drop the change-only recording (inferred).

**Notes on AC-15**
- AC-15a — `RecipientInvitationOutcomeRecorded` payload key set is closed and carries no address. Sabotage: add an address key to the payload (inferred).
- AC-15b — `RecipientDestinationRefused` payload key set is closed and carries no address. Sabotage: add an address key to the payload (inferred).

**Notes on AC-18**
- AC-18a — A delegated recipient has state `null`. Sabotage: give delegated recipients a state (inferred).
- AC-18b — An unclaimed slot has state `null`. Sabotage: give unclaimed slots a state (inferred).

**Notes on AC-19**
- AC-19a — A recipient recorded `NOT_SENT` who now has an email keeps the recorded state. Sabotage: derive from `email === null`; this case reddens.
- AC-19b — A recipient recorded `SENT` whose email was since removed keeps the recorded state. Sabotage: derive from `email === null` (inferred: same sabotage).

**Notes on AC-20**
- AC-20a — `NotifyActivatedStepRecipientsUseCase`: email null makes one `recordInvitationNotSent(NO_REACHABLE_CHANNEL)`. Sabotage: restore the bare `continue` (inferred).
- AC-20b — `NotifyCorrectedRecipientUseCase`: email null makes one `recordInvitationNotSent(NO_REACHABLE_CHANNEL)`. Sabotage: restore the bare `continue` (inferred).
- AC-20c — `NotifyResentInvitationRecipientUseCase`: email null makes one `recordInvitationNotSent(NO_REACHABLE_CHANNEL)`. Sabotage: restore the bare `continue` (inferred).

**Notes on AC-21**
- AC-21a — `NotifyActivatedStepRecipientsUseCase`: email null and delegated makes no call. Sabotage: drop the delegated exemption (inferred).
- AC-21b — `NotifyCorrectedRecipientUseCase`: email null and delegated makes no call. Sabotage: drop the delegated exemption (inferred).
- AC-21c — `NotifyResentInvitationRecipientUseCase`: email null and delegated makes no call. Sabotage: drop the delegated exemption (inferred).

**Notes on AC-22**
- AC-22a — `NotifyActivatedStepRecipientsUseCase`: email null and unclaimed slot makes no call. Sabotage: drop the unclaimed exemption (inferred).
- AC-22b — `NotifyCorrectedRecipientUseCase`: email null and unclaimed slot makes no call. Sabotage: drop the unclaimed exemption (inferred).
- AC-22c — `NotifyResentInvitationRecipientUseCase`: email null and unclaimed slot makes no call. Sabotage: drop the unclaimed exemption (inferred).

**Notes on S-1**
- S-1a — An Acceptance flow shows `SENT` over HTTP. Sabotage: —.
- S-1b — An Acceptance flow shows `FAILED` over HTTP. Sabotage: —.
- S-1c — An Acceptance flow shows `NOT_SENT_NO_REACHABLE_CHANNEL` over HTTP. Sabotage: —.

**Notes on AC-26**
- The test asserts the exact classification, not only exhaustiveness. `isUnreached()` true: `DELIVERY_FAILED`, `UNCLAIMED`, `NOT_REACHED`, `NO_REACHABLE_CHANNEL`, `INTEGRATOR_DELIVERED_NOT_OPENED`. False: `NOT_REQUIRED`, `INTEGRATOR_NO_ACT`, `OPENED_NO_ACT`, `LINK_EXPIRED`, `SENT_NO_RESPONSE`. Census of `ReleaseReason` on 2026-10-09 plus the two members §5 D1 adds.

**Notes on AC-27**
- AC-27a — A veto step with an `INTEGRATOR_DELIVERED_NOT_OPENED` member is not agreed. Sabotage: flip `isUnreached()` for the member (inferred).
- AC-27b — A veto step with a `NO_REACHABLE_CHANNEL` member is not agreed. Sabotage: flip `isUnreached()` for the member (inferred).
- AC-27a was first drafted as "agrees on silence", the option §5 D1 (ii) rejected; corrected on 2026-10-09. Both members are `isUnreached()` true, so on a veto step neither one's silence is agreement.

**Notes on AC-30**
- The `invitation_state` description must say that `SENT` means handed to the provider, not received by the recipient (carrier receipts are BL-390). The frontend team ratifies the spec from these strings.

**Notes on AC-31**
- AC-31a — `EVERY_FACT_READABLE` passes on a stream carrying the new events. Sabotage: leave a new event out of the registry (inferred).
- AC-31b — The chain recompute passes on a stream carrying the new events. Sabotage: corrupt a new event's payload in the chain (inferred).
- The harness reaches the registry and the chain; it does not reach the rendered page, which is TASK-059's.

**Notes on AC-32**
- Run `/doctrine-guard`.

- Table-test scope of AC-16 to AC-19: sent / failed / unsent instants, activation, delegated, unclaimed.
- **Gates:** full suite, Infection covered-MSI, PHPStan, deptrac and lint green in the worktree lane.

## 7. Open follow-ups (track, don't solve here)

- **The history route** (TASK-058) and the dashboard work that shows it.
- **Webhooks** for the two new facts, as candidates for ADR-0064's published set when it is built ([BL-394](../BACKLOG.md)).
- **A refused contact remembered across envelopes** (TASK-031 §7): the trace is per envelope ([BL-393](../BACKLOG.md)).
- **Several channels on one contact share one trace entry** ([BL-407](../BACKLOG.md)). `delivery` keeps one state per destination
  kind (ADR-0065), so a WhatsApp refusal, an SMS that landed and a voice call on the same phone collapse
  into one state; the events keep each, through `channel`. The likely repair keys the trace by
  destination kind and channel. The same assumption carries §5 D2's verdict rule:
  it holds while no two deliveries of one occasion share a destination kind, true while EMAIL, SMS and
  LOG are the only channels. [TASK-031](TASK-031-channel-selection-beyond-email.md), or whichever task
  first adds a second channel to one destination kind (WhatsApp, a voice call), re-cuts both first.
- **An out-of-order older observation on one destination is not recorded** (AC-14); whether evidence
  needs it wants a real case ([BL-408](../BACKLOG.md)).
- **Stale docs found on the way**: `SignerAuthPolicy::OTP_SMS_CHALLENGE_TTL_SECONDS`' docblock still says
  "no SMS channel exists yet" (still open, [BL-396](../BACKLOG.md)); `docs/LIVE_SCHEMA.md` omitted `recipient.invitations_revoked_at` (fixed on this branch, 2026-10-09).
- **The integrator-delivered outcome and `INTEGRATOR_DELIVERED_NOT_OPENED` have no writer** until TASK-031's empty channel list ([BL-400](../BACKLOG.md)).
- **A flaky `EventRelayEpochResetTest` volume case under coverage** ([BL-406](../BACKLOG.md)); this branch touches no Foundation file.
- **Release reasons are still judged on the latest invitation instant, whatever the clock's `$at`** ([BL-343](../BACKLOG.md), restated: the snapshot now carries the instants, the judgement does not use them), and **the delivery-failure path still saves unconditionally** ([BL-395](../BACKLOG.md), its closed-leg half fixed here). A correction that supplies only a phone still spends one of three and mails nothing, though the miss is now recorded ([BL-227](../BACKLOG.md)).

## 8. Deviations & honest notes

### Scope
- None beyond the record. One `src/` change the record did not name came from a pin in slice 05: `DbalEnvelopeRepository::deliveryTraceToJson()` (see *Decisions*).

### Decisions made during implementation
- **D-1 — the invitation state function lives in `Envelope/Contract/Type`.** §3.5 asked for one Domain function that the presenter and `ReleaseReasons` both call, but `deptrac.yaml` forbids `EnvelopeUI` reaching `EnvelopeDomain`. One function both can call exists only in `Contract/Type` (precedent: `RecipientDeliveryTrace`). `InvitationState::of()` is that function; the owner's decision is unchanged.
- **D-2 — one verdict per occasion, carrying a destination list.** The verdict path (`PropagateDeliveryFailureUseCase`) reports once per occasion naming every failed destination, instead of one report per failed delivery; the per-destination reaction (`OnDeliveryFailed` to `PropagateDestinationRefusalUseCase`) marks the trace only. The verdict therefore does not depend on the trace having moved (§5 D2). A transient failure marks no destination on the trace-only path (slice 13, `9b1d16e5`; pinned by `one_permanent_and_one_transient_failure_make_exactly_one_trace_only_call`).
- **D-3 — `NOT_REACHED` means "no recorded fact that the platform reached them". Approved by the owner on 2026-10-09.** §5 D1(b) said it "narrows to step never activated"; that did not hold, because a step can be activated and still produce no recorded outcome (an invitation in flight, a report not yet back). `ReleaseReasons` therefore names `NOT_REACHED` for both, and the record's reading of it as a dormant-step reason was wrong. Prose that said `NOT_REACHED` covers an unreachable recipient was swept (slice 12); `NO_REACHABLE_CHANNEL` and `DELIVERY_FAILED` carry that meaning.
- **The owner's channel decision.** Both events (`RECIPIENT_INVITATION_OUTCOME_RECORDED`, `RECIPIENT_DESTINATION_REFUSED`) carry `channel` and `destination_kind`. Both are open sets, and Envelope treats `channel` as opaque: it stores and republishes it and never branches on a member, so a channel added in Notification needs no Envelope change.
- **`delivery_trace.observed_at` precision (slice 05).** The slice's redelivery pins showed the trace was stored with whole seconds (`DATE_ATOM`), so a redelivered `DeliverySent` recorded a second SENT outcome. The write side now stores microseconds (`Y-m-d H:i:s.uP`); both readers parse with `new DateTimeImmutable($string)` and accept either form; the published format is unchanged. **Residual:** rows stored before the fix hold whole seconds, so once per destination such a row may record one extra SENT or `RecipientDestinationRefused`, or a duplicate `RecipientDeliveryFailed`, on a redelivered report. No migration; doctrine-guard noted it as a warning, not a blocker.
- **AC-36 (the handoff exists) is proven by `/contract-check-backend` and `docs/frontend-handoff/TASK-056-dashboard-integrator-invitation-state.md`, not by a test.** The closing review accepted that.
- **Slice deviations** (plan.md § Deviations): slice 03 used `Recipient::rehydrate()` where the slice named `reconstitute()`, and the lane database first recorded the still-empty generated migration as applied (rolled back with `--down` and re-applied filled in); slice 04 rewrote the call sites with a reviewed script instead of the replicator, and `EnvelopeCredentialRetirementTest` classifies `markRecipientDestinationRefused` and `recordInvitationNotSent` as not retiring a credential (system observations with no sender gesture, confirmed against ADR-0060 §2.5); slice 13 was blocked until TASK-055 merged and ran after the rebase.
- **BL-395, BL-396, BL-227, BL-343 read for tense.** BL-395: the closed-leg half is fixed here, the unconditional save on that path stays open. BL-396: the LIVE_SCHEMA half is fixed, the `SignerAuthPolicy` docblock half stays open. BL-227: still open, its skip is now recorded rather than silent. BL-343: still open; the snapshot carries the instants, `ReleaseReasons::reasonFor()` still judges the latest regardless of `$at`.

### Decisions that needed an ADR
- [ADR-0078](../adr/ADR-0078-delivery-outcomes-come-back-as-facts.md) stays **Proposed** (owner, 2026-10-09: accepted together with TASK-058 and TASK-059). Its Status, *Enforced by* and *Realized in* already state what this task realized; the Accepted step is proposed to the owner and not applied here.

### Declared and unproven properties
- **Integrator-delivered outcome and `INTEGRATOR_DELIVERED_NOT_OPENED`**: built and tested at the domain and event level, but nothing produces them until TASK-031's empty channel list ([BL-400](../BACKLOG.md)).
- **`OpenApiSpecTest`** (the two-direction key closure and the enum audit) is an Acceptance test; the contract-check verdict was conditional on the final all-tier suite, which ended green at `9b1d16e5`.
- **`composer audit`** was not run (no network, no dependency added by the diff); the security audit reports it as unverified, not clean.
- **Row locks and cross-connection ordering** are out of reach of the single-connection Integration harness; the lock on the two new port methods is the same root lock as `markRecipientDeliveryFailed`, and no test separates locked from unlocked reads (the repo's authoring rule 4 names that harness limit).
- **Infection: the §6 "covered-MSI green" bar is NOT met as a whole-file figure; the owner accepted the justification below on
  2026-10-09.** Run filtered to the 32 `src/` files the branch touches (`--min-covered-msi=85 --min-msi=70`), on the worktree lane,
  2026-10-13, at the tip that carries the slice-15 tests: 2399 mutants, 1457 killed, 335 escaped, 329 not covered, 277 skipped,
  1 timed out; **MSI 68 %, covered-MSI 81 %**, under both thresholds. The filter is whole-FILE, so it measures all of `Envelope.php`,
  `Recipient.php`, `EnvelopeCommandAdapter` and `DbalEnvelopeRepository`, most of which this task does not touch. **On the lines this
  branch changed** (Infection's `file:line` intersected with `git diff -U0`): **0 escaped, 0 not covered, 0 timed out.** The 10 escapes
  the first run found there (2026-10-09: an exception message, a closed-envelope guard, a forward-only unsent instant, the `LOG` arm and
  the addressee check of the refusal reaction) are each killed by a test added for it, every one seen red under its hand-applied
  mutant. 17 changed-line mutants are *skipped*: code reached only by Integration tests, which exceed Infection's 20 s timeout, so this
  harness cannot measure them. No develop baseline was measured, by the owner's choice, so the record does not claim the branch
  left the whole-file score unchanged. The pre-existing escapes are tracked as [BL-409](../BACKLOG.md).

### Debt left behind, and where it lives now
- Refused contact remembered across envelopes: [BL-393](../BACKLOG.md). Webhook set: [BL-394](../BACKLOG.md). `markRecipientDeliveryFailed` unconditional save: [BL-395](../BACKLOG.md). `SignerAuthPolicy` docblock: [BL-396](../BACKLOG.md). Integrator-delivered writer: [BL-400](../BACKLOG.md).
- New from this close: flaky `EventRelayEpochResetTest` at volume under coverage, seen once in an Infection initial suite on 2026-10-13, passes alone ([BL-406](../BACKLOG.md)); several channels on one contact sharing one trace entry ([BL-407](../BACKLOG.md)); the out-of-order older observation ([BL-408](../BACKLOG.md)).
- The history route is TASK-058; ADR-0078 §2.7 and the trail half of §2.5 are TASK-058 and TASK-059.

### Delegated work
- Fifteen slices. By run.log: 01 to 08, 13 and 15 (critical) on opus; 09 to 12 (standard) and 14 (critical, prose and citations) on sonnet. Review rounds per slice: 01 1, 02 1, 03 0, 04 0, 05 2, 06 0, 07 1, 08 1, 09 1, 10 0, 11 0, 12 1, 13 0, 14 0, 15 0. Every slice ended DONE or DONE_WITH_CONCERNS; every concern was routed (slice 12 sweep, docs-sync, or this record).
- No slice delegated to the `replicator` (`delegated: []` on all fifteen); slice 04 used a reviewed script for the call-site rewrite instead.

### Cost of the run
- Slice tokens by model, from run.log: opus 1,279,343 across 10 slices; sonnet 525,581 across 5 slices.
- Review rounds: 8 across 15 slices.
- Escalations: none recorded.
- Gates: final all-tier suite OK (6488 tests, 75126 assertions) at `9b1d16e5`; baseline 5182 tests.
- Infection: three runs on the lane (2026-10-09: 8m53s; 2026-10-13: one died in its initial suite on BL-406, one 10m53s).
