# TASK-048 — How an envelope ends: acts admitted when they happen, agreement secured apart from closing, one lifecycle with an outcome, and what an ending keeps

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/task-048-how-an-envelope-ends`** (`1f4af49d`), 2026-09-29 — full regression green under the main checkout's infra Makefile harness (4164 tests / 23618 assertions; one known intermittent failure in full-suite order, `StorageLifecycleScenarioTest::bytes_are_staged_promoted_and_destroyed_on_the_clock_the_platform_undertook`, green alone 3/3 and on every prior rerun — see §7), PHPStan level 9 clean, Deptrac 0 violations / 0 uncovered, Infection covered-MSI 82% / MSI 57% (floors 79/50, measured at `786c39c2`; the two commits after it touch only `migrations/`+`tests/` for one and a small, localized `src/` warning-log addition in `EnvelopeCommandAdapter` for the other — outside/marginal to Infection's `src/F5Sign` scope). The branch, with TASK-049 and TASK-050 built after it on the same branch, was merged into `develop` on 2026-09-30 at `e6a0af5e` (⛑ corrected 2026-10-01; this read "Pending review and merge"); all three deploy together. |
| **Type** | **Defect fix with a lifecycle change.** Acts are admitted on the envelope when they happen; agreement is secured apart from closing; the status becomes the phase (`VOIDED` retired, `COMPLETED` = ended) and the result becomes `outcome` + `end_cause`; the ending facts are `EnvelopeAgreed`, `EnvelopeVoided` and a both-outcome `EnvelopeCompleted`; what an ending keeps is decided by who engaged. |
| **Why** | Measured on `develop` at `3bda20a`, 2026-09-24 (§1): a void or a blocking decline landing while a signature is on its way to DSS leaves that signature out of the sealed document, and a sender can time it; a decline relayed after a void is ignored ([`BL-290`](../BACKLOG.md)); every voided envelope is sealed, so documents nobody touched are kept for years and the daily discard can delete an original before its pending seal; `SINGLE_SEAL` consents are protected only by that seal, by accident; `VOIDED` is written before its seal, so reads wait for it and promotion conserves a pre-seal tip and then the sealed one. |
| **Builds on** | Reused unchanged: [ADR-0070](../adr/ADR-0070-an-envelope-ends-in-agreement-or-is-voided-and-sealed.md)'s decline act, seal mechanism (`DocumentSigner::seal()`) and §2.7 · the locked crossing every commit makes (`CommitFieldValues` → `EnvelopeCommandInterface::recordFieldValues()`) · `RecipientOutcome::hasActed()` · TASK-034's access trace (`authenticated_at`, `first_opened_at`) · the delivery trace of ADR-0065, `PropagateDeliverySuccessUseCase` / `PropagateDeliveryFailureUseCase` and their purposes · `StoreBackedSigningTokenIssuer::LIFETIME` · the credential-retirement check of [ADR-0060](../adr/ADR-0060-retiring-a-credential-whose-holder-changed.md) · the funnel shape of `Version20260908000004` · the two-process harness of `EnvelopeConcurrentAppendTest` · the session-setting precedent of `ConnectionTenantScope` and `init-test.sql` (for `app_now()`'s test body). |
| **Scope** | (1) Admission of every act under the root lock, re-checking every precondition, with its instant and kind, the admission instant becoming the act's instant; `app_now()`, the one clock. (2) Securing (`EnvelopeAgreed`) apart from closing; a void refused once secured; `EnvelopeVoided` at the decision. (3) `acceptsActs()` and the gate rule. (4) The lifecycle, `outcome`, `end_cause` and its party fields, the dates, `EnvelopeCompleted` for both outcomes; `VOIDED` retired; the `RELEASED` outcome with its two columns, `release_reason` (every member: `NOT_REQUIRED`, `INTEGRATOR_NO_ACT`, `OPENED_NO_ACT`, `DELIVERY_FAILED`, `UNCLAIMED`, `NOT_REACHED`, `LINK_EXPIRED`, `SENT_NO_RESPONSE`) and `released_by` (`ENVELOPE_CLOSED` here; `EXPIRY` is TASK-049's, `STEP_DEADLINE` and `SENDER_CLOSED` TASK-050's), published in every union that carries an outcome; the per-recipient invitation-sent and invitation-failed columns those reasons rest on. (5) Narrow writes and `lock_timeout` for every root-lock writer. (6) The data migration of every row. (7) Keeping, discarding, promoting by "engaged"; the synchronous opening. (8) Reads by "signed" and informational. (9) A signature that does not land: counted, awaited, alarmed. (10) The closed-leg answer. (11) The sweep of every reader of the retired terms. (12) Handoffs and the acceptance bookkeeping. Out of scope: expiry (TASK-049), the step policy, release at a step's close, close-now and the refusal of an informational commit (TASK-050), freezing clocks and operator powers (deferred by ADR-0073 §2.17), DSS calls inside a transaction (a later task). |
| **Decision record** | **[ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md)**, drafted `Proposed` on 2026-09-24 and re-cut through 2026-09-28, before implementation. This task exercises its §2.1 (all but the informational-commit refusal, TASK-050's), §2.2 (all but securing per policy and close-now), §2.3 (all but the date, TASK-049's), §2.5, §2.8 (`RELEASED`, `release_reason` and every member of it, `released_by: ENVELOPE_CLOSED`, the invitation columns and the release lock), §2.9, §2.11, §2.14, §2.15 (all but the copy-ready notice, TASK-050's) and §2.17. |
| **Delivery bar** | Over HTTP under `SEQUENTIAL_PADES`, with DSS held so a signature stays in flight: (a) the second of two signers commits, then the sender voids → refused by name (agreement secured, `EnvelopeAgreed` in the log), and the envelope reaches `COMPLETED`/`AGREED` once DSS is released; (b) the first of three signers commits, the sender voids → `EnvelopeVoided` at the void instant with the sender as party, the second signer's act is refused, and at `COMPLETED`/`NOT_AGREED`/`SENDER_VOIDED` the sealed document **contains** the first signer's signature; (c) a sent envelope nobody opened, voided → no seal, originals discarded by the next discard run; (d) the same with one recipient who opened their session → sealed and conserved, and that recipient cannot read it after the end; (e) no read of the API shows `VOIDED`; (f) the first signer of (b) reads the sealed document after `COMPLETED`. |
| **Sibling** | **[TASK-049](TASK-049-an-envelope-expires.md)** and **[TASK-050](TASK-050-a-step-says-how-much-agreement-it-needs.md)**, built after this one on the same branch. **The signer, the dashboard and integrators**: handoffs (§3.12). **`feat/evidence-audit`**: adapted on 2026-10-01, after it reached `develop` (§6). **`f5sign-infra`**: the test database's setup, and the `wt-backend` lane's, install the test body of `app_now()` **after** running the migrations (§3.1). |

---

## 1. Why this task exists

Measured on `develop` at `3bda20a`, 2026-09-24:

1. **The gap between an act and its bytes.** `CommitSignatureUseCase` commits the act and calls no DSS;
   `SignForRecipientUseCase` stamps the signature later and Envelope learns of the act on `RecipientSigned`.
   `Envelope::void()` and the decline's voiding write `VOIDED` at once; a later signature is refused by
   `appendDocumentArtifact()` and parks; `SealVoidedEnvelopeUseCase` seals the tip without it.
2. **A decline relayed after a void is ignored** ([`BL-290`](../BACKLOG.md)); `recordRecipientCompletion()` has the
   same convergence no-op on a terminal envelope.
3. **The indiscriminate seal.** Every voided document with a tip is sealed; a `SEAL` is not an `UPLOAD`, so the
   promotion funnel promotes documents nobody touched; the daily discard can run before a pending seal.
4. **`SINGLE_SEAL` consents add no revision**, so artifact-based predicates read them as "nobody signed".
5. **`VOIDED` before its seal** — `readsWaitForTheSeal()` refuses reads meanwhile (its docblock carries the reason),
   and hourly promotion can conserve the pre-seal tip, then the sealed one.

## 2. What already exists (reuse, do not rebuild)

- **The ending rules, as pure code** (2026-09-28, ahead of the three tasks): `EnvelopeEndingEvaluator` (admission, securing, closing, clocks, releases, the `send()` refusals) over `StepCompletionEvaluator` and `ReleaseReasons`, run against the scenario catalog `tests/F5Sign/Envelope/Testing/Scenario/EndingScenarioCatalog.php`. Nothing calls them yet: this task wires admission, securing, closing and releases into the aggregate, which calls them rather than growing a second copy of any rule, and the catalog is the oracle of its tests.
- The locked crossing: `CommitFieldValues::record()` on every commit reaches `recordFieldValues()` (root lock,
  refuses a terminal envelope). `CommitDelegatedSignatureUseCase` calls it under a condition and before its step
  guard; `DeclineSignatureUseCase` makes no Envelope command call. Per-recipient checks are read through
  `RecipientAuthContext` before that lock; that context already carries dates, lists and strings.
- `CommitSignatureUseCase` consumes the signing challenge in memory only, before its save.
- `DocumentSigner::seal()`, the one seal both paths use; `EnvelopeReadyToSeal` → the completion seal → `complete()`.
- `RecipientOutcome::hasActed()`; `authenticated_at` and `first_opened_at`, written today through the relay.
- `ready_to_seal_at` on the envelope; each document's `SEAL` artifact with its `created_at`; `EnvelopeCompleted`'s
  `occurred_at` in `platform.event_log`.
- The storage funnels owned by `f5sign_envelope_custodian` and their per-tenant reads; `DbalUnpromotedDocuments`.
- `OnEnvelopeVoided` (session revocation) and ADR-0059's synchronous guards, which stay.
- The root-lock writers that call `save()` today: `RecordRecipientAuthenticationUseCase`,
  `RecordRecipientFirstOpenUseCase`, `RecordRecipientCompletionUseCase`, `RecordRecipientDeclineUseCase`,
  `CorrectRecipientUseCase`, `ResendRecipientInvitationUseCase`, `ClaimRecipientUseCase`,
  `UnlockRecipientAuthUseCase`, `ResetRecipientAccessCodeUseCase`, `RecordRecipientAuthHardLockUseCase`,
  `CompleteEnvelopeUseCase`, `VoidEnvelopeUseCase`, `PromoteSignedDocumentsCommand`,
  `EnvelopeCommandAdapter::markRecipientDeliverySent` and `::markRecipientDeliveryFailed` — a list §5's census
  replaces as the authority.

## 3. What gets built

### 3.1 Admission

A method on `EnvelopeCommandInterface`, extending the `recordFieldValues()` crossing, called by the commit, the
delegated commit (after its step guard, unconditionally) and the decline, **before** the session records its act.
Under the root lock it re-checks `acceptsActs()`, that the leg is open and not admitted (before the step, so a released member reads `LEG_CLOSED`, not `STEP_NOT_ACTIVE`), that the recipient's step is active (its deadline is TASK-050's), and that the credential is not retired; records the admission
instant (`app_now()`) and kind (commit or decline) by a narrow write; and returns the instant, which the session
uses as the act's instant. An informational role's commit is still admitted here, as today: refusing it belongs
with informational members no longer holding a step (TASK-050), since until then a `VIEWER` ends its leg only
by committing and today's step predicate waits for every member (`Envelope::advanceAfterRecipientTerminal()`).

`app_now()` is created here: a migration installs the production body, which returns `clock_timestamp()` and
reads nothing else; the test database's setup and the `wt-backend` lane replace it, **after** their migrations
(`init-test.sql` runs at creation, before them), with a body that honours a session setting; every test that
pins it restores it in a `finally`. PHP fast-path checks are advisory; the locked database check decides.

### 3.2 Securing and closing

Evaluated under the lock at every admission and step close, from admitted acts: the agreement secured →
`outcome: AGREED`, `agreed_at`, `EnvelopeAgreed`; a blocking decline, or a sender's void before securing →
`NOT_AGREED`, `end_cause`, the party, `closed_at`, `EnvelopeVoided` (at this instant, as today); a void after
securing → refused by name. TASK-050 replaces the step rule, not the mechanism. Every root-lock writer after send
writes narrowly under a `lock_timeout`; a timeout is a retryable 503 with a named code.

### 3.3 `acceptsActs()` and the gate rule

`acceptsActs()` = `sent_at` set, not closed, `app_now() < expires_at` (TASK-049 adds the date; every comparison
with it, the gate's unlocked read included, goes through `app_now()`). The act routes
(admission, claim, correction, resend) ask it; correction and resend also refuse any closed leg — admitted, declined or released — naming it: an invitation asks for an act that leg can no longer give; a signer or informational member gets back in by reset or unlock and the copy-ready link, never a new invitation. The
access-gate routes (one-time-code issuance, `SubmitAuthResponse`, the neutral gate's session open) ask, unlocked:
*(leg open and `acceptsActs()`) or the recipient signed or the recipient's role is informational*. The sender's access-code reset and unlock follow the gate: allowed on a draft, and after send for a recipient who could pass the gate by the rule above; refused by name otherwise (they no longer ask only `isTerminal()`, and never `acceptsActs()`: a signer who lost their code after `COMPLETED` must still be able to read). Session renewal asks the gate rule. Link minting is left as it
is (`SigningTokenIssuance`'s reserved decision; `TerminalEnvelopeClosesTheCeremonyHttpTest` pins it).

### 3.4 The lifecycle and its facts

`READY_TO_SEAL` is written by the close when nothing is in flight, or by the last landing; a landing after
`closed_at` records its recipient's outcome without re-evaluating steps. After `READY_TO_SEAL` only the seal
appends. The one seal path (§3.7) runs on `EnvelopeReadyToSeal` for both outcomes; `SealVoidedEnvelopeUseCase`
merges into it, and the SignatureExecution reaction to `EnvelopeVoided` goes. Then `COMPLETED` and
`EnvelopeCompleted` (both outcomes; `outcome`, `end_cause`, `agreed_at`, `closed_at`, declined and released
recipients with ids and enums only — each release's `release_reason` and `released_by`). `VOIDED` leaves the status enum; `void_cause`/`voided_at`/`voided_by`/
`voided_by_recipient_id`/`void_reason` become `end_cause`/`closed_at`/`ended_by`/`ended_by_recipient_id`/
`end_reason` on the envelope and the API; `EnvelopeVoided` keeps its payload keys. `expires_at` is published.

**Release.** At every close, each member still open is released (ADR-0073 §2.8): outcome `RELEASED`,
`released_by: ENVELOPE_CLOSED`, and a `release_reason` from the member's facts, by the first match of the eight —
the same reasons TASK-049 and TASK-050 reuse, so they add only their own `released_by`. The facts they rest on:
the opening columns (§3.6); `signs_via`; the claim state; whether the member's step activated; and two new
per-recipient columns, the last invitation `SENT` instant and the latest invitation failure — an invitation counts as sent when any of its channels reached `SENT`, and as failed only when none did — written by
`PropagateDeliverySuccessUseCase` / `PropagateDeliveryFailureUseCase` for invitation purposes only
(`RECIPIENT_INVITATION`, `RECIPIENT_INVITATION_RESENT`, through a new exhaustive predicate on
`NotificationPurpose`, never `carriesMeansToAct()`). Link validity is that instant plus
`StoreBackedSigningTokenIssuer::LIFETIME`; a link an integrator minted through `POST /api/v1/signing-tokens` records
no send and reads `NOT_REACHED` ([`BL-309`](../BACKLOG.md) would make it exact). Each release records
`RecipientReleased` (recipient, `release_reason`, `released_by`); its per-recipient revocation is TASK-050's (§3.8).

### 3.5 The data migration, per status

Run with the queues drained **and the event relay caught up** (nothing unpublished in `platform.event_log`). Every
status is enumerated; the migration asserts zero rows in `EXPIRED`, `SEALING`, `CORRECTING`, `ROUTING_FAILED`,
`SEALING_FAILED`.

| Row | Becomes |
|---|---|
| `DRAFT` | unchanged here; TASK-049's migration turns its date into a duration |
| `SENT` | an admission backfilled for every recipient whose **session** completed or declined, at that instant; the securing rule evaluated once — if it secures, `agreed_at` is the securing admission's instant and the post-deploy command records `EnvelopeAgreed` through the aggregate |
| `READY_TO_SEAL` | `outcome: AGREED`; `agreed_at` and `closed_at` = `ready_to_seal_at` |
| `COMPLETED` | `outcome: AGREED`; `agreed_at`/`closed_at` = `ready_to_seal_at`; `completed_at` (new) = the `ENVELOPE_COMPLETED` fact's `occurred_at` |
| `VOIDED`, sealed | `COMPLETED`, `NOT_AGREED`, `end_cause` from `void_cause`, `closed_at` from `voided_at`, `completed_at` = the latest of its `SEAL` artifacts' `created_at` |
| `VOIDED`, seal pending, every session completed before `voided_at` already on the PDF | `READY_TO_SEAL`, `NOT_AGREED`, `end_cause`, `closed_at` from `voided_at`; an admission backfilled for each of those sessions |
| `VOIDED`, seal pending, a session completed before `voided_at` whose signature is **not** on the PDF (refused by `appendDocumentArtifact()` and parked) | **`SENT`** with `closed_at` from `voided_at`, `NOT_AGREED`, `end_cause`; an admission backfilled for every such session. Never `READY_TO_SEAL`: after it only the seal appends (ADR-0073 §2.5), so the parked signature could never land. The parked messages are replayed after deploy; the last landing writes `READY_TO_SEAL` through the ordinary path |

A document is "sealed" when it carries a `SEAL` artifact; a `VOIDED` row is "sealed" when every document with
bytes does, and "seal pending" otherwise.

The two invitation columns are backfilled first. `notification.notification_delivery` holds a status but no instant; the instants are the `occurred_at` of `NOTIFICATION_DELIVERY_SENT` / `NOTIFICATION_DELIVERY_FAILED` in `platform.event_log`, whose payload names the `notification_id`, joined to `notification.notification` for its `purpose` (the two invitation purposes) and its `addressee_ref` (the recipient's id), with the same any-channel rule as above. None found: no instant, so `NOT_REACHED`. Recipients still `PENDING` on a closed row are then released `released_by: ENVELOPE_CLOSED`, each with the `release_reason` its facts give (ADR-0073 §2.8). The migration leaves rows valid and records no facts: no `RecipientReleased` for these releases and no `EnvelopeCompleted` for a sealed `VOIDED` row it moves to `COMPLETED`, so the evidence trail of an envelope that ended before the deploy is not guaranteed to match its rows — accepted, since no data before the deploy matters today (maintainer, 2026-09-28). On an `AGREED` row none is expected — today's step predicate waits for every member — so the migration counts them, releases any informational member it finds the same way, and refuses on a blocking one.

A post-deploy command (a migration dispatches nothing), through the aggregate: records `EnvelopeAgreed` where
the `SENT` row secured; **re-evaluates every `SENT` row's open step** with the aggregate's predicate as deployed
(TASK-050's: informational members never hold a step), so an envelope
whose step waits only on members that no longer hold it moves on now rather than at its expiry; and re-drives the
seal path for every `READY_TO_SEAL` row, applying §3.7's keep rule.

Conservation ceilings already resolved on `COMPLETED` and sealed `VOIDED` rows stay as they are: promotion has
already carried them to storage, and re-resolving at the end (ADR-0073 §2.16, TASK-049) applies to envelopes that
complete after the deploy.

### 3.6 The synchronous opening

The access gate (`SubmitAuthResponse`; the neutral gate's session open) records `authenticated_at` and
`first_opened_at` through an Envelope command, as a narrow write on the recipient row under that row's lock (new:
no recipient-row lock exists today) and no root lock, **before** any credential is minted or read served; refused
once `closed_at` is set — as a record: the gate itself proceeds under §3.3's rule, and a late opening simply
counts as no engagement. The two gate routes own their transactions differently:
`SigningSessionRepository::submitAuthResponse()` begins its own and commits even on a refusal, so the opening
write runs after it commits and before any minting; `StartSessionUseCase` runs in the bus's transaction and
joins that. The
close takes the recipient rows' locks before reading and writing `closed_at`, and every release takes the
released member's row lock before reading the opening columns; under that lock the opening write records nothing on a leg already closed — not a refusal — and the gate re-reads §3.3's rule under the lock: a released blocking member or a decliner is refused and no credential is minted; a signer or an informational member passes (ADR-0073 §2.8). The relay-borne writers of those columns refuse to write after `closed_at`. The opening write runs under the same `lock_timeout` and retryable 503 as every root-lock writer. The opening and admission columns are written only by their own writers — the admission; the synchronous opening and its relay-borne twins above, all as the same once-only write guarded by `IS NULL`, so a twin arriving after the synchronous write changes nothing; no other write — a narrow one or the aggregate's full upsert, which today carries `first_opened_at`/`authenticated_at` (`DbalEnvelopeRepository`'s recipient upsert) — includes them, as `upsertField()` already excludes `value`/`signed_at` (`LOAD-BEARING.md` §1.17).

### 3.7 Keeping, discarding, promoting

- **Signed** = outcome `COMPLETED` or an admitted commit (a signature or an approval); **acted** = admitted, `COMPLETED` or `DECLINED`;
  **engaged** = acted, or opened before `closed_at`. Three named predicates.
- Not agreed: anyone engaged → the seal path seals every document with bytes; nobody engaged → no seal.
- Stated as properties, never a status (ADR-0062 §2.4): promotion names documents of envelopes with
  `completed_at` set **and** (someone engaged, or carrying a `SEAL`).
- The discard names `completed_at` set, `outcome: NOT_AGREED`, nobody engaged, only an `UPLOAD`; it no longer
  reads `settings_expires_at`, and re-checks the envelope before each discard. `DbalUnpromotedDocuments` follows.
- A new migration supersedes both funnels (`CREATE OR REPLACE`, `down()` restores them) and changes
  `f5sign_envelope_custodian`'s column grants: on `envelope.envelope`, `closed_at` (renamed from `voided_at`),
  `completed_at` and `outcome` join and `settings_expires_at` leaves (today's grant, from
  `Version20260908000004`: `id`, `tenant_id`, `voided_at`, `settings_expires_at`, `conservation_until`); on
  `envelope.recipient`, `envelope_id`, `tenant_id`, `outcome`, admission and opening columns only, with a policy
  written `TO` that role and narrowed to rows that engaged.

### 3.8 Reads

From `closed_at` a recipient who neither signed nor is informational is refused every read and gate pass, and
their sessions are revoked through `EnvelopeVoided`. Per-release revocation is TASK-050's: in this task the only
releases at an agreed ending are informational members, who keep reading. Between `closed_at` and `COMPLETED` readers
wait for the seal (`readsWaitForTheSeal()`, re-keyed on "closed and not completed"). After `COMPLETED`, recipients who signed (§3.7's `Signed`, an admitted approval included) and informational recipients read the sealed document; decliners and other released members do not. Reads
follow the role and the admission, never `release_reason` or `released_by`.

### 3.9 A signature that does not land

The act counts from admission. Stamping retries as today — `DssHttpAdapter` retries `500`/`502`/`503`/`504`, and a
429 is retried by `async_events`' `retry_strategy` (4 retries, then parked on `failed`) because nothing marks it permanent (the Never list keeps it so) — with
`ArtifactChainConflictException` retried as transient under backoff rather than parked after three attempts — on a
bounded curve of about 3 h at the 60 s ceiling, longer than the 2 h alarm's threshold below, then parked like
everything else (maintainer, 2026-09-29) — not a promise the alarm fires before the park, since the budget runs from
the first failure and the alarm from the close; a parked signature keeps its envelope unsealed, so the alarm names it
either way. The
seal waits for every admitted signature. An envelope closed for more than 2 hours by `app_now()` and not
`COMPLETED` raises an alarm and shows "seal pending since"; a parked message is replayed as today.

### 3.10 Closed legs

`RecipientAuthContext` gains the recipient's outcome; token routes answer a closed leg as closed through a new
predicate beside `SessionStatus::terminalOutcome()`, under §3.3's gate rule.

### 3.11 The sweep

Every read of `COMPLETED`, `VOIDED`, `void_cause`, `voided_at`, `voided_by`, `voided_by_recipient_id`, `void_reason`, `VoidCause`, `isBlocking`,
`min_signatures`/quorum, `\F5Sign\Session\Application\Subscriber\OnEnvelopeVoided` (revocation, stays) and
`\F5Sign\SignatureExecution\Application\Subscriber\OnEnvelopeVoided` (annulment seal, goes) in `src`, `tests`,
`migrations`, `docs`, `config`, `CLAUDE.md` and both frontends (fixtures included) is classified and changed;
notices claim nothing from `COMPLETED` alone; prose made false is corrected — among it the "because the sender
voided" of `SessionRevoked`'s and `RevokeEnvelopeSessions`' docblocks and of the published `#[OA\*]` strings of
`CommitSignatureController` and `CommitDelegatedSignatureController`; `docs/ddd/` reconciles the envelope model.

