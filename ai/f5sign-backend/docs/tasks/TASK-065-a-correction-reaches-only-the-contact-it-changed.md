# TASK-065 — A correction reaches only the contact it changed, and adding a missing contact is not a correction

<!-- OFFREPO: the incident in §1 was reported by the dashboard team's session on 2026-10-21, and the decisions marked "owner, 2026-10-21" were taken in the owner's working session that day. Every fact taken from them is restated here; nothing in this record depends on reading either. -->

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/correction-reaches-the-changed-contact`** (tip `9892dd54`), 2026-10-21. Last full run `cf82c8dc`: OK (7908 tests, 90441 assertions) under the `wt-backend` lane (kept, reused) with lint, arch, PHPStan and tests; later commits touch only the record (`9892dd54`). Pending review and merge. Infection (diff-filtered to the 33 changed `src/` files, StorageLifecycleScenarioTest excluded per BL-356, worktree `wt-backend` lane, on `6de33f86` whose `src/` equals `cf82c8dc`): covered-MSI 90 %, MSI 85 %; on changed lines 2 escaped, both equivalent (`TrailAssembler.php` nullsafe on a never-null `AuthMethod::tryFrom()`, and `>` vs `>=` on the unique `sys_global_position`; proofs in slice 15), 0 not covered. A first run on `9892dd54` had left 15 alive; 13 were killed by test-only commit `6de33f86`, each seen red by hand. Left out and homed in §6 and the BACKLOG: BL-445 to BL-447. |
| **Type** | **Forward build** in Envelope, with its reactions in Notification and Evidence & Audit: the correction route classifies each supplied contact as added, changed or unchanged; only a change is a correction; each re-invitation goes out on the channels of what the call touched; a new fact records an added contact. No new route and no new HTTP code. |
| **Why** | A correction today treats every supplied contact as "the old one was wrong". Adding an email to a recipient who was authored with a phone only therefore spends one of three corrections, retires their live link, records `RecipientCorrected`, and re-sends the invitation on the channels already declared, which are not the contact that changed. When the changed contact is not a declared channel, the recipient is left with a dead link and nothing new. |
| **Builds on** | [TASK-025](TASK-025-recipient-delivery-failure-and-correction.md) (the correction route and its budget), [TASK-031](TASK-031-channel-selection-beyond-email.md) (the declared channels and `PUT …/notification-channels`), [TASK-041](TASK-041-resending-a-signing-invitation.md) (the resend route, which is the way to re-send without a change), [TASK-059](TASK-059-the-trail-shows-how-each-invitation-travelled.md) (the trail's invitation destinations). |
| **Scope** | The correction route's semantics, and (decision 9, added 2026-10-21 after the security gate) the channel change's revocation when it drops a declared channel. The gate change (ADR-0083) and the resend route are not modified. |
| **Decision record** | [ADR-0084](../adr/ADR-0084-a-correction-reaches-only-the-contact-it-changed.md), **Accepted** 2026-10-21 by the owner and realized on this branch. It amends: <br>• [ADR-0057](../adr/ADR-0057-claimable-recipient-slot.md) §2.3: a correction is a change of a contact that had a value; supplying a contact that had none is an addition, which spends no budget; <br>• [ADR-0060](../adr/ADR-0060-retiring-a-credential-whose-holder-changed.md) §2.5 (the gesture census: a correction "sets the anchor" as "the admission that an address was wrong") and §2.2 (the anchor is moved by the §2.5 gestures): a correction sets the anchor only when the contact it changed is the destination of a declared channel; an addition never does; <br>• [ADR-0077](../adr/ADR-0077-a-recipient-declares-the-channels-that-reach-them.md) §2.3: the re-invitation after a correction or an addition resolves only the declared channels whose contact the call touched; <br>• [ADR-0078](../adr/ADR-0078-delivery-outcomes-come-back-as-facts.md) §2.3: the sentence "a contact correction already re-invites" is narrowed accordingly. |

---

## 1. Why this task exists

<!-- OFFREPO: the dashboard is another repository; the only facts taken from it are the request it sent and the result the platform gave, both restated below. -->
On 2026-10-20/21 the dashboard authored a recipient (a lorry driver) with a mobile phone only:
`notification_channels: ["SMS"]`, `auth: {"access_method": "OTP_SMS"}`. The operator later added the driver's
email from the dashboard, through `POST /api/v1/envelopes/{id}/recipients/{recipientId}/corrections` with
`{"email": "..."}`, because no other route writes a contact after the send. What happened:

- the invitation was re-sent **by SMS**, the only declared channel, although the phone had not changed;
- one of the recipient's three corrections was spent;
- the recipient was recorded as `RecipientCorrected` ("the contact was wrong") when it was missing;
- the email reached nothing: it is neither a declared channel nor a gate method.

The owner decided (2026-10-21):

1. A correction re-invites **only on the channel whose contact changed** (email changed → at most one email;
   phone changed → at most one SMS), and sends nothing when that channel is not declared.
2. Adding a contact that was missing **is not a correction**: it spends no budget and is recorded as its own
   fact.
3. The same route carries both; the server decides which one it is.
4. A call that both changes one contact and adds the other **is one correction**.
5. An addition re-invites under the same conditions as a correction, on the added contact's channel only.
6. A call that changes and adds nothing answers 200 and does nothing.
7. A correction revokes the earlier links only when the changed contact is the destination of a declared
   channel.

With this, the dashboard's flow for "add a contact to a signer" is: the correction route (an addition, which
sends nothing on undeclared channels and spends nothing), then `PUT …/notification-channels` to add the
channel (later notices go there; it re-invites only a recipient never successfully invited, so to reach the new
contact now, `POST …/resends` naming that channel), then `PUT …/auth` if the recipient has not entered yet
(ADR-0083).

## 2. What already exists (reuse, do not rebuild)

- **The route.** `CorrectRecipientController` (`POST …/recipients/{recipientId}/corrections`, machine key)
  takes `CorrectRecipientRequest`: `email` (nullable, trimmed, `Assert\Email`) and `phone` (nullable, parsed by
  `PhoneNumberParser`). An absent key means "leave alone"; there is no clear. At least one is required (422 on
  `email`). It answers `200 {warnings}`. Its declared responses are 200, 400, 401, 404, 409
  (`RECIPIENT_LEG_CLOSED`, `RECIPIENT_CORRECTION_BUDGET_EXHAUSTED`, `RECIPIENT_SLOT_NOT_CLAIMED`, `CONFLICT`,
  `ENVELOPE_EXPIRED`), 422 (`RECIPIENT_CANNOT_RECEIVE_METHOD`, `PHONE_COUNTRY_NOT_SUPPORTED`,
  `VALIDATION_ERROR`), 500 and 503 (`ENVELOPE_BUSY`).
- **The use case.** `CorrectRecipientUseCase` loads the envelope with `findLockedForUpdate`, finds the
  recipient, runs `DeclaredMethodDestinations::guard()` and `NotificationChannelsGuard::guardContacts()` on the
  resulting contacts, then `guardBeforeExpiry`, then `Envelope::correctRecipientContact()`, then
  `saveLifecycle()`. The guards run before the mutation, so a refused call spends nothing.
- **The aggregate.** `Envelope::correctRecipientContact()` runs `guardAcceptsActs()` (closed or terminal →
  `EnvelopeStateException::closed`; not sent → `notYetSent`; past `expires_at` → expired), then
  `Recipient::correctContact()`, then records `RecipientCorrected`. `Recipient::correctContact()` refuses a
  closed leg, an unclaimed slot and an exhausted budget (`MAX_CORRECTIONS = 3`, `correctionsMade`, a
  monotonic counter persisted in `envelope.recipient.corrections_made`), each through
  `RecipientNotCorrectableException`. It writes the supplied contacts, forgets only the changed destination's
  delivery trace, and on **every** call runs `retireCredentialsAt()` and `revokeInvitationsAt()`. It never
  compares the supplied value with the stored one: the same value spends a correction like any other.
- **The event.** `RecipientCorrected` (`RECIPIENT_CORRECTED`): `envelope_id`, `recipient_id`, `step_ordinal`,
  `correction_ordinal`, `occurred_at`. No contact, no `schema_version`, and nothing saying which contact
  changed.
- **The reactions.** `OnRecipientCorrected` dispatches `NotifyCorrectedRecipient` unconditionally;
  `OnRecipientCorrectedCancelInvitations` dispatches `CancelPendingInvitations` for invitations requested
  before the correction. `NotifyCorrectedRecipientUseCase` re-invites when the envelope is open, the recipient
  is not delegated and not an unclaimed slot, and their step is active; it resolves **every** declared channel
  through `RecipientNotificationChannels::resolve()` from the current contacts, mints a new signing token, and
  keys the occasion on `envelope|recipient|purpose|correction:<ordinal>` so a redelivery converges.
- **The sibling that is not a correction.** `PUT …/notification-channels`
  (`ChangeRecipientNotificationChannelsController` → `ChangeRecipientNotificationChannelsUseCase` →
  `Envelope::changeRecipientNotificationChannels()`) records `RecipientNotificationChannelsChanged`, spends no
  correction (`EnvelopeNotificationChannelsChangeTest`), carries a `reinvites` flag its subscribers gate on,
  and has its own re-invitation (`NotifyRechanneledRecipientUseCase`, occasion keyed on the change's instant).
  It is the template for the new fact's reactions.
- **The trail.** `TrailAssembler` reads `RecipientCorrected` in its contact and invitation sections: any
  earlier invitation or code destination followed by a correction renders as unstated, "corrected
  afterwards", whatever contact the correction touched.
- **Nothing adds a contact today.** No `addContact`, `ContactAdded` or similar exists in `src/` or `tests/`.
  After the send, the correction route is the only writer of a named recipient's contacts; `ClaimRecipient`
  fills an unclaimed slot once, and `AddRecipient` authors in DRAFT.
- **Tests beside it.** `RecipientCorrectionHttpTest`, `CorrectedContactClosesTheLinkHttpTest`
  (Acceptance); `CorrectRecipientUseCaseTest` (Application, including the row-lock load);
  `EnvelopeDeliveryFailureTest`, `EnvelopeCredentialRetirementTest`, `RecipientTest` (Unit);
  `RecipientCorrectionPersistenceTest` (Integration); `NotifyCorrectedRecipientUseCaseTest`,
  `CancelInvitationsReactorsTest` (Notification); `TrailAssemblerTest`. There is no unit test of the
  `RecipientCorrected` event class.

## 3. Scope

In:

- Classify each supplied contact against the stored one, under the envelope's row lock: absent → untouched;
  stored empty → **added**; different → **changed**; equal → **unchanged**.
- A call with at least one changed contact is a correction (budget, `RecipientCorrected`). A call with only
  added contacts is an addition (no budget, a new fact). A call with neither does nothing.
- Re-invite only on the declared channels whose contact the call changed or added.
- Revoke and cancel only when a changed contact is a declared channel's destination; an addition never does.
- `RecipientCorrected` says which contacts it changed and which it added; a new event for an addition.
- The trail marks only the corrected destinations, and states an addition.
- A channel change that drops a declared channel once a link may have been minted retires the earlier links and re-invites
  (decision 9, ADR-0084 §2.11), with its route's `#[OA\*]` prose.
