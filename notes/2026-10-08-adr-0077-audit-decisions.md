# ADR-0077 / TASK-031 — design audit decisions (2026-10-08)

Working log of the point-by-point audit of ADR-0077 ("a recipient declares the channels that reach
them") and the TASK-031 re-cut, both in f5sign-backend. **Nothing here is applied to the ADR or the
task yet.** Uncommitted on purpose: the owner validates the docs before anything is committed.

## Gate before editing the ADR / task

⛔ **Before any of the decisions below is written into ADR-0077, TASK-031 or other docs, run a deep
side-effects review of each accepted change** (owner, 2026-10-08): enumerate every caller, event,
webhook, read-model field, test and doc the change touches, and check whether something else breaks
or a further decision falls out. Only then edit the docs.

## Decisions

### 1. A permanently refused contact is recorded even when another channel lands — option A (accepted)

- Today `delivery_trace` gets `FAILED` only when the whole occasion fails (`OnNotificationFailed` →
  `PropagateDeliveryFailureUseCase`). Under `ANY` or the ordered fallback a refused SMS beside a landed
  email is lost, so ADR-0077 §2.5's claim ("the trace already is the refused-contact marker") is false.
- Decision: every **permanent** per-delivery refusal is propagated to Envelope for **that destination**
  (`markRecipientDeliveryFailed`), whatever the occasion's outcome. `RecipientDeliveryFailed` (the
  sender-facing "could not reach this recipient") stays emitted only when every channel failed.
- Correction of the claim made in the audit: Twilio's permanent codes (21211 / 21614 / 21610) are
  rejected at the API call and, as far as known, not billed — the harm is visibility (a dead phone used
  for `OTP_SMS` goes unnoticed until the signer is stuck), not spend.
- Deferred: a refused-destination memory across envelopes (TASK-031 §7), keeping landline (permanent)
  and opt-out (reversible) apart.
- Side-effects review must cover at least: `PropagateDeliveryFailureUseCase` semantics + tests +
  docblocks; ADR-0065 (per-destination trace) wording; ADR-0064 webhooks (integrators start receiving
  per-destination `FAILED` where they received nothing); the envelope read model `delivery` map; the
  `carriesMeansToAct()` filter (does a refused sealed-copy SMS mark the trace too?); idempotency of the
  write port under redelivery; the interaction with the ordered policy's next-request in one unit of
  work.

### 2. SMS spend and abuse (decided)

Facts: OTP SMS has limiters (session 3/h, destination 5/h, source 10/h, machine 100/h). The invitation
resend has only a 60 s interval (`Recipient::MIN_RESEND_INTERVAL_SECONDS`) and no count bound;
notification SMS has no limiter; any country's mobile is accepted (premium-rate, landline, VoIP etc.
already refused by `LibPhoneNumberParser`); nothing meters spend (BL-166).

- **2a — resend cap: option 1.** A maximum number of resends per recipient when the channel list
  includes SMS (proposed 5), keeping the 60 s interval. Plus **server-side admin console commands** to
  unblock a recipient: (i) reset the resend count; (ii) clear the OTP limiter counters of their session
  (keys are digests — the command re-derives them from envelope + recipient). Each use records an
  auditable fact (who, when, what was unblocked). The sender-side auth-lockout unlock
  (`RecipientAuthUnlocked`, ADR-0049 §2.8) already exists and is not this.
- **2b — per-tenant notification SMS: option 3, alerts only, no cut-off** (owner: cutting is too risky
  for live flows). A per-tenant hourly count that logs/alerts above a threshold, never blocks.
  Accepted risk: a stolen API key (IRSF) spends before the alert; mitigated by 2a + 2c. Recommended
  outside code: Twilio Usage Triggers + prepaid balance without auto-recharge as the real hard cap.
  A money budget per tenant stays a follow-up on BL-166.
- **2c — country allowlist: option 1**, per deployment (configuration), checked at authoring when a
  recipient's channels include SMS (422), plus Twilio geo permissions as a second barrier. Initial
  list: **ES, PT, FR, IT, DE**. Open in the side-effects review: does the same allowlist apply to
  `OTP_SMS` phones (it should — same spend, same fraud)?

### 3. Invitation state recorded when it happens — option A + i (decided)