### 3.12 Handoffs and acceptance bookkeeping

- `docs/frontend-handoff/`: a signer handoff (statuses, `outcome`, `RELEASED`, the gate rule, the retired
  `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` in `useSignerNavigation`), a dashboard handoff, and an integrator notice
  listing every changed status, field, enum member, ProblemCode and event on `/v1` — including that
  `envelope.completed` now fires for both outcomes, so "agreed" is read from `outcome` (an old payload without it
  reads `AGREED`), and that `EnvelopeVoided`'s party members become nullable (expiry has no party).
- At acceptance: ADR-0070's Status (superseded in part, §2.6 narrowed), and amendment clauses on ADR-0049 (§2.8: reset and unlock follow the gate), ADR-0059, ADR-0057,
  ADR-0061, ADR-0062 (§2.4, §2.5, §2.8)
  and ADR-0064 (§2.4: `envelope.completed` widened, `envelope.expired` never emitted, and the census rows the three tasks add: `EnvelopeAgreed` published as `envelope.agreed` and `RecipientReleased` as `envelope.recipient_released`, both born here; `EnvelopeExpiryExtended` (TASK-049) and `EnvelopeClosedBySender` (TASK-050) excluded — maintainer, 2026-09-28); the `docs/adr/README.md` row and edges; `LOAD-BEARING.md`
  §1.5/§1.17 amended (the entry for ADR-0073 §2.4 is TASK-050's).

## 4. Key decisions (maintainer, 2026-09-24/25 and 2026-09-28)

- **D1** — The admission instant decides, for every cause; an admitted act's instant is the admission's.
- **D2** — Securing and closing are two instants; a secured agreement cannot be voided nor undone inside the platform.
- **D3** — Status is the phase; `COMPLETED` = ended; `outcome` (open enum) and `end_cause` carry the result.
- **D4** — `EnvelopeAgreed` at securing; `EnvelopeVoided` at a decision without agreement, unchanged in meaning;
  `EnvelopeCompleted` at the end for both outcomes.
- **D5** — Keep if anyone engaged; an opening never grants a read; signers and informational recipients read after
  the end, decliners do not.
- **D6** — A parked signature is counted and awaited, never sealed around; no freeze, no operator override.
- **D7** — `/v1` changes in place, documented for frontends and integrators.
- **D8** — A release carries two columns: `release_reason`, always the fact about the member, and `released_by`,
  what released them. One field answering both lost facts (an opening hidden under `SENDER_CLOSED`) and made a
  veto step's cause circular (maintainer, 2026-09-28).
- **D9** — Data existing before the deploy only has to be left valid: the migration records no facts and the evidence of envelopes that ended before it is not guaranteed (maintainer, 2026-09-28).

## 5. Verification

- The delivery bar, cases (a)–(f).
- **Two processes**: a commit, a decline and a correction each against a void, and a commit against a blocking
  decline — both orders; the loser refused before any fact exists, or the ending contains the winner's signature.
  An opening against a close. A void while a signing holds a document row returns within the `lock_timeout`.
  These cases opt out of DAMA's rollback (`#[SkipDatabaseRollback]`) and delete their own rows in `tearDown`, so a
  kept lane inherits nothing ([`BL-291`](../BACKLOG.md)).
- **`app_now()` cannot be steered in production**: the test database always carries the test body, so no suite
  test can observe the production one. Held by a static test over the migration's SQL, in the style of
  `MigrationVersionTest`: the production body reads `clock_timestamp()` and no setting.
- **The migration**: a fixture per row of §3.5, including a `VOIDED` row with a parked signature, which migrates to
  `SENT`/closed, lands on replay, and is sealed **with** that signature. (The re-evaluation of a `SENT` row's step is
  TASK-050's bar: it needs that task's predicate.)
- **An opening on a closed leg**: a signer after `COMPLETED` and an informational member after the close pass the gate and read, with no opening recorded; a decliner is refused and no credential is minted.
- **An opening against a stale writer** (two processes): a correction of another recipient that loaded the aggregate before an opening commits after it, and the opening survives.
- **An approver reads**: an `APPROVER` whose approval was admitted reads the sealed document after `COMPLETED`.
- **Old payloads**: an `EnvelopeCompleted` payload of the current shape deserializes as `AGREED`, `end_cause` null.
- **Recovery follows reading**: a reset and an unlock succeed on a draft, for an open leg, for a signer after `COMPLETED` and for an informational member after the close; they are refused by name for a decliner, before the close or after it.
- **Censuses**: every act route asks `acceptsActs()` and every gate route — reset and unlock included — the gate rule (sabotage one to ask
  `envelopeIsAlive`); every root-lock writer after send is narrow; no read of the retired terms survives.
- **Instants**: an admitted act's `SignatureCommitted` carries the admission instant.
- **Grant boundary**: a role-switched connection (new harness; `RlsIntegrationTestCase` has no `SET ROLE`
  scaffolding) proves the custodian reads only its columns across tenants.
- **Parity and disjointness** of funnels and per-tenant reads.
- **Release reasons**, each from its fact, released at a void (`released_by: ENVELOPE_CLOSED`): every one of the eight, including an access code sent after the invitation (still judged by the invitation), an invitation that failed and was resent, and an integrator-minted link (`NOT_REACHED`). Drop a reason's fixture and the census fails naming it.
- **Nothing pending on a closed envelope**; a late signature never moves the status; nothing appends after the seal.
- **A parked signature**: in the suite, with `app_now()` pinned 3 hours after the close, the alarm is raised;
  replayed → sealed with every admitted signature. **On the stack, never from the suite** (`async_events` is
  `in-memory://` in test): with DSS held, the other queues keep flowing.

## 6. Open follow-ups (track, don't solve here)

- Expiry (TASK-049); the step policy, release at a step's close, close-now and the informational-commit refusal
  (TASK-050); freezing and operator powers (ADR-0073 §2.17); DSS
  calls inside a transaction (a later task, already under study).
- **`feat/evidence-audit`, when it reaches `develop`.** ⛑ **2026-10-01: done** by the audit trail's re-cut. The trail ends at
  `EnvelopeCompleted` for both outcomes, a released party's outcome carries `release_reason` and `released_by`, and the roster
  check reads the outcome the trail states for each party
  ([ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md) §2.9, §9; [`BL-357`](../BACKLOG.md)). The rest of
  this bullet is the record from before the adaptation. Kept disjoint, and whichever lands second adapts to the other (ADR-0073 governs and amends ADR-0072): ADR-0073 and its pure rules reached `develop` first (2026-09-28), so `feat/evidence-audit` meets them when it merges `develop`, and this task's branch adapts that work once it too is on `develop`. Measured on
  `origin/feat/evidence-audit`: `EndedStream::TERMINAL_TYPES` treats `EnvelopeCompleted`/`EnvelopeVoided` as the
  end; `TrailAssembler` reads the void's instant, actor and `void_cause` from `EnvelopeVoided` and places the
  annulment seal after it; acts are `Signed`/`Declined`; `TrailJson` publishes `kind: VOIDED`; `rosterReconciled()`
  reads `quorum`/`min_signatures` and `Role::isBlocking()`. To adapt: the end is `EnvelopeCompleted` for both
  outcomes (`EnvelopeVoided` keeps its meaning, so the void's instant and actor stay right); `EnvelopeAgreed` and
  admission instants in the trail; a released outcome with its `release_reason` and `released_by`; the new causes; `kind` against `outcome`;
  the roster check against the step policy's new members and informational members.
- [`BL-306`](../BACKLOG.md), [`BL-307`](../BACKLOG.md), [`BL-308`](../BACKLOG.md), [`BL-309`](../BACKLOG.md).
- **Surfaced during this task's fix rounds and closure, new**: [`BL-352`](../BACKLOG.md) (retry-curve capacity), [`BL-353`](../BACKLOG.md) (`Role::isBlocking()` dead), [`BL-354`](../BACKLOG.md) (`SEAL_ONLY` zero-recipient carve-out, pre-existing), [`BL-355`](../BACKLOG.md) (`send()` did not call `refusalsAtSend()` at this task's close; closed by TASK-050, whose `Envelope::send()` now asks it), [`BL-356`](../BACKLOG.md) (`StorageLifecycleScenarioTest` intermittent full-suite failure).

## 7. Deviations & honest notes

### Scope
- None beyond what §3 already scoped. `task-validate` confirmed the diff (295 files at `786c39c2`, +2 migration/test files at `1f4af49d`) stays inside Envelope/Session/SignatureExecution/Notification(invitation-predicate-only)/Foundation-Custodian, the three migrations, and their test trees; nothing under the task's declared **Out** list (TASK-049 expiry, TASK-050's step policy/release-at-step-close/close-now/informational-commit refusal, ADR-0073 §2.17's freeze/operator-override half, DSS-in-transaction) appears anywhere in it.

### Decisions made during implementation
- **D-T1** — Informational members keep holding their step until TASK-050 (`InformationalMembers::HOLD_THEIR_STEP`); the evaluator already encodes TASK-050's rule but the aggregate passes the transitional mode until that task deletes it.
- **D-T2** — No expiry in the aggregate yet; `acceptsActs()` is `sent_at` set and not closed until TASK-049 adds the date.
- **D-T3** — The ending types (`ActRefusal`, `RoleStanding` too) are Contract types, since `EnvelopeCompleted`, `RecipientReleased` and the API publish them.
- **D-T4** — A close nobody engaged with ends the lifecycle at once (straight to `COMPLETED`, recording `EnvelopeCompleted`) rather than writing `READY_TO_SEAL` for a seal path that would seal nothing.
- **D-T5** — A decline's leg closes at its admission; the relayed `SessionDeclined` → `RecordRecipientDecline` becomes a convergent no-op.
- **D-T6** — One crossing: `recordFieldValues()` on the port became `admitCommit()`/gained `admitDecline()` (the crossing extended, §3.1) rather than living beside a second one.
- **D-T7** — Lock timeout lives in `findLockedForUpdate()`, so the 5s `lock_timeout` + `ENVELOPE_BUSY` 503 covers every root-lock writer at once.
- **D-T8** — `Envelope::SIGNING_LINK_LIFETIME` mirrors Session's `StoreBackedSigningTokenIssuer::LIFETIME` (parity pinned by `SigningLinkLifetimeParityTest`), since the Envelope domain cannot read Session's constant.
- **D-T9** — No `schema_version` bump for `EnvelopeCompleted`: an old payload decodes by the absence of `outcome` (reads `AGREED`), pinned by `EnvelopeCompletedTest` and `DomainEventPayloadTest`.
- **D-T10** — The completed notice asks the outcome; `NotifyCompletedEnvelopeRecipientsUseCase` returns for anything but `AGREED` (TASK-050 brings the copy-ready notice for `NOT_AGREED`).
- **D-T11** — The gate methods of `SigningSession` keep their `$envelopeIsAlive` parameter name, handed the gate rule's answer (`RecipientAuthContext::gatePasses`) rather than being renamed, to avoid a ripple through ~100 test sites.
- **D-T12** — A shut gate with no terminal session publishes `RELEASED`/`DECLINED`/`REVOKED` on `GET /signing/session/auth` (`SessionStatus::outcomeAtTheGate`); `POST /signing/session`'s status union is unchanged.
- **D-T13** — The synchronous opening uses `app_now()` (one instant per write); relay-borne twins keep their own fact's instant; every root-lock load also locks the recipient rows; an opening on a missing envelope records nothing at the gate.
- **D-T14** — `app:envelope:reconcile-endings` takes `--tenant` (repeatable) instead of a cross-tenant funnel, per the deploy runbook rather than the ADR's original assumption.
- **D-T15** — The `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` retirement is TASK-050 §3.3's; the attempt is parked in `var/task-runner/TASK-048/task-050-quorum-decline-retirement.patch` (`git apply`).
- **TASK-044 §4 D5's precedence on the delegated commit route is reversed** (the admission — which now judges the form — runs after the step guard, not before it): ADR-0073 §2.1 requires this order; recorded in `CommitDelegatedSignatureUseCaseTest::a_dormant_step_is_refused_before_any_value_is_judged`.
- **The bounded chain-conflict retry** (user decision B, 2026-09-29): `ArtifactChainConflictException` is retried on `async_events` for 183 attempts (the shared curve's four, then 179 at its 60s ceiling — about 3h) before the failure transport, bounded per ADR-0015 §2, deliberately longer than the 2h pending-seal alarm's threshold — not a promise the alarm fires before the park (the retry budget runs from the first failed delivery, the alarm from the envelope's close, checked hourly); what holds is that a parked signature keeps its envelope closed and unsealed, so the alarm names it whenever the park happened. Realized by `ChainConflictRetryStrategy`.
- **Case-6 release reason (N3) accepted under D9, not resolved**: a `VOIDED` row sealed around an act that had not taken effect releases that signer by their facts — typically `OPENED_NO_ACT` — even where their signing session's completion is on record as a consent. ADR-0073 §2.8's eight release reasons have no member for "acted, outside the admitted count." Accepted under D9 (data from before the deploy only has to be left valid); no ADR change. Since fix round 2 this only arises under `SEQUENTIAL_PADES` — under `SINGLE_SEAL` the consent is the act, and it is now recorded as landed (see N1/N2 below).
- **`migrations/Version20260928131928.php`'s `down()` cannot revert step 3c's landing write** (fix round 2, `1f4af49d`): no predicate over post-migration data distinguishes a step-3c-landed row from an ordinarily-landed one, unlike round 1's `RELEASED` case (where `RELEASED` never pre-existed, so `WHERE outcome = 'RELEASED'` unambiguously selected what to undo). Documented as an accepted asymmetry in the migration's own `down()` docblock rather than repaired with a marker table — an unpublished migration, and `down()` is a last-resort path nothing running depends on (repo-specific rule 2's carve-out).

### Decisions that needed an ADR
- [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md), drafted `Proposed` 2026-09-24, re-cut nine times through 2026-09-28, **accepted by the user on 2026-09-29** together with its amendment clauses on ADR-0049 §2.8, ADR-0057, ADR-0059, ADR-0061, ADR-0062, ADR-0064 and [`LOAD-BEARING.md`](../LOAD-BEARING.md) §1.5/§1.17 (§1.5/§1.17 were already reconciled in-branch, ahead of this closure). [ADR-0070](../adr/ADR-0070-an-envelope-ends-in-agreement-or-is-voided-and-sealed.md) moves to superseded-in-part.

### Declared and unproven properties
- ADR-0073 §2.4's same-facts property is pure-code tested (`StepCompletionEvaluatorTest`) but only exercises one clock (admission) today; the property becomes discriminating once TASK-049/050 add the deadline/expiry clocks to compare against.
- At this task's close `EnvelopeEndingEvaluator::refusalsAtSend()` was unit-tested (`EndingSendRefusalsTest`) but not called by `SendEnvelopeUseCase` — TASK-050 territory, tracked as [BL-355](../BACKLOG.md). **Since closed by TASK-050:** `Envelope::send()` asks it.
- **N1/N2/N4 were FIXED in fix round 2 (`1f4af49d`), not deferred**: `signatureOnChain()`'s successor, `actTookEffect()`, now reads the admitted act's own record for every signing mode and role (`SINGLE_SEAL`'s consent, `SEQUENTIAL_PADES`'s `RECIPIENT_SIGNED` fact plus, for a signing role, its SIGN artifacts) instead of falling back to `outcome = 'COMPLETED'` outside sequential-PAdES signers. `EndingDataMigrationTest` gained fixtures discriminating the previously-undiscriminated shapes (a genuinely-parked sequential-PAdES signing, a two-signer document with one on the chain and one not, an `APPROVER` with and without an admitted act) and was sabotage-checked per the commit's own account.
- `StorageLifecycleScenarioTest::bytes_are_staged_promoted_and_destroyed_on_the_clock_the_platform_undertook` fails intermittently in full-suite order, at its "and its version is gone from the bucket" assertion (`assertConserved()` → `versionExists` on the superseded staging placement, MinIO-backed) — green alone every time (3/3 on 2026-09-29) and on every prior rerun. Seen in three full-suite runs on this branch (2026-09-28 once; 2026-09-29 at `786c39c2` and at `1f4af49d` — the latter: 4164 tests/23618 assertions, only this failure, phpstan/lint/deptrac clean). The test was itself edited by this task (`8cd3424a`, `41e73bcb`). Suspected: MinIO version-deletion visibility lag under full-suite load, or order-dependent bucket state shared across tests — unconfirmed either way; not a claimed regression, not cleared either. Tracked as [BL-356](../BACKLOG.md).

### Debt left behind, and where it lives now
- [BL-352](../BACKLOG.md) — `ChainConflictRetryStrategy`'s ~3h retry curve is uncapped by how many recipients a step allows in parallel (accepted; capacity, not disclosure).
- [BL-353](../BACKLOG.md) — `Role::isBlocking()` has no production caller left; the live predicate is `StepPolicy`/`EnvelopeEndingEvaluator`.
- [BL-354](../BACKLOG.md) — `WorkflowType::SEAL_ONLY` has no zero-recipient carve-out at `send()` (pre-existing, unrelated to this task).
- [BL-355](../BACKLOG.md) — `EnvelopeEndingEvaluator::refusalsAtSend()` was built and tested but not called at this task's close; **closed by TASK-050**, whose `Envelope::send()` calls it.
- [BL-356](../BACKLOG.md) — the `StorageLifecycleScenarioTest` intermittent full-suite-order failure (see above).
- Existing [BL-306](../BACKLOG.md), [BL-307](../BACKLOG.md), [BL-308](../BACKLOG.md), [BL-309](../BACKLOG.md) — unchanged, still Open, still this task's.