- The route's `#[OA\*]` prose, a frontend handoff, ADR-0084.

Out:

- A separate route for adding a contact (owner, 2026-10-21: the same route).
- Clearing a contact.
- Re-sending on an unchanged contact: that is `POST …/resend` (TASK-041).
- Per-contact correction budgets (TASK-031 §Open follow-ups): the budget stays one counter of three.
- The live code sent to the old contact (BL-168) and the second live credential (BL-152).

Concepts re-cut: `correctContact`, `correctRecipientContact`, `RecipientCorrected`, `NotifyCorrectedRecipient`,
`retireCredentialsAt`, `revokeInvitationsAt`, `CORRECTED_AFTERWARDS`, "a correction re-invites", "only the
contact correction revokes", "spends one of the three".

## 4. Key decisions

1. **One route, classified by the server** (owner, 2026-10-21). The dashboard sends what it sends today.
2. **Comparison.** An email is compared case-insensitively, as received (the request's `trim` normalizer only
   validates, and nothing trims on the way to `Recipient::correctContact()`; `Assert\Email` already refuses
   surrounding whitespace); a phone by its E.164 form. A difference in case alone is unchanged.
3. **Changed wins over added** (owner): a call with one changed and one added contact is one correction, and
   its re-invitation covers the channels of both.
