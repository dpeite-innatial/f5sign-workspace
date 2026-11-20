# TASK-060 — A resend may name one of the recipient's declared channels

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/resend-channel`**, 2026-10-19 — full suite OK (7505 tests, 83575 assertions) plus lint, arch and phpstan, under the `wt-backend` lane that mounts this worktree, at `cfb89e1d`. After it only a source comment (`ffcd0b94`), tests (`78189c66`, `d109a449`) and documentation changed; those tests ran green on the same lane (fast tier 6233 tests at `78189c66`, the touched Acceptance and Integration classes, and the named-channel flow at `d109a449`). Infection, filtered to the 16 `src/` files of the diff (`wt-backend-infection`, verdict on changed lines): run 1 left 8 escaped and 22 uncovered mutants on changed lines; after the test-only fix (`78189c66`) run 2 leaves one, the equivalent `int $smsResendsMade = 0` default of `Recipient::rehydrate()` (§7). Four changed-line mutants were skipped for time and are exercised by the Acceptance flow and the persistence test (§7). Whole-file figures, dominated by untouched code in the same files: MSI 72 %, covered-MSI 80.2 %. ADR-0080 was accepted by the owner on 2026-10-19; the integrator handoff and the living docs are in the docs-sync commit; the four follow-ups in §6 are open. |
| **Type** | **Forward build** across Envelope (the resend route's body, the guard, the SMS resend counter, the event) and Notification (sending the resend on the named channel only). An additive contract change: a resend with no body behaves as today. |
| **Why** | An integrator whose recipient says *"the email never arrived, send it to my phone"* cannot ask for that. `POST …/recipients/{recipientId}/resends` reads no body and always resends on the declared channels under the declared mode, and under `IN_ORDER` a delivered-but-unread email is a success, so the SMS behind it never goes. The only route today is changing the declaration (`PUT …/notification-channels`), which also changes every later notice and re-invites on each call (BL-413). |
| **Decision record** | **ADR-0080, drafted as Proposed in this task's first slice and landed by this task (TASK-060).** It amends [ADR-0077](../adr/ADR-0077-a-recipient-declares-the-channels-that-reach-them.md) twice: §2.8 (a resend may name one channel of the declaration for that send only) and §2.10 (the SMS resend cap counts resends that go out by SMS, not recipients that declare SMS). It does not contradict §2.3: the named channel is always one the recipient declared. The owner accepted it on 2026-10-19. |
| **Builds on** | [TASK-041](TASK-041-resending-a-signing-invitation.md) (the resend route and `Recipient::resendInvitation`), [TASK-031](TASK-031-channel-selection-beyond-email.md) (the declared channels and their single resolver), [TASK-057](TASK-057-sms-spend-guards.md) (the SMS resend cap and the operator allowance), [TASK-058](TASK-058-recipient-notification-history.md) (the history that shows the delivery). |
| **Scope** | Only the invitation resend. A recipient declared with `[]` gains nothing here (owner, 2026-10-19). Delivered one-time codes are untouched (ADR-0077 §2.3: they never read the declaration). |

---

## 1. Why this task exists

<!-- OFFREPO: "the factor5 integrator" is the external client of the machine routes (a separate Symfony project). Nothing here depends on reading it: the only fact taken from it is the owner's request restated in this paragraph. -->

The owner, testing the factor5 integrator locally on 2026-10-19, asked whether an integrator pressing
"reenviar" can choose where the notification goes, for the case *"it did not arrive by email, try the phone"*.
It cannot: the resend takes the declared channels and mode as they are (§2). Changing the declaration first
works, but it is persistent (ending notices and the sealed copy follow it too) and its re-invite is uncapped
(BL-413). The owner chose a per-resend channel, limited to the channels the recipient declared, and decided
that the SMS cap follows what is actually sent by SMS.

## 2. What already exists (reuse, do not rebuild)

- **Route:** `resend_recipient_invitation` in `config/routes/api/envelope.php`, `POST
  /envelopes/{id}/recipients/{recipientId}/resends`, `Authn::MACHINE_KEY` (so `F5Sign-Declared-Subject` is
  required, enforced globally by `TenantRequestListener::requireDeclaredSubject`).
- **Controller:** `Envelope/UI/Http/ResendInvitationController` reads **no body**, dispatches
  `ResendRecipientInvitation(envelopeId, recipientId, issuedBy, issuedAt)` and answers 204. Its
  `#[OA\Response]`s: 204, 400, 401, 404, 409 (a closed list of problem codes in the description), 500, 503
  (`ENVELOPE_BUSY`). `OpenApiSpecTest` censuses the 409 enum, not the prose.