- The state derived at read time from today's inputs (tenant capability, list, contacts, trace)
  rewrites the past: enabling SMS for a tenant after activation leaves a never-invited recipient in no
  state at all; a later `FAILED` trace turns an attempted-and-failed invitation into "no contact".
- **A:** Notification reports to Envelope, through its write port as it already does for sent and
  failed, the decision not to send ("no reachable channel" / "delivered by the integrator", with the
  instant). Stored beside `invitation_sent_at` / `invitation_failed_at`; the state shown is derived
  from those recorded facts only. ADR-0077 §2.6's "derived, never stored beside its inputs" is
  replaced.
- **i:** a recipient who becomes reachable later is **not** invited automatically. A contact
  correction already re-invites (sender's act); otherwise the sender resends, which is allowed as soon
  as at least one channel resolves. No sweep on tenant enablement.
- Side-effects review: migration + write-port method; webhook (ADR-0064) for the new fact; the
  `release_reason` `NOT_REACHED` derivation (`ReleaseReasons`) which reads `invitationSentAt`; the
  audit trail.

### 4. Transient failures: two retry policies by kind of message (decided)

Facts: `async_events` has no retry strategy of its own, so Symfony's default applies (3 retries,
1 s / 2 s / 4 s, ~7 s) and then the `failed` transport; the `Delivery` stays `PENDING` for ever and only
an operator replays it. Already true today for email. Under the ordered policy the next channel is
never tried. OTP TTLs: SMS 300 s, email 900 s; resend cooldown 60 s, and a new code invalidates the
previous one; Session never learns whether a code was delivered.

- **Notifications (invitation, resend, ending notices, sealed copy): option B.** Their own retry
  policy, e.g. 1 min / 5 min / 15 min (~20 min); on exhaustion the delivery is recorded `FAILED` with
  a **non-permanent** reason, which moves the ordered policy to the next channel and does **not** mark
  the contact dead in the trace (decision 1 marks permanent refusals only).
- **OTP codes: option O1.** Short retries (e.g. 5 s / 15 s / 30 s) bounded by a hard **"do not send
  after"** = request time + 60 s (the resend cooldown), carried on the transmission message. Past it the
  code is never sent, not even from a dead-letter replay a day later. On exhaustion: non-permanent
  `FAILED`, **no channel change** (ADR-0049 §2.7); the signer resends or picks another declared method.
  Rationale: a code arriving after the signer could have asked for a new one collides with it ("wrong
  code", a spent attempt); a late code is worse than none. Improves today too (an OTP failing for 7 s is
  currently lost).
- **Rejected: O2** (retry while the code is valid) — reopens the double-code collision.
- **Backlog: O3** — tell the signer "we could not send your SMS" (Notification → Session signal, a new
  cross-BC path, ADR-level; plus a signer app change).