4. **Nothing changed is a no-op** (owner): 200 with `warnings`, no fact, no budget, no send. A client that
   used the correction to re-send must use `…/resend`.
5. **Revocation follows the channel** (owner): a correction retires the earlier links and credentials and
   cancels pending invitations only when a changed contact is the destination of a declared channel
   (`email` ↔ `EMAIL`, `phone` ↔ `SMS`). Accepted consequence: under `ALL_AT_ONCE` `[EMAIL, SMS]`, correcting
   the email kills the link the SMS carried too, because revocation is per recipient, and the new invitation
   goes by email only. Second consequence, derived: a wrong contact that is only a **gate's** destination
   (`OTP_EMAIL` with channels `["SMS"]` or `[]`) no longer revokes the link. That is safe because the link never
   went to that contact. Whoever holds the wrong mailbox received codes but not the link, so they could not
   open a session, and the next code goes to the corrected address.
6. **An addition revokes nothing**: it does not say the old contact was wrong (ADR-0060 §2.5 ties the anchor to
   that admission).
7. **The reaction learns what changed from the fact**, never by re-reading contacts and guessing: both events
   carry the contact kinds, never the values.
8. **An addition's occasion is keyed on its instant**, as the channel change's is
   (`NotifyRechanneledRecipientUseCase`): an addition spends no budget, so it has no ordinal. A redelivery
   carries the same instant and converges; a second addition is a later instant.