- **Use case:** `ResendRecipientInvitationUseCase::execute` — lock the envelope, `guardBeforeExpiry`, find the
  recipient, resolve its reach with `NotificationChannelResolver::resolve` (tenant, declared channels, email,
  phone, delivery trace), then `Envelope::resendInvitation(recipientId, issuedAt, $reach)`, then save.
- **Guard order in `Envelope::resendInvitation`:** `guardAcceptsActs` (closed or terminal → `CONFLICT`; not
  sent → `CONFLICT`; expired → `ENVELOPE_EXPIRED`) → unclaimed slot (`RECIPIENT_SLOT_NOT_CLAIMED`) → delegated
  (`RECIPIENT_SIGNS_BY_DELEGATION`) → reach (`RECIPIENT_NOTIFIED_BY_INTEGRATOR` for `[]`,
  `RECIPIENT_HAS_NO_REACHABLE_CHANNEL`) → step not active (`RECIPIENT_STEP_NOT_ACTIVE`) →
  `Recipient::resendInvitation`: leg closed (`RECIPIENT_LEG_CLOSED`) → SMS cap (`RECIPIENT_RESEND_CAP_REACHED`)
  → 60-second interval (`RECIPIENT_RESENT_TOO_RECENTLY`, with `next_resend_at`). All are
  `RecipientNotResendableException` (409) except the envelope-state ones.
- **The SMS cap today:** `Recipient::MAX_SMS_RESENDS = 5`, checked when the **declared** channels include `SMS`,
  against `resendsMade`, which grows on **every** successful resend whatever channel delivered it, plus
  `resendAllowance` (operator grant, `app:envelope:unblock-resends`, column `envelope.recipient.resend_allowance`).
  `resends_made` and `last_resent_at` columns: `Version20260831000002`.
- **Reach:** `Envelope/Contract/Type/NotificationChannelResolution::resolve` is the single pure resolver
  (ADR-0077 §3.3), behind `Envelope/Contract/Service/NotificationChannelResolver`. SMS is reachable only when
  `SmsAvailability::isAvailableTo` (deployment wired **and** tenant enabled), a phone exists and
  `SmsPhoneEligibility` says `TAKES_SMS` (not `NOT_A_MOBILE`, not `COUNTRY_NOT_SUPPORTED`). A channel whose
  destination's delivery trace is `FAILED` is skipped. Result: `ResolvedNotificationChannels` (channels, mode,
  `unsentKind`).
- **Event:** `Envelope/Contract/Event/RecipientInvitationResent`, `EVENT_TYPE = 'RECIPIENT_INVITATION_RESENT'`,
  payload keys `envelope_id, recipient_id, step_ordinal, resend_ordinal, occurred_at`.
- **Notification side:** `OnRecipientInvitationResent` → `NotifyResentInvitationRecipientUseCase`, which
  re-resolves the channels at send time, records `NOT_SENT_NO_REACHABLE_CHANNEL` through the envelope facts when
  nothing reaches, keys the notification on `…|purpose:RECIPIENT_INVITATION_RESENT|resend:N` (idempotent), and
  selects a policy with `DefaultChannelSelector` (one channel → SINGLE; several → `IN_ORDER` or ANY).