- Dead-letter replay must be idempotent: transmitting a delivery that is no longer `PENDING` is a no-op.
- Implementation shape to check in the side-effects review: one custom retry strategy that reads the
  message kind (model: `ChainConflictRetryStrategy`) vs a separate transport/queue (would touch
  f5sign-infra's RabbitMQ declarations); a new non-permanent failure kind on `Delivery`; the listener
  on retry exhaustion (`WorkerMessageFailedEvent`, `willRetry() === false`) writing in its own
  transaction.

### 5. Changing only the channel list — option A (decided)

- The contact correction spends one of `Recipient::MAX_CORRECTIONS` (3), records `RecipientCorrected`
  ("the sender addressed the envelope wrongly") and always re-invites — none of which fits a change of
  channel with a correct contact.
- **A:** a separate operation (e.g. `PUT /envelopes/{id}/recipients/{rid}/notification-channels`),
  same validations as authoring (contact present, tenant SMS capability, country allowlist,
  one-factor-twice warning recomputed). Does **not** spend a correction; records its own fact
  ("channels changed from X to Y"). **Re-invites only if never successfully invited** (recorded state
  `NOT_SENT_NO_CONTACT`, `DELIVERED_BY_INTEGRATOR` or `FAILED`, step activated); after `SENT` it only
  changes future notices. Allowed while the envelope is not closed.
- Correcting a contact **and** changing the list = **two separate operations** (simplest to reason
  about); a combined call is a possible later convenience.
- Side-effects review: dashboard + integrator handoff (new endpoint), webhook for the new fact, the
  resend cap (decision 2a) when the sender re-invites on the new channel, the audit trail.

### 6. `notification_channels` is REQUIRED; there is no absent value (decided)

- Problem found: with "absent = every channel at once", enabling SMS for a tenant would make every
  recipient with email + phone and `OTP_SMS` receive the link on the handset too — 2FA silently lost
  in in-flight and new envelopes — and duplicate every notice (spend) for anyone with both contacts.
- Not in production, so no backward compatibility is owed (owner, 2026-10-08). Decision: the field is
  **required** on add-recipient; absent → `422`. `[]` = the integrator delivers (OTP codes still sent);
  a list = that order, with fallback. **"Every channel at once" is dropped** (can return later as an
  explicit option if a client asks).
- Rejected: absent = `[]` (forgetting the field and "I deliver it" become the same thing — the silent
  no-invitation defect again, with a misleading state); absent = `["EMAIL","SMS"]` (a hidden default
  buys nothing once compatibility is not owed).
- What falls away: ADR-0077 §2.1's three-reading table, §2.7 (absence reproduces today), §7.4, the
  `null` vs `[]` distinction (the column becomes NOT NULL), declared-vs-effective in the read model,
  `ANY` as a reachable policy (check in the side-effects review whether anything still selects it).
- Costs: dashboard (`factor5-dashboard`) and dev integrators must send it now — tell them early; test
  helpers that create recipients; a migration backfilling dev rows (`["EMAIL"]` if email, else `[]`) —
  authoring rule 6 applies: state what that row means in each envelope state.

### 7. Claimable slots and delegated recipients (decided)

- **7a — claimable slot: option A.** The list is declared at authoring (required, like every
  recipient) and its contact check is **deferred to the claim**, mirroring ADR-0057 §2.13 (gate
  declared at authoring, destination checked at the claim). At authoring only the contact-independent
  checks run (tenant SMS capability, valid members). At the claim, contacts that cannot meet the list
  → `422` before the claim lands. The claim carries no list (ADR-0057 §2.16 stands); to change it, the
  decision-5 operation, then claim.
- **7b — delegated recipient (ADR-0055): option A.** Required too; it governs only the notices a
  delegated recipient can receive (the ending notices — today they get them by email when they have
  one; not the sealed copy, which carries a link). Invitation and resend are never sent whatever the
  list says. `[]` = no notices, the integrator informs them. Must be documented on the field.
- Verified: `NotifyEndedEnvelopeRecipientsUseCase` has no delegated/unclaimed filter;
  `NotifyResentInvitationRecipientUseCase` refuses delegated; `NotifyCompletedEnvelopeRecipientsUseCase`
  withholds the credential from delegated and unclaimed.

### 8. "All at once" returns as an explicit mode — option A (decided 2026-10-09)

- Why it existed: the owner's first proposal ("empty list → every channel at once") gave a default
  for clients that sent no list, and redundancy while late losses go undetected (BL-390). Removed in
  decision 6 because, as a default, it silently broke email + `OTP_SMS` 2FA the day a tenant was
  enabled for SMS and duplicated spend. Kept as an **explicit** choice only.
- Shape: a sibling field **`notification_mode`** (`IN_ORDER` | `ALL_AT_ONCE`), **required iff the
  list has 2 or more channels**; sent with `[]` or a single channel → `422`; missing with 2+ → `422`.
  No default anywhere.
- `ALL_AT_ONCE` means every channel **in the list** (never "every channel that exists", so a future
  WhatsApp does not join silently). One credential in every message. Policy `ANY`: delivered when one
  is sent, failed only when all are refused.
- At authoring **every** channel of an `ALL_AT_ONCE` list must be meetable (contact present, tenant
  capability, country) → `422` otherwise; for a claimable slot the check moves to the claim
  (decision 7a). Governs every notification of the recipient; for a delegated recipient, the ending
  notices only (decision 7b).
- Consequences: one-factor-twice warning when SMS + `OTP_SMS` (or EMAIL + `OTP_EMAIL`); double
  messages and spend (SMS counts in decision 2b's alerts; 2a's resend cap applies); a channel refused
  permanently gets marked (decision 1) and is skipped afterwards, so the recipient degrades to the
  working channel on its own; each channel retries independently with the notification policy
  (decision 4), no fallback; invitation state `SENT` as soon as one is sent, per-channel detail in the
  read model's delivery map.
- Restores what M7 removed: TASK-031's `ANY` bars (one sent + one refused → delivered; one pending →
  undecided) and ADR-0037's Counterpoint (never loop an occasion's deliveries in one transaction) is
  armed again.
