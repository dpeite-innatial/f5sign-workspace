# TASK-052 — The signing gate is answered on the act, and a decline passes it

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `fix/signing-gate-on-the-act`** (`c18819bc`), 2026-10-06 — not pushed, not merged. Full suite green at `009cbcfa` (5988 tests, 70910 assertions, lint, Deptrac, PHPStan level 9) under the `wt-backend` lane of this worktree, never the main checkout; covered-MSI 84 % measured at `0f1aa3d6`. Pending review. Left out: the concurrent two-call test of `BL-215` (the lock probe stands beside it), the delegated decline (`BL-282`), and the machine-surface trust decision and the neutral-gate gap recorded in §6. ADR-0075 is `Accepted` (2026-10-06, maintainer's OK). |
| **Type** | **Corrective, with a contract change.** No new capability: the decline stops being admitted without the second factor the sender declared, and the signing gate's proof stops waiting between its verification and its act, for both acts. |
| **Why** | Under `(access: OPEN, signing: <any method>)` anyone holding a forwarded link can open the session, receive a session credential and decline; for a blocking recipient that voids the envelope for every party. Underneath, a verified signing proof waits for its act and belongs to the session, so whoever reaches the session can spend it ([BL-159](../BACKLOG.md)). ADR-0075 §1 measures both. |
| **Builds on** | Reused unchanged: [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md)'s challenge, attempt budget, two-tier lockout, sender-side unlock and refusal kinds · `OpenGateResolver` · the decline of [TASK-046](TASK-046-a-recipient-may-decline.md) and its admission (`AdmitRecipientAct::decline()`) · `OneTimeCodeDeliveryService` and the two copy catalogs · `SignerAuthPolicy` · the trail's assembler and template ([ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md)) · the unit of work (`UnitOfWork::own()`, `OwnsUnitOfWork`) and its one precedent for a refusal that persists, route 5's `SubmitAuthResponseUseCase::submit()`. |
| **Scope** | Session, Notification and Evidence & Audit. The code on the commit, the decline and the machine signature route, verified and consumed in the act's unit of work; route 5 and its machine twin reduced to the access gate; the act on the signing challenge (domain, column, per-act index, issuance); the act on route 4 and its twin; the act on four facts; one notification purpose with its email and SMS copy in `en` and `es`; the trail naming the act; the removal of the waiting-proof state; the `#[OA\*]` blocks of every route touched; the tests of §5; two frontend handoffs (signer and integrator). **Not ours:** the delegated decline ([BL-282](../BACKLOG.md)); the access gate's opening write, which still holds a savepoint of its own (`DbalEnvelopeRepository::recordOpening()`) until a later persistence change moves it into its caller's boundary. |
| **Decision record** | **[ADR-0075](../adr/ADR-0075-the-signing-gate-is-answered-on-the-act.md)**, `Proposed` 2026-10-01, re-cut 2026-10-05, from the maintainer's decisions of both days: the code travels on the act, for both acts, in this one task; one live code per act; every declining role follows the gate; the decline shares the lockout; the message and the trail name the act; release in one window with the signer; `/v1` kept. It amends ADR-0049 §2.3, §2.4 and §2.5 and ADR-0070 §2.4. The maintainer agreed to it as written on 2026-10-06, and it was accepted the same day once this task's bars went green. |
| **Delivery bar** | Over HTTP, a blocking `SIGNER` behind `(access: OPEN, signing: OTP_EMAIL)`: `POST /signing/decline` with no code is refused 401 `AUTH_CODE_REQUIRED` and the envelope stays live. The recipient asks route 4 for a code with `act: DECLINE`; the email's copy says the code is to decline; the decline carrying it succeeds and the envelope is voided with cause `RECIPIENT_DECLINED`. A second session credential for the same link, while a `SIGN` code is live and verified by nobody, is refused on the decline with no code and with a guessed one, and each guess is charged. A commit carrying a `SIGN` code succeeds for another recipient on the same gate, with no call to route 5, which refuses a signing-gate submission with `SIGNING_GATE_ANSWERED_ON_THE_ACT`. The declining recipient's audit trail names the act on their verification and on the code sent, and nowhere prints the signature label for them. A recipient with no signing gate signs and declines as before. |
| **Sibling** | None in flight in this repository. The persistence work this task waited on landed on `develop` on 2026-10-05 as `refactor/persistence-incremental`: the unit of work, and changes to `SubmitAuthResponseUseCase`, `IssueAuthChallengeUseCase`, `SigningSession` and `DbalSigningSessionRepository`. Read the files it touched from the tree rather than from this record. The signer's and the integrators' flows change outside this repository, through the handoffs of §3.9, and deploy in the same window as this task (ADR-0075 §2.8). |

---

## 1. Why this task exists (measured on `6a5984f8`, re-checked 2026-10-05)

`config/routes/api/signing.php` puts `decline` on `Authn::SESSION_CREDENTIAL`, so the access gate is
asked. `DeclineSignatureUseCase` then asks the session's own guards, the step and the admission, and no
signing challenge: its docblock lists *"no signing challenge"* among what is deliberately not asked, and
`SigningSession::guardDecline()` takes no document set. `CommitSignatureUseCase` passes
`$auth->hasSigningGate() ? $auth->signableDocumentSet : null` to `guardCommit()` and `commitSignature()`,
which look at and then consume the challenge. `CommitDelegatedSignatureUseCase`, which serves ADR-0055
§2.11's machine-driven commit as well as the delegated one, does the same for a recipient who is not
asserting.

Behind a neutral access gate the session credential is minted on every open
(`StartSessionUseCase`, the `accessGateIsOpen` branch), so it proves only possession of the link.

The proof those acts consume is verified earlier, on route 5, and waits
(`AuthChallenge::isVerifiedAndUnspent()`) until its expiry: 300 s for `OTP_SMS`, 900 s for `OTP_EMAIL`,
none for `ACCESS_CODE` (`SignerAuthPolicy`). Only a pass of a declared access gate retires it early
(`invalidateRetainedSigningProof()`). ADR-0075 §1.2 shows why binding that waiting proof to an act, this
task's first cut, made `ACCESS_CODE` worse, and §1.3 why the two steps were never chosen on their merits.

The trail labels the signing gate `"Firma"` in its verifications and its codes-sent list
(`assets/evidence-audit/trail.typ`, the `gate` label map).

## 2. What already exists (reuse, do not rebuild)

- **The challenge.** `session.auth_challenge` (`Version20260818000007`): `gate`, `method`,
  `verifier_hash`, `bound_document_set`, `issued_at`, `expires_at`, `verified_at`, `consumed_at`, and
  `auth_challenge_one_live_per_gate_uniq ON (session_id, gate) WHERE consumed_at IS NULL`. Mapped in
  `DbalSigningSessionRepository`. `AuthChallenge::authorises(string $documentSet)` is the set check.
- **Consumption.** `spendableSigningChallengeFor()` refuses `AUTH_NO_OPEN_CHALLENGE`,
  `AUTH_CHALLENGE_EXPIRED` and `SIGNING_CHALLENGE_MISBOUND` (409); `consumeSigningChallengeFor()` spends
  and records `AuthGatePassed`.
- **Verification.** `SigningSession::submitAuthResponse()` checks the lockout, finds the live challenge,
  compares the code (`AccessCodeHasher`), charges a wrong one (`spendBudget()`), and records
  `AuthVerificationPassed`. For a method that delivers nothing (`ACCESS_CODE`) the repository lazily calls
  `ensureLiveChallenge()` before it. Route 5's body is `SubmitAuthResponseRequest` (`code`, `recover`).
  Its machine twin is `SubmitRecipientAuthResponseController`, which mints the integrator a session
  credential when the access gate passes.
- **Issuance.** `IssueAuthChallengeUseCase::issue()` resolves the gate through `OpenGateResolver`, calls
  `ensureLiveChallenge()` (`resend: false`) or `mintChallenge()` (`resend: true`), binds
  `$auth->signableDocumentSet` for `SIGNING`, and requests delivery with a `OneTimeCodeRequest` carrying
  `gate`. Route 4's body is `SendAuthOtpRequest` (`resend`, `recover`, `method`); its twin is
  `SendRecipientAuthOtpController`. `guardIssuanceInterval()` and `lastIssuanceFor()` work per gate.
- **The acts.** `CommitSignatureRequest` (`consent`, `reservations`, `filled_fields`),
  `DeclineSignatureRequest` (`reason`), and the machine signature route's `CommitDelegatedSignatureRequest`.
- **The lockout.** The budget and both tiers are session state (`spendBudget()`, `isHardLocked()`,
  `guardNotLockedOut()`); the sender lifts the hard tier (ADR-0049 §2.8).
- **Delivery.** `OneTimeCodeDeliveryService::purposeFor()` maps `ACCESS` → `AUTH_OTP_ACCESS` and `SIGNING`
  → `AUTH_OTP_SIGNING`, with no default arm. `NotificationPurpose` classifies each case in
  `namesItsOwnChannel()`, `carriesMeansToAct()` and `isInvitation()`; `DefaultChannelSelector` throws for
  the code purposes; `EmailLayoutView` gives each purpose a tone and icon. Copy:
  `EmailNotificationChannel` and `SmsNotificationChannel`, `en` and `es`. Tests: `AuthOtpEmailCopyTest`,
  `SmsCopyTest`. `notification.purpose` is `TEXT` with no check constraint (`Version20260824000002`), so a
  new purpose needs no migration.
- **Facts.** `AuthChallengeIssued`, `OtpSent`, `AuthVerificationPassed` and `AuthGatePassed`, each with
  `gate` and `method`.
- **The trail.** `TrailAssembler` builds a `GatePass` (`gate`, `method`, `at`) per `AuthGatePassed` and a
  `ContactUse` per `OtpSent`; `trail.typ` labels them through its `gate` map.
- **The signer already asks for the signing code at the act**: a modal over `/sign` opened by the commit's
  `AUTH_NO_OPEN_CHALLENGE`, which retries the commit on closing (`useSignFlow.ts` in `f5sign-signer`).
  The moment the recipient types the code does not move.
- **Tests to extend.** `SigningSessionAuthGateTest`, `SigningSessionDeclineTest`,
  `SigningSessionCommitRefusalTest`, `CommitSignatureUseCaseTest`, `DeclineSignatureUseCaseTest`,
  `CommitDelegatedSignatureUseCaseTest`, `GatedSigningCeremonyHttpTest`, `DelegatedSignatureHttpTest`,
  `CommitRefusalsNameTheirConditionHttpTest`, the decline's HTTP tests, `AuthChildTableHydrationTest`,
  `SchemaConformanceTest` (it already applies to the new column), and the trail's own tests.

## 3. What gets built

### 3.1 The act on the challenge

A closed enum for the act, `SIGN` and `DECLINE`, in Session. `AuthChallenge` carries it (`null` for
`ACCESS`, required for `SIGNING`).

One migration on `session.auth_challenge`, generated through the console, never named by hand:

- adds `bound_act`, `TEXT`, nullable, **with no default** (`SchemaConformanceTest` refuses a database
  default on a domain column and a `VARCHAR`);
- backfills `SIGN` with an `UPDATE` on every `SIGNING` row. Each was issued for a commit, the only act
  that consumed one before this task, and that holds in every state the row can be in (open, verified and
  waiting, consumed, invalidated), so the backfill writes the truth for all of them (the repo's
  authoring rule 6);
- adds a check constraint: `bound_act IS NULL` when `gate = 'ACCESS'`, not null when `gate = 'SIGNING'`;
- replaces `auth_challenge_one_live_per_gate_uniq` with
  `UNIQUE NULLS NOT DISTINCT (session_id, gate, bound_act) WHERE consumed_at IS NULL` (PostgreSQL 15+;
  the stack runs 18). State in its docblock why `NULLS NOT DISTINCT` is load-bearing: `ACCESS` rows carry
  no act, and with the default `NULLS DISTINCT` two live `ACCESS` rows for one session would both pass;
- `down()` restores the old index, then drops the constraint and the column. ⚠ `down()` fails if a
  session holds a live `SIGN` and a live `DECLINE` row together; say so in the docblock rather than
  deleting rows to make it pass.

**No open row is invalidated.** A `SIGNING` row left verified and unspent by the old flow is still live,
and the act after the deploy asks for the code again and checks it against that row, so the old
verification grants nothing and the in-flight recipient keeps the code they were sent. State this in the
migration's docblock: it is the reason a reader expects an invalidation and finds none.

### 3.2 Issuance per act

Route 4 and its machine twin accept an optional `act` (`SIGN` | `DECLINE`, absent means `SIGN`), carried
to `ensureLiveChallenge()` and `mintChallenge()`, which find, retire and open per `(gate, act)`.
`liveChallengeFor()`, `guardIssuanceInterval()`, `lastIssuanceFor()`, `retireTimedOutChallenge()`,
`expiredChallengeFor()` and `IssueAuthChallengeUseCase::liveMethodFor()` take the act too (the last, so the
other act's open code cannot decide whether a channel change mints or the limiter is charged). A code for the other act is minted beside the open one, never
over it. A change of channel (ADR-0054 §2.6) retires only the named act's code.

At the access gate, `act` is ignored and the answer carries `act: null` (ADR-0075 §2.3). Route 4's
answer names the act it issued for.

### 3.3 The act verifies and consumes, in its own unit of work

`SigningSession` gains one step that the commit, the decline and the machine commit share, run under the
session row's lock: find the live challenge for `(SIGNING, act)` (or, for a method that delivers nothing,
open one), check the lockout, compare the code, charge a wrong one, mark it verified, and, after the
admission, consume it and record `AuthVerificationPassed` and `AuthGatePassed` with the act. Whether it is
`submitAuthResponse()` generalized or a sibling is the implementer's call; read
`SigningSession::submitAuthResponse()` and the three act methods in full before choosing (the repo's
authoring rule 3).

The order is fixed by ADR-0075 §2.4: every guard asked before the gate today → lockout → code →
admission → act. Concretely:

- **Before the code, unchanged in place**: in the commit, the retired credential and the inactive step
  (`CommitSignatureUseCase`, before `guardCommit()`), then `guardCommit()`'s closures, live grant and
  **consent**; in the decline, `guardDecline()`'s closures, live grant and **role**; the same in the
  machine commit. Only the gate's part moves: the code check takes the place of
  `spendableSigningChallengeFor()` at the end of each guard. A missing consent therefore costs no attempt.
- **The lockout prelude route 5 runs today**, in its order: `guardTheGateIsStillTheirs()`,
  `clearSupersededLockout($recipientAuthGeneration)`, then `guardNotLockedOut()`. ⛔ Without the clearing,
  a recipient whose lock the sender lifted (ADR-0049 §2.8) stays locked out of the acts while route 5
  would admit them.
- **The inputs route 5 receives and the acts do not yet**: the recipient's auth generation and, for
  `ACCESS_CODE`, the recipient's verifier hash (both from `RecipientAuthContext`), the `AccessCodeHasher`,
  and the source IP and user agent the attempt row records.

**The unit of work.** `CommitSignature`, `DeclineSignature` and the machine commit's command implement
`OwnsUnitOfWork`, and each use case draws one unit with `UnitOfWork::own()`:

- a **wrong code** is caught inside the unit and returned in the `Ok`, so the charged attempt commits; the
  use case throws it after `own()` returns;
- **any other refusal throws inside the unit** and rolls everything back, the verification included, so
  the code stays live and uncharged;
- **never `run()`**, never an `Err` to keep a refusal (ADR-0075 §2.4).

⚑ **The act takes over route 5's shape, and differs from it in one respect, deliberately.** Route 5
(`SubmitAuthResponseUseCase::submit()`) commits every refusal it catches inside its unit, the no-live-challenge
and expired refusals included, and `SigningSession::submitAuthResponse()` records an attempt row (with no
challenge) before throwing those two — the probe shape `Version20260818000007` calls worth seeing. The act
keeps ADR-0075 §2.4's rule instead: only a wrong code (and the lock its charge may arm) persists; a missing
code, no live challenge for the act, an expired one and a misbound one roll back and leave no attempt row.
On the access gate the probe row still lands; on the signing gate a probe leaves none.

Lock order: the session row, then the recipient row (the admission's). ⛔ **Both are taken inside
`own()`.** Today each act calls `findLockedForUpdate()` first, under the transaction the bus middleware
opened; with `OwnsUnitOfWork` the middleware opens none, so a lock taken before `own()` ends with its own
`SELECT` and covers nothing (the port's *Concurrency* note; `SubmitAuthResponseUseCase::mintCredential()`'s
docblock records this exact defect on route 5). The load, the guards, the code, the admission and the save
all go inside the one call. The admission is a direct port call, not a dispatch, so it raises no
`NestedDispatchException` there; keep it that way.

**A code on an act whose recipient declares no signing gate is ignored** and records nothing (ADR-0075
§2.1).

### 3.4 Route 5 serves the access gate only

`SubmitAuthResponseUseCase` and its twin refuse a submission resolved to `SIGNING` with
`409 SIGNING_GATE_ANSWERED_ON_THE_ACT`, a new refusal whose remedy names the act routes, before any
challenge is opened or any attempt recorded. Then delete what only that path used:
`invalidateRetainedSigningProof()` and its call, and the waiting-proof branch of
`spendableSigningChallengeFor()`. ⛔ **The `ACCESS_CODE` lazy `ensure` for `SIGNING` is moved, not
deleted**: it leaves the repository's route-5 path and becomes the act's way of opening its challenge
(§3.3). Deleting it leaves `ACCESS_CODE` recipients unable to sign or decline.
Check [`docs/LOAD-BEARING.md`](../LOAD-BEARING.md) before each deletion (repo-specific rule 8), and
re-target the tests that pinned them (`SigningSessionAuthGateTest`'s P-§AUTH.10, among others) to the
property that replaces them rather than deleting them silently.

### 3.5 The message

`OneTimeCodeRequest` gains `act`, required when `gate` is `SIGNING` and refused otherwise, as `gate` itself
is refused when absent. Check first whether the request crosses an asynchronous transport anywhere between
Session and the channel; if it does, a message serialized before the deploy carries no `act` and must
decode as `SIGN`. `purposeFor()` chooses from gate and act with no default arm.

A new `NotificationPurpose` case for the decline code, classified as its siblings are:
`namesItsOwnChannel()` true, `carriesMeansToAct()` true (ADR-0065), `isInvitation()` false, the throwing
arm of `DefaultChannelSelector`, and a tone and icon in `EmailLayoutView`. Then every other
classification the enum's own docblock lists for a new case.

Copy in `en` and `es`, email and SMS, written to the conventions in the catalog's comment: the code in the
body only, no destination, the expiry stated, the verb *decline* / *rechazar*. Measure the `es` SMS body
against UCS-2's 70 before committing it.

### 3.6 The facts

`AuthChallengeIssued`, `OtpSent`, `AuthVerificationPassed` and `AuthGatePassed` gain `act`, `null` on the
access gate. Additive: no `EVENT_TYPE` changes, and each decoder reads an absent member as `SIGN` on the
signing gate and `null` on the access gate. `OnAuthGatePassed`, the one consumer outside Session and
Evidence & Audit, needs no change: it ignores the signing gate.

### 3.7 The trail names the act

`GatePass` and `ContactUse` carry the act, read from the facts of §3.6 (absent on an old fact reads as
`SIGN`). `trail.typ` labels a signing-gate entry by its act, so a decline's verification and code sent
read as a decline's, in every locale the template carries. Nothing else in the trail changes.

### 3.8 Every surface that states the old rule

Sweep, last thing before each commit (the repo's authoring rule 1), for the retired two-step shape as well
as the decline's old rule:
`rg -n 'no signing challenge|behind both gates|identity gate|authorizes nothing|verified and unspent|isVerifiedAndUnspent|retained signing proof|invalidateRetainedSigningProof|one per gate|one_live_per_gate|resend: true|signing/session/auth|serves both gates|SIGNING gate is asked' src tests docs config migrations assets`.
Known on 2026-10-05:

- `DeclineSignatureUseCase`'s class docblock, and `SigningSession::decline()`'s (*"What is NOT asked …
  the signing gate's challenge"*);
- the `#[OA\*]` strings of the commit, the decline, the machine signature route, routes 3, 4 and 5 and
  the two twins: request bodies, the 401/409/423/429 descriptions, and every remedy that says *"go to
  POST /signing/session/auth"* (`CommitSignatureController` names it for the signing gate) or *"send …
  otp/send with `resend: true`"*;
- the published refusal lists in `config/packages/nelmio_api_doc.yaml`;
- the route comments in `config/routes/api/signing.php`, including the version note, which gains the
  2026-10-05 decision (ADR-0075 §2.8);
- `SigningSessionStateException`'s docblock on the misbound refusal (it reasons from
  `isVerifiedAndUnspent()`);
- `NotificationPurpose`'s docblocks (*"one per gate of ADR-0049 §2.1"*), `ChannelSelector`'s and
  `UnresolvableAuthGateException`'s;
- `docs/LIVE_SCHEMA.md`'s `session.auth_challenge` section (the index, the new column) and
  `docs/ddd/signing-session-domain-model.md`;
- the guidance line that says there is one delivered-code purpose per gate.

### 3.9 Frontend handoffs

Two, under `docs/frontend-handoff/`, before the merge, both stating that this backend and the client
deploy in one window (ADR-0075 §2.8) and that neither works with the other's previous version behind a
signing gate.

**Signer.**

- **Commit.** The modal over `/sign` stays where it is, and stops calling route 5: it asks route 4 for a
  code with `act: SIGN` (or relies on the code already sent), and the commit carries `code`. Open the
  modal on `AUTH_CODE_REQUIRED`, `AUTH_NO_OPEN_CHALLENGE` and `AUTH_CHALLENGE_EXPIRED`;
  `AUTH_CODE_INCORRECT` keeps the modal open.
- **Decline.** The same modal on the decline, with `act: DECLINE`, asked when the recipient confirms the
  decline, not when the dialog opens. The reason is kept in memory across the modal.
- **Route 5** is called for the access gate only; `SIGNING_GATE_ANSWERED_ON_THE_ACT` from it means the
  client is running the old flow.
- **`ACCESS_CODE`**: there is nothing to send, and route 4 answers `409 AUTH_METHOD_NOT_DELIVERED` for
  it, as today. The modal asks for the code the signer already holds and sends it on the act directly,
  without calling route 4. Read the method from route 3's descriptor.
- The lockout's two answers now reach the decline too.
- A code for one act does not serve the other; changing one's mind costs a new message for the other act
  and no wait.

**Integrator** (ADR-0055 §2.11). The twin of route 4 takes `act`; the twin of route 5 no longer accepts
the signing gate; the machine signature route and `/signing/decline` carry the relayed `code`; for
`ACCESS_CODE` the code is relayed on the act with no call to the twin of route 4; the same refusals as
above. ⚑ Two things the machine surface needed for this to hold, found while building it: the machine
signature route's body accepted only the delegated shape (its three assertion members were required), so a
relayed act without an assertion was refused 422 before the use case saw it — the members are now optional
there and the use case requires them of a delegated recipient; and the twin of route 5 now opens the
recipient's session when none exists, after the same guards the twin of route 4 asks, so an `ACCESS_CODE`
access gate needs no call to the twin of route 4 either.

## 4. Key decisions

Decided in ADR-0075 and not reopened here: the code on the act, for both acts (§2.1); every declining role
follows the gate (§2.2); one live code per act, the minimum interval per act, `act` ignored at the access gate (§2.3); the order and the
persisting refusal (§2.4); the message (§2.5); the facts and the trail (§2.6); the shared lockout (§2.7);
one release window and `/v1` (§2.8). Left to the implementer, within those: the enum's name and home,
whether the act's verification generalizes `submitAuthResponse()` or sits beside it (§3.3), the names of
the index and the constraint, and the trail's wording for a decline's verification.

## 5. Verification

Harness: the ephemeral lane (`make -C ../f5sign-infra wt-backend src=$(pwd)`) from a worktree, or the
main stack from the main checkout, full suite through `test-runner`, and the harness named with every
green run.

- **One case per refusal** of ADR-0075 §2.1's table, on the commit, the decline and the machine signature
  route. Each sabotaged by deleting its guard, checking **which** refusal then fires: the lockout and
  expiry guards sit in series with the code check, and a case meant for one must not be answered by the
  other (the repo's authoring rule 4; build each fixture so only its own guard can refuse it, e.g. a live
  challenge for the misbound case).
- **The persisting refusal**, at the `Integration/` tier where the unit of work is real: a wrong code on
  each act leaves the attempt row and the charged budget on a fresh read, and no act. Sabotage: return
  the refusal as a throw instead of inside the `Ok`; the charge must disappear. ⚠ **This test leaves DAMA**
  (`#[SkipDatabaseRollback]`, precedents `tests/F5Sign/Integration/AuthHardLockCrossingTest.php` and
  [`ProbesRowLocks`](../../tests/F5Sign/Support/ProbesRowLocks.php)) and cleans its own rows: what it asserts
  is what a committed unit leaves for a later read, and under DAMA's one static connection a fresh read and
  the unit's own writes are the same transaction.
- **The session lock covers the act**, with [`ProbesRowLocks`](../../tests/F5Sign/Support/ProbesRowLocks.php):
  the `Integration/` tier runs one connection under DAMA, so a lock taken outside `own()` and one taken
  inside it read the same there; the test is `#[SkipDatabaseRollback]` for the same reason, with its own
  cleanup. ⚑ **It needs a probe hook inside the unit**: the probe asks a second database session for the row
  at the moment the act reaches the admission, through an Envelope command port whose admission probes and
  then refuses, so nothing commits. Sabotage: move `findLockedForUpdate()` ahead of `own()`; the probe must
  go red. Run it on the machine commit too, which this task rewrites. ⚠ **That probe does not close
  [`BL-215`](../BACKLOG.md)**: the row asks for two *concurrent delegated calls* producing one signature, one
  `ConsentRecorded` and one `SignatureCommitted`, which needs a second process, and the probe shows the lock
  is held, not that two calls serialize. The row stays open with this as evidence beside it.
- **The rolled-back refusal**: right code, refused admission (a missing required field on the commit;
  a closed leg on the decline) → the challenge is neither verified nor consumed, nothing is charged, and
  the same code then succeeds.
- **The retry after success**: the same commit and the same decline sent twice; the second answers the
  closed state and charges nothing.
- **Guards before the code**: a commit with no consent and a wrong code answers the consent refusal and
  charges nothing; the same for a role that may not decline.
- **Each act's own code**: a live `SIGN` code on the decline is refused, and the mirror; both live
  together, each act succeeds with its own.
- **Route 5 and its twin** refuse a signing-gate submission and record no attempt.
- **The second holder**, over HTTP: two credentials from two opens of the same neutral-gated link; the
  first asks for a `SIGN` code; the second declines without a code, then with a guessed one; both refused,
  the guess charged, the envelope live.
- **`ACCESS_CODE`**, both acts: open, verify and consume in one unit; a wrong code leaves no verified row.
- **Per-act issuance**: ensure for the same act returns the open challenge and sends nothing; the other
  act's code is minted beside it; the minimum interval is per act; at the access gate `act` is ignored
  and the answer says `act: null`.
- **The machine-driven ceremony**, over HTTP: the twin of route 4 with `act: DECLINE`, then
  `/signing/decline` with the code; the twin with `SIGN`, then the machine signature route with the code.
- **The lockout**: wrong codes on the acts reach both tiers; a hard-locked recipient's act is refused
  before the code is read; after the sender's unlock it succeeds. Sabotage: drop `clearSupersededLockout()`
  from the act's prelude; the post-unlock case must go red.
- **The role census** over `Role::cases()`: every role `mayDecline()` admits is asked the gate, a fixture
  per role, failing on an unclassified member. Include `CERTIFIED_DELIVERY`.
- **No signing gate**: both acts succeed with no code, and with a stray one.
- **The migration**: on a database holding a verified-and-unspent `SIGNING` row written before it, the
  commit after it asks for the code, checks it against that row and consumes it; the check constraint
  refuses an `ACCESS` row with an act and a `SIGNING` row without one; the new index admits one live row
  per act and refuses a second for the same act; `SchemaConformanceTest` stays green.
- **The copy**: the decline purpose renders in `en` and `es`, both channels; the SMS is one segment; the
  stated expiry equals the TTL; `purposeFor()` refuses a signing request with no act; an undeliverable
  decline code records a failed delivery.
- **Closed key sets** on the four facts' payloads, and a decode of each from a stored fact without `act`.
- **The trail**: a declining party's trail names the act on their verification and code sent, and a
  signing party's is unchanged; a trail built from facts written before this task reads as today. If the
  act gets a label map in `trail.typ`, add it to `TypstTrailRendererTest`'s map of label groups to
  `::cases()`, so a new act fails there unlabelled.
- **The delivery bar**, over HTTP.

## 6. Open follow-ups (track, don't solve here)

- **A method whose proof cannot travel on a request** (`EUDI_WALLET`, `DNIE_NFC`) will need its own
  record for an intermediate state (ADR-0075 §2.9). Nothing to file until one is wired.
- **The `/v1` premise** (ADR-0075 §2.8) expires the day an integrator drives the machine ceremony against
  a live deployment; whoever wires the first one re-reads it.
- **The machine signature route trusts any session the recipient's access gate opened** ([`BL-367`](../BACKLOG.md)).
  This task made ADR-0055 §2.11's relayed act reachable over HTTP (the assertion members are optional). The use
  case finds the recipient's session without checking which surface opened it, so for a platform recipient with
  **no** signing gate whose session a human opened in the signer and took through the access gate, an integrator
  holding the machine key can complete the act with no code. ⚑ **Maintainer decision, 2026-10-06: keep it as
  is and record it** for a possible later improvement, for example accepting a relayed act only on a session the
  machine surface opened.
- **A neutral access gate is impassable over the machine surface, for every method** ([`BL-368`](../BACKLOG.md)).
  Pre-existing, found again by this task and not caused by it. Fixing it needs a decision first: what admission
  a machine-opened session behind a neutral gate records.
- **`IssueAuthChallengeUseCase` opens the machine session outside a unit of work** (autocommit), while the new
  twin of route 5 does it inside `own()` ([`BL-369`](../BACKLOG.md)). Two siblings that differ: a decision or a
  bug in one of them, not yet found out.
- **[`BL-215`](../BACKLOG.md) stays open**: the test of two concurrent delegated calls was not built; the lock
  probe of §5 stands beside it as evidence.

## 7. Deviations & honest notes

### Scope
- None outside what §3 names. Files the validation gate listed as undeclared are consequences of the scope:
  `config/packages/nelmio_api_doc.yaml`, `config/services.yaml`, `templates/notification/auth-otp.html.twig`,
  the `SignatureExecution` integration tests and `tests/Fixtures/audit-trail/*.json`. `migrations/Version20260818000007.php`
  was edited for its docblock only.

### Decisions made during implementation
- `SigningSession::answerSigningGate()` is a sibling returning `?DomainException`, not a generalization of
  `submitAuthResponse()`: the persist-or-roll-back split lives in the return type, and route 5's path stays the
  access gate's.
- The answered challenge is held in memory for the unit and never rehydrated, so a persisted verified row (the
  old flow's) can never be spent without the code.
- A challenge bound to another set is refused before the compare, charging nothing.
- Machine `ACCESS_CODE`: the act alone opening the session would only have turned a 404 into a 409; the gap that
  broke the contract was the twin of route 5, which could not find a session without a prior call to the twin of
  route 4. It now opens the session for a machine caller, mirroring the twin of route 4.
- The machine signature route's assertion members are optional in the request, because ADR-0055 §2.11's relayed act
  was unreachable over HTTP; `672d8892` refuses a stray asserted member as an assertion. This is the change `BL-367` records.
- A guess with no live `DECLINE` code answers `AUTH_NO_OPEN_CHALLENGE` and is not charged; once a code exists a
  guess is charged. Pinned that way against the delivery bar's wording.
- The act rolls back a no-live-code or expired refusal (no attempt row), unlike route 5; stated in §3.3.
- `4d9805a5`: the twin of route 5 declared no `423` or `429` while its prose promised the same lockout. Declared
  there; no row needed.

### Decisions that needed an ADR
- ADR-0075, agreed by the maintainer on 2026-10-06; moved to `Accepted` the same day on the maintainer's OK, after
  the full suite went green at `009cbcfa`.

### Declared and unproven properties
- Two concurrent delegated calls producing one signature (`BL-215`): needs a second process. The lock probe shows
  the lock is held at the admission, not that two calls serialize.
- A race of a decline against a commit rests on `findLockedForUpdate()` and the one-connection integration suite.

### Debt left behind, and where it lives now
- The machine route's trust model: §6 and `BL-367`.
- The neutral access gate over the machine surface: §6 and `BL-368`.
- The unit-of-work difference between the two machine siblings: §6 and `BL-369`.
- `BL-215`: still open, row updated.
- `BL-159` and `BL-197`: rows updated for tense, closed by this branch and not merged.
- Methods whose proof cannot travel on a request, and the `/v1` premise: §6.

### ADR-0075: proposal to move it to `Accepted` (applied 2026-10-06)
Proposed for the maintainer, and accepted by them the same day: ADR-0075 moves from `Proposed` to `Accepted` because it is exercised by
the tests named in its §5 (`SigningSessionGateOnTheActTest`, `SigningGateOnTheActUnitOfWorkTest`,
`SigningGateOnTheActHttpTest`, `AuthChallengeConstraintTest`), the use cases' tests and the trail tests, all green
in the full run at `0f1aa3d6`. Its `Enforced by` (§5) and `Realized in` (§6) already name those artifacts, and
§5 states what is held by review alone (§2.9). On acceptance, the same changeset sets the header `Status` to
`Accepted`, replaces the README index row's "`Proposed` ... turns `Accepted` when its bars go green" with
`Accepted (2026-10-06 or the day of the OK)`, and updates the `BL-159` / `BL-197` rows if still worded as pending.