- **Tests beside it:** `tests/F5Sign/Envelope/Unit/Domain/Aggregate/EnvelopeInvitationResendTest`,
  `EnvelopeResendCapTest`, `tests/F5Sign/Envelope/Application/UseCase/Lifecycle/ResendRecipientInvitationUseCaseTest`,
  `tests/F5Sign/Envelope/Integration/RecipientInvitationResendPersistenceTest`,
  `tests/F5Sign/Acceptance/RecipientInvitationResendHttpTest`,
  `tests/F5Sign/Envelope/Unit/Contract/Event/RecipientInvitationResentTest`,
  `tests/F5Sign/Notification/Application/UseCase/NotifyResentInvitationRecipientUseCaseTest`,
  `tests/F5Sign/Acceptance/OpenApiSpecTest`.

## 3. Scope

**In:**
1. An optional JSON body on the resend route, `{"channel": "EMAIL" | "SMS"}`, typed as Envelope's
   `NotificationChannel`.
2. The named channel must be one the recipient declared, and must reach them now; otherwise two new 409 codes,
   `RESEND_CHANNEL_NOT_DECLARED` and `RESEND_CHANNEL_UNREACHABLE`. **Where they sit:** with a channel named, these
   two checks take the place of the generic reach check, after the `[]` refusal and before the step check:
   `guardAcceptsActs` → unclaimed slot → delegated → `[]` (`RECIPIENT_NOTIFIED_BY_INTEGRATOR`) → not declared →
   unreachable → step not active → leg closed → cap → interval. So a named channel never answers
   `RECIPIENT_HAS_NO_REACHABLE_CHANNEL`, even for a one-channel declaration. With no channel named the order is
   today's, unchanged.
3. A per-recipient count of resends that went out by SMS, which the cap reads instead of `resendsMade`, with its
   migration and backfill.
4. The event carries the named channel; Notification sends that resend on that channel alone.
5. The OpenAPI surface of the route.

**Out:** a channel outside the declaration; anything for a `[]` recipient; other notification occasions
(ending notices, sealed copy); OTP codes; BL-413 (the channel-change re-invite stays uncapped).

