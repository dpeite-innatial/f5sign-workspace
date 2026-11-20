# TASK-031 — A recipient declares the channels that reach them, and a recipient nobody can reach is shown

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/channel-selection`** (2026-10-14) — last green full suite on the code tip **`20497fa1`: 6856 tests / 78433 assertions**, lint, deptrac and PHPStan clean (wt-backend lane on the worktree, `full-suite-final.log`). Phase 3 gates: task-validate pass with warnings; doctrine-guard, contract-check and security-audit warn with 0 blocking, their accepted fixes in `94045d58` and `6f4421c2` (§12). **Infection (changed-line gate, 98 `src` files):** the first run on `6f4421c2` left 27 mutants escaped on changed lines; 18 were killed by tests, 3 exposed dead code that was removed (`4130aaab`, `57f919f2`, `20497fa1`), and the 6 left are equivalent and accepted by the orchestrator (two `break`s in a lookup over unique ids, two email coalesces where only presence is checked, two `isset`-only set values; §12). ADR-0077 moved to **Accepted (enforcement partial)** by the owner on 2026-10-14 (`b9c2a4d3`): §2.10 waits on TASK-057. |
| **Type** | **Forward build** across Envelope (authoring contract, resolution, the channel-change operation, resend guard, read model), Notification (selection, an ordered delivery policy, a terminal "not needed" delivery status, five creation sites) and Identity & Access (one tenant capability). |
| **Why** | A recipient with no email receives **nothing** and nobody is told. Found on the dev stack on 2026-10-08: an eCMR waybill whose carrier and consignees had only a phone was sent, the carrier's step activated, and no invitation was created — no occasion, no `invitation_sent_at`, no `invitation_failed_at`. Every Notification use case skips `email === null` with a bare `continue`/`return`, and the selector answers `[EMAIL]` for every purpose. [BL-173](../BACKLOG.md), [BL-227](../BACKLOG.md) and [BL-228](../BACKLOG.md) are the same hole reached through invitation, correction and resend. |
| **Decision record** | [ADR-0077](../adr/ADR-0077-a-recipient-declares-the-channels-that-reach-them.md) — **Accepted** (2026-10-19; *Accepted (enforcement partial)* from 2026-10-14, when the §6 bars below went green, until [TASK-057](TASK-057-sms-spend-guards.md) landed §2.10). It amends [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) §2 and applies [ADR-0065](../adr/ADR-0065-recipient-delivery-is-its-own-dimension.md). Its siblings [ADR-0078](../adr/ADR-0078-delivery-outcomes-come-back-as-facts.md) and [ADR-0079](../adr/ADR-0079-a-delivery-retries-by-what-it-carries.md) are realized by other tasks (below). Its §2.10 (spend guards) is [TASK-057](TASK-057-sms-spend-guards.md), **not this task**. |
| **Builds on** | **Prerequisites, in this order:** [TASK-055](TASK-055-delivery-reliability.md) (the transient `FAILED` kind that §3.6's fallback moves on, and the send-time re-check and cancellation that §3.9's channel change triggers) and [TASK-056](TASK-056-delivery-facts-and-sender-visibility.md) (the trace-only per-destination refusal §3.6 skips, and the recorded invitation state §3.9 reads). Then: [TASK-030](TASK-030-sms-delivery-channel.md) (the SMS channel and its copy for every purpose, landed 2026-08-20), [TASK-023](TASK-023-sms-codes-and-recipient-phone.md) (the recipient's phone and the delivered code's own channel), [ADR-0065](../adr/ADR-0065-recipient-delivery-is-its-own-dimension.md), [ADR-0054](../adr/ADR-0054-ordered-auth-method-list.md) (the ordered-list authoring shape this mirrors), [ADR-0057](../adr/ADR-0057-claimable-recipient-slot.md) (the deferred destination check) and [ADR-0055](../adr/ADR-0055-delegated-signature.md) (the delegated recipient). |

---

## 1. Why this task exists

A notification reaches a recipient only by email, so a recipient authored with only a phone — the
carrier in an eCMR flow — is never invited, never resent to, and never told the envelope ended. The
authoring side accepts them (`AddRecipientRequest` makes `email` and `phone` both nullable), sending
does not check whether anyone can be told, and nothing records that an invitation was not sent, so the
envelope looks healthy while it is stuck.

The repair is not a tenant-wide switch that adds SMS beside email, and it is not a hidden default. The
integrator authoring the envelope knows how each party is reached, so [ADR-0077](../adr/ADR-0077-a-recipient-declares-the-channels-that-reach-them.md)
makes it **say so, per recipient, always**: `notification_channels` is required, a list of two or more
also states how it is used (`notification_mode`), what cannot be met is refused at authoring, and a
recipient the platform sends nothing to (`[]`, the integrator delivers the link through
`POST /api/v1/signing-tokens`) is a supported, visible state rather than a silent one.

Why required and not defaulted: with any default that reaches a phone, the day a tenant is enabled for
SMS every recipient with an email, a phone and `OTP_SMS` would receive the link on the handset too — in
envelopes already in flight — losing the second factor with nobody deciding it, and every notice would be
duplicated at a per-message cost. Nothing is in production, so the stricter contract costs only the
callers listed in §3.11.

## 2. What already exists (reuse, do not rebuild)

Each line below was checked against the tree on 2026-10-09; re-run the command beside it before relying on
it, because this record is not rebuilt when the tree moves.

- **The occasion is already multi-channel.** `DeliveryTarget` carries a channel, its template pin and its
  own `ContactPoint`, and `Notification::request()` materializes one `Delivery` per target and emits one
  `DeliveryRequested` per child. `DeliveryPolicy` has `ANY` / `ALL` / `SINGLE` with `isDefeated()` derived
  from `isSatisfied()`; only `SINGLE` has ever run.
- **`DeliveryStatus` already has the terminal `NOT_NEEDED`** (TASK-055, [ADR-0079](../adr/ADR-0079-a-delivery-retries-by-what-it-carries.md)
  §2.5; `rg -n 'case ' src/F5Sign/Notification/Domain/ValueObject/DeliveryStatus.php`). Today it means *the world
  moved on*: `TransmitDeliveryUseCase` sets it on the one delivery it was asked to send when the send-time re-check
  answers no, and `CancelPendingInvitationsUseCase` sets it on every pending delivery of a cancelled occasion.
  `Notification::needed()` leaves it out of the total, so `isDelivered()` / `isUndeliverable()` fold only over the
  deliveries still needed, and `isTerminal()` counts it. No new status and no deploy-ordering step are needed.
- **`RecipientView` already carries the phone** (`Envelope/Contract/View/RecipientView.php`, TASK-023) and
  Notification reads it through `EnvelopeQueryInterface::getEnvelopeContext()`. No Notification use case reads
  it for a destination yet: each builds `ContactPoint::of($recipient->email)`.
- **Five selector call sites.** `rg -n '\$this->selector->select\(' src` lists them: the activated-step
  (`NotifyActivatedStepRecipientsUseCase`), corrected (`NotifyCorrectedRecipientUseCase`), resent
  (`NotifyResentInvitationRecipientUseCase`), completed (`NotifyCompletedEnvelopeRecipientsUseCase`) and ended
  (`NotifyEndedEnvelopeRecipientsUseCase`) reactions. Each has an `email === null` branch and an `SMS` arm that
  throws `UnroutableChannelException`. In the three invitation-family reactions (activated, corrected, resent) that
  branch is not a bare skip since TASK-056: it records `EnvelopeFacts::recordInvitationNotSent(…,
  NOT_SENT_NO_REACHABLE_CHANNEL)`. The completed and ended reactions still `continue` with nothing recorded. `OneTimeCodeDeliveryService` **does not** ask the selector — it builds its
  own `SINGLE` selection from the requested medium — and `DefaultChannelSelector` throws for the three
  `AUTH_OTP_*` purposes. Both must stay so (§4).
- **The destination trace exists.** `Recipient::correctContact()` forgets the trace of the destination it
  replaces, and `delivery_trace` is keyed per destination (`MOBILE_PHONE` / `EMAIL_ADDRESS`). What writes it
  today is `OnNotificationFailed` → `PropagateDeliveryFailureUseCase`, and only when the **whole** occasion fails
  and only for purposes where `NotificationPurpose::carriesMeansToAct()` holds. ADR-0077 §2.6 skips a destination
  the trace records as refused; TASK-056 added the per-destination write beside a landed channel
  (`PropagateDestinationRefusalUseCase`, reached from `OnDeliveryFailed`), so the skip fires on a trace-only
  refusal too. Both propagation use cases were written for fan-out: §3.6 walks them for a held `IN_ORDER` tail.
- **The signing credential is minted once per recipient per occasion** in `NotifyActivatedStepRecipientsUseCase`,
  after the idempotency guard, and the same link goes into every target's variables.
- **The claimable and delegated filters.** `Recipient::declared_claimable` / `claimed_at` and `SignsVia` /
  `isDelegated()` already exist. `NotifyEndedEnvelopeRecipientsUseCase` has no delegated/unclaimed `if`, but its audience is
  `NotificationRepository::addresseesFor(…, RECIPIENT_INVITATION)` and `NotifyActivatedStepRecipientsUseCase` skips
  a delegated recipient before any occasion exists, so **a delegated recipient receives no ending notice today**;
  `NotifyResentInvitationRecipientUseCase` refuses a delegated recipient, and
  `NotifyCompletedEnvelopeRecipientsUseCase` withholds the credential from delegated and unclaimed recipients.
  ([BL-194](../BACKLOG.md): the order of those `continue`s is load-bearing.)
- **The phone predicate and its callers.** `LibPhoneNumberParser::canReceiveSms()` (port `PhoneNumberParser`) is
  called from exactly one place, `DeclaredMethodDestinations` (the `MOBILE_PHONE` arm, for `OTP_SMS` and
  `OTP_WHATSAPP`). The parser uses no default region and **no country allowlist exists anywhere**.
- **Availability-by-configuration has a model**: `ConfiguredAuthMethodAvailability` reads the methods a deployment
  wired from a container parameter. The "SMS is wired" check copies its shape.
- **Identity & Access** has `Contract/Query/TenantNames` (a read on the identity connection, tenant scope not
  consulted) and `UI/Cli/ProvisionTenantCommand`. `identity.tenant` is granted `SELECT` to `f5sign_identity` and
  `SELECT, INSERT` to `f5sign_provisioning` (`Version20260730000001`, `Version20260803000011`): **no role holds
  `UPDATE` on it**, so a command that flips a column needs a grant. `deptrac.yaml` already lets
  `EnvelopeApplication` and `NotificationApplication` depend on `IdentityAccessContract`.
- **`Envelope::resendInvitation()`** and `Recipient::resendInvitation()` (refused inside
  `MIN_RESEND_INTERVAL_SECONDS`, counted in `resendsMade`); `Recipient::MAX_CORRECTIONS` (3) and
  `correctionsMade`. The aggregate cannot read the tenant capability, so any guard that needs it is resolved in
  Application and passed in.
- **Test builders create recipients below the HTTP edge.** `EnvelopeBuilder::withRecipient` calls
  `Envelope::addRecipient` directly; `SeedsSentEnvelopes::seedSentEnvelope` goes through the real commands;
  six Integration tests `INSERT INTO envelope.recipient` by hand (`rg -l 'INSERT INTO envelope.recipient' tests`).
- ⛔ **Authoring rule 3 applies with force**: the five reactions are near-identical and one of them will differ for
  a reason. Read all five before converting one, and read `OneTimeCodeDeliveryService` as the deliberately
  different sixth. The same goes for the three authoring entry points (`AddRecipientUseCase`,
  `CorrectRecipientUseCase`, `ClaimRecipientUseCase`) and their requests.

## 3. What gets built

**3.1 The declaration.** `notification_channels` and `notification_mode` on `AddRecipientRequest`, persisted on
`envelope.recipient` and carried by the `Recipient` entity.

- `notification_channels`: **required** ordered list over a new Envelope `Contract/Type` enum
  `NotificationChannel` (`EMAIL`, `SMS`). Absent or `null` → `422`; `[]`, `["EMAIL"]`, `["SMS"]`,
  `["EMAIL","SMS"]` are accepted subject to §3.5. Duplicates are refused `422` (a list names each channel once).
- `notification_mode`: `IN_ORDER` | `ALL_AT_ONCE` (a second Envelope `Contract/Type` enum), **required iff the
  list has two or more channels**; sent with `[]` or one channel → `422`; missing with two or more → `422`. No
  default anywhere.
- Columns on `envelope.recipient`: `notification_channels JSONB NOT NULL` (a JSON array of strings) and
  `notification_mode TEXT NULL`, with CHECKs that state the properties rather than today's members (a
  predicate, authoring rule 5): the array has no duplicates and `jsonb_typeof = 'array'`; `notification_mode IS
  NULL` **iff** `jsonb_array_length(notification_channels) < 2`. The vocabulary check on the elements lives in
  the enum; the database refuses the shapes that no enum can express.
- Published on the envelope read model beside `auth`, in declared order.
- The `#[OA\*]` descriptions are the surface the integrator ratifies: they state the table of ADR-0077 §2.1,
  that `ALL_AT_ONCE` means the channels listed and never "every channel that exists", that `SENT` means *handed
  to the provider, not received* (the `DeliveryStatus` meaning, ADR-0065), that the fallback covers only a refusal
  or an exhausted retry and **not** a message accepted by the provider and lost downstream
  ([BL-390](../BACKLOG.md)), and what ADR-0077 §2.9 says of the three empty lists (§3.10).

