# TASK-064 — The gates are editable until the recipient enters

<!-- OFFREPO: the incident in §1 was reported by the dashboard team's session on 2026-10-20, and the review findings restated in §4 and §6 came from four review agents in the owner's working session that day. The decisions marked "owner, 2026-10-20" were taken in the owner's sessions that day. Every fact taken from them is restated here; nothing in this record depends on reading either. -->

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/gates-editable-before-entry`** (tip `17e8951c`), 2026-10-21. Full suite green at `4307495f` (7776 tests, 86141 assertions) under the `wt-backend` lane of this worktree (kept lane, `src=` this tree), with lint, deptrac and PHPStan clean; the later commits changed only docs, docblocks and one `#[OA\*]` string, and the affected tests (54) were re-run green at `0729dd0f`. At `17e8951c` the fast tiers (6458 tests), the gate-change and OpenAPI acceptance tests (80) and lint, deptrac and PHPStan are green on the same lane. Infection on the changed lines: the real escapes killed by tests, the rest justified (§7). ADR-0083 is Accepted (owner, 2026-10-20, `2d5ead35`). Merge pending. Left out by design: editing after the first opening (§6, BL-437). |
| **Type** | **Forward build** in Envelope: a new machine route replaces a recipient's declared gates, allowed only while that recipient has never opened their link. A new event, and one new statement in the audit trail. One small change on the opening path, which Envelope and Session share: the opening is refused when the declaration it was decided under has changed (§4 #6). |
| **Why** | A recipient's gates are fixed at authoring, and nothing can repair a wrong declaration. That has three consequences today: <br>• A claimable slot that declared `[OTP_EMAIL, OTP_SMS]` can never be claimed with only an email: 422 for ever, and the only exit is voiding the envelope (BL-205). <br>• A sender who forgot to declare OTP cannot add it. <br>• A correction that would leave a declared method unreachable is refused, with no way to drop the method. |
| **Builds on** | [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md) (the two gates), [TASK-036](TASK-036-claimable-recipient-slot-and-claim.md) (the slot and the claim), [TASK-034](TASK-034-recipient-access-trace.md) (`firstOpenedAt`), and the `PUT …/notification-channels` route of [ADR-0077](../adr/ADR-0077-a-recipient-declares-the-channels-that-reach-them.md) §2.7, which is the template. |
| **Scope** | Before the recipient's first opening only. Editing after a session exists is deliberately out (§4 #1, §6). |
| **Decision record** | **[ADR-0083](../adr/ADR-0083-a-recipients-gates-are-editable-until-they-enter.md)**, drafted as Proposed while planning this task and accepted by the owner on 2026-10-20. It amends: <br>• [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md): the requirement is no longer authoring-only; <br>• [ADR-0054](../adr/ADR-0054-ordered-auth-method-list.md) §2.4: the mode stays frozen, while the lists become editable before entry; <br>• [ADR-0057](../adr/ADR-0057-claimable-recipient-slot.md) §2.13 and §2.14: a slot's declaration is editable before entry, and the claim records the gate it was made under (§2.1's `claimable` flag stays never edited); <br>• [ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md) §2.4: the trail states the change; <br>• [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md) §2.14 and [ADR-0055](../adr/ADR-0055-delegated-signature.md) §2.11: every path that opens a session records the opening first, under the declaration it was decided under. |
| **Sibling** | ⚑ TASK-063 (`TASK-063-the-access-gate-is-always-declared.md`, on branch `feat/explicit-access-gate` until it merges): this route's body follows its declaration rules (the access gate required, `DIRECT_LINK` for open). The domain, event and trail slices run in parallel with it; the HTTP slice starts after TASK-063 is merged to `develop`. |

---

## 1. Why this task exists

On 2026-10-20 the dashboard authored a claimable slot without `auth`, because declaring both OTP methods would
have made the claim fail whenever it brought one contact only. The slot was signed with the link alone. That
failure has two halves. TASK-063 makes the omission an error. This task removes the reason the client had for
trimming: a slot declares the sender's full policy, and before the claim the sender narrows it to the
contact the claim will bring.

The owner's idea (2026-10-20) was a `PUT` that replaces a recipient's gates. Four review agents then went
through the code. Every serious defect they found only exists once the recipient has a signing session:
- a live code;
- a verified signing challenge;
- a credential;
- a race with the act's admission.