**Concepts re-cut:** `resendsMade` as the input of the SMS cap (the cap moves to a new SMS count;
`resendsMade` stays as the resend ordinal); "the cap applies to a recipient whose channels include SMS"
(ADR-0077 §2.10, the `Recipient::MAX_SMS_RESENDS` docblock, `RecipientNotResendableException::resendCapReached`,
the route's OA description, the TASK-057 handoff `docs/frontend-handoff/TASK-057-dashboard-resend-cap.md`,
`UnblockResendsCommand::MAX_GRANT` and its `--grant` error text, which bound the grant by "`resends_made` is a
SMALLINT", the `MAX_SMS_RESENDS` mention in `NotifyCorrectedRecipientUseCase`, and the docblock of
`Envelope/Contract/Event/RecipientResendsUnblocked`); "the resend has no body"
(`ResendInvitationController`'s class docblock: "No body, and 204", "the channels are the ones the recipient
declared").

## 4. Key decisions

- **Only declared channels** (owner, 2026-10-19). A resend narrows the declaration for one send; it never widens
  it, so ADR-0077 §2.3 stands.
- **`[]` stays "the platform never writes to them"** (owner, 2026-10-19), with or without a channel.
- **The SMS cap follows the spend** (owner, 2026-10-19): it counts resends that go out by SMS. With no channel
  named and `SMS` declared, the resend counts as today, because under `IN_ORDER` or `ALL_AT_ONCE` it may go
  out by SMS. That requires a counter separate from `resendsMade`, which grows on every resend.
- **No fallback.** A named channel is one delivery under the SINGLE policy, so a refusal records the outcome
  and stops; it never moves to the other declared channel. `IN_ORDER`'s fall-back is a property of a declared
  list ([ADR-0077](../adr/ADR-0077-a-recipient-declares-the-channels-that-reach-them.md) §2.6), and a named
  channel is a list of one.
- **"Still declared" is checked when the notification is created; after that, a channel change stops the
  resend only through the existing cancellation.** The send-time re-check of
  [ADR-0079](../adr/ADR-0079-a-delivery-retries-by-what-it-carries.md) §2.5 (`TransmitDeliveryUseCase::stillNeeded`)
  asks whether the envelope and leg are open and the destination is still current, and does not read the
  declaration. But a channel change whose `RecipientNotificationChannelsChanged::reinvites` is true (step active,
  never successfully invited) already cancels the recipient's pending invitation deliveries
  (`OnRecipientNotificationChannelsChangedCancelInvitations` → `CancelPendingInvitationsUseCase`, which covers
  `RECIPIENT_INVITATION_RESENT` through `NotificationPurpose::isInvitation()`), so a named-channel resend still
  `PENDING` is marked `NOT_NEEDED`. It goes out on the channel it named in three cases: `reinvites` is false; the
  delivery has already left `PENDING`; or the resend was requested in the same second as the change, because the
  cancellation is bounded by `requestedBefore = occurredAt` compared to the second. ADR-0080 states all three.

## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | A resend with `{"channel":"EMAIL"\|"SMS"}` sends the invitation on that channel only, whatever `notification_mode` (members AC-1a…b) | owner | Application (Notification use case) + Acceptance | ignore the event's channel in Notification |
| AC-2 | A resend with a channel leaves `notification_channels` and `notification_mode` unchanged, and the next ending notice follows the declaration | owner | Unit (aggregate) + Acceptance read-back | store the named channel on the recipient |
| AC-3 | A resend with no body, or with `{}`, behaves exactly as today: same channels, same mode, same codes | owner | Acceptance, the existing `RecipientInvitationResendHttpTest` cases unchanged | default the channel to the first declared one |
| AC-4 | A channel the recipient did not declare is refused 409 `RESEND_CHANNEL_NOT_DECLARED`; nothing is recorded and no counter moves | owner | Unit + Acceptance | drop the declared-channel check |
| AC-5 | A recipient declared `[]` is refused 409 `RECIPIENT_NOTIFIED_BY_INTEGRATOR` with or without a channel (members AC-5a…b) | owner | Unit | check the named channel before the `[]` reach |
| AC-6 | The SMS resend cap counts resends that go out by SMS (members AC-6a…d) | owner | Unit (`EnvelopeResendCapTest`) | see *Notes on AC-6* |
| AC-7 | A declared channel that cannot reach the recipient now is refused 409 `RESEND_CHANNEL_UNREACHABLE`, recording nothing (members AC-7a…e) | derived — census of `NotificationChannelResolution::resolve`, ADR-0077 §2.5 | Unit + Application | see *Notes on AC-7* |
| AC-8 | A `channel` that is not `EMAIL` or `SMS`, or not a string, is refused 422 `VALIDATION_ERROR` | derived — src/F5Sign/Envelope/UI/Http/Request/ChangeRecipientNotificationChannelsRequest.php | Acceptance | accept any string |
| AC-9 | With a channel named, every existing refusal still answers with today's code, in the order §3 #2 states (members AC-9a…i) | derived — src/F5Sign/Envelope/Domain/Aggregate/Envelope.php | Unit | move the channel checks before `guardAcceptsActs` |
| AC-10 | `RECIPIENT_INVITATION_RESENT` carries `channel` (`null` when none was named); its key set is closed; a payload written before this task decodes with `channel` null | derived — rule 5 (closed key set) | Unit (`RecipientInvitationResentTest`) | omit the key when null |
| AC-11 | Notification creates one delivery on the named channel under the SINGLE policy; if, when the notification is created, that channel is no longer declared or no longer reaches, nothing is sent, `NOT_SENT_NO_REACHABLE_CHANNEL` is recorded, and no other channel is tried | derived — ADR-0077 §2.6, ADR-0079 §2.5 | Application (`NotifyResentInvitationRecipientUseCaseTest`) | fall back to the resolved declaration |
| AC-12 | The migration adds the SMS resend count; an existing row reads `resends_made` when its current declaration includes `SMS` and 0 otherwise; `down()` drops the column | derived — rule 6 | Integration (migration test) | revert the backfill |
| AC-13 | The route's OpenAPI documents the request body, the two new 409 codes in the enum and the 422 | derived — rule 1 (a closed enumeration is a surface) | Acceptance (`OpenApiSpecTest`) | leave the enum unchanged |
| S-1 | With `["EMAIL","SMS"]` under `IN_ORDER`, a resend with `channel:SMS` produces one SMS and no email; the recipient's notification history (TASK-058) shows that one delivery; `GET` the envelope returns the channels unchanged | derived — tests/F5Sign/Acceptance/RecipientInvitationResendHttpTest.php | Acceptance, worktree lane | — |

- **Gates:** suite, PHPStan, deptrac and lint, under the `wt-backend` lane that mounts this tree.
  <!-- OFFREPO: `wt-backend` is a make target of the sibling infra repository that runs this repo's suite in a container mounting this worktree; nothing here depends on reading it. -->

**Notes on AC-8**
- The scalar `channel` carries `Assert\Type('string')` beside its `Assert\Choice` in the request DTO, and an
  acceptance case sends `{"channel": 1}`. As built, `Assert\Choice` (strict) is what refuses it: removing
  `Assert\Type` leaves that case green (slice 08's sabotage), so `Type` states the intent and `Choice` holds it.
- The body is optional: the controller argument defaults to null, so a bodiless POST reaches today's path (AC-3).

**Notes on AC-1**
- Owner said: "Optional `channel` on POST …/resends" (the request, 2026-10-19).
- AC-1a — declared `["EMAIL","SMS"]` `IN_ORDER`, named `SMS`: one SMS delivery, no email.
- AC-1b — declared `["EMAIL","SMS"]` `ALL_AT_ONCE`, named `EMAIL`: one email delivery, no SMS.

**Notes on AC-5**
- AC-5a — `[]`, no channel: `RECIPIENT_NOTIFIED_BY_INTEGRATOR` (today's behaviour).
- AC-5b — `[]`, channel `SMS`: `RECIPIENT_NOTIFIED_BY_INTEGRATOR`, not `RESEND_CHANNEL_NOT_DECLARED`.

**Notes on AC-6**
- AC-6a — named `SMS` counts toward the cap. Sabotage: never increment on a named SMS.
- AC-6b — named `EMAIL` with `SMS` declared neither counts nor is refused at the cap. Sabotage: count every resend.
- AC-6c — no channel, `SMS` declared: counts, as today. Sabotage: count only named SMS.
- AC-6d — the operator allowance raises the same ceiling. Sabotage: compare against `MAX_SMS_RESENDS` alone.
- Owner said: "Si el envío sale por SMS".

**Notes on AC-7** (the census of what makes a declared channel unreachable)
- AC-7a — `SMS` with SMS not wired on the deployment.
- AC-7b — `SMS` with the tenant switch off.
- AC-7c — `SMS` with no phone, or a phone that is `NOT_A_MOBILE` or `COUNTRY_NOT_SUPPORTED`.
- AC-7d — `EMAIL` with no email.
- AC-7e — a channel whose destination's delivery trace is `FAILED`.
- Each holds for a one-channel declaration too: the named checks replace the generic reach check (§3 #2), so
  the answer is `RESEND_CHANNEL_UNREACHABLE`, never `RECIPIENT_HAS_NO_REACHABLE_CHANNEL`.
- Sabotage for each: drop that branch of the reach check for the named channel.

**Notes on AC-9** (with a channel named, each refusal unchanged)
- AC-9a closed or terminal envelope (`CONFLICT`) · AC-9b unsent envelope (`CONFLICT`) · AC-9c expired
  (`ENVELOPE_EXPIRED`) · AC-9d unclaimed slot · AC-9e delegated recipient · AC-9f step not active · AC-9g leg
  closed · AC-9h interval (`RECIPIENT_RESENT_TOO_RECENTLY`, with `next_resend_at`) · AC-9i cap
  (`RECIPIENT_RESEND_CAP_REACHED`, for a named `SMS`).

## 6. Open follow-ups (track, don't solve here)

- **ADR-0080** was drafted as Proposed in slice 01 (2026-10-19, `2bc257de`). Accepted by the owner on 2026-10-19.
  The index row, relationship graph and crosswalk are docs-sync's, in its own commit.
- **Frontend handoff for the integrator** (`docs/frontend-handoff/TASK-060-integrator-resend-channel.md`): the
  body, the two codes, and that a named `EMAIL` does not spend the SMS cap. Written by docs-sync in this task's
  changeset (2026-10-19); the integrator still has to be told.
- **A channel change that does not re-invite** (`reinvites` false) leaves an already-created named-channel resend
  to go out on the channel it named (§4). If that proves wrong, the fix is for the transmission re-check
  (`TransmitDeliveryUseCase::stillNeeded`) to read the declaration as well.
- **The TASK-057 handoff** says the cap applies to a recipient whose channels include SMS; it is superseded in part.
- **BL-413** (the channel-change re-invite is uncapped) stays open; this task gives integrators a reason to use
  it less, not a fix.
- **A resend's SMS classification is read at resend time, its delivery resolved later** ([`BL-429`](../BACKLOG.md)).
  An unnamed resend is counted as SMS-or-not from the declaration when it is requested, and
  `NotifyResentInvitationRecipientUseCase` resolves the declaration afterwards; if `SMS` is added in between, one
  send goes out by SMS uncounted. Bounded by the 60 s interval; the same window as before this task (security audit).
- **No test sends a notice after a named resend** ([`BL-430`](../BACKLOG.md)). AC-2's "the next ending notice
  follows the declaration" holds because the declaration is left unchanged and asserted unchanged; nothing sends an
  ending notice afterwards to watch it.
- **A named-SMS resend that Notification later records as unsent still counted toward the cap**
  ([`BL-431`](../BACKLOG.md)). The count is taken at the write (ADR-0080 §7.5), before Notification decides.
- **A declaration emptied between a resend and the notification's creation** ([`BL-432`](../BACKLOG.md)): a named
  resend records `NOT_SENT_NO_REACHABLE_CHANNEL` where an unnamed one records `DELIVERED_BY_INTEGRATOR` (as AC-11
  specifies); the difference is deliberate and unobserved by a client.

---

## 7. Deviations & honest notes

### Scope
- None beyond the plan. Three files were added to slices by the orchestrator: `EnvelopeInvitationResendTest`
  (slice 02, its closed refusal lists omitted the two new codes), and `OnRecipientInvitationResentTest`
  (slice 07, created because none existed and the sabotage table needed one).

### Decisions made during implementation
- The guard in `Envelope::resendInvitation()` is plain `if`s rather than a split `match` (PHPStan narrowing); the
  order is unchanged and is ADR-0080 §2.2's.
- The SMS cap's refusal message was re-worded to say the resend "may go out by SMS"; the test's assertion on it was
  re-worded with it, not weakened (slice 04, reviewer confirmed).
- `tests/Fixtures/audit-trail/factor5-closed-now.json` was regenerated: only the resend fact's commitment and chain
  root moved, because the fact now carries `channel` (slice 02, reviewer confirmed). The frozen event-payload golden
  for `RECIPIENT_INVITATION_RESENT` is untouched: a payload without `channel` decodes with it null.
- `Assert\Type('string')` on the request's `channel` is kept as documentation; `Assert\Choice` is the guard that
  holds (see *Notes on AC-8*). The comment saying so was corrected in `ffcd0b94`.
- An unnamed resend to `[EMAIL, SMS]` with no phone counts toward the SMS cap (declared, not reachable: the
  owner's rule that no channel named means "may go out by SMS").
- A recipient whose resends all name `EMAIL` is now uncapped by count as well as by the cap: only the 60 s interval
  bounds them. [`BL-213`](../BACKLOG.md) carries a note.
- Slice 03's empty generated migration was recorded as executed on the kept lane by a concurrent migrate; repaired
  on the lane databases only, and the shared dev database was verified untouched.

### Decisions that needed an ADR
- [ADR-0080](../adr/ADR-0080-a-resend-may-name-one-declared-channel.md), drafted as Proposed in slice 01 (it
  amends ADR-0077 §2.8 and §2.10). It is exercised by `EnvelopeInvitationResendTest`, `EnvelopeResendCapTest`,
  `NotifyResentInvitationRecipientUseCaseTest`, `OnRecipientInvitationResentTest`,
  `RecipientInvitationResendPersistenceTest` and `RecipientInvitationResendHttpTest`. Accepted by the owner on 2026-10-19.

### Declared and unproven properties
- A channel change that does not re-invite (`reinvites` false) does not cancel an already-created named-channel
  resend, and the transmission re-check does not read the declaration (§4, §6). Stated in ADR-0080; no harness
  drives a change between a resend and its transmission.
- The counter's concurrent behaviour is the row lock's, as for `resends_made`; `Integration/` runs one connection,
  so a second writer is not exercised.
- Infection: pending (see Status).

### Debt left behind, and where it lives now
- Window between classification and delivery of an unnamed resend → §6 and `BL-429`.
- Ending notice after a named resend not exercised → §6 and `BL-430`.
- Named-SMS resend counted though recorded unsent → §6 and `BL-431`.
- Emptied declaration between resend and notification → §6 and `BL-432`.
- A channel change that does not re-invite → §6 (first bullet of that kind).
- `BL-413` (the channel-change re-invite is uncapped) stays open; `BL-213` gained a note.

### Delegated work
- Nine slices, no replicator delegation (`delegated` empty on every line). Mechanical: 01 (sonnet, 1 round).
  Critical on opus: 02 (2 rounds), 03, 04, 07 (1 round each). Standard on sonnet: 05, 06 (review on opus), 08, 09
  (1 round each). All approved by their review; 03, 04, 06, 07 and 08 closed DONE_WITH_CONCERNS, each concern
  routed to a later slice or recorded above.

### Cost of the run
- Slice work: one sonnet mechanical slice, four opus critical slices, four sonnet standard slices; one fix round
  (slice 02). Closing review approved with no finding at the 80 cut. Plan on opus (about 300k tokens).
  Implementer tokens, rounded: opus 02 (two rounds, about 340k), 03 (143k), 04 (121k), 07 (126k); sonnet 01 (79k),
  05 (100k), 06 (106k), 08 (115k), 09 (88k), and the Infection fix slice 10 (99k). No escalation to opus was needed.
  Infection ran twice (about 11 and 10 minutes); the full suite once (27 minutes).

### Infection, and coverage attribution (added at close)
- **The one surviving changed-line mutant is equivalent.** `Recipient::rehydrate()` keeps `int $smsResendsMade = 0`
  because a required parameter cannot follow the optional ones before it; its only production caller,
  `DbalEnvelopeRepository`, always passes the value, so incrementing or decrementing the default changes nothing.
- **`ResendInvitationController` and `ResendInvitationRequest` are exercised by the Acceptance flow
  `ResendOnANamedChannelHttpTest`, which declares `#[CoversNothing]` like every top-level Acceptance flow
  (tests/README.md).** A commit credited them to it so Infection would count their lines; it was reverted to the
  convention (`d109a449`). Their mutants therefore read "not covered" or "skipped" to Infection, as every other
  controller's do; the published request schema is pinned by `OpenApiSpecTest`.