**3.2 The resolution, in one place.** One Envelope `Contract/` type that, given the recipient's declaration,
contacts, delivery trace, whether SMS is available to the tenant and whether the deployment wires it, answers
the ordered channels an occasion targets and the policy to use (`SINGLE` for one, ordered for `IN_ORDER`, `ANY`
for `ALL_AT_ONCE`, nothing for `[]` or when nothing resolves). It skips a channel with no contact, a phone the
SMS predicate refuses, and a destination whose trace records a permanent refusal. Every Notification use case,
the resend guard (§3.8) and the channel-change operation (§3.9) call it; **none reimplements it** (ADR-0077
§3.3). The vocabulary is Envelope's: Notification maps `NotificationChannel` onto its own `DeliveryChannel` at
the boundary, as it already does for destinations.

**3.3 The tenant capability and the deployment wiring.** A boolean on `identity.tenant`, off by default,
exposed by a new `IdentityAccess/Contract/Query` interface (adapter on the identity connection, as
`DbalTenantNames` is), and set by a new `app:identity:*` console command. The migration adds the column and the
`UPDATE` grant the command needs on exactly that column for the provisioning role; a test connects as that role
and proves it, because every other test connects as the application role and cannot see a missing grant. The
deployment check — an SMS transport is wired — is read as configuration in the shape of
`ConfiguredAuthMethodAvailability`. SMS is available to a tenant only when **both** hold.