- Rejected: an object `notification: {channels, mode}` (reshapes the agreed field); a magic `"ALL"`
  token (string-or-array type, and grows silently with every new channel).

### Minor items (decided 2026-10-09)

- **M1** — SMS in `notification_channels` uses the same phone predicate as `OTP_SMS`
  (`LibPhoneNumberParser`: landline, premium-rate, VoIP… refused) plus the country allowlist (2c).
- **M2** — the country allowlist (ES, PT, FR, IT, DE) applies to `OTP_SMS` phones too (`422` at
  authoring). Closes 2c's open question.
- **M3** — the ordered policy materializes every target at creation; the targets no longer needed
  reach a new terminal `Delivery` status ("not needed"). Needs a migration + DB constraint; keeps
  `DeliveryPolicy`'s fixed-total fold and `forgetSecretsOnceSettled()` working. Rejected: lazily
  creating the next target (the fold assumes a fixed total).
- **M4** — keep `SENT` (= handed to the provider, not received) as in `DeliveryStatus` and ADR-0065;
  document it on the published field.
- **M5** — verification inside the task: whether the production email transport (Outlook SMTP+OAuth2 /
  Graph) ever returns a synchronous permanent refusal; if not, document that an `IN_ORDER` list never
  falls back from EMAIL.
- **M6** — outside the code, a production prerequisite: DPA with Twilio as sub-processor (phones and
  signing links) and the privacy notice.
- **M7** — superseded by decision 8: `ANY` is used again, by `ALL_AT_ONCE` only.
- Audit trail: no decision needed — it already renders contacts through `MaskedContact`, whose private
  constructor keeps an unmasked contact out of the trail; the invitation channel follows that.

## Side-effects review (2026-10-09)

Three read-only sweeps (Notification, Envelope, cross-context). Findings per decision; **[DECIDE]**
marks a new question for the owner.

- **Correction to decision 4's facts.** `async_events` uses `ChainConflictRetryStrategy`
  (SignatureExecution) for every event: 4 retries at 2 / 6 / 18 / 54 s (~80 s), then `failed`.
  Retries are per **event** (`DeliveryRequested`); `TransmitDelivery` is a sync command dispatched by
  the reactor inside it. So an OTP can already arrive ~80 s late today, past the 60 s resend cooldown —
  the double-code collision exists now and O1 fixes it.
- **S1 (decision 1).** `Envelope::markRecipientDeliveryFailed()` couples three writes: the destination
  trace, `invitation_failed_at`, and `RecipientDeliveryFailed` (on a trace change). Decision 1 needs a
  **separate trace-only path** ("destination refused"), so the recipient-level verdict still fires only
  when every channel failed — which is exactly what
  `one_refused_channel_does_not_flip_the_recipient_while_another_is_still_live` protects (its event half
  stays; its trace half changes). Existing deliberate rule: only `carriesMeansToAct()` purposes touch
  the recipient (TASK-040 §6 case 11, `a_refused_completion_notice_flips_nobody`).
  **[DECIDE D-a]** does a permanent refusal of an informational notice (ending, completed, sealed copy)
  mark the destination trace? Recommended: no, keep the rule.
  Pre-existing defect found: `Envelope::markRecipientDeliveryFailed()` stamps `invitation_failed_at`
  before the closed-leg check (a closed leg can still get it) → backlog row.
- **S2 (decision 3).** `invitation_sent_at` / `invitation_failed_at` are written only through the
  write port, forward-only; nothing records "not invited". The presenter exposes none of them (nor
  `resends_made`, `corrections_made`, `claimed_at`). `ReleaseReasons` derives `NOT_REACHED` from
  `invitationSentAt === null`, and `LINK_EXPIRED` / `SENT_NO_RESPONSE` from `invitationSentAt`.
  **[DECIDE D-b]** release reasons for (i) a recipient the platform could not reach (today
  `NOT_REACHED`, indistinguishable from a dormant step) and (ii) a `[]` recipient the integrator
  delivered to (today `NOT_REACHED` — false; Envelope does not know when the integrator minted).