Before the first opening, none of these exists, once every path that opens a session records the opening
first (§4 #6: the machine twins do not today). The owner decided to cut the task there (§4 #1).

## 2. What already exists (reuse, do not rebuild)

- **The template**, the notification-channels `PUT`:
  - `ChangeRecipientNotificationChannelsController` → command `ChangeRecipientNotificationChannels` →
    `ChangeRecipientNotificationChannelsHandler` (command bus) → `ChangeRecipientNotificationChannelsUseCase`.
  - The use case finds the envelope locked for update (`findLockedForUpdate`), runs its guards (the contact
    guard is skipped for an unclaimed slot), and runs `guardBeforeExpiry(appNow())` only once sent.
  - `Envelope::changeRecipientNotificationChannels()` refuses a closed or terminal envelope, returns early
    with no event when nothing changes, and records `RecipientNotificationChannelsChanged` with before and
    after. It allows DRAFT.
- **The declaration guards authoring runs**:
  - `DeclaredMethodDestinations::guard()`: every member of both slots must be reachable. It throws
    `RecipientCannotReceiveMethodException` or `PhoneCountryNotSupportedException`.
  - The `AuthMethodAvailability` port (`AUTH_METHOD_UNAVAILABLE`).
  - The structural rules of `AuthRequirementRequest`, as TASK-063 leaves them.
  - For an unclaimed slot the destination check is deferred to the claim
    (`ClaimRecipientUseCase` re-runs it against the contact the claim supplies).
- **The first opening**:
  - `Recipient::firstOpenedAt()` is `null` exactly when the recipient never opened their link, in every state,
    backfilled for old rows.
  - It is written by `Envelope::recordOpening()`, which Session's `StartSessionUseCase` calls synchronously
    **before** `startIfAbsent()` and before any mint.
  - `DbalEnvelopeRepository::recordOpening()` takes the recipient's row lock (bounded).
  - ⛔ The opening request decides under a declaration it read **before** any lock. `StartSessionController`
    reads `RecipientAuthContextReader` (`accessGateIsOpen`) and builds the refresh credential before it
    dispatches. `StartSessionUseCase` then calls `recordOpening()`, which receives only `DIRECT_LINK` or `null`
    as the executed method, and after it `SigningSession::start(accessGateIsOpen: …)`.
  - `Envelope::recordOpening()` applies the leg rule and never compares the declaration. So a `PUT` committed
    between the read and the recipient lock is admitted (`first_opened_at` is still null), and the opening
    then succeeds under the gate the `PUT` replaced. AC-9a and §4 #6 exist for this window.
  - `findLockedForUpdate` locks the root row and every recipient row in id order, so a `PUT` built on the
    template already serialises with `recordOpening()` and with the claim at the row. On the browser path the
    stale read is the only gap.
  - ⛔ **The machine twins open a session without recording the opening.** `IssueAuthChallengeUseCase`
    (`machine_auth_otp_send`) and `SubmitAuthResponseUseCase` (`machine_auth_submit`) call
    `startIfAbsent(SigningSession::start(…, false, …))` for a machine caller, with no `recordOpening()` before it.
    They serve ordinary `SIGNING_PLATFORM` recipients ("the recipient authenticates for real"). There
    `first_opened_at` is written only later, by the relay-borne `OnSigningSessionStarted` →
    `RecordRecipientFirstOpen`. So today an `AUTH_PENDING` session, and an issued code, can exist while
    `firstOpenedAt` is still `null`. §4 #6 closes that window.
  - The machine twins open the session with `accessGateIsOpen: false` whatever the declaration says. They are
    reached with an open access gate too (a signing code asked for by a machine), and `OpenGateResolver` then
    resolves the signing gate from the declaration, not from the session's status.
  - In `IssueAuthChallengeUseCase` the session is opened before the method is resolved and before the limiter
    is charged, so a call that ends in 429 or "no destination" has already opened it.
  - `machine_auth_submit` is `POST /envelopes/{id}/recipients/{recipientId}/auth`, declared in
    `config/routes/api/signing.php`. This task's `PUT` shares that path with another verb, from
    `config/routes/api/envelope.php`. Both verbs on one path are intended.
- **The access code**:
  - `AddRecipientController::generatedCodeFor()` mints a code when either slot declares `ACCESS_CODE` and none
    was supplied, and returns it once in the 201.
  - `ResetRecipientAccessCode` is the existing re-mint.
- **The audit trail**:
  - `TrailAssembler::route()` builds `Claimable(gateWasOpen: …)` from the **current** recipient row
    (`authRequirement->access->isOpen()`), rendered "Acceso al reclamar".
  - A change after the claim would rewrite that statement, so AC-11 moves it to what the claim recorded.
  - The assurance tier is derived from the executed facts (`SigningSessionStarted.accessMethodExecuted`,
    `AuthGatePassed`), not from the declaration.
- **The claim**:
  - `RecipientClaimed` carries `envelope_id`, `recipient_id`, `step_ordinal` and `occurred_at`. It carries no
    gate and no `schema_version`.
  - `Recipient::guardReplayMatches()` compares the claim's identity members only.
- **Event registration** is automatic (`RegisterDomainEventsPass` discovers every concrete event).
- **No platform-wide payload census exists.** [ADR-0061](../adr/ADR-0061-retention-deletion-and-purge.md)
  §2.10(a) says the closed-key-set assertion exists per event, not platform-wide, and lists the census as owed.
  The precedent this task follows is a per-event closed-key-set unit test (`RecipientNotificationChannelsChangedTest`).
- **The trail's data contract**: `TrailJson` publishes `gate_was_open`, `assets/evidence-audit/trail.typ`
  renders it, and `tests/Fixtures/audit-trail/*.json` pin the shape.
- **Concurrency harness**: `tests/F5Sign/Support/ProbesRowLocks.php` (a second connection). `Integration/`
  alone cannot see a lock.

## 3. Scope

**In**

1. Route `PUT /api/v1/envelopes/{id}/recipients/{recipientId}/auth`, authenticated by machine key. The body
   is the `auth` object of add-recipient: the same keys, and the same rules as TASK-063 leaves them. An
   optional `access_code` behaves as on add-recipient. `selection` is accepted only when it equals the stored
   mode.
2. Admitted while:
   - the envelope is not closed or terminal;
   - once sent, it is not expired (DB clock, under the lock);
   - the recipient's leg is open;
   - the recipient's `firstOpenedAt` is `null`;
   - its `signs_via` is not `MACHINE_KEY`.

   DRAFT is admitted.
3. The authoring guards, with the slot deferral.
4. The access code: introducing `ACCESS_CODE` mints (or takes the supplied code) and returns it once. Keeping
   it touches nothing.
5. The event `RecipientAuthRequirementChanged`, its per-event closed-key-set test, and its statement in the
   audit trail (`TrailAssembler`, `TrailJson`, `trail.typ`, the fixtures under `tests/Fixtures/audit-trail/`).
6. The claim records whether the access gate was open when it was made, and the trail's "Acceso al reclamar"
   reads that record, not the current row.
6b. The opening path refuses an opening decided under a declaration that has since changed (§4 #6): Envelope's
   `recordOpening()`, the Envelope command port Session calls it through, and the refusal's handling in
   `StartSessionUseCase`. The two machine twins (`IssueAuthChallengeUseCase`, `SubmitAuthResponseUseCase`)
   record the opening synchronously through the same port before they open a session, and handle the same
   refusals. Their routes' `#[OA\Response]` texts gain the new codes.
7. The race with the first opening (AC-9) and with the claim.
8. ADR-0083 (drafted as Proposed, accepted by the owner 2026-10-20), a frontend handoff for the dashboard, and the `BL-205` / `BL-208` / `BL-176` tense
   sweep.

**Out**

- **Editing after the first opening.** The route answers 409 then; §6 carries what it would take.
- Notifying the sender or the recipient of a change.
- Re-inviting on a change: the link does not change.
- Changing the mode (`selection`).

Concepts re-cut:
- "the declaration is written at authoring and never edited" (ADR-0057 §2.1);
- "the requirement is authoring data";
- `gateWasOpen` (its source moves from the row to the claim's record);
- `RecipientClaimed` (it gains a key);
- "the only exit from a stranded slot is `void()`" (BL-205).

## 4. Key decisions

1. **Before the first opening only** (owner, 2026-10-20). The review found the following in the code, and each
   defect needs a session to exist:
   - Session's verification never compares a live challenge's method with the current declaration: an SMS
     code issued under `[OTP_SMS]` would still pass after a change to `[OTP_EMAIL]`.
   - An `ACCESS_CODE` signing challenge has no expiry, so after a change it would let the old code sign.
   - The act's admission detects a retired credential but not a changed signing gate, so a change between
     verification and admission would leave an act made under the old gate.
   - Strengthening an open gate after entry would not ask the entered party for the new code, because their
     single session row is already `AUTH_PASSED` (BL-230's shape).
   - Opening the gate of a session that is still `AUTH_PENDING` would strand it with a 409 on every commit.
     (The machine twins already open `AUTH_PENDING` sessions under an open access gate, §2, so this item may
     hold only on the browser path. The cut makes it unreachable either way.)

   Gating on `firstOpenedAt === null` makes all of them unreachable, provided every path that opens a session
   records the opening first. That is §4 #6, which brings the machine twins into line. The cases that need a
   later edit go to §6.
2. **"Has not opened" is the admission question, for every role.** An informational role (`VIEWER`,
   `REVIEWER`, `EDITOR`) never acts, so "until the act" would have meant "for ever" for them. The first opening
   is a fact every role has.
3. **No ranking of methods** ([ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §7.3).
   - The event carries both declarations verbatim, and two structural flags: `access_opened` (the access gate
     goes from declared to open) and `signing_dropped` (the signing gate goes from declared to none).
   - A swap such as `OTP_SMS` → `ACCESS_CODE` is not flagged. It is visible in before and after, and the trail
     prints both.
4. **The claim records its own gate.** If the trail kept reading the row, "Acceso al reclamar" would describe
   the declaration after any later change. The claim is the moment the statement is about, so it records the
   fact. The key is added to `RecipientClaimed`'s payload, and an old payload without it decodes as today.
5. **One route for both gates**, replaced whole like the channels `PUT`: the admission rules are the same for
   both, and a sender usually changes both at once.
6. **The opening carries what it decided under, and the recipient lock judges it.** The opening request today
   passes `DIRECT_LINK` (decided "open") or `null` (decided "declared") to `recordOpening()`, which runs under the
   recipient's row lock.
   - The lean: `Envelope::recordOpening()` compares that decision with the current access gate's openness and
     refuses on a mismatch, so nothing is minted and no session row is written. The signer's retry re-reads.
   - Openness is the one fact the opening decides on: everything after the opening re-reads the declaration
     per request (ADR-0049 §2.2).
   - A mismatch in either direction is refused:
     - "open" then declared: the session would be `AUTH_PASSED` under a closed gate;
     - declared then "open": the session would be `AUTH_PENDING` with nothing to pass, stranded.
   - The plan picks the refusal's code and status. The repo's existing busy answer (`ENVELOPE_BUSY`, 503) is
     the first candidate to weigh.
   <!-- OFFREPO: the list below restates the findings of the claims check run on this record on 2026-10-20; every fact is re-stated here against the tree, and nothing depends on reading that check. -->
   - What it takes, from the claims check of 2026-10-20:
     - The decided openness reaches `Envelope::recordOpening()` through `EnvelopeCommandInterface::recordRecipientOpening()`
       (its `?AuthMethod` argument is `DIRECT_LINK` or `null` today). `OpeningFacts` has no member for it.
     - `ActRefusal` gains a member, or the port a result, for "the declaration changed".
     - `StartSessionUseCase::refusedAtTheGate()` maps it: today it maps every refusal other than
       `ENVELOPE_CLOSED` to `legClosed()`.
     - `StartSessionController`'s `#[OA\Response]` 409 text lists a closed set of codes and gains the new one.
       It declares no 503 today, because the opening cannot answer `ENVELOPE_BUSY` (the adapter fails open), so
       the 503 is added.
   - **The comparison is opt-in.** `Envelope::recordOpening()` is also reached by the relay-borne paths
     (`RecordRecipientFirstOpenUseCase`, `RecordRecipientAuthenticationUseCase`), which carry no decided
     openness. A redelivery there must not be refused.
   - ⛔ **It does not fail open.** `EnvelopeCommandAdapter::recordOpening()` turns a recipient-lock timeout into
     "admitted" (it logs a warning, and the gate proceeds without writing `first_opened_at`). On the opening
     path that would let an opening start a session on its stale read while a `PUT` holds the rows, and leave
     `first_opened_at` null for the `PUT` to admit. So an opening that carries a decided openness refuses on a
     lock timeout (503 `ENVELOPE_BUSY`, retried by the signer) instead of proceeding. The relay-borne callers
     keep today's behaviour.
   - **The machine twins record the opening too** (owner, 2026-10-20, over refusing the `PUT` while a session
     row exists, which would make Envelope read Session and close a dependency cycle).
     - Before `startIfAbsent()`, each twin calls the same port with the openness it **read**
       (`$auth->accessGateIsOpen()`, from the `RecipientAuthContextReader` read at the top of the use case).
       It never passes a constant: the twins are reached under an open access gate as well (§2), and a constant
       "declared" would refuse every such call although nothing changed.
     - The same refusals follow: a mismatch, and a lock timeout answering 503 `ENVELOPE_BUSY` rather than
       proceeding. Both are new answers on two published machine routes, so the integrator gets a handoff.
     - The cost, accepted:
       - each machine call takes the recipient row lock, not only the first;
       - the opening and the session insert are two transactions, so a failed insert leaves `first_opened_at`
         set with no session. That closes the window early, never late, as on the browser path;
       - the window closes on the first machine call even when that call then ends in 429 or "no destination".
         The relay already closes it a few seconds later today, so only the timing changes.
     - `RecordRecipientFirstOpen` stays, and becomes a no-op on these paths.

## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | A `PUT` replaces both gates; the envelope read shows the new declaration and the recipient's first opening is presented the new access gate | owner | Acceptance | write only the access gate |
| AC-2 | Each admission refusal answers its code and writes nothing (members AC-2a…f) | owner + derived — ADR-0077 | Application + Acceptance | drop each guard in turn |
| AC-3 | The mode is frozen: `selection` equal to the stored mode is accepted, a different one is 422 | owner | Acceptance | ignore `selection` |
| AC-4 | The declaration guards of authoring run on the new declaration (members AC-4a…e) | owner | Application + Acceptance | skip `DeclaredMethodDestinations::guard()` |
| AC-5 | On an unclaimed slot the destination check is deferred, and the claim re-runs it against the new declaration | owner | Acceptance | run the check on the slot |
| AC-6 | `RecipientAuthRequirementChanged` is recorded once per effective change, with a closed key set (asserted by its own unit test, as `RecipientNotificationChannelsChangedTest` does), no contact and no code, and the API client as the log row's actor | owner + derived — ADR-0061 | Unit (event) + Integration (log row) | add an `email` key |
| AC-7 | `access_opened` and `signing_dropped` are set exactly when a gate goes from declared to neutral; a method swap sets neither | derived — ADR-0049 §7.3 | Unit | flag on any removal |
| AC-8 | A body equal to the stored declaration after normalisation (`["DIRECT_LINK"]` ≡ open; order significant) answers 200, records nothing and mints nothing | derived — ADR-0077 | Application | compare raw bodies |
| AC-9 | A `PUT` and the recipient's first opening never both take effect on the old declaration (members AC-9a…f) | derived — rule 4 | Integration (staged two-step) + `ProbesRowLocks` (second connection) | drop the mismatch refusal; drop the `PUT`'s `firstOpenedAt` check |
| AC-10 | A `PUT` and a claim on one slot serialise: the claim's destination check reads the declaration the `PUT` committed | derived — rule 4 | Integration with `ProbesRowLocks` | read the declaration outside the lock |
| AC-11 | The trail's "Acceso al reclamar" states the access gate as it was at the claim, from the claim's record; a change made later appears as its own statement (instant, actor, before → after). A claim logged before this task carries no record: the trail takes the `before` of the first `RecipientAuthRequirementChanged` after that claim, else the current row (exact, because the declaration could not change before this task) | derived — ADR-0072 §2.4 | Application (`TrailAssembler`) + Acceptance | read `gateWasOpen` from the row |
| AC-12 | Introducing `ACCESS_CODE` on either slot mints a code and returns it once (or stores the supplied one); keeping it neither re-mints nor returns a code. A retried minting `PUT` whose first answer was lost is equal to the stored declaration (AC-8): it answers 200 with no code, and `ResetRecipientAccessCode` is the way to a new one | derived — ADR-0049 §2.8 | Acceptance | mint on every `PUT` |
| AC-13 | Another tenant's key gets 404 and no event is written | derived — ADR-0017 | Acceptance | look up without the tenant |
| AC-14 | Every reachable code is an `#[OA\Response]`, and the route, command and handler are wired (members AC-14a…h) | derived — rule 1 | Acceptance (`OpenApiSpecTest`) | omit a response |
| S-1 | A slot declared `[OTP_EMAIL, OTP_SMS]` → `PUT` `[OTP_EMAIL]` → a claim with an email only answers 204 → the party opens, passes an email code and signs; the trail shows the change and "Acceso al reclamar: con verificación" | owner | Acceptance | — |
| S-2 | A sent recipient (one SIGNER, one APPROVER) declared `DIRECT_LINK` who has not opened → `PUT` `[OTP_EMAIL]` → their first opening asks for the email code, then the act is admitted | owner | Acceptance | — |
| S-3 | A correction to a landline is refused 422 for a recipient declaring `OTP_SMS` → `PUT` `[OTP_EMAIL]` → the same correction passes | derived — ADR-0060 (correction path) | Acceptance | — |
| S-4 | A DRAFT recipient's gates are changed, then the envelope is sent and the recipient is invited under the new declaration | derived — ADR-0077 §2.7 | Acceptance | — |
| AC-15 | Regression: the claim, the correction, the channels `PUT`, resend, unlock and access-code reset behave as before; a claim replay is unaffected by a `PUT` between the two calls | derived — tests/F5Sign/Envelope/Acceptance/RecipientClaimHttpTest.php | existing suites + one replay case | — |
| AC-16 | ADR-0083 is drafted as Proposed with the three `docs/adr/README.md` edits; the amended ADRs carry their notes; a frontend handoff for the dashboard; `rg 'BL-205\|BL-208\|BL-176\|never edited'` is read for tense | derived — rule 7 | review | — |

<!-- OFFREPO: the `wt-backend` lane is a target of the f5sign-infra Makefile; its one relevant fact is restated in the line below. -->
- **Gates:** suite, PHPStan, deptrac and lint, under the `wt-backend` lane: an ephemeral stack (its own PHP
  container, Postgres cluster and broker) that mounts this worktree's tree rather than the main checkout's.
- **Reproduction first** (owner, 2026-10-20). Each defect this task exists for gets a test that is run **red
  against the unchanged `src/`** before its fix is written. Its literal failure goes in the slice report, and the
  record's §7 at close. The test then stays in the suite as the regression guard. Each reproduction reaches the
  defect without the new route where it can, because the route does not exist on the unchanged tree. A
  declaration change is staged by writing the recipient's declaration through the repository.
  - R-1 — the incident (BL-205): a slot declared `[OTP_EMAIL, OTP_SMS]` can never be claimed with an email
    only. The defect is that nothing repairs the declaration, so the red form needs the repair's own path. A
    repair staged through the repository already passes today, because the claim reads the stored declaration.
    So R-1 is S-1's first half written against the `PUT`: `PUT` `[OTP_EMAIL]` answers 200, then the email-only
    claim answers 204. On the unchanged tree it is red on the `PUT` (no such route); it is written and run red
    in the HTTP slice, before the controller.
  - R-2 — the opening's stale read (AC-9a, AC-9b): an opening dispatched with the openness read before a
    declaration change starts a session under the replaced gate.
  - R-3 — the machine twins (AC-9e): after a `machine_auth_otp_send` that opened a session and issued a code,
    with the relay not run, `first_opened_at` is still `null`.
  - R-4 — the trail (AC-11): a declaration changed after a claim changes "Acceso al reclamar".
  - A reproduction that cannot be made red on the unchanged tree is reported as such, with the reason. It is not
    rewritten until it passes.

**Notes on AC-2** — the codes are named in ADR-0083. An existing code is reused where its meaning fits
(`EnvelopeStateException`, `EnvelopeExpiredException`, `RecipientNotFoundException`). The new ones are exactly
two: "the recipient has already entered" and "a delegated recipient has no gates".
- AC-2a — a closed or terminal envelope: 409.
- AC-2b — a sent envelope past its `expires_at`: 409 `ENVELOPE_EXPIRED`, judged by the DB clock under the lock.
- AC-2c — a recipient whose `firstOpenedAt` is set: 409, new code. One case per role standing: blocking,
  informational.
- AC-2d — a recipient whose leg is closed (skipped, released, deadline): 409.
- AC-2e — a `signs_via: MACHINE_KEY` recipient: 409, new code.
- AC-2f — an unknown recipient: 404.
- Owner said: "se rechaza si el destinatario ya hizo su acto" and "nunca se aplica a un destinatario con
  MACHINE_KEY"; the cut at the first opening is the owner's 2026-10-20 decision ("pártela así").

**Notes on AC-14** — AC-14a 200; AC-14b 400; AC-14c 401; AC-14d 404; AC-14e 409; AC-14f 422; AC-14g 500 and
503 (`ENVELOPE_BUSY`); AC-14h the route in `config/routes/api/envelope.php` with `_authn` `MACHINE_KEY`, its
command on the command bus, and its handler. Also, from §4 #6: the start route's 409 gains the new code and its
503 is added; the two machine twins' `#[OA\Response]` texts gain the mismatch refusal and the 503.

**Notes on AC-4**
- AC-4a — an unavailable method: 422 `AUTH_METHOD_UNAVAILABLE`.
- AC-4b — an unreachable member, the head or a later one: 422 `RECIPIENT_CANNOT_RECEIVE_METHOD`.
- AC-4c — an `OTP_SMS` phone in an unsupported country: 422 `PHONE_COUNTRY_NOT_SUPPORTED`.
- AC-4d — a TASK-063 structural refusal (no access declaration, `DIRECT_LINK` on signing, `DIRECT_LINK` in a
  list of two): 422.
- AC-4e — `access_code` sent while neither slot declares `ACCESS_CODE`: 422.

**Notes on AC-9**
- AC-9a — stale "open": the opening read an open gate, then a `PUT` declares `[OTP_EMAIL]` and commits, then
  the opening reaches `recordOpening()`. The opening is refused: no `first_opened_at`, no session row, no
  credential. The retry is asked for the email code. Built as a staged two-step test that dispatches
  `StartSession` with the stale `accessGateIsOpen` after the `PUT`; `ProbesRowLocks` alone cannot produce the
  interleaving.
- AC-9b — stale "declared": the mirror case. The opening read a declared gate, then a `PUT` opens it. The
  opening is refused and the retry enters with the link.
- AC-9c — the opening is recorded first: the `PUT` answers 409 (AC-2c), checked under a held recipient lock
  with `ProbesRowLocks`.
- AC-9d — a recipient lock held past its bound (by a `PUT`, via `ProbesRowLocks`) makes the opening refuse with
  503 rather than start a session. The relay-borne `recordOpening()` callers keep failing open, and a redelivery
  is not refused for a changed declaration.
- AC-9e — the machine twins: a `machine_auth_otp_send` call stamps `first_opened_at` before it opens the session,
  so a later `PUT` answers 409 (AC-2c) with the relay not run. A staged call carrying a stale read after a `PUT`
  is refused, with no session row and no code issued. The same holds for `machine_auth_submit`.
- AC-9f — a machine twin under an **open** access gate whose declaration did not change is admitted (it carries
  the openness it read, not a constant). Sabotage: pass a constant "declared".
- The sabotage must check WHICH guard fired (the repo's authoring rule 4).

## 6. Open follow-ups (track, don't solve here)

- **Editing a recipient's gates after their first opening.** It is needed for "the SMS never arrives" once the
  signer is at the gate. Until then, a list such as `[OTP_SMS, OTP_EMAIL]` lets the signer move to email
  themselves. The review of 2026-10-20 found what it would take:
  - verification and `ensureLiveChallenge` refuse and retire a live challenge whose method the current
    declaration no longer names, decided in the same request rather than by an asynchronous subscriber;
  - an `ACCESS_CODE` signing challenge, which has no expiry, is retired too;
  - the act's admission compares a declaration revision read under the envelope lock (commit and decline),
    refusing with its own 409;
  - strengthening an open gate moves an `AUTH_PASSED` session back to pending, or the edit is refused (this is
    BL-230's shape);
  - opening the gate of an `AUTH_PENDING` session is refused;
  - any access change retires credentials (ADR-0060 §2.5);
  - the send budgets and the issuance interval are never cleared (invalidation is consumption, never deletion);
  - a signer handoff for the new refusal and for credential retirement.

  The `docs/BACKLOG.md` row is written at task close.
- **Notify the sender (and the recipient) of a change**, above all when `access_opened` is set. Today the only
  mitigation is the trail statement. A compromised machine key can already redirect a code by correcting the
  contact, so this adds visibility rather than closing a new door.
- **BL-208** (an `ACCESS_CODE` slot needs a second call after the claim): **narrowed, not closed** (decided at
  close, 2026-10-21). A slot authored without the method can be given its code before the claim through the new
  route; a slot that declared `ACCESS_CODE` at authoring still needs *claim, then reset*, because the route
  refuses a supplied code for a declaration that already names the method (`ACCESS_CODE_ALREADY_DECLARED`). The
  row stays Open.
- **Indexed at close:** BL-437 (editing after the first opening, the first bullet above), BL-441 (notify the
  sender and the recipient of a change, the second bullet).

## 7. Deviations & honest notes

### Scope
- Files the record did not name, all following from items 5, 6 and 7: `config/services.yaml`,
  `EvidenceAudit/Domain/Trail/Party.php` and `Route/Claimable.php`, and test infrastructure.
- `DeclaredMethodAvailability` was extracted from add-recipient and shared with the new use case; add-recipient's
  behaviour is unchanged.
- The nelmio `ProblemCode` enum gained the five new codes (orchestrator ruling in slice 04).
- Two audit-trail golden fixtures (`factor5-voided.json`, `factor5-closed-now.json`) move `gate_was_open` from
  `true` to `null` on their unclaimed slot, as ADR-0083 §2.9 requires. The slice's "no golden moves" held only for
  claimed slots.

### Decisions made during implementation
- `RecipientClaimed::toPayload()` omits `access_gate_was_open` when it is null, so a claim logged before ADR-0083
  re-encodes byte-identically (ADR-0031 golden bytes) and no existing commitment moves. Production commitments
  come from stored bytes, never from a re-encode.
- Decoding the new event through `requiring()` stays strict. A future tightening owes an upcaster (ADR-0031), not
  a lenient decoder.
- A lock timeout on the opening's shut-read branch answers 503 `ENVELOPE_BUSY`, not `LEG_CLOSED` (ADR-0083 §2.7 is
  keyed on the decided openness; the old `LEG_CLOSED` was a guess).
- The gate-change refusals follow ADR-0083 §2.1 order (closed or expired before 404) over the slice's reference
  order.
- `AUTH_REQUIREMENT_CHANGED` carries two meanings across routes, both published: on the three opening routes, an
  opening decided under a stale openness; on the `PUT`, the access-code premise moved. Each 409 text gives its own
  remedy.
- A first machine authentication call (`auth/otp/send` or `POST auth`) also fixes the gates, because both twins
  record the opening before the limiter and before any attempt. The `PUT`'s description and its
  `RECIPIENT_ALREADY_ENTERED` text say so.
- The `PUT`'s 200 carries a generated `access_code` without `Cache-Control: no-store`, like its two siblings; one
  change for all three is BL-439 (authoring rule 3).

### Decisions that needed an ADR
- ADR-0083, drafted as Proposed while planning and accepted by the owner on 2026-10-20 (`2d5ead35`) before slice 10.
  It is already Accepted: this close does not propose the status move. Two dated notes were added to its
  consequences (BL-208 narrowed; the delegated commit as a classified exception to the opening-first cut); the
  accepted text was not rewritten.

### Declared and unproven properties
- None unproven by the harness for the row-lock and opening-race properties: AC-9 and AC-10 run on a second
  connection (`AuthRequirementChangeRowLockTest`, `OpeningUnderAChangedDeclarationTest`,
  `EnvelopeRootLockRaceTest` with its second process, `EnvelopeRaceActs`).
- Held by review alone, as ADR-0083 §3.3 states: that a future route opening a session records the opening first.
  `CommitDelegatedSignatureUseCase` is the classified exception (it opens a session without recording one, and is
  safe because the gate change refuses `signs_via: MACHINE_KEY` with `RECIPIENT_HAS_NO_GATES` first).
- The golden fixture exercises only email and SMS on the access gate with the signing gate empty, so a future
  tightening of `requiring()` for `ACCESS_CODE` or the signing gate passes the golden-bytes alarm.
- `methodList()` decodes a malformed list to `[]` (the permissive direction, opposite of `MapsAuthRequirement`);
  unreachable from canonical bytes.
- `factor5-completed.json` pairs a post-ADR-0083 change with a claim in the pre-ADR shape, so no golden carries a
  claim together with its record. `insertedBefore()` in the trail test support walks back to the nearest gap; a
  second caller should assert that every skipped row belongs to another party.
- An undecodable change row is skipped silently by the trail reader, which then falls through to the row.
- **Infection** (filtered to the branch's 41 `src/` files, which it mutates whole; bars 85 covered-MSI / 70 MSI),
  `wt-backend-infection` on this worktree's lane, tip `0729dd0f`: 2169 killed, 500 escaped, 414 not covered —
  covered-MSI **81 %**, MSI **70 %**. The whole-file numbers include the untouched parts of large touched files
  (`Envelope.php`, `Recipient.php`, the twins), the pre-existing debt of BL-409. Judged on the changed lines (1485 lines
  since `edd04506`): 71 escaped, 0 not covered, 108 skipped (Integration-only, over the per-mutant timeout). **Killed
  by tests in `17e8951c`**, each checked red by hand where it guards behaviour: the exact message and problem code of
  every factory of `RecipientAuthNotChangeableException` and `AuthRequirementChangeRefusedException` (their message is
  the `detail` a client reads), and the `ENVELOPE_CLOSED` and `LEG_CLOSED` arms of both twins'
  `refusedAtTheOpening()` (the `AUTH_REQUIREMENT_CHANGED` arm was already pinned). The 15 `Concat` mutants on the
  `selection` `#[OA\Property]` description are published prose under `// @infection-ignore-all`, as its siblings;
  `OpenApiSpecTest` pins its substrings. **Justified:** `ChangeRecipientAuthRequirementUseCase`'s `Break_` is
  equivalent (recipient ids are unique, so the loop ends on the same match); `TrailAssembler::gateAtClaim()`'s
  `GreaterThan` → `GreaterThanOrEqual` is equivalent (two log rows never share a position, and the claim's own row is
  not a `RecipientAuthRequirementChanged`); `Envelope::guardRecipientAuthChangeable()`'s `PublicVisibility` is killed
  by `ChangeRecipientAuthRequirementUseCaseTest` (made `protected` by hand, every case errors) but Infection's test
  selection does not pair that signature line with the use case test. Re-run on the six files `17e8951c` touched: on
  the changed lines only that last mutant is reported.

### Debt left behind, and where it lives now
- Editing after the first opening → §6 and BL-437.
- Notifying the sender and the recipient of a change → §6 and BL-441.
- An access-code reset can mint a hash for a recipient without an `ACCESS_CODE` gate (pre-existing) → BL-438.
- `no-store` on every response carrying a plaintext access code → BL-439.
- `composer audit`: `symfony/http-foundation` CVE-2026-108082 and `symfony/yaml` CVE-2026-109413, pre-existing, lock
  untouched, updating needs the owner's request → BL-440.
- BL-205 resolved by this task; BL-208 narrowed (§6); BL-176 repointed (the claim re-runs the guard on the
  declaration stored when it runs, and the authoring deferral is keyed on `Recipient::isUnclaimedSlot()`).
- Doctrine-guard did not run: no migration in the diff.

### Delegated work
- Slices 01 to 07 ran on the top model with a review each; slices 08 to 10 were gated on TASK-063 and ran after
  the merge of `develop` (`18f99ae8`). No slice report records a `replicator` brief: every slice's `## Delegated`
  says none, each citing a deterministic `sed` or `perl` substitution as cheaper than briefing one.

  | Slice | Tier | Model | Review rounds | Status |
  |-------|------|-------|---------------|--------|
  | 01 event | critical | opus | 1 | approved |
  | 02 opening under its decided declaration | critical | opus | 2 | approved |
  | 03 claim records its gate | critical | opus | 1 | approved |
  | 06 machine twins | critical | opus | 1 | approved |
  | 07 trail | critical | opus | 1 | approved |
  | 04 envelope replaces gates | critical | opus | 2 | approved |
  | 05 command on the bus | critical | opus | 2 | approved |
  | 08 PUT route | critical | opus | 3 | approved |
  | 09 refusals and stories | standard | not logged | 1 | approved |
  | 10 docs, ADR landing, handoff, sweep | critical | opus | 1 | approved, findings fixed by the orchestrator |

### Cost of the run
- Tokens logged for slices 01 to 07: 216k, 615k, 168k, 187k, 189k, 404k and 533k, all opus (about 2.3M). The
  run log carries no token figure for slices 08 to 10.
- Review rounds: 15 across 10 slices; one closing review (opus) returned `changes` with three findings, fixed in
  `0804742e` and `8e9024e5`.
- Escalations: two orchestrator rulings on slice 03 and one on slice 04; orchestrator-made fixes in slice 08
  (`fdf0e511`, `dde20a99`) and slice 10 (`0729dd0f`) in place of another implementer round.