9. **Dropping a declared channel after an invitation revokes** (owner, 2026-10-21, after the security gate
   found the hole decision 5 left): `["SMS"]` → link to a wrong phone → re-declare `["EMAIL"]` → correct the
   phone would revoke nothing under decision 5 alone, leaving the wrong holder a live link. So a channel change
   of a sent envelope that removes a channel, for a recipient a link may already have been minted for (step activated, not delegated, not an unclaimed slot; an invitation still in flight counts) on an open leg, retires the
   earlier links and re-invites on the new declaration (`RecipientNotificationChannelsChanged.revokes`,
   ADR-0084 §2.11). Every live link then went out on a channel declared now, which is what decision 5 reads.

## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | A correction re-invites only on the declared channels whose contact it changed (members AC-1a…c) | owner | Application (Notification) + Acceptance | resolve every declared channel |
| AC-2 | An addition spends no correction and records `RecipientContactAdded`, not `RecipientCorrected` (members AC-2a…b) | owner | Unit (aggregate) + Acceptance | route an addition through `correctContact()` |
| AC-3 | An addition re-invites under the correction's conditions, only on the added contact's channel, and sends nothing when that channel is not declared (members AC-3a…b) | owner | Application (Notification) | resolve every declared channel |
| AC-4 | A call that changes one contact and adds the other is one correction, and re-invites on the channels of both | owner | Unit + Application | classify as an addition |
| S-1 | The incident replayed over HTTP: a recipient `["SMS"]` / `OTP_SMS` with no email gets `{"email": ...}` → 200; nothing is sent; `correctionsMade` is still 0; no `RecipientCorrected`; the SMS link still opens the session | owner | Acceptance | the code before this task |
| AC-5 | Each supplied contact is classified added, changed or unchanged (members AC-5a…e) | derived — rule 5 | Unit | compare case-sensitively |
| AC-6 | A call with no changed and no added contact answers 200, records nothing, spends nothing and sends nothing | derived — docs/adr/ADR-0083-a-recipients-gates-are-editable-until-they-enter.md | Application + Acceptance | record on equal values |
| AC-7 | A correction retires links and credentials and cancels pending invitations exactly when a changed contact is a declared channel's destination (members AC-7a…e) | derived — docs/adr/ADR-0060-retiring-a-credential-whose-holder-changed.md | Unit + Acceptance | revoke on every correction |
| AC-8 | An addition revokes nothing: the earlier link still opens, and pending invitations are not cancelled | derived — docs/adr/ADR-0060-retiring-a-credential-whose-holder-changed.md | Unit + Acceptance | revoke on an addition |
| AC-9 | An addition keeps every refusal of the correction except the budget (members AC-9a…i) | derived — src/F5Sign/Envelope/UI/Http/CorrectRecipientController.php | Unit + Acceptance | drop each guard in turn |
| AC-10 | `RecipientCorrected` carries the changed and added contact kinds as a closed key set; a payload logged before this task decodes as "every contact changed", the behaviour of today | derived — rule 5 | Unit (event) | decode an old payload as none |
| AC-11 | `RecipientContactAdded` has a closed key set with the added kinds and no email or phone value | derived — tests/F5Sign/Envelope/Unit/Contract/Event/RecipientNotificationChannelsChangedTest.php | Unit (event) | add an `email` key |
| AC-12 | A redelivered `RecipientContactAdded` converges on one notification; a second addition is its own occasion | derived — tests/F5Sign/Notification/Application/UseCase/NotifyCorrectedRecipientUseCaseTest.php | Application | key the occasion on the recipient only |
| AC-13 | The trail marks "corrected afterwards" only the destinations of the corrected kinds; an addition marks nothing and is stated under its party | derived — tests/F5Sign/EvidenceAudit/Application/Service/TrailAssemblerTest.php | Application (`TrailAssembler`) + Acceptance | mark every destination |
| AC-14 | The classification reads the stored contacts from the envelope loaded under its row lock | derived — tests/F5Sign/Envelope/Application/UseCase/Lifecycle/CorrectRecipientUseCaseTest.php | Application | classify from an unlocked read |
| AC-15 | Regression: correcting the email of an `["EMAIL"]` recipient spends one correction, records `RecipientCorrected`, closes the old link and sends a fresh email invitation, as today | derived — tests/F5Sign/Acceptance/RecipientCorrectionHttpTest.php | existing suites | — |
| S-2 | The security gate's sequence over HTTP: `["SMS"]`, link sent to phone P1; `PUT …/notification-channels` `["EMAIL"]` (with an email); `POST …/corrections` `{"phone": P2}` → the P1 link no longer opens; a fresh invitation went by email | owner | Acceptance | drop the channel-change revocation |
| AC-18 | A channel change revokes exactly when it removes a declared channel from a recipient a link may already have been minted for (step activated, not delegated, not an unclaimed slot, an in-flight invitation included), on a sent envelope and an open leg; when it revokes it re-invites on the new declaration; `revokes` is on the fact as a closed key, and an old payload decodes `false` (members AC-18a…e: drop after invite revokes and re-invites; add-only does not; drop before the step is activated, or for a delegated or unclaimed recipient, does not (a drop while the invitation is in flight DOES revoke); drop on a closed leg does not; the payload key set and old decode) | owner | Unit (aggregate, event) + census + Acceptance | revoke on every change |
| AC-16 | The route's `#[OA\*]` strings state the classification, the budget and the re-invitation channels, with no new code; ADR-0084 lands with its three `docs/adr/README.md` edits; the amended ADRs carry their notes; a frontend handoff for the dashboard | derived — rule 7 | review + `OpenApiSpecTest` | — |

