# TASK-037 — the claim's own invitation, sent exactly once, and a wait the sender can see

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/claimed-recipient-invitation`** (code tip `0e58b9a5`; the branch head `7a91c404` adds only documentation), 2026-10-14 — full suite green under the `wt-backend` worktree lane (kept): OK (7233 tests, 81564 assertions), with lint, deptrac (0 violations, 0 uncovered) and PHPStan level 9 clean on the same tree. Pending review and merge. Built: the claim's invitation (command, use case, reactor and both Messenger adapters) under the activation's cause token (§4 D2), the `declared_claimable` and `claimed_at` keys on the `Recipient` object, the census rows, the handoff note and the prose sweep. Left open: the dashboard's adoption (§6 item 1, another repository), the two concurrency/timing warnings homed in [`BL-420`](../BACKLOG.md) and [`BL-421`](../BACKLOG.md), and [ADR-0057](../adr/ADR-0057-claimable-recipient-slot.md), which the owner promoted to `Accepted` on 2026-10-14, every clause being built (until then: *"stays `Proposed` — every clause is built and its promotion is the owner's call"*). The record's earlier re-cut note (2026-10-14, against `develop` at `7e87ce31`) is kept in §4 D2 and in ADR-0057 §2.7's dated amendment. |
| **Type** | Forward build, in the Notification BC and on one published read surface. It adds a notification occasion (command, use case, reactor and its Messenger adapter) and two keys to the `Recipient` object of `GET /api/v1/envelopes/{id}`. No route, no write-side command, no column, no migration. |
| **Why** | ADR-0057 §2.7 and §2.11. A claim landing on a step that is **already active** fires nothing today: the activation fan-out has run, skipped the then-unclaimed slot, and steps do not re-activate — so the eCMR consignee named in transit, the case the whole feature exists for, is never invited. And while a slot waits, the sender cannot cleanly tell *"nobody has been named"* from *"the named party is slow"*: both read `outcome: PENDING`, and the remedies differ (name somebody vs chase somebody). |
| **Builds on** | [TASK-036](TASK-036-claimable-recipient-slot-and-claim.md) (the two facts, the claim route, once-only, `RecipientClaimed`, the fan-out exclusion) · [TASK-031](TASK-031-channel-selection-beyond-email.md) (channels resolved from the recipient's declaration, `RecipientNotificationChannels`) · [TASK-055](TASK-055-delivery-reliability.md) and [ADR-0078](../adr/ADR-0078-delivery-outcomes-come-back-as-facts.md) §2.2 (a missed invitation is a recorded fact, `recordInvitationNotSent`) · [TASK-056](TASK-056-delivery-facts-and-sender-visibility.md) (`invitation_state` on the same `Recipient` object) · [TASK-040](TASK-040-cancellation-notice.md) (the `closedAt` guard) · [ADR-0066](../adr/ADR-0066-no-recipient-acts-before-their-step.md) (`EnvelopeContextView::recipientStepIsActive()`) · [ADR-0055](../adr/ADR-0055-delegated-signature.md) §2.15 (the delegated door) · [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) · [ADR-0056](../adr/ADR-0056-terminal-state-on-pre-credential-routes.md) (an undifferentiated answer is legitimate only where every branch it collapses has the same remedy) |
| **Scope** | ADR-0057 §2.7's notification occasion (its guards and its cause token, amended by this re-cut — §4 D2) and §2.11's read-model keys. Not the claim, not the fan-out exclusion (§3 Out). |
| **Decision record** | [ADR-0057](../adr/ADR-0057-claimable-recipient-slot.md) §2.7 and §2.11. ⚑ **§2.7 is amended by this re-cut**: it required the claim occasion's cause token to be its own; the owner decided on 2026-10-14 that the claim **shares** the activation's token (§4 D2), and §2.7 carries a dated note saying so. No new ADR: Notification already depends on `EnvelopeContract` (`OnRecipientCorrected` imports `RecipientCorrected`), so a second inbound event opens no dependency and needs no `deptrac.yaml` edit. |
| **Delivery bar** | A claimed recipient is invited **exactly once**, in **every** order the claim and the activation of their step can be handled in — claim before activation, claim after activation, and the activation fan-out handled before a late claim reaction — and never before their step is active. |
| **Sibling** | [TASK-036](TASK-036-claimable-recipient-slot-and-claim.md) — the write half of the same ADR, landed. |

---

## 1. Why this task exists

**The claim has no invitation of its own.** `NotifyActivatedStepRecipientsUseCase` invites a step's
recipients when the step activates, reading envelope state fresh when it runs. Against a claim, that gives
three orderings:

- a claim before `send()`, or before its own step activates, **is** invited: when the step opens, the
  fan-out reads a claimed recipient and lets it through (TASK-036's exclusion refuses only an *unclaimed*
  slot);
- a claim on a step that is **already active** is invited by nothing — the fan-out ran before the claim,
  skipped the slot, and will not run again.

The third is the eCMR consignee named while the goods are in transit. And the boundary between the cases is
**relay timing**, not sender intent: the activation fact travels event log → relay → broker, so a claim
racing it lands on either side by chance. Today whether a claimed party is invited at all is partly a coin
flip.

**The wait is only half legible.** An unclaimed slot holds its step open — that is ADR-0057 §2.11's intent —
and publishes `outcome: PENDING`, as does an invited signer who has not acted. TASK-056's `invitation_state`
narrows it (an unclaimed slot reads `null`, an invited one `SENT`), but `null` also means *dormant step* and
*delegated*, so it is not the separator. The two facts the model actually stores — the slot was **declared**
claimable, and **when** it was claimed — are what separate the cases, and neither is published.

⚑ **The wait is bounded now, and this task does not change that.** ADR-0073 (TASK-048 to TASK-050) releases
an unclaimed slot as `RELEASED/UNCLAIMED` when the envelope expires or the step's deadline passes. No
reminder is sent. This task makes the wait legible; it adds no clock.

---

## 2. What already exists (reuse, do not rebuild)

Measured against `develop` at `7e87ce31` on 2026-10-14. Counts below are dated; re-derive them with the
command given rather than trusting the number.

### 2.1 The activation fan-out, and its guards

[`NotifyActivatedStepRecipientsUseCase`](../../src/F5Sign/Notification/Application/UseCase/NotifyActivatedStepRecipientsUseCase.php)
returns early on a closed envelope (`closedAt !== null`, TASK-040), then loops over the activated step's
recipients. Its `continue`s (`grep -c 'continue;'` on the file: **5** on 2026-10-14), in source order:

| Guard | Kind |
|---|---|
| `stepOrdinal !== $command->stepOrdinal->value` | filter: not this step |
| `$recipient->isUnclaimedSlot()` | filter: a slot nobody has claimed (TASK-036 `b0c5eb5`) — ⛔ **built, do not rebuild** |
| `$recipient->signsVia->isDelegated()` | filter: ADR-0055 §2.15's door |
| `$unsentKind !== null`, after `recordInvitationNotSent(...)` | no channel resolved: the miss is recorded, nothing is sent (ADR-0078) |
| `$this->notifications->find($id) !== null` | **idempotency**, not a filter |

Its cause token is `envelope:E|recipient:R|purpose:RECIPIENT_INVITATION` — no step, no generation — and its
own comment calls that triple *"a stable, redelivery-safe cause token"* for *"a recipient's invitation"*,
which fires once. §4 D2 builds on exactly that.

### 2.2 The single-recipient re-invitations, which are the shape to copy

Five Notification use cases mint a signing token today (`rg -l 'tokenIssuer->issueFor' src/F5Sign/Notification`):
the activation fan-out, the correction, the resend, the channel change and the completed-envelope copy. The
claim occasion is the **sixth**. The two closest siblings are single-recipient and carry the same guard
sequence, which is the template:

- [`NotifyRechanneledRecipientUseCase`](../../src/F5Sign/Notification/Application/UseCase/NotifyRechanneledRecipientUseCase.php)
  — the newest (2026-10-13), and the nearest in shape;
- [`NotifyCorrectedRecipientUseCase`](../../src/F5Sign/Notification/Application/UseCase/NotifyCorrectedRecipientUseCase.php)
  — whose class docblock carries the reasoning for each guard.

Their sequence, in order: `closedAt !== null` → return · recipient not resolved by the read → return ·
`signsVia->isDelegated()` → return · `isUnclaimedSlot()` → return · `!$envelope->recipientStepIsActive($recipient)`
→ return · `channels->resolve()`, and on an `unsentKind()` `envelopeFacts->recordInvitationNotSent(..., InvitationPurpose::INVITATION, $command->issuedAt)`
→ return · cause token → find-or-skip → `channels->selection()` → `issueFor()` → `channels->targets()` → `save(Notification::request(...))`.

- `EnvelopeContextView::recipientStepIsActive()` is the shared predicate (ADR-0066 §2.1): matched by step
  id, **fail-closed** on a step the read does not resolve. It replaced the private helper the previous cut
  of this record named.
- The contact is **re-read**, never carried on the event (`platform.event_log` is append-only);
  `RecipientClaimed` carries no identity (ADR-0057 §2.14), so the claim occasion must read too.
- The reactor trio: a command under `Notification/Application/Command/`, a dispatch-only reactor under
  `Notification/Application/Subscriber/` (`OnRecipientCorrected`, `OnRecipientNotificationChannelsChanged`),
  and a Messenger adapter under `Notification/Infrastructure/Messenger/Subscriber/` carrying
  `#[AsMessageHandler(bus: 'event.bus')]` (`OnRecipientCorrectedHandler`).