- **S3 (decision 4).** Per-kind retry needs: (a) the kind and, for OTP, a `send_before` on
  `DeliveryRequested` (additive payload on a Notification Contract event) and on `OneTimeCodeRequest`
  (no deadline field today; Session computes it); (b) a retry strategy that dispatches per message,
  but the `async_events` strategy is SignatureExecution's — Notification logic must not go there; a
  Foundation-level composite that delegates per message type is a cross-cutting change (check
  ADR-0031 / messenger docs; may need an ADR note); (c) a `WorkerMessageFailedEvent` listener for
  exhaustion (precedents: `SentryMessengerContextListener`, `CustodianRunListener`). Dead-letter
  replay is already safe: `TransmitDeliveryUseCase` returns when the delivery is not `PENDING`.
- **S4 (decision 2a).** `resendsMade` is documented monotonic (a count of resends, evidence); CHECK
  `>= 0`. **[DECIDE D-c]** the unblock command: reset the counter (loses the history) vs grant extra
  allowance (new column, history kept). OTP limiter unblock: keys are digests of session, destination
  and **source IP** — the IP key cannot be re-derived by an operator; only session + destination (and
  the machine key by API client) can be cleared. No console command records an audit fact today and
  there is no operator actor kind (`SystemActorId::scheduler` exists) — an operator actor is a
  Foundation change.
- **S5 (decision 2b).** No per-tenant counters exist anywhere. **[DECIDE D-d]** implementation: a
  Redis counter on the send path vs an hourly custodian report querying
  `notification.notification_delivery` (SMS, last hour, per tenant) that logs at error above a
  threshold — the `app:storage:report-*` pattern, durable, off the hot path. Recommended: the report.
- **S6 (decision 2c, M1, M2).** `canReceiveSms()` is called only from `DeclaredMethodDestinations`
  (MOBILE_PHONE arm: `OTP_SMS`, and `OTP_WHATSAPP` judged by the same predicate); parse uses no default
  region; no allowlist exists. The allowlist lands in the guard; M2 changes `OTP_SMS` authoring for
  non-allowlisted phones (dev data only). The claim path does not call `AuthMethodAvailability`
  (authoring already did) — the tenant SMS capability is checked at authoring (7a), consistent.
- **S7 (decision 6, required field).** 33 test files POST `/recipients`, 27 call `addRecipient(`;
  builders `EnvelopeBuilder::withRecipient` (47 files) and `SeedsSentEnvelopes::seedSentEnvelope`
  (53) can default it centrally; the JSON-posting acceptance tests need the field (mechanical sweep).
  Migration backfill of dev rows under authoring rule 6. Dashboard + integrator handoff.
- **S8 (decision 8, `ALL_AT_ONCE`).** `Notification::request()` already emits one `DeliveryRequested`
  per child, so ADR-0037's no-loop shape holds. `forgetSecretsOnceSettled()` waits for every delivery
  to be terminal — a channel stuck `PENDING` would keep the link for ever; decision 4's transient
  `FAILED` closes that.
- **S9 (M3).** `notification_delivery.status` is `TEXT` with no CHECK, so the new "not needed" status
  needs no constraint migration; hydration is strict (`DeliveryStatus::from`), so code must deploy
  before data. The ordered policy needs its own fold (`NOT_NEEDED` counts as neither success nor
  failure).
- **S10 (ADR-0077 §2.8, evidence).** The audit trail renders **no** invitation delivery today — only
  `OtpSent` as `ContactUse`. And Evidence & Audit cannot read Notification's events (category (c),
  ADR-0037). So "the trail names the invitation channel" is new work that must come through
  **Envelope** facts (decision 3's recorded facts carrying channel + masked destination, as an Envelope
  event the trail can read). **[DECIDE D-e]** record the facts in TASK-031 and render them in the trail
  later (the trail's JSON form is a published, chained format), or render in TASK-031 too.
- **S11 (tenant capability).** `identity.tenant` has no RLS; read by `f5sign_identity` through its own
  connection (as `TenantNames` does); writes by `f5sign_provisioning` (SELECT, INSERT — an UPDATE
  grant is needed for the enable command). Envelope and Notification read it through a new
  IdentityAccess `Contract/Query`, adapter on the identity connection.
- **S12 (webhooks).** ADR-0064 is Proposed and unbuilt (`src/F5Sign/Webhook` absent): no runtime
  impact. Its published set excludes Notification events and `RECIPIENT_INVITATION_RESENT`; the new
  Envelope facts (not invited, channels changed) are not in it → note for ADR-0064's author.
- **S13 (stale docs found on the way).** `SignerAuthPolicy::OTP_SMS_CHALLENGE_TTL_SECONDS` docblock
  says "inert; no SMS channel exists yet"; `docs/LIVE_SCHEMA.md` omits `recipient.invitations_revoked_at`.
  Not this task's to fix unless touched; backlog/hygiene.

## Decisions after the side-effects review (2026-10-09)

- **D-a — option 1.** Only `carriesMeansToAct()` purposes touch the recipient's trace (TASK-040 §6
  case 11 and §6.6 stand). Informational notices never mark a contact dead.