AC-17 is not used: it named a success-body criterion the owner considered and dropped on 2026-10-21 before any code; ids are never renumbered, so the gap stays.

<!-- OFFREPO: the `wt-backend` lane is a target of the f5sign-infra Makefile; its one relevant fact is restated in the line below. -->
- **Gates:** suite, PHPStan, deptrac and lint, under the `wt-backend` lane: an ephemeral stack (its own PHP
  container, Postgres cluster and broker) that mounts this worktree's tree rather than the main checkout's.
- **Reproduction first.** S-1 and AC-1c are written and run red against the unchanged `src/` before their
  fix; the literal failure goes in the slice report.

**Notes on AC-1**
- AC-1a — `[EMAIL, SMS]` declared, the email changed → one email, no SMS.
- AC-1b — `[EMAIL, SMS]` declared, the phone changed → one SMS, no email.
- AC-1c — `["SMS"]` declared, the email changed → nothing is sent (today: an SMS).

**Notes on AC-2**
- AC-2a — the budget is unchanged after an addition.
- AC-2b — an addition is accepted with the budget exhausted.

**Notes on AC-3**
- AC-3a — declared → that channel only.
- AC-3b — not declared → nothing, and no "not sent" fact claims a channel failed.

**Notes on AC-5**
- AC-5a — absent → untouched. AC-5b — stored empty → added. AC-5c — different → changed.
- AC-5d — an email equal but for case → unchanged. AC-5e — a phone written differently with the same E.164 →
  unchanged.