- Their tests are `tests/F5Sign/Notification/Application/UseCase/NotifyRechanneledRecipientUseCaseTest.php`
  and `NotifyCorrectedRecipientUseCaseTest.php`, hermetic, with fakes for the query port, the repository,
  the issuer and the template archive.

### 2.3 How a purpose is added, and why this task adds none

[`NotificationPurpose`](../../src/F5Sign/Notification/Domain/ValueObject/NotificationPurpose.php)'s own
docblock is the enumeration to trust. The compiler forces a new case's `match` arms; it does **not** force
its copy, which is checked only by `EmailNotificationChannelTest::every_purpose_is_authored_in_the_fallback_locale`
and, since TASK-031, its SMS twin in `SmsCopyTest`. A new purpose owes e-mail **and** SMS copy in every
locale. §4 D1 is why this task owes none.

### 2.4 The cause-token shape

[`NotificationId::fromCause()`](../../src/F5Sign/Notification/Contract/Type/NotificationId.php) is
`v5(NS, causeToken)` over an opaque token. Its **Never** section forbids anchoring on the
`(subject, addressee, purpose)` tuple, because that collapses a genuine re-send (a resend, a correction, a
re-activation) into the first attempt. A new cause is a new occasion with a new id; the same cause arriving
twice converges through find-or-skip.