- **Delivery history — option A.** A per-recipient notification history served by **Notification**
  (e.g. `GET /envelopes/{id}/recipients/{rid}/notifications`): every message of any purpose, channel,
  masked destination, status, timestamps, failure reason. Reads Notification's own tables; checks
  envelope ownership through Envelope's Contract. Separates *showing everything* (history) from
  *deciding automatically* (trace, prudent). Rejected: widening the `delivery` map with a last failure
  (still not a history); copying the history into Envelope (two copies).
- **Evidence — option E1.** Envelope records each invitation outcome as its own fact/event (sent: by
  which channel, to which masked destination, when; refused: reason; not sent: no channel / delivered
  by the integrator — the same fact decision 3 needs), fed by the write port Notification already
  calls. The audit trail reads Envelope events, which ADR-0037 allows. Rejected: letting Evidence &
  Audit read Notification events (breaks ADR-0037's category-(c) rule); leaving invitations out of the
  evidence (today's gap: the trail cannot prove how the signer got the link, for email either).
- Verified facts behind it: `notification_delivery` keeps channel, destination, status (overwritten),
  failure reason, provider reference, but **no per-delivery timestamp**; `DeliveryRequested` /
  `DeliverySent` / `DeliveryFailed` / `NotificationFailed` payloads carry ids + `occurred_at` only (no
  channel, no destination); no purge of notification data found; the trail renders only `OtpSent`
  contact uses.

## Scope: this is several pieces of work, not one task (proposal, 2026-10-09)

The audit showed the problem crosses selection, retries, facts back to Envelope, evidence, the
sender's view and spend control. Proposed split — **not yet agreed, nothing written into docs**:

Decision records:
- **ADR-0077** (rewrite): a recipient declares its notification channels — required field, modes
  (`IN_ORDER` / `ALL_AT_ONCE`), validations (contact, tenant capability, countries, phone predicate),
  claim deferral, delegated semantics, the change-channels operation, one-factor-twice warnings.
- **New ADR — delivery outcomes come back as facts**: the trace-only per-destination path, invitation
  facts incl. "not sent", Envelope invitation events for the evidence, release reasons, the history
  endpoint as Notification's first own route.
- **New ADR — delivery retry by kind of message**: per-kind retry (notifications ~20 min, OTP within
  60 s with `send_before`), transient `FAILED` on exhaustion, a Foundation-level retry dispatcher
  instead of SignatureExecution's strategy deciding for everyone.

Tasks, in dependency order:
1. **Delivery reliability** (retry ADR): improves today's email and OTP paths on its own.
2. **Delivery facts + sender visibility** (facts ADR): trace-only path, invitation facts, Envelope
   invitation events, release reasons (D-b), invitation state on the read model.
3. **TASK-031, recipient channels** (ADR-0077): declaration, tenant capability, countries, selection,
   ordered and all-at-once policies, the five creation sites, change-channels, warnings.
4. **SMS spend controls**: resend cap, admin unblock commands (D-c, operator actor), per-tenant SMS
   alert report (D-d).
5. **Delivery history endpoint** + dashboard handoff.
6. **Trail renders invitation facts** (D-e) — after 2; the trail's JSON form is published and chained.

Production gate before enabling SMS for any tenant: tasks 1–4 + DPA/privacy notice + approved sender
ID + Twilio usage triggers, prepaid balance, geo permissions.

Backlog follow-ups: BL-390 (receipts and bounces), O3 (tell the signer a code was not sent),
cross-envelope refused-contact memory, ADR-0064 webhook additions, BL-391 (tenant capability for
`OTP_SMS`), the pre-existing `invitation_failed_at`-on-closed-leg defect, the stale docs of S13.

Still open: D-b, D-c, D-d, D-e — each belongs to the task that needs it.

## Business loose ends (owner, 2026-10-09)

1. **Late sends after the world changed — accepted, into task 1.** `TransmitDeliveryUseCase` only
   checks that the delivery is still `PENDING`; with ~20 min retries a delayed invitation can go out
   after a correction (to the old, wrong contact), a void, an expiry, a revocation or a channel change.
   Before every transmission re-check that it still makes sense (envelope open, contact current,
   invitation not revoked); on correction / void / channel change, cancel that recipient's pending
   deliveries.
2. **SMS without a recognisable sender looks like phishing** (today: "Tiene un documento pendiente de
   firma: {link}", from "Factor5", unknown to the driver) — **parked**, to be worked later together
   with the SMS copy (sender name vs segment length).
3. **Country allowlist vs real carriers** (RO, BG, PL, MA, UA drivers are common in Spanish road
   transport) — **accepted**: confirm the real list with whoever knows the transport clients before
   fixing it; production prerequisite for SMS.
4. **Who pays the SMS — answered**: the deployment is **on-premise on one client's servers**, so a
   single client pays everything. No pass-through billing needed now. Consequences to carry into the
   drafts: per-tenant spend alerts (2b / D-d) lose priority but stay useful as a runaway guard.
   **Factor5 is that client** (owner): the Twilio account, the `Factor5` sender ID and the DPA are all
   Factor5's — no ownership question left.
5. **Sensitive data in SMS** (envelope title, cancellation reason in ending notices) — **accepted as
   is for now**.
6. **SMS at night** (automatic sweeps at 3 a.m.) — **to evaluate later**: backlog row (defer
   non-urgent notices to daytime; never invitations or codes).
7. **Integrator-delivered recipients re-inviting** (`[]` → resend refused → new `POST /signing-tokens`
   → several live links, BL-152 shape) — **accepted**: document it.

## Second pass on business risks (owner, 2026-10-09)

1. **One phone shared by many recipients — accepted, into task 4.** Verified: `OtpSendKeys::of()`
   keys the destination limiter on `sha256(phone)` alone, so `otp_sms_destination` (5/h) is shared
   across every session, envelope and tenant. A warehouse or traffic-desk phone signing several
   waybills in an hour is locked out at the sixth code. Task 4 decides the key/limit (e.g. phone +
   envelope, or a higher ceiling) alongside the unblock command.
2. **"Visible" needs someone looking** (no webhooks, no sender alert) — **nothing for now**.
3. **Does the consignee really sign by link?** (BL-191 `IN_PERSON_HOST`: signs on the carrier's device,
   unbuilt) — **nothing for now**.
4. **Legal sufficiency of SMS link + SMS code for e-CMR** — **nothing for now**.
5. **SMS only in es/en** for foreign drivers — **backlog**.
6. **Phones stored in clear** (BL-171, field cipher uncalled) grows with SMS — **backlog** (extend the
   existing row rather than a new one if it fits).
7. **No reminders for unopened invitations** (`first_opened_at` is visible) — **backlog**.

## Drafting (2026-10-09)

Written, uncommitted: ADR-0077 (rewritten), ADR-0078, ADR-0079; TASK-031 (rewritten), TASK-055,
TASK-056, TASK-057, TASK-058, TASK-059; `docs/adr/README.md` (index, graph, crosswalk); BACKLOG (rows
repointed, BL-392..BL-399 new, BL-171 extended); `docs/ddd/notification-domain-model.md`.

Corrections the drafting made against the tree (applied to the ADRs):
- ADR-0079 §2.5: the send-time check depends on what the delivery carries — ending notices, the
  completed notice and the sealed copy go out after closure by design; only a correction revokes
  invitations (a resend adds a link).
- ADR-0079 §2.4: the exhaustion listener must re-establish the tenant from the message stamp (the
  handler's scope has unwound, per `SentryMessengerContextListener`).
- ADR-0079 §2.2: reuse `DeliveredCodePolicy::nextIssuanceAllowedAt()` for "do not send after".
- ADR-0078 §2.1: the verdict must not depend on the trace having moved (else the per-destination path
  pre-empts `RecipientDeliveryFailed`).
- ADR-0078 §2.2: one "sent" per delivery, one failed / not sent / integrator per occasion.
- ADR-0078 §2.5: purposes are invitation | resend (a re-invitation is an invitation under a
  correction-keyed cause); the chain already folds every event, so the facts enter it when TASK-056
  emits them and TASK-059 changes only the JSON model.
- ADR-0078 §2.7: the history serves a closed failure kind, never the provider's free-text
  `failure_reason` (it can quote the destination).
- Counts: 29 test files hit `/recipients` (not 33); `SeedsSentEnvelopes` has 49 users with private
  redefinitions; six Integration tests INSERT into `envelope.recipient` directly and must gain the
  column. `SystemActorId::bootstrap` exists but is tenant-less.

Decisions the drafts propose that touch shared ground — **need the owner's OK**:
- TASK-058 D-3: move `MaskedContact` from EvidenceAudit's Domain to Foundation (Notification cannot
  import it) — a Foundation change (repo rule 7).
- TASK-057 D-c2: a new operator actor (`SystemActorId::operator()`) — a Foundation change.
- TASK-059 D1: render the invitation facts as a new key at trail schema `/1` (vs `/2`), valid only if
  no consumer outside the repo rejects unknown keys.
- TASK-056 D1 (= D-b): new release reasons `NO_REACHABLE_CHANNEL` (counts as unreached) and
  `INTEGRATOR_DELIVERED_NO_RESPONSE` (counts as reached); consequence: a veto step can agree on a `[]`
  member's silence.
- TASK-031: backfill gives unclaimed claimable slots without email `["EMAIL"]`, so a later claimant is
  still emailed.
- TASK-057 D-c: grant a resend allowance (new column) rather than reset `resendsMade`; D-d: hourly
  custodian report; D-e: two destination limiter keys, narrow (phone + envelope, 5/h) and wide (phone,
  30/h).

Owner's answers (2026-10-09):
- **`MaskedContact` → Foundation: accepted**, written into ADR-0078 §2.7. Session's `MaskedDestination`
  stays and stays different (it discloses more, to the signer recognising their own contact); the two
  are not merged.
- **Operator actor: accepted**, written into ADR-0077 §2.10: `SystemActorId::operator()` in
  Foundation/Identity, carrying the tenant (unlike `bootstrap`); the operator name is declared, not
  verified, and the evidence says so.
- **Release reasons (TASK-056 D1): decided.** (i) `NO_REACHABLE_CHANNEL`, unreached; `NOT_REACHED`
  narrows to a step never activated. (ii) a `[]` recipient is judged on whether the link was opened:
  opened → `OPENED_NO_ACT` (reached); never opened → `INTEGRATOR_DELIVERED_NOT_OPENED`, **unreached**
  (the subagent's "reached" option was rejected: it records "did not veto" for someone who may never
  have known). New BL-400: a route for the integrator to declare it delivered the link — a claim, not a
  proof.
- **Trail (TASK-059 D1): decided (A)** — a new key at schema `/1`; the owner confirmed nothing outside
  the repo reads the trail JSON.
- **Backfill (TASK-031 §3.12): decided** — `["EMAIL"]` for **every** existing row, with or without an
  email (email was the only channel ever contemplated); no `[]`, no claimable-slot exception. Rows
  without an email resolve to nothing and are recorded "not sent, no reachable channel"; read side must
  tolerate a list authoring could never produce. Test builders default to `["EMAIL"]` likewise.
- **TASK-057: decided** — D-c B (resend allowance column), D-d B (hourly custodian report), D-e (4)
  (two destination counters: phone + envelope 5/h, phone 30/h, both media).

Found on the way, not in scope: the backend's AI instructions cite TASK-022 for the OTP limiter's
fail-open, but fail-open was argued for email (ADR-0014) and must be re-argued for a billable medium —
TASK-057 §7 carries it.

## Status

Audit closed 2026-10-09: decisions 1–8, M1–M7, the side-effects review and every drafting decision.
ADR-0077/0078/0079, TASK-031 and TASK-055..059, the ADR index, BACKLOG (BL-392..BL-400) and the
Notification domain model are written and **uncommitted, awaiting the owner's review**. Spec-lint: the
remaining blocking findings are the expected "builds on a task not started" ordering gates; TASK-055 has
no prerequisite.