**3.4 Selection and the policies.** `ChannelSelector::select()` widens from the purpose to the purpose plus the
§3.2 resolution; the `AUTH_OTP_*` guard keeps throwing. `DeliveryPolicy` gains an **ordered** member; the
existing terminal **`NOT_NEEDED`** (§2) ends the targets never used. Under `IN_ORDER` every target is materialized at
creation (so the occasion holds the whole order and the per-delivery reactions find every target; the alternative of
creating the next target lazily was rejected), only the head is requested, and the targets never needed reach
`NOT_NEEDED` **in the same unit of work** as the predecessor's `recordSent`. The ordered member states its own
`isSatisfied()` over the needed deliveries: one sent. The fold already treats `NOT_NEEDED` as neither success nor
failure; `Notification::forgetSecretsOnceSettled()` waits for every delivery to be terminal and must still fire.
⚑ **A head that itself ends `NOT_NEEDED` at send time** (`TransmitDeliveryUseCase`'s re-check answers no) ends its
held tails `NOT_NEEDED` in the same unit of work: today that path marks only the one delivery it holds, and a held
tail left `PENDING` would keep the link stored forever. `CancelPendingInvitationsUseCase` already marks every pending
delivery, held tails included. Under `ALL_AT_ONCE` the occasion runs `DeliveryPolicy::ANY`, which
no occasion has used until now: delivered when one is sent, undeliverable when every one has failed.
No `DeliveryStatus` reader changes.

**3.5 Authoring checks, in one function used three times.** At add-recipient, at a correction and at the channel
change of §3.9:

- an `IN_ORDER` list none of whose channels the recipient has a contact for → `422`; one with at least one → ok;
- an `ALL_AT_ONCE` list is refused unless **every** channel has its contact → `422`;
- `SMS` for a tenant not enabled, or a deployment not wired, → `422` with **its own code** (two codes, one per
  cause, so an integrator can tell "ask the operator" from "fix the request");
- a phone used for `SMS` passes `canReceiveSms()` (mobile only; landline, premium-rate and VoIP refused) **and** a
  country allowlist held as deployment configuration, initially `ES`, `PT`, `FR`, `IT`, `DE`, `PL`, `RO`, `BG`
  (owner, 2026-10-09). The list was set against the client's own data since 2025-10-01: over 95% of the carriers
  with a phone have a Spanish mobile, and the foreign prefixes present are Portugal, Poland, Bulgaria and Romania;
  Morocco and Ukraine appear only as carrier companies, never as phones, and stay out (no traffic, more costly and
  more fraud-prone SMS routes). Adding a country is a configuration change.
  ⚑ **A mobile outside the list is refused with its own code, `PHONE_COUNTRY_NOT_SUPPORTED`** (owner, 2026-10-09),
  never with `RECIPIENT_CANNOT_RECEIVE_METHOD` (which says the number cannot receive an SMS at all, as a landline
  cannot): the problem body names the number's country (`country`, ISO 3166-1 alpha-2, from the parsed number) and
  the configured list (`supported_countries`), so the integrator can tell the operator "this country is not
  supported" instead of "this phone is wrong". Same code on every path that checks it: add-recipient, correction,
  claim, the channel change, and an `OTP_SMS` declaration. **The same allowlist applies to `OTP_SMS`** — a code
  costs the same per message — so `DeclaredMethodDestinations`' `MOBILE_PHONE` arm gains it: this is a behaviour
  change for `OTP_SMS` authoring (a non-allowlisted mobile is now refused `422`), visible to dev data only
  because nothing is in production. It does not apply to `OTP_WHATSAPP`, which is not SMS;
- a **claimable slot** (`declared_claimable`): authoring checks only what needs no contact — the vocabulary, the
  mode, and the tenant capability and deployment wiring. The contact-dependent checks run **at the claim**
  (`ClaimRecipientUseCase`), and a claim whose contacts cannot meet the list is refused `422` **before the claim
  lands** (no `claimed_at`, the slot still open). The claim request carries no list (ADR-0057 §2.16 stands); to
  change it the sender uses §3.9 and then the claim is made.

A correction whose result leaves the declared list unmeetable is refused **before it spends a correction**
([BL-227](../BACKLOG.md)). A capability or list that changes *after* authoring is not re-checked: it is resolved at
each occasion, and an occasion with nothing to send is reported as not sent (TASK-056's fact).

**3.6 The five creation sites.** Each replaces its `email === null` branch with the §3.2 resolution, builds a
`ContactPoint` from the phone for `SMS`, and keeps the throw only for the desync it guards (a channel selected
with no contact). The claimable-slot and delegated `continue`s stay where they are and run first
([BL-194](../BACKLOG.md)), except the one change the delegated bullet below makes to the ending audience.

- **What a site records when the resolution yields nothing.** The three invitation-family sites (activated,
  corrected, resent) **keep** TASK-056's `recordInvitationNotSent` call and choose its kind from the resolution:
  a declared `[]` → `DELIVERED_BY_INTEGRATOR` (TASK-056 §3.2 hands that emission to this task, the first with a `[]`
  list); a non-empty list that resolves nothing (no contact, every destination refused, capability or wiring gone) →
  `NOT_SENT_NO_REACHABLE_CHANNEL`. The completed and ended sites record nothing, as today.

- **One list governs every notification** of the recipient (invitation, resend, re-invitation after a correction,
  ending notices, sealed copy). **A delivered one-time code is not governed by it** (§4).
- **A delegated recipient** (`SignsVia` delegated) is never invited and never resent to, whatever the list says;
  the list governs only the notices they can receive — the ending notices. **Today they receive none**: the ended
  reaction's audience is the recipients with an invitation occasion, and a delegated recipient never has one (§2).
  This task widens that audience (owner, 2026-10-13; ADR-0077 §2.3 now states it): the ended audience is the
  recipients with an invitation occasion **plus every delegated recipient whose step activated** — the moment a
  non-delegated recipient would have been written to, so ADR-0058 §2.4's "someone this context addressed" keeps its
  meaning, and a delegated recipient on a step that never activated gets nothing. The empty-audience early return
  is computed over that union, so an envelope whose only recipients are delegated still ends with their notices.
  Their ending notice then follows their list like anyone else's; the ended reaction's idempotency (keyed on the
  cause, not on the audience) and its other filters stay as they are. The sealed copy carries a link and stays withheld. `[]` means no notices; the integrator informs
  them. The `#[OA\*]` description of the field says so.
- **`IN_ORDER`** requests only the head. The next target is requested when the previous delivery fails, either
  permanently (a refusal on the send call) or transiently (retries exhausted, TASK-055), **in the same unit of work**
  as the predecessor's `recordFailed`; one `TransmitDelivery` handles one delivery and nothing loops sends inside
  one transaction (ADR-0037's Counterpoint, §5). A head refused permanently while a tail is still to be tried leaves
  the occasion not undeliverable: `PropagateDestinationRefusalUseCase` marks the head's destination (the trace-only
  path) and `PropagateDeliveryFailureUseCase` does not report the invitation failed; only when the last target fails
  is the occasion undeliverable and the invitation failed.
- **`ALL_AT_ONCE`** requests every target at once, one `DeliveryRequested` per child; each channel retries on its
  own (TASK-055); a channel refused permanently is marked on its destination (TASK-056) and skipped from then on.
- Before building anything, **verify what the production email transport can report** and write the finding into the
  field's description: whether Outlook SMTP+OAuth2 / Graph ever returns a *synchronous permanent refusal*. If it
  does not, an `IN_ORDER` list never falls back from `EMAIL` on a refusal (only on exhaustion), and the published
  text says exactly that instead of implying more.

**3.7 Tenant changes after authoring.** `["SMS"]` authored for an enabled tenant, then SMS disabled for that
tenant: the next occasion resolves nothing and is reported as not sent; it never throws and the envelope proceeds.

**3.8 The resend asks whether anything would be sent.** `Envelope::resendInvitation()`'s "has an email" guard
becomes "the resolution yields at least one channel", computed in Application and handed to the aggregate
([BL-228](../BACKLOG.md)). A `[]` recipient is refused: the integrator mints a new link through
`POST /api/v1/signing-tokens`, which leaves the earlier link live as well (the [BL-152](../BACKLOG.md) shape,
**documented on that route rather than changed here**).

**3.9 Changing the channels is its own operation.** A route on the recipient sub-resource (proposed
`PUT /api/v1/envelopes/{id}/recipients/{recipientId}/notification-channels`, `MACHINE_KEY`, declared in
`config/routes/api/envelope.php` like its siblings) takes `notification_channels` and `notification_mode`, with the
§3.5 checks and the §3.10 warnings recomputed.

- It does **not** spend a correction (`correctionsMade` unchanged) and does not record `RecipientCorrected`
  ("the sender addressed the envelope wrongly"); it records its own Envelope event carrying the list and mode
  before and after.
- It **re-invites only a recipient whose step is active and who was never successfully invited** (TASK-056's
  recorded state is `NOT_SENT_NO_REACHABLE_CHANNEL`, `DELIVERED_BY_INTEGRATOR` or `FAILED`); after `SENT` it changes future
  notices only. A recipient whose state is `NOT_YET` (activated, nothing recorded) is **not** re-invited either: the
  state cannot tell an invitation in flight from a row written before TASK-056, and re-inviting the first would
  send two links (decided 2026-10-09 under the owner's standing grant; nothing is in production, so the rows it
  leaves stuck are dev data, repaired by a correction). Re-invitation is the same `RecipientInvitation` flow a correction triggers, and it cancels that
  recipient's pending deliveries first (TASK-055).
- It is allowed while the envelope is not closed. Correcting a contact **and** changing the list are two
  operations, each recording what it did; a combined call is a possible later convenience.
- It touches the same row as a concurrent resend or correction, so it takes the same envelope write path and the
  same lock they do (§6 bar 13).

**3.10 One factor twice: allowed, warned, recomputed.** When a channel the invitation may travel on equals the
channel of a delivered method on either gate — `SMS` with `OTP_SMS`, `EMAIL` with `OTP_EMAIL`, and under
`ALL_AT_ONCE` any channel of the list — add-recipient, the correction and the channel change answer success with a
`warnings` entry (additive member, empty list when none) naming the condition, and the recipient on the envelope
read model carries it for as long as it holds. It is allowed because the eCMR carrier has one phone; it is not
hidden. This is the authoring-time warning [BL-117](../BACKLOG.md) recorded as missing, delivered by the backend so
every client receives it. The published description and the frontend handoff carry ADR-0077 §2.9's two-factor
example (`notification_channels: ["EMAIL"]` with `OTP_SMS` on both gates) and its table of what each empty list
means:

| Field | `[]` means |
|---|---|
| `auth.access_methods` | opens the document with no code |
| `auth.signing_methods` | signs with no code |
| `notification_channels` | the platform sends no notification (no invitation, resend, ending notice or sealed copy); every delivered code the gates require is still sent |

**3.11 The callers of the new required field.** Counts taken 2026-10-09; re-run before you cite them.

- **Test builders default it centrally.** `EnvelopeBuilder::withRecipient` (used by `rg -l 'withRecipient\(' tests`
  → 47 files) and `SeedsSentEnvelopes::seedSentEnvelope` (`rg -l 'SeedsSentEnvelopes' tests` → 57 files on 2026-10-13; the
  helper is also redefined privately in several Integration tests (`rg -n "function seedSentEnvelope" tests`) that this default does not reach) get a
  parameter whose default is `["EMAIL"]`, with or without an email on the fixture — the same rule as the
  migration (§3.12), so a fixture means what a backfilled row means; a test about `[]` or `SMS` sets it.
- **The tests that post JSON get the field.** `rg -l '/recipients' tests` → 30 files on 2026-10-13, of which the ones that POST
  an add-recipient body (not a correction or a resend) must send `notification_channels`; the notes of the audit
  counted 33, which `rg` did not reproduce, so the implementer's own census is the authority and is recorded in
  the commit message. The 27 files that call `addRecipient(` at the aggregate (`rg -l 'addRecipient\(' tests`)
  pass the new argument.
- **Six hand-written INSERTs** into `envelope.recipient` (`rg -l 'INSERT INTO envelope.recipient' tests`) gain the
  column, because it is `NOT NULL` with no database default — a default would make "forgot the field" and
  "chose `[]`" the same row again, which is what the field exists to prevent.
- **Docs, in one sweep** (authoring rule 1): run
  `rg -n 'degenerate|EMAIL-only|single channel|Preference- and capability|email === null|TASK-031' src tests docs config CLAUDE.md`
  and convert one file at a time — `docs/ddd/notification-domain-model.md` § Channel selection and § Deferred
  surface; the envelope domain model's recipient section; the docblocks of `ChannelSelector`,
  `DefaultChannelSelector` and the five use cases; `config/services.yaml`'s selector comment;
  `DefaultChannelSelectorTest` and `DbalNotificationRepositoryTest` fixture notes; `docs/LIVE_SCHEMA.md` (the new
  columns); ADR-0037's deferral; ADR-0077's Status / Enforced by / Realized in (the mirror of landing a record);
  the BACKLOG rows of §7. Then re-run the sweep last: a change after a sweep invalidates it.
- **A frontend handoff in `docs/frontend-handoff/` is a deliverable of this task** (not written with this record),
  for the dashboard and the integrators: phones are sent in international (E.164) form — a Portuguese mobile typed
  without `+351` parses as a Spanish landline and is refused for SMS —, `PHONE_COUNTRY_NOT_SUPPORTED` and its two fields, the required field, the mode, the new `422` codes, the `warnings`
  member, the channel-change route, the read-model member, the three-empty-lists table and the two-factor
  example. The dashboard and dev integrators must send the field as soon as this merges, so they are told when
  the branch opens, not when it lands.

**3.12 The migration, and what each row means.** One generated migration (`make wt-backend-sf … cmd=doctrine:migrations:generate`;
never a hand-picked version). It adds the two columns nullable, backfills, then makes `notification_channels`
`NOT NULL` and adds the CHECKs. **Backfill, decided by the owner on 2026-10-09: `["EMAIL"]` for every existing row**, with or without an
email, because email was the only channel the platform had ever contemplated; `notification_mode` stays
`NULL` for every row. `[]` is **not** used for any backfilled row: it would claim that an integrator delivers
the link, which no existing envelope ever agreed to. Authoring rule 6 asks what that row means in every state
it can land on, on the write side as well as the read side:

| State of the row | What the backfilled value means |
|---|---|
| **Draft, with an email** | `["EMAIL"]` is exactly what the platform did for it before; the sender may change it with §3.9. |
| **Draft, without an email** | `["EMAIL"]` says what the platform intended — email — and has no address to meet it. This is the one shape authoring can never produce (§3.5 refuses it), so the read side must tolerate it: resolution finds nothing to send, and the occasion is recorded as not sent, no reachable channel (TASK-056). The sender fixes it by adding an email or changing the channels before sending. |
| **Sent, step activated, invitation already sent** | `["EMAIL"]` is true to history: it was emailed. Future notices go by email, as before. |
| **Sent, step activated, no email** | `["EMAIL"]` is true to history: the platform was to email and had no address, so nothing was sent. There is **no recorded outcome** for the past occasion (TASK-056 records outcomes from its own merge onward); TASK-056 states how the read model shows that. A later occasion is recorded as not sent, no reachable channel, and a release reads `NO_REACHABLE_CHANNEL` — unreached, as `NOT_REACHED` was — so no veto verdict changes. |
| **Sent, step not yet active** | Resolved at activation from the stored value, as for any recipient; without an email it is recorded as not sent. |
| **Terminal envelope or closed leg** | The ending notices have already gone out by email or not at all; the value changes nothing that can still happen, and §3.9 refuses on a closed envelope. |
| **Claimable slot, unclaimed** | `["EMAIL"]`, by the same rule. Because the claim checks the list (§3.5), claiming an old slot requires an email unless the sender first changes its channels with §3.9. |
| **Claimed slot / delegated recipient** | `["EMAIL"]`, by the same rule; a delegated recipient's list governs the ending notices only (§3.6). |

The `down()` drops the columns and constraints. The migration's docblock states this table, not a summary of it.

**3.13 The channel in Envelope's invitation events is a closed Envelope enum** (owner, 2026-10-13, requested by
[TASK-059](TASK-059-the-trail-shows-how-each-invitation-travelled.md), whose trail census compares against it).
`RecipientInvitationOutcomeRecorded::$channel` and `RecipientDestinationRefused::$channel` are typed today as
an opaque `string`, under TASK-056 §3.4's "open set". They become a new enum in `src/F5Sign/Envelope/Contract/Type/`
(`InvitationChannel`), following the same pattern as `RequiredDestination` / `InvitationOutcome`: Notification informs Envelope
in Envelope's vocabulary ([ADR-0078](../adr/ADR-0078-delivery-outcomes-come-back-as-facts.md)).

- **Members: `EMAIL`, `SMS`**, the channels a delivery that can produce either event travels on. Not `LOG`: no
  invitation is selected onto it. Not `WHATSAPP`: no `DeliveryChannel` carries it (§4), and a member nothing can
  produce is a promise in the published contract. A channel added later needs a case here as well, a cost the owner accepted.
- `?InvitationChannel` on the outcome (`SENT` only), `InvitationChannel` on the refusal. The wire values are the
  same strings, so the payload does not change. `fromPayload` uses `::from`, and the empty-string guards go away
  because the type now holds them.
- Notification keeps its own `DeliveryChannel` (with `LOG`) and maps it where it writes the string today
  (`PropagateDeliverySuccessUseCase`, `PropagateDestinationRefusalUseCase`), the way it already maps to
  `RequiredDestination`. A `LOG` arm throws, because reaching it means a desync. `DeliveryChannel` is **not** moved to Foundation:
  Foundation holds what every context references, and the delivery channel is Notification's own.
- ⚠ **History already written:** before merging, count `channel` values in the dev `platform.event_log` for
  both event types. Any value outside the enum makes `::from` throw on replay and must be reported, not hidden.
- **Sweep (authoring rule 1):** the two events' "OPEN sets … opaque" docblocks; the `#[OA\*]` text that publishes
  `channel`, which becomes a closed enum; ADR-0078, which is still Proposed and is amended rather than superseded;
  `docs/ddd/` for Envelope; and TASK-056 §3.4, where a note is added below the historical text rather than a
  rewrite. Tell the dashboard sessions that `channel` is now a closed enum.

## 4. Scope

**In scope:** §3.1–§3.13.

**Out of scope:**

- **SMS spend guards** — the resend cap, the operator unblock commands, the re-cut of the OTP destination limiter
  and the per-tenant volume alert (ADR-0077 §2.10) are [TASK-057](TASK-057-sms-spend-guards.md). This task adds
  the field that task reads; it adds no limit.
- **Transient-failure handling, retry profiles, the send-time re-check and delivery cancellation**
  ([TASK-055](TASK-055-delivery-reliability.md)); **the trace-only destination refusal, the recorded invitation
  state, release reasons and the Envelope invitation events** ([TASK-056](TASK-056-delivery-facts-and-sender-visibility.md));
  **the history route** ([TASK-058](TASK-058-recipient-notification-history.md)); **the trail rendering invitations**
  ([TASK-059](TASK-059-the-trail-shows-how-each-invitation-travelled.md)). This task *uses* the first two and
  waits for them.
- **Delivery receipts and bounce ingestion** ([BL-390](../BACKLOG.md)). Without them `IN_ORDER` recovers only from
  a refusal or an exhausted retry; with them it would also recover from a message accepted and lost downstream.
- **Gating `OTP_SMS` on the tenant capability** ([BL-391](../BACKLOG.md)). The allowlist and the deployment gate
  `OTP_SMS`; who may declare it is a decision about authentication.
- **The signature-level projection** BL-117 also asks for; it waits on [BL-119](../BACKLOG.md).
- **A per-recipient preference set by the recipient**, WhatsApp, voice and push.
- ⛔ **`OneTimeCodeDeliveryService` must not be routed through the widened selector.** Widening is exactly the
  change that makes an OTP override look natural, and it would let a recipient's notification list change the
  channel of a legally material factor (ADR-0049 §2.7). A recipient with `[]` and `OTP_SMS` receives no
  notification and every code they ask for.

## 5. Key decisions

All of them are [ADR-0077](../adr/ADR-0077-a-recipient-declares-the-channels-that-reach-them.md)'s; the ones the
implementer is most likely to get wrong:

- **The field is required and there is no database default.** Neither the wire nor the column may have a value for
  "absent" (ADR-0077 §2.1, §7.5). Do not give the column `DEFAULT '[]'` to make the migration shorter.
- **`[]` means "the platform sends no notification", never "unspecified" — and never "no codes".** Delivered
  one-time codes do not read the list at all.
- **`ALL_AT_ONCE` means the channels in the list**, never every channel that exists: a channel added to the
  vocabulary later must not join an existing list. A test enumerates the vocabulary, adds a fake member and asserts
  an existing `ALL_AT_ONCE` list does not grow.
- ⛔ **Do NOT loop an occasion's deliveries inside one command transaction.** ADR-0037's Counterpoint: *"latent while
  selection returns a single channel; armed the moment `ANY`/`ALL` is used."* `ALL_AT_ONCE` arms it. One
  `DeliveryRequested` per child, one delivery per `TransmitDelivery`, and under `IN_ORDER` the next request rides
  the predecessor's failure, not a loop.
- **Do not mint per channel.** One credential per recipient per occasion, carried in every message; two live
  credentials is the BL-152 shape.
- **The aggregate cannot read the tenant capability** (Domain may not see `IdentityAccessContract`), so every guard
  that needs it is resolved in Application and passed in.
- **A closed list of refusals each gets its own code**, and the `#[OA\*]` text enumerating them is re-read whole when
  one is added (authoring rule 1, closed enumerations).
- **A channel-change is not a correction**: it must not touch `correctionsMade` and must not emit
  `RecipientCorrected`.

## 6. Acceptance bars

Each bar names a fixture whose variables **disagree** (so the guard under test is the only thing that can make it
pass) and the sabotage that must redden it. Tiers follow `tests/README.md`: Unit/Application for pure rules,
Integration for real SQL and constraints, Acceptance for HTTP.

1. **The eCMR case, end to end (Application driving the real reaction, Acceptance for the authoring).** A phone-only
   recipient with `["SMS"]` in an SMS-enabled tenant receives the invitation by SMS when their step activates,
   carrying a working signing link. Sabotage: restore the `email === null` branch in `NotifyActivatedStepRecipientsUseCase`
   — the test reddens with no occasion created and the invitation recorded `NOT_SENT_NO_REACHABLE_CHANNEL`.
   A second arm: a recipient with `[]` is recorded `DELIVERED_BY_INTEGRATOR`, and one with `["EMAIL"]` and no email
   (tenant capability gone) `NOT_SENT_NO_REACHABLE_CHANNEL` (sabotage: record one kind for both — one arm reddens).
2. **The field is required and the mode is conditional.** Absent `notification_channels` → `422`; `[]` accepted;
   `["EMAIL","SMS"]` without mode → `422`; `["EMAIL"]` with a mode → `422`; `[]` with a mode → `422`; a duplicate →
   `422`. Integration: a raw `INSERT` with `notification_mode` set and a one-element list, and one with two elements
   and a null mode, are both refused by the CHECK (sabotage: drop the CHECK; the raw insert succeeds and the test
   names it).
3. **Enabling SMS changes nothing for an `["EMAIL"]` recipient — the 2FA bar.** Fixture: email + phone + `OTP_SMS` on
   both gates + tenant **enabled for SMS** + `notification_channels = ["EMAIL"]`. The invitation, a resend, a
   correction and an ending notice each produce exactly one email and **no SMS**. Sabotage: make the resolution
   return every channel that has a contact — this fixture reddens (it is the one where "has a phone" and "declared
   SMS" disagree).
4. **`ALL_AT_ONCE` under `ANY`.** One channel sent + one refused permanently → the occasion is delivered; one sent +
   one `PENDING` → delivered; both `PENDING` → undecided (neither delivered nor failed); both refused → undeliverable.
   Sabotage: bind `ALL_AT_ONCE` to `SINGLE` or to `ALL` — the "sent + refused" case reddens.
5. **`IN_ORDER` sends only the head and falls back in the same unit of work (Application, with a recording
   repository, plus Integration for atomicity).** Head refused permanently → next requested; head's retries
   exhausted (transient, TASK-055) → next requested; head sent → next reaches `NOT_NEEDED` in the same `save()` and is never requested; head ends `NOT_NEEDED`
   at send time → every held tail ends `NOT_NEEDED` and the link is forgotten (sabotage: mark only the head — the
   tail stays `PENDING` and the test names it); head refused permanently with a tail left → the head's destination
   is marked and the invitation is **not** recorded failed.
   Assert the failure and the next request are one `save()`: an Integration case makes the second write throw and
   asserts the failure was rolled back with it. Sabotage: record the failure and request the next in two units — the
   occasion stays undecided and the test names it.
6. **The ordered policy over the existing fold, and secrets are forgotten.** `NOT_NEEDED` and its fold are
   TASK-055's; this bar covers the new ordered member over them. A property test enumerates every
   combination of the five statuses for totals 1–3 under each policy, the ordered one included, and asserts exactly one of *undecided /
   satisfied / defeated / void* (a settled occasion of only `NOT_NEEDED`, from a cancellation, is *void*: neither
   delivered nor failed). `forgetSecretsOnceSettled()` fires once every delivery is terminal, including when the
   last is `NOT_NEEDED` (fixture: the link is erased from `variables`; sabotage: count `NOT_NEEDED` as non-terminal and
   the link stays).
7. **Authoring matrix.** For contacts (email only / phone only / both / none) × list × mode × tenant (enabled /
   not) × wiring × phone kind (ES mobile / ES landline / non-allowlisted mobile): the accept/refuse table of §3.5,
   with the code each refusal carries. Includes `["SMS"]` with a landline → `422`; `["SMS"]` with a valid mobile in
   a non-allowlisted country → `422` `PHONE_COUNTRY_NOT_SUPPORTED` carrying `country` and `supported_countries`, while the landline
   carries `RECIPIENT_CANNOT_RECEIVE_METHOD` (the fixture where the two refusals must not share a code); **`OTP_SMS` with that same non-allowlisted mobile → `422` `PHONE_COUNTRY_NOT_SUPPORTED`** (sabotage: leave
   the allowlist out of `DeclaredMethodDestinations`; this case reddens while `["SMS"]` still refuses); `ALL_AT_ONCE`
   with only an email → `422`; `IN_ORDER` with only an email → accepted.
8. **A claimable slot defers the contact check to the claim.** Authoring `["SMS"]` with no phone on a claimable slot is
   accepted; the claim with an email only is refused `422` and the slot still has `claimed_at = null`; the claim with
   a phone succeeds. Fixture where the list is `ALL_AT_ONCE ["EMAIL","SMS"]` and the claimant brings one of the two:
   refused. Sabotage: run the contact check at authoring for a slot — the first assertion reddens.
9. **A delegated recipient.** Delegated with an email and `[]` → no ending notice; with `["EMAIL"]` → one ending notice,
   still no invitation and no resend (`resendInvitation` refused), still no sealed copy credential; a delegated
   recipient whose step never activated → no ending notice; an envelope whose only recipients are delegated still
   sends theirs (sabotage: keep the early return over invitation occasions only — that fixture reddens). The fixture where
   email present and list `[]` disagree is the one that reddens if the use case falls back to "has an email". At authoring,
   a delegated recipient with no contact is accepted with `[]` and refused `422` with `["EMAIL"]` — the list's contact
   check is not waived for delegation, so an integrator whose delegated signers have no address declares `[]`
   (the case of a warehouse that signs by delegation). Sabotage: skip the contact check for delegated recipients.
10. **Codes bypass the list.** `[]` + `OTP_SMS` → the code is sent by SMS; `["SMS"]` + `OTP_EMAIL` → the code goes by
    email; the `AUTH_OTP_*` arm of the selector still throws, asserted directly. Sabotage: route
    `OneTimeCodeDeliveryService` through the widened selector — the `[]` case reddens.
11. **One resolution.** A property test feeds the same recipient over the full input space (declaration × mode ×
    contacts × trace × capability × wiring) to the resolution, to each of the five use cases (through their fakes) and
    to the resend guard, and asserts the same ordered channels. Sabotage: special-case one use case — the case that
    differs is named.
12. **Resend.** Reaches a phone-only recipient (`["SMS"]`); refused for `[]` and for a recipient whose list resolves
    nothing (tenant disabled after authoring).
13. **The channel change.** `correctionsMade` unchanged and no `RecipientCorrected` after it; its own event carries
    before and after; re-invites a step-active recipient recorded `NOT_SENT_NO_REACHABLE_CHANNEL`, `DELIVERED_BY_INTEGRATOR`
    or `FAILED`, and **does not** re-invite one recorded `SENT`, one in `NOT_YET`, nor one whose step has not activated; refused on a
    closed envelope; the same refusals as authoring. **Locking:** a concurrent resend and channel change on one
    recipient are serialized — Integration runs one connection under DAMA, so locked and unlocked reads are
    indistinguishable to it; this bar uses [`ProbesRowLocks`](../../tests/F5Sign/Support/ProbesRowLocks.php) (as
    `NotificationRowLockTest` does). Sabotage: weaken the lock on the path and the probe reddens.
14. **Warnings.** `OTP_SMS` with `["SMS"]` → warning; with `["EMAIL"]` → none; `OTP_EMAIL` with `["EMAIL"]` → warning;
    `["SMS","EMAIL"]` `IN_ORDER` with `OTP_SMS` → warning (a channel the invitation *may* travel on); `ALL_AT_ONCE`
    with `OTP_SMS` → warning; `[]` → none. The warning appears on add, correction, channel change and the read
    model, and **disappears from the read model** once a channel change removes the cause (fixture: warn, then
    change, then read).
15. **Contact corrected, list unchanged.** Correcting a phone that was refused (trace `FAILED`) re-enables SMS for the
    next occasion (the trace clearing already exists); a correction that would make the list unmeetable is refused
    and `corrections_made` is unchanged.
16. **The migration.** Integration: seed rows in the states of §3.12 through the old schema shape (a migration test
    that migrates up on a fixture schema), then assert `["EMAIL"]` in every state, **including the rows with no
    email**. Then the read side: activate the step of a backfilled row with no email and assert nothing throws,
    nothing is sent, and the occasion is recorded as not sent, no reachable channel — not as delivered by the
    integrator. Sabotage: backfill `[]` for the rows without an email — the recorded state turns into
    `DELIVERED_BY_INTEGRATOR` and the bar reddens naming it.
17. **Published contract.** The OpenAPI test shows `notification_channels` in `required`, `notification_mode` with its
    two values, the channel-change route with `MACHINE_KEY`, every new refusal code in the responses it can
    produce, and a `warnings` member; `/contract-check-backend TASK-031` is run and reported. A handoff exists in
    `docs/frontend-handoff/`.
18. **The tenant capability.** The command flips it; a test connected as the provisioning role proves the `UPDATE`
    grant; the query returns `false` for a tenant never touched.
19. **The email-transport finding** is recorded in the field's description with the evidence it rests on (§3.6).

Full suite, Infection covered-MSI, PHPStan, deptrac and lint green in the worktree lane
(`make -C ../f5sign-infra wt-backend src=$(pwd)`), not the main-checkout targets. Integration/ and Acceptance/ run <!-- OFFREPO: the ephemeral per-worktree lane is a target of the sibling repository f5sign-infra's Makefile; it mounts the given tree into its own containers and runs this repo's own test suites there, so it validates this tree rather than the main checkout. -->
once as regressions when the task is complete, not per commit.

## 7. Open follow-ups (track, don't solve here)

- [BL-390](../BACKLOG.md) — delivery receipts and bounce ingestion, so `IN_ORDER` covers a message lost after the
  provider accepted it.
- [BL-391](../BACKLOG.md) — whether `OTP_SMS` should require the tenant capability too.
- **A refused contact remembered across envelopes.** The trace is per envelope, so the same dead number is tried
  again on the next one. ⛔ Whoever builds it keeps the two refusals apart: a landline (`21614`) is a property of the
  number; an opt-out (`21610`) is a property of our provider account and reversible by the person texting `START`.
- **The correction budget is per recipient**, and now covers two contacts; whether it should be per contact wants a
  real sender running out of it as evidence.
- **A combined call** that corrects a contact and changes the list in one request.
- **A webhook** for the invitation facts and the channel change, if integrators need them pushed
  ([ADR-0064](../adr/ADR-0064-outbound-integrator-webhooks.md)): its published set excludes them today; a note for
  its author.
- **Telling the signer a code was not sent** (Notification to Session, a new cross-context path) — follow-up of
  TASK-055, described there.
- **Production prerequisites for SMS, outside the code:** the provider agreement and privacy notice, an approved
  sender ID, the SMS copy and sender name, and the provider's own geo permissions matching the allowlist. The
  allowlist itself was confirmed against the client's data on 2026-10-09 (§3.5).

BACKLOG rows this task closes when it lands: [BL-173](../BACKLOG.md), [BL-227](../BACKLOG.md),
[BL-228](../BACKLOG.md), the warning half of [BL-117](../BACKLOG.md); it must honour [BL-194](../BACKLOG.md) and
[BL-196](../BACKLOG.md). Whoever closes them runs `rg 'BL-NNN' src tests migrations config docs` and reads every hit
for tense.

**2026-10-14, at close:** BL-173, BL-227, BL-228 and BL-194 are marked closed on the branch (pending merge); the warning half of BL-117 is built and its projection half still waits on BL-119; BL-196's trigger was reached without a fifth filter and the question is not moved, so it stays open; BL-327's first trigger is built and the truncation is published rather than avoided; BL-400's `[]` declaration exists. New rows from the run: [BL-410](../BACKLOG.md) to [BL-414](../BACKLOG.md) (§12).

---

## 8. What the 2026-08-20 review changed

A read of this record against the tree, after [TASK-030](TASK-030-sms-delivery-channel.md) merged.
Kept as written because §9 explains which of it the re-cut overturned.

1. **The OTP bypass was assumed, not built, and nobody owned it.** Assigned to
   [TASK-023](TASK-023-sms-codes-and-recipient-phone.md), which built it.
2. **The tenant policy went from binary to per purpose** — a completion notice should not be the price
   of the invitation.
3. **A permanently-refused contact was to be remembered**, envelope-scoped.
4. **Two things this record did not name were added**: the correction re-send as a selector call
   site, and ADR-0037's loop-the-deliveries Counterpoint, armed by this task.
5. **The `RecipientDeliveryFailed` ambiguity was raised and dismissed.**

## 9. What the 2026-10-08 re-cut changed

Prompted by the eCMR case in the header, and decided with the product owner the same day; the
decisions are [ADR-0077](../adr/ADR-0077-a-recipient-declares-the-channels-that-reach-them.md)'s.

1. **The choice moved from the tenant to the recipient.** §8 item 2's per-purpose tenant policy is
   withdrawn: it could not express "this carrier has only a phone" and left that recipient skipped in
   every tenant that had not opted in. The tenant keeps one switch, whether SMS may be used at all.
2. **Fan-out is no longer the only mode.** Absence fans out (`ANY`); a declared list is ordered with
   an immediate-refusal fallback, a `DeliveryPolicy` member this record previously said nothing in the
   model expressed.
3. **§8 item 3's marker is not built; ADR-0065's trace already is it.** A `FAILED` destination is only
   ever a permanent refusal, and `correctContact()` already forgets it.
4. **A recipient nobody can reach is shown rather than skipped**, and `[]` is a supported way for an
   integrator to deliver the link itself.
5. **Claims of this record the tree had overtaken**: `RecipientView` had gained the phone; the
   selector call sites were five, and `OneTimeCodeDeliveryService` was no longer one of them.
6. **Two decisions were added that no earlier version had**: the one-factor-twice warning and the
   delivery channel named in the evidence.

## 10. What the 2026-10-09 audit changed

A point-by-point audit of the 2026-10-08 re-cut with the product owner, followed by a side-effects review of every
accepted change. The decisions are [ADR-0077](../adr/ADR-0077-a-recipient-declares-the-channels-that-reach-them.md)'s
(re-cut the same day) and its siblings'. Sections 8 and 9 above are kept as written; this one lists what moved.

1. **The list is required, not optional.** §9 item 2 made absence mean "every channel at once" (`ANY`). On the audit
   that was found to remove a second factor silently the day a tenant is enabled for SMS (email + phone + `OTP_SMS`
   would receive the link on the handset) and to duplicate every notice. Absence is now `422`; there is no database
   default and no `null` versus `[]` distinction left. §3.1 and §5 changed accordingly, and the old "absence is a
   value; do not backfill it" key decision is gone.
2. **`ALL_AT_ONCE` returns as an explicit mode.** A second required-when-two-or-more field, `notification_mode`
   (`IN_ORDER` | `ALL_AT_ONCE`); it means the channels listed, never every channel that exists. `ANY` is reachable
   only through it, which re-arms ADR-0037's Counterpoint and the bars on `ANY` removed in the first pass of this
   audit.
3. **The record was split.** The refused-destination write, the invitation facts, release reasons and the history
   route are ADR-0078 ([TASK-056](TASK-056-delivery-facts-and-sender-visibility.md),
   [TASK-058](TASK-058-recipient-notification-history.md), [TASK-059](TASK-059-the-trail-shows-how-each-invitation-travelled.md));
   retry by kind of message, the transient failure and the send-time re-check are ADR-0079
   ([TASK-055](TASK-055-delivery-reliability.md)). §9 item 3 ("ADR-0065's trace already is the marker") was
   **wrong**: the trace is written only when the whole occasion fails, so a refusal beside a landed channel was
   lost. This task depends on TASK-055 and TASK-056 and no longer builds around that gap.
4. **Spend guards left this task.** The resend cap, operator unblock commands, the OTP destination limiter re-cut
   and the per-tenant volume alert are [TASK-057](TASK-057-sms-spend-guards.md). §7 no longer lists
   "metering SMS spend" as an open follow-up of this task for those parts; metering itself stays [BL-166](../BACKLOG.md).
5. **A country allowlist and the phone predicate were added** to every SMS authoring path, `OTP_SMS` included.
6. **Claimable slots and delegated recipients got explicit rules.** A claimable slot declares its list at authoring
   and meets it at the claim; a delegated recipient's list governs the ending notices only.
7. **Changing the channels is its own operation** and not a correction: a correction spends a bounded budget, records
   that the sender addressed the envelope wrongly and always re-invites.
8. **The ordered policy materializes every target and ends the unused ones in a new terminal status** (`NOT_NEEDED`),
   instead of creating the next target lazily, so the fold over a fixed total and the forgetting of secrets keep
   working.
9. **The migration, the test-builder defaults and the callers of the field** (§3.11–§3.12) are new: the field being
   required is a contract change for the dashboard and every integrator.
10. **Claims of §2 the tree had overtaken, corrected here:** the selector call sites are five and none is the
    one-time-code service; `identity.tenant` has no `UPDATE` grant for any role; `canReceiveSms()` has exactly one
    caller; the number of tests that post an add-recipient body is what `rg` finds, not what the audit estimated.

## 11. What the 2026-10-13 claims check changed

Run against develop after TASK-055 and TASK-056 merged, before any code.

1. **`NOT_NEEDED` already existed** (TASK-055, ADR-0079 §2.5), with a fold that leaves it out of the total. §2, §3.4 and
   bar 6 reuse it instead of adding it, and ADR-0077 §2.6 says so. The check also found a hole the earlier text
   missed: a head ending `NOT_NEEDED` at send time left its held tails `PENDING`. §3.4 and bar 5 close it.
2. **A delegated recipient received no ending notice**, because the ended audience comes from invitation occasions.
   §3.6 now widens that audience (owner, 2026-10-13), so bar 9 can pass.
3. **`DELIVERED_BY_INTEGRATOR` had no emitter.** TASK-056 hands it to this task, and §3.6 now lists it, so bars 13
   and 16 can pass.
4. **TASK-056's not-sent fact was already in three creation sites.** §3.6 keeps it, and bar 1's sabotage is restated.
   Two caller counts in §3.11 were refreshed.

## 12. Deviations & honest notes

### Scope

- **Files outside the slices' lists**, each forced and recorded in its slice: the four use-case tests whose
  `DeclaredMethodDestinations` or constructor factory changed (slices 08, 11, 12, 13), `AuthoringLoadsUnderRowLockTest`
  (slice 09), the census tests `SigningReadersRefuseUnsentEnvelopeTest` and `ReactorConvergenceTest` (slice 16, classifications
  verified), two tenant-insert fixtures and `SystemCommandClosedListRuleTest`'s expected roster (slice 04).
- **Inside EvidenceAudit, and only these**, owner-approved on 2026-10-13: `IssueAuditTrailPhaseBoundaryTest` and
  `ClosedNowEnvelopeTrailHttpTest` (4 lines between them), and two label lines in `assets/evidence-audit/trail.typ`
  (`IDENTITY_TENANT_SMS_NOTIFICATIONS_CHANGED`, `RECIPIENT_NOTIFICATION_CHANNELS_CHANGED`), because
  `TypstTrailRendererTest::the_template_labels_every_code_the_model_owns` demands a label for every registered event
  type. task-validate reports the `trail.typ` edit as an undeclared file; it is intended.
- `deptrac.yaml`, `phpstan.dist.neon`, the baseline, `infection.json5.dist` and `composer.lock` are untouched. The one rule
  edit, `SystemCommandClosedListRule::ALLOWED`, is the accepted ADR-0077 §2.4 amendment.

### Decisions made during implementation

- **The record was re-cut after the claims check (§11)** before any code: `NOT_NEEDED` already existed, a delegated
  recipient received no ending notice, `DELIVERED_BY_INTEGRATOR` had no emitter, and TASK-056's not-sent fact was already in
  three creation sites. The rerun passed against the re-cut record (`253133c6`).
- **Owner decisions.** (B2) the ended audience is the invitation occasions plus the delegated recipients whose step activated,
  so bar 9 can pass. (§3.13) `InvitationChannel`, a closed Envelope enum of `EMAIL` and `SMS`, replaces the opaque `string`
  in the two TASK-056 events, absorbed here at TASK-059's request. (ADR-0077 §2.4) the tenant SMS capability is a third
  `SystemCommand` (`SetTenantSmsNotifications`, recording `TenantSmsNotificationsChanged`, with a column-scoped `UPDATE`
  grant), which edits the rule file's closed list (`99cc1c17`, accepted 2026-10-13). The two EvidenceAudit test edits and the
  two `trail.typ` lines (Scope above).
- **Additions the plan made**: a persisted delivery position (`notification_delivery.position`, slice 02), because the
  repository read `ORDER BY channel` and would have reversed `["SMS","EMAIL"]`; the correction answers `200 {warnings}` where
  it answered `204`, a contract change carried by the handoff (`docs/frontend-handoff/TASK-031-notification-channels.md`);
  `RECIPIENT_HAS_NO_ADDRESS` retired for `RECIPIENT_NOTIFIED_BY_INTEGRATOR` and `RECIPIENT_HAS_NO_REACHABLE_CHANNEL`, and a
  delegated recipient refused by name on resend (`RECIPIENT_SIGNS_BY_DELEGATION`); the ordered member is `DeliveryPolicy::IN_ORDER`;
  deployment configuration is two literal parameters (`envelope.sms_notifications.wired`, `.supported_countries`) with no new
  env var; two migrations beyond slice 02's (identity, envelope).
- **Expand/contract.** Slice 30 made `notification_channels` required end to end and removed the `["EMAIL"]` add-path default
  and the null-skips-guards branch, after 27–29 had made every test body declare it. Between 10 and 30 an absent member
  answered `201` with `warnings: []` while the read model warned over the stored `["EMAIL"]`; slice 30 closed both. Slice 04
  added `sms_notifications_enabled` with `DEFAULT false` for the backfill and dropped the default in the same migration
  (precedent `Version20260818000007`, ADR-0019 §4).
- **Latent recipient-ordering bug, found by the full suite** (`c068dc2a`): both envelope repositories ordered recipients by
  step ordinal alone, so recipients sharing a step came back in table order, which moves after an update. The first full run
  (at `7363c6b6`, 6843 tests) had 2 failures, both this. Ties now break on the recipient id (a UUIDv7, creation order). It
  predates the task and the suite was the only thing that could see it.
- **Gate fixes.** doctrine-guard W1 and contract-check W2 were fixed in `94045d58` (the list-shape CHECK function answers
  false for a non-array instead of raising, because PostgreSQL promises no evaluation order for the CHECK's `AND`; a warning's
  channel is a published enum); doctrine-guard W2 was dismissed (`[]` is a declaration, not an absence); contract-check W1 was
  checked against dev history (`InvitationChannel::from` tightens decoding; EMAIL×2 and null×1, nothing else). Security-audit
  W1 became slice 32 (`6f4421c2`: 401 and cross-tenant tests of the channel change; green on first run, no sabotage
  available because tenant scoping is RLS plus the tenant GUC, not a line in the use case); W2 (`PHONE_COUNTRY_NOT_SUPPORTED`
  carries a country derived from the phone, owner-required) was accepted as a knowing exception to `ProblemExtensions`.
- **Slice names for the channel change** carry `Recipient` throughout, and the event is `RECIPIENT_NOTIFICATION_CHANNELS_CHANGED`
  (the amend message wrote `RECIPIENT_NOTIFICATION_CHANGED`).

### Decisions that needed an ADR

- **[ADR-0077](../adr/ADR-0077-a-recipient-declares-the-channels-that-reach-them.md): exercised, move to Accepted PROPOSED and not
  applied.** The artifacts that exercise it: `NotificationChannelResolution::resolve()` and the `NotificationChannelResolver`
  port (§2.1, §2.6), the channel guards' tests including `CodesIgnoreTheNotificationListTest` and
  `OneTimeCodeDeliveryServiceIsolationTest` (§2.5), `InOrderFallbackAtomicityTest` and the `IN_ORDER` tests of the aggregate
  (§2.6), `SystemCommandClosedListRuleTest` with the `SetTenantSmsNotifications` roster entry (§2.4, amendment accepted
  2026-10-13), and the acceptance tests `RecipientNotificationChannelsHttpTest` and `RecipientNotificationChannelsChangeHttpTest`
  (§2.7–§2.9). Its §2.10 (spend guards) is TASK-057, so the honest form may be `Accepted (enforcement partial)`; the owner
  decides. docs-sync records the realization in the ADR itself.
- The §2.4 amendment is the only ADR change accepted during the run.

### Declared and unproven properties

- **Infection**: changed-line gate over the 98 changed `src` files: 27 escaped on the first run (`6f4421c2`); 18 killed by tests, 3 removed as dead code, 6 accepted as equivalent — `break`→`continue` in `ChangeRecipientNotificationChannelsUseCase` and `ResendRecipientInvitationUseCase` (recipient ids are unique in an envelope), the swapped email coalesce in `ClaimRecipientUseCase` and `CorrectRecipientUseCase` (the guard reads presence only), and `true`→`false` in `NotifyEndedEnvelopeRecipientsUseCase`'s audience set (read only through `isset`). The gate has no ignore list, so its last run exits 1 on exactly these six. Outside its `source` and guarded only by their own
  tests: the phpstan rule roster, the migrations and the CLI command.
- **The SMS path is proven against fakes and a null transport only.** No SMS has left this system (BL-169); the provider's
  geo permissions, the sender ID and the privacy notice are production prerequisites outside the code (§7).
- **Bar 19 (the email transport's refusal)** is a reading of the code and of the production SMTP configuration in
  `../f5sign-infra`, not an observation: the only synchronous refusal is an SMTP 5xx at submission, and the published text says
  EMAIL rarely falls back on a wrong address.
- Slices 27–29's commit bodies say the fast tier ran; only the 17 edited classes ran (127 tests). The full suite at the tip
  covers them.
- `composer audit` could not run (offline), so the dependency-CVE check is not evidence.
- The security audit's plaintext SMS destinations at rest follow the known ADR-0033 gap (`FieldCipher` has no callers).

### Debt left behind, and where it lives now

- [BL-410](../BACKLOG.md): about 160 mentions of the guide by file name in `src`, `tests`, `config` and `migrations`
  (zero-AI-trace rule); this branch adds none.
- [BL-411](../BACKLOG.md): "issuance is additive (ADR-0045 §2.6)" is ADR-0060 §1; surfaces left in `EmailNotificationChannel`,
  `RecipientInvitationResendHttpTest`, `EnvelopeCredentialRetirementTest`, ADR-0059 (twice) and BL-152's kept text.
- [BL-412](../BACKLOG.md): `ResolvedSigningToken::wasIssuedBefore()` has no callers.
- [BL-413](../BACKLOG.md): repeated channel-change calls re-invite by SMS while the invitation keeps failing; not taken by TASK-057, which capped only the resend route.
- [BL-414](../BACKLOG.md): the same-second gap in the pending-invitation cancellation.
- [BL-327](../BACKLOG.md) (truncated reason by SMS), [BL-400](../BACKLOG.md) (an integrator cannot declare it delivered) and
  [BL-196](../BACKLOG.md) (which recipients are actionable) were touched in tense only and stay open.
- Low items left in slice reviews and accepted: a failed `IN_ORDER` head whose fallback ends `NOT_NEEDED` folds undeliverable
  with no `NotificationFailed` (as `ANY` does today); `NOT_YET` gets no cancellation on a channel change; `notifiedByIntegrator`
  keeps an unused `RecipientId` parameter; the old handoffs of TASK-023 and TASK-025 say `204` for the correction and this
  task's handoff says `200`; `docs/frontend-handoff/TASK-041` and the TASK-041 record still name `RECIPIENT_HAS_NO_ADDRESS` and
  are historical.
- Docs owed to docs-sync were handed over in `plan.md` (ADR-0077/0078/0037 realization, `docs/ddd`, `LIVE_SCHEMA`); the §7
  items (BL-390, BL-391, the remembered refusal, the correction budget, the combined call, the webhook, signer-side code
  failures, SMS production prerequisites) are unchanged by the run.

### Delegated work

- 31 planned slices plus one fix slice (32, from the security audit) and one plan amendment (the channel change's names). 18
  critical slices ran on opus: 01–11, 13–17, 30 and 31. Slice 12 ran as standard on sonnet. The twelve mechanical slices
  (18–29) ran on sonnet, 20–22 and 24–26 in parallel, reviewed as batches. The replicator was used once (slice 01).
- Review rounds: twelve slices needed one round (01, 03, 04, 06, 08–15), six needed none (02, 05, 07, 16, 17, 30); the
  mechanical slices were reviewed as batches and approved. Most round-one fixes were prose or comment corrections applied
  directly against the review's wording (`run.log` marks 01, 03, 06, 09, 11, 13 and 15 so) rather than by a relaunched implementer.
- Slice 04 returned `NEEDS_CONTEXT` twice (the `DEFAULT false` against schema conformance, settled by the 20260818 precedent).
  Slice 03's first lane run self-deadlocked on `var/cache/test`'s container lock and was re-run clean. Lane queue waits of 107 s
  and 122 s in slice 30 were shared with the TASK-045 session. Slices 16 and 17 are `DONE_WITH_CONCERNS` with doc-only findings
  handed to docs-sync.

### Cost of the run

- Slices by model: opus 18 critical slices plus the plan and the closing review; sonnet 13 (12 mechanical, 1 standard); the fix
  slice 32 has no model line in `run.log`. Token totals are not recorded in `run.log`.
- Rounds: 12 slices with one review round, 6 with none; no slice needed a second round.
- Escalations: none to a higher model; two relaunches of slice 04 for context, and seven round-one fixes taken by the orchestrator.
- Full suites: three runs (6843 tests); the first found the ordering bug, the second was stopped by the owner, the third is the
  green run at `f7697685`.
- Baseline before the work: 5394 tests / 60082 assertions on the lane; at the tip 6843 / 78358.