### 2.5 Channel resolution

[`RecipientNotificationChannels`](../../src/F5Sign/Notification/Application/Service/RecipientNotificationChannels.php)
resolves the channels the recipient declared (ADR-0077): `resolve()` → `unsentKind()` / `selection()` /
`targets()`. `DefaultChannelSelector` no longer chooses `[EMAIL]`; it guards `namesItsOwnChannel()` and
returns the declared channels. A slot declaring `SMS` and claimed with a phone alone is invited by SMS
(ADR-0057 §2.7's dated note of 2026-10-13). Nothing in this task touches channel resolution.

### 2.6 The read model

- [`RecipientView`](../../src/F5Sign/Envelope/Contract/View/RecipientView.php) **already carries**
  `declaredClaimable`, `claimedAt` and `isUnclaimedSlot()`, and **both** hydration sites already select the
  columns (`DoctrineEnvelopeReadRepository`, the read `SELECT`; `DbalEnvelopeRepository`, the write-side
  load). The one read feeds both `GET /api/v1/envelopes/{id}` and Notification's
  `EnvelopeQueryInterface::getEnvelopeContext()` (`EnvelopeQueryAdapter` delegates to the same query).
- [`EnvelopeJsonPresenter::recipient()`](../../src/F5Sign/Envelope/UI/Http/EnvelopeJsonPresenter.php)
  publishes neither fact. It publishes `invitation_state` (TASK-056), which `InvitationState::of()` answers
  `null` for an unclaimed slot. Read its existing comments before adding keys: they record why
  `first_opened_at` is flat, and why `accessCodeHash` must never reach this method.
- So the read-model half is **presenter + schema only**.

### 2.7 The published-contract surface

The `Recipient` schema lives in [`config/packages/nelmio_api_doc.yaml`](../../config/packages/nelmio_api_doc.yaml).
`tests/F5Sign/Acceptance/OpenApiSpecTest.php` checks that every response schema publishes exactly the keys
its presenter emits, in both directions, and maps `recipients` to `Recipient` — confirm the check reaches
`Recipient` (sabotage: add the key to the presenter only) before citing it. Its enum census is untouched:
§4 D6 publishes no enum.

### 2.8 The minting-site census

`tests/F5Sign/Session/Application/Query/SigningReadersRefuseUnsentEnvelopeTest.php` classifies every caller
of `SigningTokenIssuer::issueFor(` on three axes, and a new caller turns the census red until it has a row
on each:

- `ISSUER_CALLERS` — `[count, unsentCaseClass, unsentMethod, delegatedCaseClass, delegatedMethod]`. The
  delegated columns may only be answered by **a case that drives a delegated recipient**, never by an
  argument about the trigger.
- `SLOT_CLASSIFIED` — `ASKS` / `DELEGATES` / `UPSTREAM`, plus the case that proves it; an `ASKS` site must
  spell the conjunction `isUnclaimedSlot()`.
- `STEP_ISSUER_CLASSIFIED` — the same three values on the step axis; an `ASKS` site must carry
  `recipientStepIsActive(`.

Each row's named case must exist (`every_*_row_names_a_case_that_exists`).

### 2.9 The handoff format

[`docs/frontend-handoff/`](../frontend-handoff/README.md) names files `TASK-NNN-<slug>.md`, with the
README's header table; its template headings and every existing note are in Spanish; recent notes put the audience in the slug
(`TASK-NNN-<audience>-<slug>.md`), which is practice rather than a README rule. The nearest model for an
additive key on this same object is `TASK-056-dashboard-integrator-invitation-state.md`.

---

## 3. Scope

### In

1. **The claim's notification occasion** — `NotifyClaimedRecipient` (command), `NotifyClaimedRecipientUseCase`,
   `OnRecipientClaimed` (reactor) and `OnRecipientClaimedHandler` (Messenger adapter on `event.bus`), with
   §2.2's guard sequence, the invitation purpose (D1) and the activation's cause token (D2). Its tests at the
   `Notification/Application` tier.
2. **Its census rows** on all three axes of §2.8 (D5), each with the case that proves it.
3. **The read-model keys** — `declared_claimable` and `claimed_at` on `recipients[]` of
   `GET /api/v1/envelopes/{id}`, in the presenter and the `Recipient` schema (D6).
4. **The handoff note** to the dashboard and integrator (D7).
   <!-- OFFREPO: the note is read in the dashboard and integrator repositories; the in-repo deliverable is the file itself -->
5. **ADR-0057** — §2.7's dated amendment (D2); §5's preamble, bar rows 7 and 12, `Status` and §6, per
   that section's own instruction.
6. **The rule-1 sweep** of the prose this task falsifies: the delegated-door count — *"the count is five"* in
   `NotifyCorrectedRecipientUseCase` (wrapped across two comment lines, so grep `is five`), and the door enumeration in
   `SigningTokenIssuance` (*"a fifth door could land"*), which must name the claim occasion (that list
   already omits the completed-envelope copy; say so or add it, do not leave it silently short); the `DoctrineEnvelopeReadRepository`
   comment that names the keys as TASK-037's; [`BL-255`](../BACKLOG.md), which this re-cut resolves; and the
   activation fan-out's token comment, which must now say that the claim shares the token on purpose (D2).
   Scope by `rg`, never by directory: `rg -n 'TASK-037|stepHasActivated|is five|own cause token|its own token' src tests config docs`.

### Out

- **Everything TASK-036 built**: the facts and their migration, the claim route and use case, once-only,
  replay, `RecipientClaimed`, the issuer refusal, the correction refusal, the fan-out exclusion.
- **Channel resolution** (TASK-031) — consumed unchanged.
- **Bounding or chasing the wait** — ADR-0073 releases; reminders are nobody's yet.
- **Self-claim** (ADR-0057 §2.9), **in-person signing** ([`BL-191`](../BACKLOG.md)),
  **a `CERTIFIED_DELIVERY` slot's completion path** (ADR-0057 §2.17).
- **The dashboard's rendering** of the two keys — another repository's change.
  <!-- OFFREPO: the dashboard frontend repository consumes the read model; nothing here depends on it, and the in-repo half is the schema plus the handoff note -->

---

## 4. Key decisions

### D1 — The claim reuses `RECIPIENT_INVITATION`: a new occasion, not a new purpose

The claimed party has never been written to, so what they need is the invitation itself — the same
semantics as the activation's. A new purpose would owe e-mail and SMS copy in every locale to say what the
existing copy says (§2.3). ▶ What would force one: copy that must differ (*"you have been named as the
consignee"*), which nobody has asked for.

### D2 — The claim shares the activation's cause token; the two triggers are one occasion

⚑ **Decided by the owner 2026-10-14; amends ADR-0057 §2.7**, which required a token of the claim's own.

The token is the activation's, byte for byte:

```
envelope:<id>|recipient:<id>|purpose:RECIPIENT_INVITATION
```

**Why the previous cut was wrong.** It gave the claim its own token (`…|claim`) and held *exactly once* on
the step guard alone. That holds only when the claim reaction runs before the activation. Both reactions
read envelope state fresh, are separate handlers on an async transport with retries, and may run in either
order. If the activation fan-out runs **first** on a step whose slot was already claimed, it invites the
party; when the claim reaction runs **afterwards** (a slower worker, a retry, a redelivery), it reads a
claimed recipient on an active step, passes every guard, and — with a different token — mints a second
live credential and creates a second notification. Nothing converges them.

**Why sharing is right, not merely convenient.** Both triggers mean the same thing for this recipient:
*their invitation is now due*. The activation's token already names exactly that occasion — once per
recipient, no step, no generation — and the claim is once-only (TASK-036), so there is no second claim
whose send a shared token could swallow. Find-or-skip then converges every order:

| Order | Result |
|---|---|
| claim reaction on a dormant step, activation later | claim withholds (step guard), activation sends |
| claim reaction on an active step, activation redelivered later | claim sends, activation skips |
| activation first (slot already claimed), claim reaction late | activation sends, claim skips |
| activation before the claim committed, claim reaction after | activation skips the unclaimed slot, claim sends |

⛔ **This is not the re-anchoring `NotificationId`'s Never section forbids.** That rule forbids collapsing
genuine re-sends — resend, correction, re-channel — into the first attempt; each of those keeps its own
counter in its token, untouched. Here two triggers of **one** occasion converge, which is what cause-derived
ids exist for.

⚠ **What it costs.** The stored notification no longer says which trigger sent it. Nothing reads that.
⚠ **What it does not cover.** Two reactions running **concurrently** both see no row and may both mint before
either saves; that is the same window every find-or-skip in this BC already has under concurrent redelivery,
and this task does not widen or close it.
▶ **What would break it:** re-assignment (ADR-0057 §2.4 defers it). A second occupant of the slot needs a
generation in the token, on both paths.

### D3 — The occasion carries its siblings' guards, in their order

§2.2's sequence, each for its siblings' reason:

- **`closedAt`** — a claim recorded while open may be handled after the envelope closed (`claimRecipient`
  is refused only at write time); a credential must not go out then.
- **`isDelegated()`** — ADR-0055 §2.15: the sixth door, and a claimable slot may be declared delegated.
- **`isUnclaimedSlot()`** — see D5 for whether the site asks or relies on its trigger.
- **`recipientStepIsActive()`**, **before the mint** — a claim on a dormant step (the eCMR consignee behind
  the consignor) must mint nothing: a token is a live credential whether or not anything mails it. The
  invitation is not lost: the fan-out sends it when the step opens, with the same token (D2). A claim on a
  `DRAFT` envelope (legal pre-send) is withheld by the same guard, and `send()` invites through the fan-out.
- **`resolve()` / `recordInvitationNotSent`** — a claimed slot whose declared channels resolve nothing has
  the miss recorded (ADR-0078), so `invitation_state` reads the miss rather than waiting for ever. The
  instant is the event's. ⛔ **The claim reaction records the miss only when the read shows none
  (`$recipient->invitationUnsentAt === null`).** `Recipient::recordInvitationNotSent()` is forward-only on
  the instant, so in D2's third order (activation first, at `T_a`; claim reaction late, at `T_c > T_a`) a
  second record would move the instant and emit a second `RecipientInvitationOutcomeRecorded` for the same
  miss. The shared token converges the send; this converges the miss. ⚠ The skip also holds when the
  stored kind differs from what the claim's own `resolve()` would answer now: the stored kind is whichever
  path recorded last, and the correction, resend and re-channel reactions record their own misses. The activation fan-out is unchanged.

### D4 — The fan-out exclusion: built, and governed by ADR-0057 §2.7

The `isUnclaimedSlot()` `continue` in the fan-out reads **both** facts (declared AND unclaimed). Keyed on the
declaration alone, a claimed recipient is muted for ever; keyed on *unclaimed* alone, it says nothing about
whether the emptiness was intended. It is placed by ADR-0057 bar 1 and not edited here.

### D5 — The census rows

The claim occasion's rows (§2.8), each answered by a case this task writes:

- **`ISSUER_CALLERS`** — unsent axis: a claim is legal on a `DRAFT` envelope, so no trigger argument
  holds; the case is *a claim on an envelope that was never sent mints nothing*. Delegated axis: a case that
  drives a delegated claimed recipient and asserts nothing is minted.
- **`SLOT_CLASSIFIED`** — `ASKS`, with the conjunction guard and the case that drives a recipient the read
  reports as unclaimed, as the rechannel and correction sites do. `RecipientClaimed` only fires for a claimed
  slot, so the guard is defensive; it is kept because its siblings carry it and a projection read is not the
  event.
- **`STEP_ISSUER_CLASSIFIED`** — `ASKS`, the case being bar 2's dormant-step arm.

⚠ **The fixture trap the census already caught once**: a case meant to prove a step refusal, with one
recipient on one step, has no later step to activate and stays green with the guard deleted. Put the slot on
step 2 or later, use no `self::fail()` before the assertion that matters, and sabotage it.

### D6 — The read model publishes two keys, flat, and widens no enum

`recipients[]` gains:

| Key | Type | Meaning |
|---|---|---|
| `declared_claimable` | `boolean`, always present | the sender declared the slot fillable after send; `false` for every ordinary recipient |
| `claimed_at` | ISO-8601 `string` or `null` | when the slot was filled; `null` on an unclaimed slot **and** on an ordinary recipient |

The wait is `declared_claimable === true && claimed_at === null`. Two keys because the model has two facts;
`claimed_at` being `null` in two situations is not a collapse, because `declared_claimable` separates them.
Not a new `outcome` member (the leg genuinely is `PENDING`, and `outcome` is a published enum), and not
nested under a `claim` object (flat, like `first_opened_at` and `invitation_state`). `declared_claimable`
rather than `claimable`, because the short name reads as *"can be claimed now"*, which is the other key's
question.

### D7 — The handoff note

`docs/frontend-handoff/TASK-037-dashboard-integrator-claimable-wait.md`, in Spanish, per the README. It
carries:

1. The two keys, additive; nothing changes type or disappears.
2. **The rule**: the wait is `declared_claimable === true && claimed_at === null`. Do not branch on
   `declared_claimable` alone, and do not infer an unclaimed slot from a missing contact or from
   `invitation_state: null` (which also means a dormant step or a delegated recipient).
3. **The claimed party is now invited** when the claim lands on an active step, once — the eCMR case
   the dashboard is waiting on — and no workaround (claim then correct) is needed.
4. **What is not ready**: no reminder for an unclaimed slot. **What will never exist**: re-assignment of a
   claimed slot.
5. Origin commit, and deployed vs merged.

<!-- OFFREPO: the note's readers work in the dashboard and integrator repositories; nothing here depends on them -->

---

## 5. Verification

**Harness.** This is a worktree: run through the worktree lane (`wt-backend` targets with `src=` set to the
worktree), never the main checkout's targets, which validate another tree.
<!-- OFFREPO: the lane targets live in the infra repository's Makefile; nothing in this record's properties depends on how the lane is built -->
Bars 1, 2 and 4 are hermetic (`Notification/Application`); bar 3 runs against the database.

### Bar 1 — exactly once, in every order (ADR-0057 §5 bar 7)

`NotifyClaimedRecipientUseCaseTest` (new), driving the claim occasion and the activation fan-out over the
**same** `FakeNotificationRepository` and `FakeSigningTokenIssuer`, slot on **step 2**, asserting over the
**whole** repository and the issuer's count, never scoped to one id:

1. **Dormant step**: claim reaction → 0 notifications, **0 tokens issued**. Activate step 2, run the fan-out
   → exactly 1 notification, 1 token.
2. **Active step, claim first**: claim reaction → 1 and 1, addressed to the claimed recipient, with a link.
   Run the fan-out for that step again (a redelivery) → still 1 and 1.
3. **Active step, activation first**: the slot is claimed in the read, the fan-out runs → 1 and 1; then the
   claim reaction → still 1 and 1. ⛔ **This is the arm the previous cut had no test for.**
4. **Draft envelope**: claim reaction → 0 and 0.

**Sabotage**: (a) give the claim occasion its own token (append `|claim`) → arm 3 must go to **2 and 2**;
(b) delete the step guard → arm 1's first half must go to 1 and 1. Check which assertion fired.

### Bar 2 — the occasion carries its siblings' guards

In the same test class, one case per guard, each with a recipient that **differs from a control** in the
guarded property only: a closed envelope sends nothing; a delegated claimed recipient is sent nothing and
nothing is minted; a recipient the read reports unclaimed is sent nothing; a claimed recipient whose
channels resolve nothing has `recordInvitationNotSent` called once with `InvitationPurpose::INVITATION` and
is minted nothing; and a claimed recipient whose read **already** shows a recorded miss has nothing
recorded again (D3). ⚠ The recording fake has no forward-only logic, so it pins only the reaction's own
skip; the aggregate's behaviour is `Recipient::recordInvitationNotSent()`'s and is covered where it lives.
These are the census's named cases (D5).

### Bar 3 — the read model separates the wait (ADR-0057 §5 bar 12)

`Envelope/Acceptance`, through the claim route and `GET /api/v1/envelopes/{id}`. One envelope, three
recipients, all `outcome: PENDING`: an unclaimed slot (`true`/`null`), a claimed recipient who has not acted
(`true`/the claim's instant), an ordinary recipient (`false`/`null`). Assert the pair per recipient.
**Sabotage**: publish `declared_claimable` as `$recipient->claimedAt !== null` → the unclaimed slot reads `false` and is indistinguishable from the ordinary recipient.
`OpenApiSpecTest`'s closed key set gates the schema; sabotage it once (presenter key without the schema
entry) to confirm it reaches `Recipient`.

### Bar 4 — the claim's invitation is the invitation

The occasion carries `RECIPIENT_INVITATION`, resolves the locale `recipient → tenant → system`, and pins a
template — the shape of `NotifyActivatedStepRecipientsUseCaseTest::each_addressee_is_authored_in_the_locale_the_chain_resolved_for_them`.

### Wiring

`OnRecipientClaimedHandler` is registered: `debug:messenger` from the worktree lane lists it on `event.bus`
for `RecipientClaimed`. A reactor that is not wired is silent, and no bar above sees it.

### The census

`SigningReadersRefuseUnsentEnvelopeTest` green with the three new rows; drop one row and it fails naming the
use case.

### What no bar here can see

- Whether a message leaves: `async_events` is `in-memory://` in test.
- The concurrent window of D2: one connection, one process.
- Whether the party named in a claim is the right party: the integrator's assertion.
  <!-- OFFREPO: the integrator is the API client that names the party; nothing in this repository can check its choice -->

---

## 6. Open follow-ups (track, don't solve here)

1. **The dashboard's adoption** of the two keys and of the claim's invitation. ▶ Forced by: the handoff note
   landing; the dashboard has deferred its eCMR flow on this task.
   <!-- OFFREPO: the dashboard repository; nothing here waits on it -->
2. **No reminder for an unclaimed slot.** ▶ Forced by: the first customer who asks to chase a stalled slot
   before its deadline.
3. **A claim on a `CERTIFIED_DELIVERY` slot succeeds and its leg can never close** (ADR-0057 §2.17,
   [`BL-190`](../BACKLOG.md)). ▶ Forced by: the first tenant authoring one.
4. **Re-assignment** would need a generation in the shared token on both paths (D2). ▶ Forced by:
   ADR-0057 §2.4 being reopened.

---

## 7. Sequencing

TASK-036 landed first and carries its own fan-out exclusion, so its state alone leaks nothing — but it is
**stalled** for a claim on an already-active step, which nothing invites until this task lands. The two
records agreed on one shape: `claimed_at` is stored as an instant (TASK-036 §4), which is what lets D6
publish *when* rather than a boolean.

The claim occasion sees a claimed slot because by the time it runs the claim has committed: the event
reaches Notification through the ADR-0031 relay, which hands on only committed transactions. Notification
mints through the raw `SigningTokenIssuer` port, which carries no slot guard (`SigningTokenIssuance` guards
the sender-side mint route only), so what stands between an unclaimed slot and a credential here is the
occasion's own `isUnclaimedSlot()` guard (D3, D5). A synchronous dispatch that ran before the claim
committed would read the slot as unclaimed and silence the occasion.

---

## 8. Deviations & honest notes

### Scope
- Two files beyond the four classes §3 lists, both because every sibling has them: `Infrastructure/Messenger/Command/NotifyClaimedRecipientHandler` and a `services.yaml` binding (the use case is unreachable without the first, and the container cannot bind `$signingBaseUrl` without the second). One `Integration/` crossing test, `ClaimInvitesCrossingTest`, was added as the channel-change sibling has one, to hold the wiring, the payload round trip and D2's fourth order on the real stack.
- Slice 07 (closing) was not in the original cut: the closing review found three stale present-tense claims the branch itself falsified, and slice 07 corrected them (`SigningTokenIssuance` and the `ISSUER_CALLERS` docblocks, a `'claimed'` arm in `OneResolutionTest`, a dated note appended to ADR-0058 §2.3).

### Decisions made during implementation
- No new ADR: no accepted ADR is contradicted, Notification already consumes Envelope `Contract/` events (`OnRecipientCorrected`), and no `deptrac.yaml`, PHPStan or baseline edit was needed.
- The command carries no step ordinal and no instant in its cause: the use case reads the step fresh and the token is the activation's.
- A recorded miss is skipped on the read's `invitationUnsentAt !== null`, whatever its stored kind.
- The draft case is held by the step guard, not by a `sentAt` check: a draft has no active step. The census's unsent column points at the case that proves it (`a_claim_on_an_envelope_that_was_never_sent_mints_nothing`).
- The two new keys sit right after `released_by`, because `EnvelopeJsonPresenterTest::it_publishes_the_five_invitation_keys_and_no_more` pins that run.
- The handoff note was written by this task (slice 06) rather than left to docs-sync, because §3 In 4 makes it a deliverable.
- Slice 02: the first sabotage (dropping `#[AsMessageHandler]`) cannot go red, because `services.yaml` `_instanceof` tags every `MessengerEventSubscriber` onto the event bus; the guard was proved by dropping the attribute and the `implements` together. Red-first was not observed for that one guard.
- Slice 07: one `OneResolutionTest` docblock line is left unwrapped (192 characters), cosmetic, to keep the tip the full suite ran on.
- ADR-0057's edits landed in slice 05, after the commits that place bars 7 and 12: the ADR preamble's "in the same commit" is met at changeset level, not literally.
- A full-suite run on `4018f904` was red twice over: `EnvelopeHttpTest`'s closed key set (ours, fixed in `b0dfd5a6`) and `StorageLifecycleScenarioTest` ([`BL-356`](../BACKLOG.md), passes alone on the same tree).

### Decisions that needed an ADR
- [ADR-0057](../adr/ADR-0057-claimable-recipient-slot.md) §2.7 was amended by the owner on 2026-10-14 (the claim shares the activation's cause token, §4 D2). The owner promoted the ADR to `Accepted` on 2026-10-14 (it read *"The ADR stays `Proposed`"* until then); this task exercises every clause (the claim's invitation by `NotifyClaimedRecipientUseCaseTest` and `ClaimInvitesCrossingTest`, the two keys by `EnvelopeJsonPresenterTest` and `EnvelopeHttpTest`), and its promotion was returned to the owner as a proposal, then applied on their acceptance.

### Declared and unproven properties
- Whether a message leaves: `async_events` is `in-memory://` in test.
- The concurrent window of D2 (two reactions both passing find-or-skip): one connection and one process cannot reach it. Homed in [`BL-420`](../BACKLOG.md).
- A claim reaction arriving after the claimed member was released by a step deadline: the predicate it shares with its siblings means "activated", not "open". Probably unreachable, never driven. Homed in [`BL-421`](../BACKLOG.md).
- Whether the party named in a claim is the right party: the integrator's assertion.
- **Final, on the tree `develop` receives** (`ed15cbd5`, `develop` `1262d9ec` merged in, which brings TASK-059's audit-trail invitations): the full suite is green on the worktree lane, OK (7255 tests, 82370 assertions), with lint, deptrac and PHPStan clean. Infection, filtered to the 14 `src` files that differ from `develop` (435 s): **0 escaped, 0 uncovered and 0 timed out on the 411 changed lines**. Whole-file figures, as information: 887 mutants, MSI 88 %, covered-MSI 90 %. The merge needed one fix that no textual merge shows. TASK-059's trail stated an empty invitation list, meaning *"the platform invited none"*, for a claimable slot claimed after its step activated, and this task now invites exactly that slot. So `TrailAssembler::invitations()` exempts only a slot the log never records as claimed (`302be97a`, `ed15cbd5`), and the slot otherwise reads `OUTCOME_NOT_RECORDED` like any other party.
- Earlier run, before the merge: Infection, filtered to the diff's 12 `src` files, on the worktree lane at `2b036801` (447 s): **0 escaped and 0 uncovered mutants on the 393 lines this branch changed**, which is the lane's verdict. The whole-file figures are information only: 356 mutants, covered-MSI 78 %, MSI 74 %. The survivors sit on lines that predate the branch, mostly in `EnvelopeJsonPresenter`, plus 18 uncovered in `RecipientView` and `DoctrineEnvelopeReadRepository`. The first run, at `393197dd`, found three escaped mutants on changed lines: the claim invitation's template variables (`recipient_name`, its `?? ''`, `envelope_title`) were pinned by no test. `2b036801` adds `NotifyClaimedRecipientUseCaseTest::the_claims_invitation_carries_the_closed_set_of_invitation_variables`, and each of the three was sabotaged red by hand before the re-run. ⚠ This re-run was launched by the orchestrator directly rather than through the validation agent, against the workflow's rule; the result was read from the lane's own log.

### Debt left behind, and where it lives now
- Dashboard adoption of the two keys and of the claim's invitation: §6 item 1 (another repository; the handoff note is landed).
- Unclaimed-slot reminders: §6 item 2, now also indexed by [`BL-399`](../BACKLOG.md) (no reminders for an unopened invitation).
- `CERTIFIED_DELIVERY` slot whose leg can never close: §6 item 3, [`BL-190`](../BACKLOG.md).
- Re-assignment needs a generation in the shared token: §6 item 4, [`BL-193`](../BACKLOG.md).
- The find-then-mint concurrent window: [`BL-420`](../BACKLOG.md). The late reaction after a release: [`BL-421`](../BACKLOG.md).
- [`BL-195`](../BACKLOG.md) restated ADR-0058's "two minting sites react to triggers only a sent envelope can fire" in the present tense; it now carries a dated qualifier (the claim's invitation is the first whose trigger a draft can produce). [`BL-255`](../BACKLOG.md) moved to the Closed table in slice 05.

### Delegated work
- Slice 01 (critical): opus, 0 review rounds, DONE (158,798 tokens). Slice 03 (standard, review opus): sonnet, 0 rounds, DONE (114,600). Slice 02 (standard): sonnet, DONE_WITH_CONCERNS, approved by a sonnet reviewer (102,088). Slice 04 (mechanical): sonnet, DONE, approved. Slices 05 and 06 (standard, docs): the reviewer found one miss in each (BL-255 left in the Open table; the release reasons named wrongly in the note) and the orchestrator fixed both. Slice 07 (critical): opus, approved.
- No slice used the `replicator`: every report's `## Delegated` reads none or "under the 3-target threshold".

### Cost of the run
- Slice implementers (tokens reported in run.log, three of seven): opus 158,798 (slice 01); sonnet 216,688 (slices 03 and 02).
- Slices 04 to 07 reported no token figure in run.log: not measured.
- Reviews: slices 01 and 03 on opus; 02, 04, 05, 06 on sonnet; closing review on opus (one round, three findings, all fixed in slice 07).
- Rounds: 1 fix round (slice 05, by the orchestrator), 0 escalations beyond the planned critical tiers.
- Full-suite runs: baseline 6031 tests; red on `4018f904` (two failures attributed above); last green `0e58b9a5`, 7233 tests, 81564 assertions.