**Notes on AC-7**
- AC-7a — the changed contact is a declared channel's destination → the old link is refused, pending
  invitations are cancelled.
- AC-7b — it is not (`["SMS"]`, email changed) → the old link still opens; the correction is still spent and
  recorded.
- AC-7c — `ALL_AT_ONCE` `[EMAIL, SMS]`, email changed → the link the SMS carried is refused and the new
  invitation goes by email only (the accepted consequence of §4 #5).
- AC-7d — `["SMS"]`, `OTP_EMAIL`, email changed → the old link still opens; the next access code goes to the
  corrected email (the second consequence of §4 #5).
- AC-7e — `EnvelopeCredentialRetirementTest::every_recipient_addressed_gesture_is_classified()` is re-cut: the
  correction is classified as setting the anchor conditionally, and an addition, whether it is a new `Envelope`
  method or a branch of `correctRecipientContact()`, is classified as not setting it. Sabotage: leave the
  correction classified as unconditional.

**Notes on AC-12**
- The discriminator is the addition's instant (§4 #8). Sabotage: key the occasion on the recipient only, and
  watch the second addition converge on the first.

**Notes on AC-9** — each refusal answers its current code and writes nothing:
- AC-9a — envelope not sent (`CONFLICT`). AC-9b — envelope closed or terminal (`CONFLICT`).
- AC-9c — past `expires_at` (`ENVELOPE_EXPIRED`). AC-9d — closed leg (`RECIPIENT_LEG_CLOSED`).
- AC-9e — unclaimed slot (`RECIPIENT_SLOT_NOT_CLAIMED`: a slot is filled by the claim, ADR-0057 §2.3).
- AC-9f — `RECIPIENT_CANNOT_RECEIVE_METHOD`. AC-9g — `PHONE_COUNTRY_NOT_SUPPORTED`.
- AC-9h — unknown envelope or recipient, or another tenant's (404). AC-9i — envelope row busy (503
  `ENVELOPE_BUSY`).

## 6. Open follow-ups (track, don't solve here)

- **Per-contact budgets.** The budget stays one counter over two contacts (TASK-031's open question); this task
  only stops additions from spending it.
- **Per-channel revocation.** §4 #5's consequence exists because a link is revoked per recipient, not per
  channel. Per-channel tokens would remove it; not designed.
- **BL-168 / BL-152** stay open: a correction still leaves the code sent to the old contact alive, and still
  issues a credential beside the old one when nothing is revoked.

- **Closed by this task (2026-10-21).** The three outcomes of a correction (added, changed, unchanged), the
  budget no longer spent by an addition, the re-invitation on the touched channels only, `RecipientContactAdded`
  and the trail's statement of an addition.
- **Deferred, with homes.** BL-445 (an invitation in flight escaping a channel drop's retirement), BL-446 (the SMS
  cost of an addition's re-invitation has no limiter), BL-447 (`RecipientCorrectionHttpTest` drains the relay with
  a fixed 20 pumps); `NotifyAddedContactUseCase` appended to the lists of BL-420 and BL-421.

---

## 7. Deviations & honest notes

### Scope
- The channel change's revocation when it drops a declared channel (decision 9) was added after the security gate
  and is in scope as the header now states; the record was amended for it (`9892dd54`). The trail's wording of an
  addition and the `RecipientCorrected` payload (`contacts_changed`, `contacts_added`, `revokes`) are in the diff
  as ADR-0084 §2.6 and §2.9 anticipate. ADR-0057 §2.14's count of `RecipientCorrected` keys was amended in the
  same branch (`10f3bda7`).

### Decisions made during implementation
- `ContactRevision::classify()` was renamed `fromContacts()`: the value-object rule `factoryNaming` requires
  `from*`/`empty`.
- The voided-trail golden was re-baselined (approved by the owner, slice 03).
- `OneResolutionTest` gained a cited exception: the correction site expects no unsent fact when the declaration is
  `[]` (ADR-0084 §2.7, confirmed by the owner).
- The record's flow paragraph and ADR-0084 §3.1 were corrected: declaring a channel does not re-invite an
  already-invited recipient (ADR-0077 §2.7). No decision changed.
- Owner dropped the `outcome` / `corrections_remaining` response body (no carrier without a cross-cutting change);
  the record amendment was reverted.
- Security gate, first run: `revokesFor` read the current declaration, so declare [SMS], link to the wrong phone,
  re-declare [EMAIL], correct the phone left the wrong holder a live link. Fixed by slices 13 and 14 (revocation
  fires once a link may have been minted, an invitation in flight included).

### Decisions that needed an ADR
- ADR-0084, drafted as Proposed by the plan and accepted by the owner on 2026-10-21 (`e403ec7c`), including its
  five derived points. Now recorded as realized (its Status, §5 and §6).

### Declared and unproven properties
- That a future reaction to `RecipientCorrected` gates on `revokes` wherever it cancels or revokes anything, and
  that the route's published description names the three outcomes: held by review alone (ADR-0084 §5).
- The async race of BL-445: no harness here holds a second connection for the invitation path.
- Infection (diff-filtered to the 33 changed `src/` files, StorageLifecycleScenarioTest excluded per BL-356, worktree `wt-backend` lane, on `6de33f86` whose `src/` equals `cf82c8dc`): covered-MSI 90 %, MSI 85 %; on changed lines 2 escaped, both equivalent (`TrailAssembler.php` nullsafe on a never-null `AuthMethod::tryFrom()`, and `>` vs `>=` on the unique `sys_global_position`; proofs in slice 15), 0 not covered. A first run on `9892dd54` had left 15 alive; 13 were killed by test-only commit `6de33f86`, each seen red by hand.

### Debt left behind, and where it lives now
- BL-445, BL-446, BL-447 (new rows in `docs/BACKLOG.md`); `NotifyAddedContactUseCase` added to BL-420 and BL-421.
- Per-contact budgets, per-channel revocation, BL-168 and BL-152 stay as listed in the follow-ups above.
- Review lows that closed in the branch or are covered by the rows above: the `RecipientCorrectionHttpTest`
  fixed drain (BL-447); the `NotifyAddedContactUseCaseTest` unused `$withSteps` fixture variable and the
  addition-on-an-unsent-envelope case, refused first by the aggregate (slice 04 tests); whole-second revocation
  compare is pre-existing (BL-351, BL-414). ADR-0072's `CORRECTED_AFTERWARDS` wording was handed to docs-sync.

### Delegated work
- Slices (run.log): 01 critical opus 1 round; 02 standard sonnet 0 rounds; 03 critical opus 1; 04 critical opus 1;
  05 and 11 approved; 06 standard sonnet 1; 07 critical opus 1; 08 critical opus 2; 09 standard sonnet 2;
  10 standard sonnet 1; 13 critical opus 2; 14 standard sonnet 2. Slices 13 and 14 answered the security gate. No slice reported a `## Delegated` replication.

### Cost of the run
- Models: opus on the critical slices (01, 03, 04, 07, 08, 13), sonnet on the standard ones (02, 06, 09, 10, 14).
- Rounds: 14 review rounds across the eleven slices that log them, two slices (08, 13) at 2 on opus, two (09, 14) at 2 on sonnet.
- Escalations: two NEEDS_CONTEXT (slice 01 naming rule, slice 03 golden re-baseline), both answered in-run.
- Full suites: baseline 6458 tests, then three green runs (7880, 7899, 7908 tests, the last at `cf82c8dc`); one security-gate fail, repaired by slices 13 and 14.
- Token and money totals are not recorded in run.log; none is claimed here.
